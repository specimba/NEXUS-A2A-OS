"""Tests for nexus_os.relay.model_relay_adapter — ChimeraRouter⇄ModelRelay adapter.

Covers:
    - RelayRequest / RelayResult dataclasses
    - ModelRelayAdapter 3-tier fallback (primary → godmode → python relay)
    - execute_decision() convenience function
    - ChimeraRouterV2.execute() integration
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nexus_os.relay.model_relay_adapter import (
    ModelRelayAdapter,
    RelayRequest,
    RelayResult,
    execute_decision,
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

class TestRelayRequest:
    def test_basic_fields(self):
        req = RelayRequest(
            model="qwen2.5-7b",
            prompt="hello",
            temperature=0.5,
            max_tokens=128,
            relay_url="http://localhost:7350",
            metadata={"category": "test"},
        )
        assert req.model == "qwen2.5-7b"
        assert req.prompt == "hello"
        assert req.temperature == 0.5
        assert req.max_tokens == 128
        assert req.metadata["category"] == "test"

    def test_defaults(self):
        req = RelayRequest(model="test-model", prompt="hi", relay_url="")
        assert req.temperature == 0.7
        assert req.max_tokens == 512
        assert req.metadata == {}

    def test_frozen(self):
        req = RelayRequest(model="m", prompt="p", relay_url="")
        with pytest.raises(AttributeError):
            req.model = "other"


class TestRelayResult:
    def test_basic_fields(self):
        result = RelayResult(
            status="ok",
            provider="qwen2.5-7b",
            model="qwen2.5-7b",
            used_fallback=False,
            latency_ms=42.5,
            raw="response text",
        )
        assert result.status == "ok"
        assert result.provider == "qwen2.5-7b"
        assert result.used_fallback is False
        assert result.latency_ms == 42.5
        assert result.raw == "response text"
        assert result.attempts == []

    def test_frozen(self):
        result = RelayResult(status="ok", provider="p", model="m", used_fallback=False, latency_ms=0.0)
        with pytest.raises(AttributeError):
            result.status = "error"


# ---------------------------------------------------------------------------
# ModelRelayAdapter
# ---------------------------------------------------------------------------

class TestModelRelayAdapterInit:
    def test_defaults_from_env(self):
        import nexus_os.relay.model_relay_adapter as mod
        old_node = mod.os.environ.get("NODERELAY_PORT")
        old_god = mod.os.environ.get("GODMODE_PORT")
        old_py = mod.os.environ.get("PYTHONRELAY_PORT")
        try:
            mod.os.environ["NODERELAY_PORT"] = "7350"
            mod.os.environ["GODMODE_PORT"] = "7357"
            mod.os.environ["PYTHONRELAY_PORT"] = "7355"
            adapter = ModelRelayAdapter()
            assert "7350" in adapter.primary_url
            assert "7357" in adapter.godmode_url
            assert "7355" in adapter.fallback_url
        finally:
            if old_node is not None:
                mod.os.environ["NODERELAY_PORT"] = old_node
            elif "NODERELAY_PORT" in mod.os.environ:
                del mod.os.environ["NODERELAY_PORT"]
            if old_god is not None:
                mod.os.environ["GODMODE_PORT"] = old_god
            elif "GODMODE_PORT" in mod.os.environ:
                del mod.os.environ["GODMODE_PORT"]
            if old_py is not None:
                mod.os.environ["PYTHONRELAY_PORT"] = old_py
            elif "PYTHONRELAY_PORT" in mod.os.environ:
                del mod.os.environ["PYTHONRELAY_PORT"]

    def test_explicit_urls(self):
        adapter = ModelRelayAdapter(
            primary_url="http://primary:1111",
            fallback_url="http://fallback:2222",
            godmode_url="http://god:3333",
        )
        assert adapter.primary_url == "http://primary:1111"
        assert adapter.fallback_url == "http://fallback:2222"
        assert adapter.godmode_url == "http://god:3333"

    def test_timeout(self):
        adapter = ModelRelayAdapter(timeout_seconds=5)
        assert adapter.timeout_seconds == 5


class TestModelRelayAdapterExecute:
    @pytest.fixture
    def relay_req(self):
        return RelayRequest(
            model="test-model",
            prompt="hello world",
            temperature=0.7,
            max_tokens=50,
            relay_url="http://localhost:7350",
        )

    @patch.object(ModelRelayAdapter, "_call_chat")
    def test_primary_success(self, mock_call, relay_req):
        mock_call.return_value = ("ok", "test-model", "hello from relay")
        adapter = ModelRelayAdapter()
        result = adapter.execute(relay_req)
        assert result.status == "ok"
        assert result.provider == "test-model"
        assert result.used_fallback is False
        assert result.raw == "hello from relay"
        assert len(result.attempts) == 1
        assert result.attempts[0]["tier"] == "primary"

    @patch.object(ModelRelayAdapter, "_call_chat")
    def test_primary_fails_godmode_succeeds(self, mock_call, relay_req):
        mock_call.side_effect = [
            Exception("connection refused"),
            ("ok", "god-routed-model", "hello from godmode"),
        ]
        adapter = ModelRelayAdapter()
        result = adapter.execute(relay_req)
        assert result.status == "ok"
        assert result.provider == "god-routed-model"
        assert result.used_fallback is False
        assert len(result.attempts) == 2
        assert result.attempts[0]["status"].startswith("error")
        assert result.attempts[1]["tier"] == "godmode"

    @patch.object(ModelRelayAdapter, "_call_chat")
    def test_primary_godmode_fail_fallback_succeeds(self, mock_call, relay_req):
        mock_call.side_effect = [
            Exception("primary down"),
            Exception("godmode down"),
            ("ok", "fallback-model", "hello from fallback"),
        ]
        adapter = ModelRelayAdapter()
        result = adapter.execute(relay_req)
        assert result.status == "ok"
        assert result.provider == "fallback-model"
        assert result.used_fallback is True
        assert len(result.attempts) == 3

    @patch.object(ModelRelayAdapter, "_call_chat")
    def test_all_fail(self, mock_call, relay_req):
        mock_call.side_effect = [
            Exception("primary down"),
            Exception("godmode down"),
            Exception("fallback down"),
        ]
        adapter = ModelRelayAdapter()
        result = adapter.execute(relay_req)
        assert result.status == "error:both_failed"
        assert result.provider == "none"
        assert result.used_fallback is True
        assert result.raw is None
        assert len(result.attempts) == 3
        for attempt in result.attempts:
            assert attempt["status"].startswith("error")

    @patch.object(ModelRelayAdapter, "_call_chat")
    def test_status_error_not_ok_counts_as_failure(self, mock_call, relay_req):
        mock_call.side_effect = [
            ("error:HTTPError", "unknown", None),
            ("ok", "god-model", "recovered"),
        ]
        adapter = ModelRelayAdapter()
        result = adapter.execute(relay_req)
        assert result.status == "ok"
        assert result.provider == "god-model"
        assert len(result.attempts) == 2


class TestModelRelayAdapterCallChat:
    def test_builds_openai_payload(self):
        """Test that _call_chat constructs the correct OpenAI-compatible payload."""
        adapter = ModelRelayAdapter(timeout_seconds=5)

        captured_request = {}

        class FakeResponse:
            def __init__(self, body):
                self._body = body

            def read(self):
                return self._body.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        def fake_urlopen(req, timeout):
            captured_request["url"] = req.full_url
            captured_request["method"] = req.get_method()
            captured_request["data"] = json.loads(req.data.decode("utf-8"))
            captured_request["timeout"] = timeout
            return FakeResponse(json.dumps({
                "choices": [{"message": {"content": "hello"}}],
                "model": "actual-model",
            }))

        relay_req = RelayRequest(
            model="test-model",
            prompt="hello",
            temperature=0.3,
            max_tokens=100,
            relay_url="http://localhost:7350",
        )

        with patch("nexus_os.relay.model_relay_adapter.urllib.request.urlopen", side_effect=fake_urlopen):
            status, provider, text = adapter._call_chat(relay_req, "http://localhost:7350")

        assert status == "ok"
        assert provider == "actual-model"
        assert text == "hello"
        assert captured_request["url"] == "http://localhost:7350/v1/chat/completions"
        assert captured_request["method"] == "POST"
        assert captured_request["data"]["model"] == "test-model"
        assert captured_request["data"]["temperature"] == 0.3
        assert captured_request["data"]["max_tokens"] == 100
        assert captured_request["timeout"] == 5

    def test_malformed_response(self):
        adapter = ModelRelayAdapter()

        class FakeResponse:
            def read(self):
                return b"not json at all"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        relay_req = RelayRequest(model="m", prompt="p", relay_url="http://x")

        with patch("nexus_os.relay.model_relay_adapter.urllib.request.urlopen", return_value=FakeResponse()):
            status, provider, text = adapter._call_chat(relay_req, "http://localhost:7350")

        assert status == "error:malformed_response"
        assert provider == "unknown"
        assert text is None


# ---------------------------------------------------------------------------
# Guard enforcement: circuit breaker, RPM quota, context fit
# ---------------------------------------------------------------------------

class TestGuardEnforcement:
    @pytest.fixture
    def relay_req(self):
        return RelayRequest(model="test-model", prompt="hello", max_tokens=50)

    @patch.object(ModelRelayAdapter, "_call_chat")
    def test_open_tier_is_skipped_not_hammered(self, mock_call, relay_req):
        from nexus_os.relay.circuit_breaker import ProviderCircuitBreaker

        breaker = ProviderCircuitBreaker(failure_threshold=1)
        breaker.record_failure("relay:primary")  # trips OPEN at threshold 1
        mock_call.return_value = ("ok", "god-model", "hello")
        adapter = ModelRelayAdapter(circuit_breaker=breaker)

        result = adapter.execute(relay_req)

        assert result.status == "ok"
        assert result.attempts[0]["tier"] == "primary"
        assert result.attempts[0]["status"] == "error:circuit_open"
        assert result.attempts[1]["tier"] == "godmode"
        # _call_chat must never have been invoked for the OPEN primary tier
        called_urls = [c.args[1] for c in mock_call.call_args_list]
        assert adapter.primary_url not in called_urls

    @patch.object(ModelRelayAdapter, "_call_chat")
    def test_tier_failures_trip_breaker_per_tier(self, mock_call, relay_req):
        from nexus_os.relay.circuit_breaker import ProviderCircuitBreaker, ProviderState

        breaker = ProviderCircuitBreaker(failure_threshold=2)
        mock_call.side_effect = [
            Exception("down"), ("ok", "m", "x"),   # execute 1: primary fails
            Exception("down"), ("ok", "m", "x"),   # execute 2: primary fails again -> OPEN
        ]
        adapter = ModelRelayAdapter(circuit_breaker=breaker)
        adapter.execute(relay_req)
        adapter.execute(relay_req)

        assert breaker.state("relay:primary") == ProviderState.OPEN
        assert breaker.state("relay:godmode") == ProviderState.CLOSED

    @patch.object(ModelRelayAdapter, "_call_chat")
    def test_malformed_200_fails_over_to_next_tier(self, mock_call, relay_req):
        mock_call.side_effect = [
            ("error:malformed_response", "unknown", None),
            ("ok", "god-model", "recovered"),
        ]
        adapter = ModelRelayAdapter()
        result = adapter.execute(relay_req)
        assert result.status == "ok"
        assert result.provider == "god-model"
        assert result.attempts[0]["status"] == "error:malformed_response"

    @patch.object(ModelRelayAdapter, "_call_chat")
    def test_rpm_exhausted_returns_error_without_dispatch(self, mock_call, relay_req):
        from nexus_os.relay.quota import SlidingWindowRPMTracker

        tracker = SlidingWindowRPMTracker(rpm_limit=2)
        tracker.record_request()
        tracker.record_request()
        adapter = ModelRelayAdapter(rpm_tracker=tracker)

        result = adapter.execute(relay_req)

        assert result.status == "error:rpm_exhausted"
        assert result.attempts[0]["tier"] == "rpm_guard"
        assert result.attempts[0]["retry_after_seconds"] > 0
        mock_call.assert_not_called()

    @patch.object(ModelRelayAdapter, "_call_chat")
    def test_rpm_pacing_sleeps_briefly(self, mock_call, relay_req):
        from nexus_os.relay.quota import SlidingWindowRPMTracker

        tracker = SlidingWindowRPMTracker(rpm_limit=10, backoff_threshold=0.5)
        for _ in range(6):  # 60% > 50% threshold -> proactive backoff
            tracker.record_request()
        mock_call.return_value = ("ok", "m", "x")
        adapter = ModelRelayAdapter(rpm_tracker=tracker)

        with patch("nexus_os.relay.model_relay_adapter.time.sleep") as mock_sleep:
            result = adapter.execute(relay_req)

        assert result.status == "ok"
        mock_sleep.assert_called_once()
        assert 0 < mock_sleep.call_args.args[0] <= ModelRelayAdapter.MAX_PACING_SLEEP_SECONDS
        # dispatched request must be counted in the window
        assert tracker.state()["current_count"] == 7

    @patch.object(ModelRelayAdapter, "_call_chat")
    def test_context_overflow_fails_without_dispatch(self, mock_call):
        # zai-org/GLM-5 window is 32,768; ~50K-token prompt cannot fit.
        req = RelayRequest(model="zai-org/GLM-5", prompt="x" * 200_000, max_tokens=512)
        adapter = ModelRelayAdapter()
        result = adapter.execute(req)
        assert result.status == "error:context_overflow"
        assert result.attempts == []
        mock_call.assert_not_called()

    @patch.object(ModelRelayAdapter, "_call_chat")
    def test_completion_budget_clamped_to_window(self, mock_call):
        # ~25K-token prompt in the 32,768 window leaves < 30K completion room.
        prompt = "x" * 100_000  # ~25K estimated tokens
        req = RelayRequest(model="zai-org/GLM-5", prompt=prompt, max_tokens=30_000)
        mock_call.return_value = ("ok", "m", "x")
        adapter = ModelRelayAdapter()

        result = adapter.execute(req)

        assert result.status == "ok"
        sent_request = mock_call.call_args.args[0]
        est_input = len(prompt.encode("utf-8")) // 4
        assert sent_request.max_tokens == 32_768 - est_input - 100
        assert sent_request.max_tokens < 30_000


# ---------------------------------------------------------------------------
# execute_decision convenience
# ---------------------------------------------------------------------------

class TestExecuteDecision:
    def test_creates_request_from_decision(self):
        decision = MagicMock()
        decision.model = "routed-model"
        decision.temperature = 0.5
        decision.budget.max_tokens = 200
        decision.temperature_policy.value = "edt"

        adapter = MagicMock()
        adapter.execute.return_value = RelayResult(
            status="ok", provider="routed-model", model="routed-model",
            used_fallback=False, latency_ms=10.0, raw="ok",
        )

        result = execute_decision(decision, "test prompt", adapter=adapter)
        assert result.status == "ok"
        # Verify the adapter was called with the correct request
        call_args = adapter.execute.call_args[0][0]
        assert call_args.model == "routed-model"
        assert call_args.prompt == "test prompt"
        assert call_args.temperature == 0.5
        assert call_args.max_tokens == 200
        assert call_args.metadata["policy"] == "edt"

    def test_default_adapter_created(self):
        decision = MagicMock()
        decision.model = "m"
        decision.temperature = 0.7
        decision.budget.max_tokens = 10
        decision.temperature_policy.value = "fixed"

        with patch.object(ModelRelayAdapter, "execute") as mock_exec:
            mock_exec.return_value = RelayResult(
                status="ok", provider="m", model="m",
                used_fallback=False, latency_ms=1.0, raw="x",
            )
            result = execute_decision(decision, "prompt")
            assert result.status == "ok"


# ---------------------------------------------------------------------------
# ChimeraRouterV2.execute() integration
# ---------------------------------------------------------------------------

class TestChimeraRouterExecute:
    def test_execute_returns_relay_result(self):
        from nexus_os.twave.chimera_router_v2 import ChimeraRouterV2, Tier

        router = ChimeraRouterV2(
            has_cloud_access=False,
            available_tiers=[Tier.CONTROL_PLANE, Tier.LOCAL_STANDARD, Tier.LOCAL_POWER],
        )
        decision = router.route("hello world", latency_budget_ms=2000, quality_target=0.60)

        mock_adapter = MagicMock()
        mock_adapter.execute.return_value = RelayResult(
            status="ok", provider=decision.model, model=decision.model,
            used_fallback=False, latency_ms=5.0, raw="test response",
        )

        result = router.execute("hello world", decision=decision, adapter=mock_adapter)
        assert result.status == "ok"
        assert result.raw == "test response"
        # Verify the adapter was called
        mock_adapter.execute.assert_called_once()

    def test_execute_routes_first_if_no_decision(self):
        from nexus_os.twave.chimera_router_v2 import ChimeraRouterV2, Tier

        router = ChimeraRouterV2(
            has_cloud_access=False,
            available_tiers=[Tier.CONTROL_PLANE, Tier.LOCAL_STANDARD, Tier.LOCAL_POWER],
        )
        mock_adapter = MagicMock()
        mock_adapter.execute.return_value = RelayResult(
            status="ok", provider="p", model="m",
            used_fallback=False, latency_ms=1.0, raw="response",
        )

        result = router.execute("test prompt", adapter=mock_adapter)
        assert result.status == "ok"
        # The adapter should have been called with a RelayRequest
        call_req = mock_adapter.execute.call_args[0][0]
        assert call_req.prompt == "test prompt"


# ---------------------------------------------------------------------------
# Resilience tier limits (Hermes's contribution)
# ---------------------------------------------------------------------------

class TestResilienceTierLimits:
    def test_router_has_tier_limits(self):
        from nexus_os.twave.chimera_router_v2 import ChimeraRouterV2

        router = ChimeraRouterV2()
        assert hasattr(router, "_resilience_tier_limits")
        assert "hotTier" in router._resilience_tier_limits
        assert "coldTier" in router._resilience_tier_limits
        assert "thermalTier" in router._resilience_tier_limits

    def test_hot_tier_values(self):
        from nexus_os.twave.chimera_router_v2 import ChimeraRouterV2

        router = ChimeraRouterV2()
        hot = router._resilience_tier_limits["hotTier"]
        assert hot["latMs"] == 4500.0
        assert hot["retries"] == 4
        assert hot["timegapSeconds"] == 5.0

    def test_router_has_recent_routes(self):
        from nexus_os.twave.chimera_router_v2 import ChimeraRouterV2

        router = ChimeraRouterV2()
        assert hasattr(router, "_recent_routes")
        assert isinstance(router._recent_routes, list)

    def test_route_records_recent_route(self):
        from nexus_os.twave.chimera_router_v2 import ChimeraRouterV2, Tier

        router = ChimeraRouterV2(
            has_cloud_access=False,
            available_tiers=[Tier.CONTROL_PLANE, Tier.LOCAL_STANDARD, Tier.LOCAL_POWER],
        )
        assert len(router._recent_routes) == 0
        router.route("test prompt", latency_budget_ms=2000, quality_target=0.60)
        assert len(router._recent_routes) == 1

    def test_recent_routes_capped_at_32(self):
        from nexus_os.twave.chimera_router_v2 import ChimeraRouterV2, Tier

        router = ChimeraRouterV2(
            has_cloud_access=False,
            available_tiers=[Tier.CONTROL_PLANE, Tier.LOCAL_STANDARD, Tier.LOCAL_POWER],
        )
        for i in range(40):
            router.route(f"prompt {i}", latency_budget_ms=2000, quality_target=0.60)
        assert len(router._recent_routes) <= 32
