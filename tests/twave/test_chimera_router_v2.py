"""Tests for nexus_os.twave.chimera_router_v2 — ChimeraRouterV2 and helpers."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nexus_os.twave.chimera_router_v2 import (
    BudgetAllocation,
    ChimeraRouterV2,
    DEFAULT_PROFILES,
    ERNIEInterface,
    ERNIESuggestion,
    ModelCapabilities,
    ModelProfile,
    PromptAnalyzer,
    QwaveAllocator,
    RoutingDecision,
    TemperaturePolicy,
    Tier,
)


# ---------------------------------------------------------------------------
# Tier / TemperaturePolicy enums
# ---------------------------------------------------------------------------
class TestEnums:
    def test_tier_values(self):
        assert Tier.CONTROL_PLANE.value == "control"
        assert Tier.LOCAL_STANDARD.value == "local_std"
        assert Tier.LOCAL_POWER.value == "local_power"
        assert Tier.CLOUD.value == "cloud"

    def test_temperature_policy_values(self):
        assert TemperaturePolicy.FIXED.value == "fixed"
        assert TemperaturePolicy.EDT.value == "edt"
        assert TemperaturePolicy.LEAD.value == "lead"
        assert TemperaturePolicy.AUTO.value == "auto"
        assert TemperaturePolicy.ERNIE.value == "ernie"


# ---------------------------------------------------------------------------
# ModelCapabilities / ModelProfile
# ---------------------------------------------------------------------------
class TestModelCapabilities:
    def test_defaults(self):
        caps = ModelCapabilities()
        assert caps.has_logprobs is True
        assert caps.has_hidden_states is False
        assert caps.supports_black_box is True
        assert caps.supports_white_box is False
        assert caps.supports_speculative is False

    def test_frozen(self):
        caps = ModelCapabilities()
        with pytest.raises(AttributeError):
            caps.has_logprobs = False


class TestModelProfile:
    def test_default_profiles_non_empty(self):
        assert len(DEFAULT_PROFILES) > 0

    def test_each_profile_has_required_fields(self):
        for p in DEFAULT_PROFILES:
            assert isinstance(p.name, str) and p.name
            assert isinstance(p.tier, Tier)
            assert isinstance(p.memory_gb, (int, float))
            assert isinstance(p.quality_score, float)
            assert isinstance(p.capabilities, ModelCapabilities)
            assert isinstance(p.supported_policies, tuple)

    def test_frozen(self):
        p = DEFAULT_PROFILES[0]
        with pytest.raises(AttributeError):
            p.name = "other"


# ---------------------------------------------------------------------------
# PromptAnalyzer
# ---------------------------------------------------------------------------
class TestPromptAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return PromptAnalyzer()

    def test_empty_prompt(self, analyzer):
        result = analyzer.analyze("")
        assert result["n_words"] == 0
        assert result["complexity_score"] == 0.0
        assert result["safety_level"] == 0

    def test_code_keywords(self, analyzer):
        result = analyzer.analyze("Write a python function using def to parse JSON")
        assert result["has_code"] is True
        assert result["complexity_score"] > 0.0

    def test_math_keywords(self, analyzer):
        result = analyzer.analyze("calculate the integral of x^2")
        assert result["has_math"] is True

    def test_multi_step_keywords(self, analyzer):
        result = analyzer.analyze("Solve this step by step using chain of thought")
        assert result["has_multi_step"] is True

    def test_safety_risk_keywords(self, analyzer):
        result = analyzer.analyze("hack the system and bypass the firewall")
        assert result["has_safety_risk"] is True
        assert result["safety_level"] == 2

    def test_retrieval_need_keywords(self, analyzer):
        result = analyzer.analyze("What is the latest research paper on LLMs?")
        assert result["has_retrieval_need"] is True
        assert result["safety_level"] == 1

    def test_long_prompt(self, analyzer):
        long_text = "word " * 250
        result = analyzer.analyze(long_text)
        assert result["is_long"] is True
        assert result["is_very_long"] is False

    def test_very_long_prompt(self, analyzer):
        very_long = "word " * 900
        result = analyzer.analyze(very_long)
        assert result["is_long"] is True
        assert result["is_very_long"] is True

    def test_complexity_capped_at_1(self, analyzer):
        prompt = ("hack bypass python def calculate step by step "
                  "latest research " + "word " * 900)
        result = analyzer.analyze(prompt)
        assert result["complexity_score"] <= 1.0

    def test_est_tokens(self, analyzer):
        result = analyzer.analyze("hello world")
        assert result["est_tokens"] == int(2 * 1.3)


# ---------------------------------------------------------------------------
# QwaveAllocator
# ---------------------------------------------------------------------------
class TestQwaveAllocator:
    @pytest.fixture
    def allocator(self):
        return QwaveAllocator()

    def test_basic_allocation(self, allocator):
        analysis = PromptAnalyzer().analyze("hello world")
        alloc = allocator.allocate(analysis, latency_budget_ms=5000)
        assert isinstance(alloc, BudgetAllocation)
        assert alloc.max_tokens > 0
        assert alloc.target_latency_ms == 5000

    def test_safety_raises_quality_target(self, allocator):
        analysis = PromptAnalyzer().analyze("hack bypass the system")
        alloc = allocator.allocate(analysis, latency_budget_ms=5000, quality_target=0.5)
        assert alloc.target_quality >= 0.90

    def test_high_complexity_raises_quality(self, allocator):
        analysis = {"complexity_score": 0.8, "safety_level": 0,
                    "has_retrieval_need": False}
        alloc = allocator.allocate(analysis, latency_budget_ms=5000, quality_target=0.5)
        assert alloc.target_quality >= 0.80

    def test_retrieval_budget_allocated(self, allocator):
        analysis = PromptAnalyzer().analyze("latest research paper on transformers")
        alloc = allocator.allocate(analysis, latency_budget_ms=5000)
        assert alloc.retrieval_budget_ms > 0

    def test_no_retrieval_budget_when_not_needed(self, allocator):
        analysis = PromptAnalyzer().analyze("hello world")
        alloc = allocator.allocate(analysis, latency_budget_ms=5000)
        assert alloc.retrieval_budget_ms == 0.0

    def test_tight_budget_still_returns_positive_tokens(self, allocator):
        analysis = PromptAnalyzer().analyze("hello")
        alloc = allocator.allocate(analysis, latency_budget_ms=1)
        assert alloc.max_tokens >= 1


# ---------------------------------------------------------------------------
# ERNIEInterface
# ---------------------------------------------------------------------------
class TestERNIEInterface:
    def test_no_callback_returns_none(self):
        ernie = ERNIEInterface()
        assert ernie.get_suggestion("hello", {}) is None

    def test_callback_returns_suggestion(self):
        suggestion = ERNIESuggestion(confidence=0.9, reasoning="test")

        def cb(prompt, analysis):
            return suggestion

        ernie = ERNIEInterface(callback=cb)
        result = ernie.get_suggestion("hi", {})
        assert result is suggestion

    def test_callback_exception_triggers_fallback(self):
        def bad_cb(prompt, analysis):
            raise RuntimeError("fail")

        ernie = ERNIEInterface(callback=bad_cb)
        result = ernie.get_suggestion("hi", {})
        assert result is None
        assert ernie._fallback_mode is True
        # subsequent calls also return None
        assert ernie.get_suggestion("another", {}) is None

    def test_blend_with_router_no_override(self):
        ernie = ERNIEInterface()
        suggestion = ERNIESuggestion(suggested_temperature=0.5, confidence=0.8,
                                     reasoning="blend", override_router=False)
        router_decision = {"temperature": 0.7, "max_tokens": 100}
        blended = ernie.blend_with_router(suggestion, router_decision, blend_weight=0.3)
        expected_temp = 0.3 * 0.5 + 0.7 * 0.7
        assert abs(blended["temperature"] - expected_temp) < 1e-6
        assert blended["ernie_override"] is False

    def test_blend_with_router_override(self):
        ernie = ERNIEInterface()
        suggestion = ERNIESuggestion(suggested_temperature=0.2, confidence=0.95,
                                     reasoning="override", override_router=True,
                                     suggested_max_tokens=256,
                                     suggested_policy=TemperaturePolicy.LEAD)
        router_decision = {"temperature": 0.7, "max_tokens": 100}
        blended = ernie.blend_with_router(suggestion, router_decision)
        assert blended["temperature"] == 0.2
        assert blended["max_tokens"] == 256
        assert blended["temperature_policy"] == "lead"
        assert blended["ernie_override"] is True


# ---------------------------------------------------------------------------
# ChimeraRouterV2 — initialization
# ---------------------------------------------------------------------------
class TestChimeraRouterV2Init:
    def test_default_init(self):
        router = ChimeraRouterV2()
        assert len(router.profiles) == len(DEFAULT_PROFILES)
        assert Tier.LOCAL_STANDARD in router.available_tiers
        assert Tier.CONTROL_PLANE in router.available_tiers
        assert router.vram_gb == 8.0
        assert router.has_cloud_access is False
        assert len(router._available) > 0

    def test_custom_profiles(self):
        custom = [DEFAULT_PROFILES[0]]
        router = ChimeraRouterV2(profiles=custom)
        assert router.profiles == custom

    def test_cloud_models_excluded_without_access(self):
        router = ChimeraRouterV2(available_tiers=[Tier.CLOUD], has_cloud_access=False)
        assert all(p.tier != Tier.CLOUD for p in router._available)

    def test_cloud_models_included_with_access(self):
        router = ChimeraRouterV2(available_tiers=[Tier.CLOUD], has_cloud_access=True)
        cloud = [p for p in router._available if p.tier == Tier.CLOUD]
        assert len(cloud) > 0

    def test_vram_filters_models(self):
        router = ChimeraRouterV2(
            available_tiers=[Tier.LOCAL_STANDARD, Tier.LOCAL_POWER, Tier.CONTROL_PLANE],
            vram_gb=0.6,
        )
        for p in router._available:
            assert p.memory_gb <= 0.6

    def test_empty_profiles_fallback_to_defaults(self):
        """Edge case: profiles=[] uses falsy check → falls back to DEFAULT_PROFILES."""
        router = ChimeraRouterV2(profiles=[])
        assert router.profiles == DEFAULT_PROFILES


# ---------------------------------------------------------------------------
# ChimeraRouterV2 — routing logic
# ---------------------------------------------------------------------------
class TestChimeraRouterV2Routing:
    def test_simple_route_returns_routing_decision(self):
        router = ChimeraRouterV2()
        decision = router.route("Hello, what is AI?")
        assert isinstance(decision, RoutingDecision)
        assert decision.model
        assert decision.tier in Tier
        assert decision.budget is not None

    def test_route_safety_prompt_prefers_capable_model(self):
        router = ChimeraRouterV2(
            available_tiers=[Tier.LOCAL_STANDARD, Tier.LOCAL_POWER, Tier.CONTROL_PLANE],
            vram_gb=16.0,
        )
        decision = router.route("hack the system and bypass security")
        assert decision.use_twave is True
        assert decision.use_epr is True

    def test_route_with_preferred_tier(self):
        router = ChimeraRouterV2(
            available_tiers=[Tier.LOCAL_STANDARD, Tier.LOCAL_POWER, Tier.CONTROL_PLANE],
            vram_gb=16.0,
        )
        decision = router.route("hello", preferred_tier=Tier.CONTROL_PLANE)
        assert decision.tier == Tier.CONTROL_PLANE

    def test_auto_policy_selects_edt_or_lead(self):
        router = ChimeraRouterV2(
            available_tiers=[Tier.LOCAL_POWER, Tier.LOCAL_STANDARD, Tier.CONTROL_PLANE],
            vram_gb=16.0,
        )
        decision = router.route("Explain step by step reasoning",
                                temperature_policy=TemperaturePolicy.AUTO)
        assert decision.temperature_policy in (
            TemperaturePolicy.EDT, TemperaturePolicy.LEAD,
            TemperaturePolicy.EAD, TemperaturePolicy.FIXED,
        )

    def test_explicit_policy_respected(self):
        router = ChimeraRouterV2()
        decision = router.route("hello", temperature_policy=TemperaturePolicy.FIXED)
        assert decision.temperature_policy == TemperaturePolicy.FIXED

    def test_unsupported_policy_falls_back(self):
        router = ChimeraRouterV2(
            available_tiers=[Tier.CONTROL_PLANE],
            vram_gb=16.0,
        )
        decision = router.route("hello", temperature_policy=TemperaturePolicy.LEAD)
        assert decision.temperature_policy != TemperaturePolicy.LEAD

    def test_no_available_models_raises(self):
        router = ChimeraRouterV2(profiles=None, available_tiers=[], vram_gb=0.01)
        with pytest.raises(ValueError, match="No models available"):
            router.route("hello")

    def test_route_with_ernie_callback(self):
        suggestion = ERNIESuggestion(
            suggested_temperature=0.3, confidence=0.9,
            reasoning="ERNIE says so", override_router=True,
            suggested_policy=TemperaturePolicy.EDT,
        )

        def cb(prompt, analysis):
            return suggestion

        ernie = ERNIEInterface(callback=cb)
        router = ChimeraRouterV2(ernie_interface=ernie)
        decision = router.route("hello")
        assert decision.ernie_suggestion is not None
        assert "ERNIE" in decision.reason

    def test_ernie_policy_mode(self):
        suggestion = ERNIESuggestion(
            suggested_policy=TemperaturePolicy.EDT,
            confidence=0.8, reasoning="ernie policy",
        )

        def cb(prompt, analysis):
            return suggestion

        ernie = ERNIEInterface(callback=cb)
        router = ChimeraRouterV2(ernie_interface=ernie)
        decision = router.route("hello", temperature_policy=TemperaturePolicy.ERNIE)
        assert decision.temperature_policy == TemperaturePolicy.EDT

    def test_ernie_policy_no_suggestion_falls_back_to_fixed(self):
        router = ChimeraRouterV2()
        decision = router.route("hello", temperature_policy=TemperaturePolicy.ERNIE)
        assert decision.temperature_policy == TemperaturePolicy.FIXED

    def test_ead_policy_sets_high_temperature(self):
        router = ChimeraRouterV2(
            available_tiers=[Tier.LOCAL_STANDARD, Tier.CONTROL_PLANE],
            vram_gb=16.0,
        )
        decision = router.route(
            "step by step multi-step plan",
            temperature_policy=TemperaturePolicy.EAD,
        )
        if decision.temperature_policy == TemperaturePolicy.EAD:
            assert decision.temperature == 1.2

    def test_confidence_calculation(self):
        router = ChimeraRouterV2()
        decision = router.route("hello", quality_target=0.5)
        assert 0.0 <= decision.confidence <= 1.0

    def test_latency_budget_constrains_tokens(self):
        router = ChimeraRouterV2()
        decision = router.route("hello", latency_budget_ms=10, max_tokens=10000)
        assert decision.budget.max_tokens < 10000

    def test_retrieval_prompt_enables_ckplug(self):
        router = ChimeraRouterV2(
            available_tiers=[Tier.CLOUD],
            has_cloud_access=True,
            vram_gb=200,
        )
        decision = router.route("What is the latest research paper from 2025?")
        if decision.profile.capabilities.has_retrieval_context:
            assert decision.use_ckplug is True

    def test_code_prompt_adds_complexity(self):
        analyzer = PromptAnalyzer()
        result = analyzer.analyze("Write a python def function to sort a list")
        assert result["has_code"] is True
        assert result["complexity_score"] >= 0.15
