from __future__ import annotations

from datetime import datetime, timedelta, timezone

from nexus_os.relay.score_evidence import resolve_arena_score


NOW = datetime(2026, 7, 12, tzinfo=timezone.utc)


def _source(
    name: str = "aa_coding",
    *,
    trust_tier: str = "tier1",
    age_days: int = 1,
    stale: bool = False,
) -> dict:
    return {
        "normalized": 0.91,
        "trust_tier": trust_tier,
        "fetched_at": (NOW - timedelta(days=age_days)).isoformat(),
        "stale": stale,
        "external_id": "frontier-model",
    }


def _overlay(*, version: int = 1, sources: dict | None = None) -> dict:
    return {
        "version": version,
        "generated_at": NOW.isoformat(),
        "models": {
            "frontier-model": {
                "arena_score": 0.91,
                "confidence": "high",
                "no_data": False,
                "sources": sources if sources is not None else {"aa_coding": _source()},
            },
        },
    }


def test_resolve_accepts_only_fresh_capability_evidence_and_exact_identity():
    overlay = _overlay(sources={
        "aa_coding": _source(),
        "openrouter_usage": _source("openrouter_usage", trust_tier="usage"),
    })

    result = resolve_arena_score(["FRONTIER-MODEL"], overlay, now=NOW)

    assert result is not None
    assert result["arena_score"] == 0.91
    assert result["evidence_sources"] == ["aa_coding"]
    assert "openrouter_usage" in result["sources"]
    assert resolve_arena_score(["frontier-model-v2"], overlay, now=NOW) is None


def test_resolve_rejects_usage_only_and_stale_evidence():
    usage_only = _overlay(sources={
        "openrouter_usage": _source("openrouter_usage", trust_tier="usage"),
    })
    stale = _overlay(sources={
        "aa_coding": _source(age_days=8),
    })

    assert resolve_arena_score(["frontier-model"], usage_only, now=NOW) is None
    assert resolve_arena_score(["frontier-model"], stale, now=NOW) is None


def test_resolve_rejects_missing_contract_or_unusable_confidence():
    invalid_version = _overlay(version=2)
    no_sources = _overlay(sources={})
    no_sources["models"]["frontier-model"]["confidence"] = "no_data"

    assert resolve_arena_score(["frontier-model"], invalid_version, now=NOW) is None
    assert resolve_arena_score(["frontier-model"], no_sources, now=NOW) is None
