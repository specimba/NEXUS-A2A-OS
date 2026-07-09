"""Tests for Chimera + LG pipeline and catalogue telemetry parsing."""

from __future__ import annotations

from nexus_os.gmr.chimera_lg_pipeline import (
    resolve_execute_model,
    run_lg_track,
    run_pipeline,
)
from nexus_os.gmr.telemetry import parse_models_payload


def test_parse_openai_v1_models_shape():
    payload = {
        "object": "list",
        "data": [
            {"id": "auto-fastest", "owned_by": "router"},
            {"id": "deepseek-ai/deepseek-v4-pro", "owned_by": "nvidia", "status": "up"},
        ],
    }
    models = parse_models_payload(payload, timestamp="t0")
    assert "auto-fastest" in models
    assert models["deepseek-ai/deepseek-v4-pro"].provider == "nvidia"
    assert models["auto-fastest"].status == "up"


def test_parse_legacy_models_shape():
    payload = {
        "models": [
            {"name": "glm-5.2", "provider": "nvidia", "tier": 90, "uptime": 0.9, "status": "up"}
        ]
    }
    models = parse_models_payload(payload, timestamp="t0")
    assert models["glm-5.2"].tier == 90
    assert models["glm-5.2"].is_available


def test_lg_track_dry_run_stable():
    lg = run_lg_track(category="F1.1", temperature=0.6, tokens=12)
    assert lg["mode"] == "dry_run"
    assert lg["tokens_simulated"] == 12
    assert "mean_entropy" in lg
    assert "honesty" in lg


def test_pipeline_decision_only_no_execute():
    report = run_pipeline(
        "Explain carefully how entropy cooling relates to hallucination risk.",
        execute=False,
        cloud=True,
        track=True,
        track_tokens=16,
        category="F1.1",
        policy="auto",
    )
    assert report.status in {"ok", "degraded"}
    assert report.route["model"]
    assert report.route["policy"]
    assert report.execution is None
    assert report.lg is not None
    assert report.lg["chimera_policy"] == report.route["policy"]
    # Cloud should be eligible so we are not stuck on local GGUF-only names only
    # when cloud profiles exist (decision may still pick local_power if scored higher).
    assert "features" in report.route


def test_resolve_execute_model_remaps_synthetic_cloud_id():
    catalogue = {
        "auto-fastest",
        "deepseek-ai/deepseek-v4-pro",
        "claude-haiku-4.5",
    }
    model, note = resolve_execute_model("qwen2.5-72b-instruct-bf16", catalogue)
    assert model == "auto-fastest"
    assert note is not None
    assert "remapped" in note

    exact, note2 = resolve_execute_model("deepseek-ai/deepseek-v4-pro", catalogue)
    assert exact == "deepseek-ai/deepseek-v4-pro"
    assert note2 is None
