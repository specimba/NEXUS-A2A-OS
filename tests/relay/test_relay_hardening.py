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
import json
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


# ── P2-1: LG relay logprobs feed ──────────────────────────────────────


class TestLogprobsFeed:
    """Verify logprobs are requested, parsed, and fed to the hallucination
    detector (was synthetic dry-run before this slice)."""

    @pytest.mark.asyncio
    async def test_logprobs_requested_in_payload(self, relay, monkeypatch):
        """Ollama payload includes logprobs option."""
        captured = {}

        class _Resp:
            ok = True
            def raise_for_status(self):
                pass
            def json(self):
                return {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": {}}

        def _capture(url, json=None, **kw):
            captured.update(json or {})
            return _Resp()

        monkeypatch.setattr(ModelRelay, "health_check", lambda self, m: True)
        monkeypatch.setattr(model_relay.requests, "post", _capture)
        await relay.proxy_completion(
            {"model": "auto", "messages": [{"role": "user", "content": "hi"}]}
        )
        assert captured.get("options", {}).get("logprobs") == 10

    @pytest.mark.asyncio
    async def test_logprobs_disabled_when_opt_out(self, relay, monkeypatch):
        """Caller can disable logprobs via logprobs=False."""
        captured = {}

        class _Resp:
            ok = True
            def raise_for_status(self):
                pass
            def json(self):
                return {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": {}}

        def _capture(url, json=None, **kw):
            captured.update(json or {})
            return _Resp()

        monkeypatch.setattr(ModelRelay, "health_check", lambda self, m: True)
        monkeypatch.setattr(model_relay.requests, "post", _capture)
        await relay.proxy_completion(
            {"model": "auto", "messages": [{"role": "user", "content": "hi"}], "logprobs": False}
        )
        assert "logprobs" not in captured.get("options", {})

    @pytest.mark.asyncio
    async def test_hallucination_verdict_in_relay_info(self, relay, monkeypatch):
        """When Ollama returns logprobs, relay_info includes hallucination verdict."""
        class _Resp:
            ok = True
            def raise_for_status(self):
                pass
            def json(self):
                # Simulate OpenAI-compatible logprobs response
                return {
                    "choices": [{
                        "message": {"content": "hello"},
                        "finish_reason": "stop",
                        "logprobs": {
                            "content": [{"top_logprobs": [
                                {"token": "hello", "logprob": -0.5},
                                {"token": "hi", "logprob": -1.0},
                                {"token": "hey", "logprob": -2.0},
                            ]}]
                        },
                    }],
                    "usage": {},
                }

        monkeypatch.setattr(ModelRelay, "health_check", lambda self, m: True)
        monkeypatch.setattr(model_relay.requests, "post", lambda *a, **k: _Resp())
        result = await relay.proxy_completion(
            {"model": "auto", "messages": [{"role": "user", "content": "hi"}]}
        )
        # Hallucination verdict should be present (low risk for normal response)
        vi = result["relay_info"]
        assert "hallucination" in vi
        assert "risk_level" in vi["hallucination"]
        assert vi["hallucination"]["risk_score"] >= 0.0

    def test_extract_logprobs_openai_format(self, relay):
        data = {
            "choices": [{
                "logprobs": {
                    "content": [{"top_logprobs": [
                        {"logprob": -0.1}, {"logprob": -1.0}, {"logprob": -3.0},
                    ]}]
                }
            }]
        }
        probs = relay._extract_logprobs(data)
        assert probs is not None
        assert len(probs) == 3
        assert abs(sum(probs) - 1.0) < 1e-6
        assert probs[0] > probs[1] > probs[2]

    def test_extract_logprobs_ollama_native(self, relay):
        data = {"logprobs": {"hello": -0.5, "world": -1.5, "!": -3.0}}
        probs = relay._extract_logprobs(data)
        assert probs is not None
        assert len(probs) == 3
        assert abs(sum(probs) - 1.0) < 1e-6

    def test_extract_logprobs_missing_returns_none(self, relay):
        assert relay._extract_logprobs({"choices": [{"message": {"content": "ok"}}]}) is None
        assert relay._extract_logprobs({}) is None

    def test_normalize_logprobs(self):
        raw = [-1.0, -2.0, -4.0]
        probs = model_relay.ModelRelay._normalize_logprobs(raw)
        assert abs(sum(probs) - 1.0) < 1e-6
        assert probs[0] > probs[1] > probs[2]

    @pytest.mark.asyncio
    async def test_hallucination_assessment_graceful_failure(self, relay, monkeypatch):
        """If detector throws, relay still returns the response."""
        class _Resp:
            ok = True
            def raise_for_status(self):
                pass
            def json(self):
                return {
                    "choices": [{
                        "message": {"content": "ok"},
                        "finish_reason": "stop",
                        "logprobs": {"content": [{"top_logprobs": [{"logprob": -0.5}]}]},
                    }],
                    "usage": {},
                }

        monkeypatch.setattr(ModelRelay, "health_check", lambda self, m: True)
        monkeypatch.setattr(model_relay.requests, "post", lambda *a, **k: _Resp())
        # Force detector to throw
        monkeypatch.setattr(
            ModelRelay, "_get_hallucination_detector",
            lambda self: (_ for _ in ()).throw(RuntimeError("detector down")),
        )
        result = await relay.proxy_completion(
            {"model": "auto", "messages": [{"role": "user", "content": "hi"}]}
        )
        # Response still comes back, just no hallucination key
        assert result["choices"][0]["message"]["content"] == "ok"
        assert "hallucination" not in result["relay_info"]


# ── P2-7: verdict persistence + monitor daemon consumption ──────────────


class TestVerdictPersistence:
    """Relay persists non-low verdicts; monitor daemon consumes them."""

    def test_persist_writes_jsonl(self, relay, tmp_path, monkeypatch):
        monkeypatch.setattr(model_relay, "HALLUCINATION_VERDICTS_PATH", tmp_path / "v.jsonl")
        relay._persist_hallucination_verdict({"risk_level": "high", "risk_score": 0.85, "reasons": ["high_epr"]})
        lines = (tmp_path / "v.jsonl").read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["risk_level"] == "high"
        assert "ts" in entry

    def test_persist_skips_low(self, relay, tmp_path, monkeypatch):
        monkeypatch.setattr(model_relay, "HALLUCINATION_VERDICTS_PATH", tmp_path / "v.jsonl")
        relay._persist_hallucination_verdict({"risk_level": "low", "risk_score": 0.05, "reasons": []})
        assert not (tmp_path / "v.jsonl").exists()

    @pytest.mark.asyncio
    async def test_high_risk_verdict_persisted(self, relay, monkeypatch, tmp_path):
        monkeypatch.setattr(model_relay, "HALLUCINATION_VERDICTS_PATH", tmp_path / "v.jsonl")
        monkeypatch.setattr(ModelRelay, "health_check", lambda self, m: True)

        class _Resp:
            ok = True
            def raise_for_status(self):
                pass
            def json(self):
                return {
                    "choices": [{
                        "message": {"content": "hmm"},
                        "finish_reason": "stop",
                        "logprobs": {"content": [{"top_logprobs": [
                            {"logprob": -0.01}, {"logprob": -0.02}, {"logprob": -0.03},
                        ]}]},
                    }],
                    "usage": {},
                }

        monkeypatch.setattr(model_relay.requests, "post", lambda *a, **k: _Resp())
        result = await relay.proxy_completion(
            {"model": "auto", "messages": [{"role": "user", "content": "hi"}]}
        )
        # If risk is not low, file should exist
        vi = result["relay_info"].get("hallucination", {})
        if vi.get("risk_level") != "low":
            assert (tmp_path / "v.jsonl").exists()


class TestPerTokenAssessment:
    """P2-1 repair: every token's top-k feeds the detector; verdict is the
    worst token's, and the model name is threaded into persistence."""

    def test_sequences_extracted_per_token(self, relay):
        data = {"choices": [{"logprobs": {"content": [
            {"top_logprobs": [{"logprob": -0.01}, {"logprob": -4.0}]},
            {"top_logprobs": [{"logprob": -0.7}, {"logprob": -0.8}]},
            {"top_logprobs": [{"logprob": -0.05}, {"logprob": -3.5}]},
        ]}}]}
        sequences = relay._extract_logprob_sequences(data)
        assert len(sequences) == 3
        for vec in sequences:
            assert sum(vec) == pytest.approx(1.0, abs=1e-6)

    def test_worst_token_wins(self, relay, monkeypatch, tmp_path):
        monkeypatch.setattr(model_relay, "HALLUCINATION_VERDICTS_PATH", tmp_path / "v.jsonl")

        class _Detector:
            def __init__(self):
                self.calls = 0
            def assess(self, *, position, temperature, topk_probs):
                self.calls += 1
                # Second token is the risky one
                if position == 1:
                    return {"risk_level": "high", "risk_score": 0.9, "reasons": ["spike"]}
                return {"risk_level": "low", "risk_score": 0.1, "reasons": []}

        det = _Detector()
        monkeypatch.setattr(type(relay), "_get_hallucination_detector", lambda self: det)
        data = {"choices": [{"logprobs": {"content": [
            {"top_logprobs": [{"logprob": -0.01}, {"logprob": -4.0}]},
            {"top_logprobs": [{"logprob": -0.7}, {"logprob": -0.8}]},
            {"top_logprobs": [{"logprob": -0.05}, {"logprob": -3.5}]},
        ]}}]}
        verdict = relay._assess_logprobs(data, 0.7, model="qwen3:8b")
        assert det.calls == 3
        assert verdict["risk_level"] == "high"
        assert verdict["risk_score"] == pytest.approx(0.9)
        assert verdict["tokens_assessed"] == 3
        entry = json.loads((tmp_path / "v.jsonl").read_text().strip())
        assert entry["model"] == "qwen3:8b"
