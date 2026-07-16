from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from nexus_os.relay.bridge_client import ModelRelayBridge


class _Response:
    def __init__(self, payload: dict):
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def _install_requests(monkeypatch, payload: dict) -> None:
    def get(url: str, timeout: int):
        assert url.endswith("/api/models")
        assert timeout == 10
        return _Response(payload)

    monkeypatch.setitem(sys.modules, "requests", SimpleNamespace(get=get))


def test_bridge_preserves_unknown_benchmarks_as_null(monkeypatch):
    payload = {
        "models": [
            {"name": "new-frontier-model", "provider": "nvidia", "status": "pending"},
        ],
    }
    _install_requests(monkeypatch, payload)

    bridge = ModelRelayBridge("http://relay.test", refresh_interval=0)
    model = bridge.refresh()["new-frontier-model"]

    assert model["overall_score"] is None
    assert all(model[key] is None for key in (
        "swe_score", "math_score", "code_score", "quality_score",
        "reasoning_score", "speed_score", "cost_efficiency_score",
    ))
    assert model["score_provenance"] == "unknown"
    assert model["score_confidence"] == "no_data"
    assert model["isEstimatedScore"] is True


def test_bridge_labels_existing_static_scores_as_legacy(monkeypatch):
    payload = {"models": [{"name": "deepseek-v3", "provider": "deepseek", "status": "up"}]}
    _install_requests(monkeypatch, payload)

    bridge = ModelRelayBridge("http://relay.test", refresh_interval=0)
    model = bridge.refresh()["deepseek-v3"]

    assert model["overall_score"] is not None
    assert model["score_provenance"] == "legacy_static_registry"
    assert model["score_confidence"] == "legacy_static"
    assert model["isEstimatedScore"] is False


def _fresh_sidecar(path, model_id: str, score: float = 0.91, *, age_days: int = 1) -> None:
    now = datetime.now(timezone.utc)
    fetched_at = (now - timedelta(days=age_days)).isoformat()
    path.write_text(json.dumps({
        "version": 1,
        "generated_at": now.isoformat(),
        "models": {
            model_id: {
                "arena_score": score,
                "confidence": "high",
                "no_data": False,
                "sources": {
                    "aa_coding": {
                        "normalized": score,
                        "trust_tier": "tier1",
                        "fetched_at": fetched_at,
                        "stale": False,
                    },
                    "openrouter_usage": {
                        "normalized": 1.0,
                        "trust_tier": "usage",
                        "fetched_at": fetched_at,
                        "stale": False,
                    },
                },
            },
        },
    }), encoding="utf-8")


def test_bridge_uses_fresh_arena_sidecar_without_faking_dimensions(monkeypatch, tmp_path):
    payload = {"models": [{"name": "new-frontier-model", "provider": "nvidia", "status": "pending"}]}
    _install_requests(monkeypatch, payload)
    sidecar = tmp_path / "scores.json"
    _fresh_sidecar(sidecar, "new-frontier-model")

    bridge = ModelRelayBridge("http://relay.test", refresh_interval=0, arena_scores_path=sidecar)
    model = bridge.refresh()["new-frontier-model"]

    assert model["overall_score"] == 0.91
    assert model["score_provenance"] == "arena_sidecar"
    assert model["score_confidence"] == "high"
    assert model["score_coverage"] == ["aa_coding"]
    assert model["isEstimatedScore"] is False
    assert model["swe_score"] is None
    assert model["code_score"] is None


def test_bridge_rejects_stale_sidecar_evidence(monkeypatch, tmp_path):
    payload = {"models": [{"name": "new-frontier-model", "provider": "nvidia", "status": "pending"}]}
    _install_requests(monkeypatch, payload)
    sidecar = tmp_path / "scores.json"
    _fresh_sidecar(sidecar, "new-frontier-model", age_days=8)

    bridge = ModelRelayBridge("http://relay.test", refresh_interval=0, arena_scores_path=sidecar)
    model = bridge.refresh()["new-frontier-model"]

    assert model["overall_score"] is None
    assert model["score_provenance"] == "unknown"
    assert model["isEstimatedScore"] is True
