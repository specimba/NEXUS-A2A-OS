"""Phase 2 done-gate (roadmap IMPROVEMENT_ROADMAP_2026-07-02):

One e2e chain proves the built-but-unplugged wiring is live:
  auto-gmr request → GMR classification in relay_info → per-token
  logprobs → REAL CalibratedHallucinationDetector entropy math
  (non-dry-run) → hallucination verdict in relay_info → verdict JSONL →
  monitor daemon → A2A alert.

Only the model HTTP response is stubbed (the local Ollama engine needs
an operator reinstall; cloud lanes return no logprobs). Everything else
is production code. Companion gates covered by their own suites:
TrustKernel budget (test_trust_kernel_singleton, test_agent_pool_kernel,
TestCogERTrustBudget), GMR breaker sync (TestSyncFromRelay), encrypted
vault persistence (test_channel_encryption).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.relay import model_relay
from nexus_os.relay.model_relay import ModelRelay


@pytest.fixture
def relay(monkeypatch):
    monkeypatch.setattr(ModelRelay, "_discover_ollama_models", lambda self: None)
    monkeypatch.setattr(ModelRelay, "_start_health_loop", lambda self: None)
    monkeypatch.setattr(ModelRelay, "health_check", lambda self, m: True)
    return ModelRelay()


def _token(logprobs: list[float]) -> dict:
    return {"top_logprobs": [{"logprob": lp} for lp in logprobs]}


def _fake_ollama_response() -> dict:
    """Five confident tokens, then one maximum-entropy token (uniform
    top-10) — the entropy spike the detector must flag."""
    confident = _token([-0.01] + [-8.0] * 9)
    uniform = _token([math.log(1.0 / 10.0)] * 10)
    return {
        "choices": [{
            "message": {"content": "The capital of Australia is Sydney maybe"},
            "finish_reason": "stop",
            "logprobs": {"content": [confident] * 5 + [uniform]},
        }],
        "usage": {"prompt_tokens": 12, "completion_tokens": 6},
    }


class TestPhase2DoneGate:
    @pytest.mark.asyncio
    async def test_auto_gmr_real_entropy_verdict_to_a2a_alert(
        self, relay, monkeypatch, tmp_path,
    ):
        # ── arrange: stub ONLY the model HTTP boundary ────────────
        verdicts_file = tmp_path / "hallucination_verdicts.jsonl"
        monkeypatch.setattr(model_relay, "HALLUCINATION_VERDICTS_PATH", verdicts_file)

        captured_payload = {}

        class _Resp:
            ok = True
            def raise_for_status(self):
                pass
            def json(self):
                return _fake_ollama_response()

        def _post(url, json=None, **kw):
            captured_payload.update(json or {})
            return _Resp()

        monkeypatch.setattr(model_relay.requests, "post", _post)

        # Real detector, real entropy math — tightened threshold so the
        # uniform token deterministically crosses the risk line.
        from nexus_os.monitoring.calibrated_hallucination_detector import (
            CalibratedHallucinationDetector,
        )
        relay._hallucination_detector = CalibratedHallucinationDetector(
            threshold=0.05, adaptive=False, bebop_weight=0.0,
        )

        # ── act: one auto-gmr request through the production path ─
        result = await relay.proxy_completion({
            "model": "auto-gmr",
            "messages": [{"role": "user", "content": "What is the capital of Australia?"}],
        })

        # ── assert: logprobs were requested from the model ────────
        assert captured_payload.get("options", {}).get("logprobs") == 10

        # ── assert: GMR pre-stage classified the request ───────────
        info = result["relay_info"]
        assert info.get("gmr_level") in {"L1", "L2", "L3", "L4"}

        # ── assert: REAL (non-dry-run) entropy verdict in relay_info ─
        verdict = info.get("hallucination")
        assert verdict is not None, "hallucination verdict missing from relay_info"
        assert verdict["tokens_assessed"] == 6
        assert verdict["risk_level"] != "low"
        assert 0.0 < verdict["risk_score"] <= 1.0

        # ── assert: verdict persisted for the monitor daemon ───────
        assert verdicts_file.exists()
        entry = json.loads(verdicts_file.read_text().strip().splitlines()[-1])
        assert entry["risk_level"] == verdict["risk_level"]
        assert entry["model"], "model attribution missing from persisted verdict"

        # ── assert: monitor daemon consumes and alerts on A2A ─────
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        (tmp_path / ".nexus").mkdir(exist_ok=True)
        (tmp_path / ".nexus" / "hallucination_verdicts.jsonl").write_text(
            json.dumps(entry) + "\n", encoding="utf-8",
        )

        published = []

        class _StubBus:
            def publish(self, channel_id, sender, message, topic, **kw):
                published.append({"topic": topic, "message": json.loads(message)})

        import nexus_os.bridge.a2a_channels as a2a
        monkeypatch.setattr(a2a, "A2AChannelBus", _StubBus)

        from nexus_os.monitor_daemon import MonitorDaemon
        daemon = MonitorDaemon(a2a_channel="hallucination-alerts")
        check = daemon._run_hallucination_check()

        assert check["ok"] is True
        assert check["result"]["alert_count"] >= 1
        assert published, "no A2A alert emitted for a non-low verdict"
        assert published[0]["topic"] == "hallucination"
        assert published[0]["message"]["type"] == "hallucination-alert"
        assert published[0]["message"]["risk_level"] == verdict["risk_level"]
