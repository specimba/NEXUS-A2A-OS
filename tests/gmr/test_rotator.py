"""tests/gmr/test_rotator.py — GeniusModelRotator, IntentClassifier, and related tests"""
import time
import pytest

from nexus_os.gmr.rotator import (
    GeniusModelRotator, ModelProfile, ModelPool, IntentCategory,
    IntentClassifier, CircuitBreaker, GMRSelection,
)
from nexus_os.gmr.telemetry import ModelTelemetry


class MockTelemetryIngest:
    def __init__(self):
        self.cache = {
            "osman-coder": ModelTelemetry("osman-coder", "ollama", 40, 50, 1.0, "up", "now"),
            "Trinity Large Preview": ModelTelemetry("Trinity Large Preview", "opencode", 97, 1707, 1.0, "up", "now"),
            "Devstral 2 123B": ModelTelemetry("Devstral 2 123B", "nvidia", 86, 542, 1.0, "up", "now"),
        }

    def fetch(self):
        return self.cache


def make_gmr():
    gmr = GeniusModelRotator()
    gmr.telemetry = MockTelemetryIngest()
    gmr._sync_profiles()
    return gmr


class TestIntentClassifier:
    def test_classify_code(self):
        assert IntentClassifier.classify("fix the function bug") == IntentCategory.CODE

    def test_classify_research(self):
        assert IntentClassifier.classify("research the literature on transformers") == IntentCategory.RESEARCH

    def test_classify_reasoning(self):
        assert IntentClassifier.classify("plan an optimization strategy") == IntentCategory.REASONING

    def test_classify_speed(self):
        assert IntentClassifier.classify("quick summarize this list") == IntentCategory.SPEED

    def test_classify_security(self):
        assert IntentClassifier.classify("audit the vulnerability risk") == IntentCategory.SECURITY

    def test_classify_general_for_unknown(self):
        assert IntentClassifier.classify("hello world") == IntentCategory.GENERAL

    def test_metadata_boosts_code(self):
        result = IntentClassifier.classify("do something", {"is_code_task": True})
        assert result == IntentCategory.CODE

    def test_metadata_boosts_reasoning(self):
        result = IntentClassifier.classify("do something", {"requires_deep_reasoning": True})
        assert result == IntentCategory.REASONING

    def test_metadata_boosts_speed(self):
        result = IntentClassifier.classify("do something", {"time_sensitive": True})
        assert result == IntentCategory.SPEED


class TestCircuitBreakerSimple:
    """Tests for the simple CircuitBreaker in rotator.py (not AdaptiveCircuitBreaker)."""

    def test_initial_no_failures(self):
        cb = CircuitBreaker()
        assert not cb.should_open("m1")

    def test_two_failures_not_tripped(self):
        cb = CircuitBreaker()
        cb.record_failure("m1")
        cb.record_failure("m1")
        assert not cb.should_open("m1")

    def test_three_failures_trips(self):
        cb = CircuitBreaker()
        for _ in range(3):
            cb.record_failure("m1")
        assert cb.should_open("m1")

    def test_reset_clears_state(self):
        cb = CircuitBreaker()
        for _ in range(3):
            cb.record_failure("m1")
        cb.reset("m1")
        assert not cb.should_open("m1")

    def test_independent_models(self):
        cb = CircuitBreaker()
        for _ in range(3):
            cb.record_failure("m1")
        assert not cb.should_open("m2")

    def test_cooldown_expires(self):
        cb = CircuitBreaker()
        for _ in range(3):
            cb.record_failure("m1")
        cb._cooldowns["m1"] = time.time() - 1
        assert not cb.should_open("m1")


class TestModelProfile:
    def test_positional_args(self):
        mp = ModelProfile("test", "nvidia", 5.0, 8192, ["code"], 500, False, 0.95)
        assert mp.name == "test"
        assert mp.provider == "nvidia"
        assert mp.cost_per_million == 5.0
        assert mp.context_window == 8192
        assert mp.is_local is False

    def test_kwargs(self):
        mp = ModelProfile(name="test", provider="ollama", cost_per_1m=0.0)
        assert mp.name == "test"
        assert mp.cost_per_million == 0.0

    def test_is_available_always_true(self):
        mp = ModelProfile("t", "p")
        assert mp.is_available()

    def test_pool_auto_assignment_local(self):
        mp = ModelProfile(name="m", provider="ollama", is_local=True, cost_per_million=0)
        assert mp.pool == ModelPool.FAST

    def test_pool_auto_assignment_premium(self):
        mp = ModelProfile(name="m", provider="nvidia", is_local=False, cost_per_million=5.0)
        assert mp.pool == ModelPool.PREMIUM


class TestGMRSelection:
    def test_fields(self):
        sel = GMRSelection(
            primary="m1", fallbacks=["m2"], reason="test",
            budget_remaining=100000, tier_used=40,
        )
        assert sel.primary == "m1"
        assert sel.tier_used == 40


