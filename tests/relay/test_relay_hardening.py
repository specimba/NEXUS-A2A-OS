"""Relay hardening tests (full-audit HIGH cluster, roadmap P1-4).

Four findings in nexus_os/relay/model_relay.py:
- :471 guard pipeline failed open (guard error / ambiguous output / zero
  healthy stages all returned safe=True)
- :396 errors returned as HTTP 200 chat completions, defeating upstream
  retry/fallback
- :272 model health cached forever with the refresh loop off by default
- :991 unauthenticated 0.0.0.0 bind
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.relay import model_relay
from nexus_os.relay.model_relay import ModelRelay


@pytest.fixture
def relay(monkeypatch):
    """A relay that never touches the network during construction."""
    monkeypatch.setattr(ModelRelay, "_discover_ollama_models", lambda self: None)
    monkeypatch.setattr(ModelRelay, "_start_health_loop", lambda self: None)
    return ModelRelay()


# ── :272 health TTL ─────────────────────────────────────────────────────


class TestHealthTTL:
    def test_unhealthy_reprobes_after_negative_ttl(self, relay, monkeypatch):
        probes = []
        monkeypatch.setattr(
            ModelRelay, "_check_health",
            lambda self, m: probes.append(m) or self._model_health.setdefault(m, True),
        )
        relay._model_health["m1"] = False
        relay._health_checked_at["m1"] = time.time() - (model_relay.HEALTH_NEG_TTL_S + 1)
        relay.health_check("m1")
        assert probes == ["m1"], "expired negative entry must re-probe"

    def test_unhealthy_cached_within_negative_ttl(self, relay, monkeypatch):
        monkeypatch.setattr(
            ModelRelay, "_check_health",
            lambda self, m: pytest.fail("fresh negative entry must not re-probe"),
        )
        relay._model_health["m1"] = False
        relay._health_checked_at["m1"] = time.time()
        assert relay.health_check("m1") is False

    def test_healthy_cached_within_ttl_but_reprobed_after(self, relay, monkeypatch):
        probes = []
        monkeypatch.setattr(
            ModelRelay, "_check_health", lambda self, m: probes.append(m) or True
        )
        relay._model_health["m1"] = True
        relay._health_checked_at["m1"] = time.time()
        assert relay.health_check("m1") is True
        assert probes == []
        relay._health_checked_at["m1"] = time.time() - (model_relay.HEALTH_TTL_S + 1)
        relay.health_check("m1")
        assert probes == ["m1"]

    def test_check_health_records_timestamp(self, relay, monkeypatch):
        monkeypatch.setattr(
            model_relay.requests, "post",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")),
        )
        assert relay._check_health("gone-model") is False
        assert relay._health_checked_at["gone-model"] == pytest.approx(time.time(), abs=5)


# ── :471 guard fail-closed ──────────────────────────────────────────────


class TestGuardFailClosed:
    @pytest.mark.asyncio
    async def test_guard_stage_error_is_unsafe_vote(self, relay, monkeypatch):
        monkeypatch.setattr(
            model_relay.requests, "post",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("ollama down")),
        )
        result = await relay._classify_one("llama-guard3:1b", [{"role": "user", "content": "hi"}], 1)
        assert result["safe"] is False
        assert result.get("error") is True

    @pytest.mark.asyncio
    async def test_zero_healthy_stages_fails_closed(self, relay, monkeypatch):
        monkeypatch.setattr(ModelRelay, "health_check", lambda self, m: False)
        result = await relay.check_guard([{"role": "user", "content": "hi"}])
        assert result["safe"] is False
        assert result["reason"] == "no_healthy_guard_models"

    @pytest.mark.asyncio
    async def test_strict_treats_ambiguous_as_block(self, relay, monkeypatch):
        monkeypatch.setattr(ModelRelay, "health_check", lambda self, m: True)

        async def fake_classify(self, model, messages, timeout_s):
            return {"safe": True, "output": "cannot determine", "ambiguous": True}

        monkeypatch.setattr(ModelRelay, "_classify_one", fake_classify)
        strict = await relay.check_guard(
            [{"role": "user", "content": "hi"}], stages=["llama-guard3:1b"], strategy="strict"
        )
        assert strict["safe"] is False
        consensus = await relay.check_guard(
            [{"role": "user", "content": "hi"}], stages=["llama-guard3:1b"], strategy="consensus"
        )
        assert consensus["safe"] is True, "ambiguous stays advisory outside strict mode"

    @pytest.mark.asyncio
    async def test_clean_safe_verdicts_still_pass(self, relay, monkeypatch):
        monkeypatch.setattr(ModelRelay, "health_check", lambda self, m: True)

        async def fake_classify(self, model, messages, timeout_s):
            return {"safe": True, "output": "safe"}

        monkeypatch.setattr(ModelRelay, "_classify_one", fake_classify)
        result = await relay.check_guard([{"role": "user", "content": "hi"}], strategy="strict")
        assert result["safe"] is True

    @pytest.mark.asyncio
    async def test_proxy_blocks_with_503_when_guard_unavailable(self, relay, monkeypatch):
        monkeypatch.setattr(ModelRelay, "health_check", lambda self, m: False)
        result = await relay.proxy_completion(
            {"guard": "strict", "messages": [{"role": "user", "content": "hi"}]}
        )
        assert result["relay_info"]["error"] == "guard_unavailable"
        assert result["_status_code"] == 503


# ── :396 real status codes ──────────────────────────────────────────────


class TestErrorStatusCodes:
    def test_error_response_carries_status(self, relay):
        assert relay._error_response("m", "r", 0.0, "x", "guard_blocked")["_status_code"] == 403
        assert relay._error_response("m", "r", 0.0, "x", "no_healthy_ollama_model")["_status_code"] == 503
        assert relay._error_response("m", "r", 0.0, "x", "inference_error")["_status_code"] == 502

    @pytest.mark.asyncio
    async def test_chat_endpoint_maps_status(self, relay, monkeypatch):
        monkeypatch.setattr(model_relay, "relay", relay)
        monkeypatch.setattr(ModelRelay, "health_check", lambda self, m: False)

        class FakeRequest:
            async def json(self):
                return {"model": "auto", "messages": [{"role": "user", "content": "hi"}]}

        resp = await model_relay.chat(FakeRequest())
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_success_path_has_no_status_key(self, relay, monkeypatch):
        monkeypatch.setattr(ModelRelay, "health_check", lambda self, m: True)

        class _Resp:
            ok = True

            def raise_for_status(self):
                pass

            def json(self):
                return {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": {}}

        monkeypatch.setattr(model_relay.requests, "post", lambda *a, **k: _Resp())
        result = await relay.proxy_completion(
            {"model": "auto", "messages": [{"role": "user", "content": "hi"}]}
        )
        assert "_status_code" not in result
        assert result["choices"][0]["message"]["content"] == "ok"


# ── :991 bind + token ───────────────────────────────────────────────────


class TestBindAndAuth:
    def test_non_loopback_bind_without_token_hard_fails(self):
        with pytest.raises(SystemExit, match="non-loopback"):
            model_relay._validate_bind("0.0.0.0", None)

    def test_loopback_bind_needs_no_token(self):
        model_relay._validate_bind("127.0.0.1", None)

    def test_non_loopback_bind_with_token_allowed(self):
        model_relay._validate_bind("0.0.0.0", "tok")

    def test_no_token_configured_allows_local_requests(self, monkeypatch):
        monkeypatch.setattr(model_relay, "RELAY_TOKEN", None)
        assert model_relay._relay_request_authorized({}) is True

    def test_token_required_when_configured(self, monkeypatch):
        monkeypatch.setattr(model_relay, "RELAY_TOKEN", "sekret")
        assert model_relay._relay_request_authorized({}) is False
        assert model_relay._relay_request_authorized({"x-api-key": "wrong"}) is False
        assert model_relay._relay_request_authorized({"x-api-key": "sekret"}) is True
        assert model_relay._relay_request_authorized({"authorization": "Bearer sekret"}) is True

    def test_middleware_rejects_unauthenticated(self, monkeypatch):
        fastapi = pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        monkeypatch.setattr(model_relay, "RELAY_TOKEN", "sekret")
        client = TestClient(model_relay.app)
        assert client.get("/health").status_code == 200  # exempt
        assert client.get("/v1/models").status_code == 401
        assert client.get("/v1/models", headers={"X-Api-Key": "sekret"}).status_code == 200
        assert client.get("/v1/models", headers={"Authorization": "Bearer sekret"}).status_code == 200
