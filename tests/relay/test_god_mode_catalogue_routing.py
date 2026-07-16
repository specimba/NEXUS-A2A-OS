from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from nexus_os.relay import god_mode_proxy as gmp


def _model(
    model_id: str,
    status: str,
    *,
    provider: str = "nvidia",
    hidden: bool = False,
    rate_limited: bool = False,
    intelligence: float = 0.8,
) -> dict:
    return {
        "modelId": model_id,
        "label": model_id,
        "providerKey": provider,
        "status": status,
        "hidden": hidden,
        "isRateLimited": rate_limited,
        "intell": intelligence,
        "avg": 1000,
        "qos": 0.5,
        "uptime": 0.5,
        "ctx": "256k",
    }


def test_routable_models_distinguish_catalogue_from_verified_health():
    models = [
        _model("verified", "up"),
        _model("catalogue", "pending"),
        _model("hidden", "pending", hidden=True),
        _model("limited", "pending", rate_limited=True),
        _model("down", "down"),
        _model("noauth", "noauth"),
        _model("disabled", "disabled"),
        _model("banned", "banned"),
    ]

    assert [model["modelId"] for model in gmp._verified_up_models(models)] == ["verified"]
    assert [model["modelId"] for model in gmp._routable_models(models)] == [
        "verified",
        "catalogue",
    ]


def test_catalogue_only_models_are_selectable_without_claiming_verified_up():
    models = [
        _model("z-ai/glm-5.2", "pending", intelligence=0.95),
        _model("mistral/labs-leanstral-1-5-1", "pending", provider="mistral"),
        _model("unavailable", "down", intelligence=0.99),
    ]

    selected, metadata, fallback = gmp.select_model(models, "god-smart", [])

    assert selected == "z-ai/glm-5.2"
    assert metadata["candidates_up"] == 0
    assert metadata["candidates_routable"] == 2
    assert fallback[0]["model_id"] == "mistral/labs-leanstral-1-5-1"


def test_health_reports_catalogue_only_without_false_online_claim(monkeypatch):
    async def fake_models():
        return [_model("z-ai/glm-5.2", "pending")]

    monkeypatch.setattr(gmp, "get_models", fake_models)
    payload = asyncio.run(gmp.health())

    assert payload["status"] == "ok"
    assert payload["models_up"] == 0
    assert payload["models_routable"] == 1
    assert payload["catalogue_only"] is True


def test_unknown_intelligence_is_not_synthesized_or_ranked_as_45_percent():
    unknown = _model("mistral/labs-leanstral-1-5-1", "pending", intelligence=None)
    measured = _model("z-ai/glm-5.2", "pending", intelligence=0.61)
    profile = gmp.GOD_PROFILES["god-smart"]

    candidates = gmp.select_candidates([unknown, measured], profile, [], top_n=2)
    assert [model["modelId"] for _, model in candidates] == ["z-ai/glm-5.2"]
    assert gmp._observed_intelligence(unknown) is None

    selected, metadata, fallback = gmp.select_model([unknown], "god-smart", [])
    assert selected == "mistral/labs-leanstral-1-5-1"
    assert metadata["intelligence"] is None
    assert metadata["intelligence_evidence"] == "unknown"
    assert "No measured intelligence score" in metadata["why_selected"]


def test_fresh_arena_sidecar_enriches_only_an_unknown_exact_model(monkeypatch):
    now = datetime.now(timezone.utc)
    unknown = _model("mistral/labs-leanstral-1-5-1", "pending", provider="mistral", intelligence=None)
    measured = _model("z-ai/glm-5.2", "pending", intelligence=0.61)
    sidecar = {
        "version": 1,
        "generated_at": now.isoformat(),
        "models": {
            "mistral/labs-leanstral-1-5-1": {
                "arena_score": 0.91,
                "confidence": "high",
                "no_data": False,
                "sources": {
                    "aa_coding": {
                        "normalized": 0.91,
                        "trust_tier": "tier1",
                        "fetched_at": (now - timedelta(hours=1)).isoformat(),
                        "stale": False,
                    },
                },
            },
        },
    }
    monkeypatch.setattr(gmp, "load_arena_score_overlay", lambda: sidecar)

    selected, metadata, _ = gmp.select_model([unknown, measured], "god-smart", [])

    assert selected == "mistral/labs-leanstral-1-5-1"
    assert metadata["intelligence"] == 0.91
    assert metadata["intelligence_evidence"] == "arena_sidecar"
    assert metadata["intelligence_sources"]["aa_coding"]["trust_tier"] == "tier1"
    assert "Highest fresh Arena score" in metadata["why_selected"]
    assert unknown.get("intell") is None  # enrichment is a copied routing row