class TestGeniusModelRotator:
    def test_register_from_mapping_populates_models(self):
        gmr = GeniusModelRotator()
        assert len(gmr.models) > 0

    def test_select_reasoning_domain(self):
        gmr = make_gmr()
        sel = gmr.select("reasoning", budget_remaining=200000)
        assert sel.primary is not None
        assert isinstance(sel.fallbacks, list)

    def test_select_fast_domain(self):
        gmr = make_gmr()
        sel = gmr.select("fast", budget_remaining=100000)
        assert sel.primary is not None

    def test_select_security_domain(self):
        gmr = make_gmr()
        sel = gmr.select("security", budget_remaining=200000)
        assert sel.primary is not None

    def test_select_general_domain(self):
        gmr = make_gmr()
        sel = gmr.select("general", budget_remaining=100000)
        assert sel.primary is not None

    def test_low_budget_forces_fast_pool_selection(self):
        gmr = make_gmr()
        # budget < 50k triggers _select_pool to return FAST
        # No research models are in FAST pool, so cascade empties
        # and falls back to domain fallback_chain
        sel = gmr.select("research", budget_remaining=10000)
        assert sel.primary is not None
        # The primary comes from the research domain's fallback_chain
        from nexus_os.gmr.domain_mapping import DOMAIN_MAPPING
        research_fallbacks = DOMAIN_MAPPING["research"]["fallback_chain"]
        assert sel.primary in research_fallbacks or sel.primary in [
            m["model"] for m in DOMAIN_MAPPING["research"]["primary"]
        ]

    def test_get_routing_cascade_returns_tuple(self):
        gmr = make_gmr()
        cascade, context = gmr.get_routing_cascade(prompt="fix the code bug")
        assert isinstance(cascade, list)
        assert len(cascade) <= 3
        assert context.intent == "code"

    def test_get_routing_cascade_auto_classifies_intent(self):
        gmr = make_gmr()
        _, context = gmr.get_routing_cascade(prompt="research the literature on AI safety")
        assert context.intent == "research"

    def test_get_routing_cascade_respects_explicit_intent(self):
        gmr = make_gmr()
        _, context = gmr.get_routing_cascade(
            prompt="hello", intent=IntentCategory.SECURITY,
        )
        assert context.intent == "security"

    def test_execute_with_fallback_success(self):
        gmr = make_gmr()
        for m in gmr.models.values():
            m.record_failure = lambda: None
            m.reset_failure_count = lambda: None

        def mock_execute(model, prompt, context):
            return {"success": True, "output": "done", "tokens_used": 100}

        result = gmr.execute_with_fallback("test prompt", mock_execute)
        assert result["success"] is True
        assert "model_used" in result
        assert result["fallback_count"] == 0

    def test_execute_with_fallback_all_fail(self):
        gmr = make_gmr()
        for m in gmr.models.values():
            m.record_failure = lambda: None
            m.reset_failure_count = lambda: None

        def mock_execute(model, prompt, context):
            return {"success": False, "error": "fail"}

        result = gmr.execute_with_fallback("test prompt", mock_execute)
        assert result["success"] is False

    def test_execute_with_fallback_uses_second_model(self):
        gmr = make_gmr()
        for m in gmr.models.values():
            m.record_failure = lambda: None
            m.reset_failure_count = lambda: None
        call_count = {"n": 0}

        def mock_execute(model, prompt, context):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {"success": False, "error": "timeout"}
            return {"success": True, "output": "ok", "tokens_used": 50}

        result = gmr.execute_with_fallback("test prompt", mock_execute)
        assert result["success"] is True
        assert result["fallback_count"] >= 1

    def test_execute_with_fallback_handles_exception(self):
        gmr = make_gmr()
        for m in gmr.models.values():
            m.record_failure = lambda: None
            m.reset_failure_count = lambda: None

        def mock_execute(model, prompt, context):
            raise RuntimeError("connection lost")

        result = gmr.execute_with_fallback("test prompt", mock_execute)
        assert result["success"] is False
        assert "connection lost" in result["error"]


class TestKnownProductionBugs:
    """Regression tests documenting pre-existing bugs in production code.
    These tests verify the *current* (buggy) behavior so they break when fixed.
    """

    def test_sync_profiles_overwrites_cost_with_tier(self):
        """BUG: _sync_profiles sets cost_per_million = float(tel.tier)
        instead of preserving the actual cost. See rotator.py:211."""
        gmr = GeniusModelRotator()
        gmr.telemetry = MockTelemetryIngest()
        # Before sync, osman-coder has cost 0 from domain mapping
        original_cost = gmr.models.get("osman-coder")
        if original_cost:
            assert original_cost.cost_per_million == 0.0
        gmr._sync_profiles()
        synced = gmr.models.get("osman-coder")
        if synced:
            # After sync, cost is incorrectly set to tier value (40)
            assert synced.cost_per_million == 40.0  # BUG: should remain 0.0

    def test_speed_intent_value_mismatches_domain_key(self):
        """BUG: IntentCategory.SPEED.value is 'speed' but DOMAIN_MAPPING
        uses 'fast' as the key. The fallback path in get_routing_cascade
        uses intent.value, so SPEED fallbacks are never found."""
        from nexus_os.gmr.domain_mapping import DOMAIN_MAPPING
        assert IntentCategory.SPEED.value == "speed"
        assert "speed" not in DOMAIN_MAPPING  # BUG: should match
        assert "fast" in DOMAIN_MAPPING

    def test_model_profile_missing_record_failure_method(self):
        """BUG: ModelProfile.__getattr__ returns None for record_failure
        and reset_failure_count, causing TypeError in
        execute_with_fallback. See rotator.py:427,451,455."""
        mp = ModelProfile("test", "p")
        assert mp.record_failure is None  # BUG: should be a callable
        with pytest.raises(TypeError):
            mp.record_failure()
