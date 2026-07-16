"""Read-only, provenance-aware runtime benchmark evidence.

The Arena ingestion job writes a sidecar outside the committed registry. This
module is deliberately narrow: it can enrich an otherwise unknown model score,
but it never manufactures one, changes provider health, or promotes a model.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_ARENA_SCORES_PATH = Path.home() / ".nexus" / "arena" / "scores.json"
_CAPABILITY_TIERS = frozenset({"tier1", "tier2"})
_SOURCE_MAX_AGE_DAYS = {
    "aa_": 7,
    "lmarena_": 7,
    "openrouter_": 3,
}


def load_arena_score_overlay(path: Path | str | None = None) -> dict[str, Any]:
    """Load one local Arena sidecar safely; invalid or absent data is no-data."""
    target = Path(path) if path is not None else DEFAULT_ARENA_SCORES_PATH
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": None, "models": {}, "generated_at": None}
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), dict):
        return {"version": None, "models": {}, "generated_at": None}
    return {
        "version": payload.get("version"),
        "models": payload["models"],
        "generated_at": payload.get("generated_at"),
    }


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _fresh_capability_sources(sources: dict[str, Any], now: datetime) -> list[str]:
    """Return only source keys that can substantiate a runtime score.

    The ingest job retains usage and meta observations for operator context.
    Runtime selection may never treat those as benchmark evidence, and it
    rechecks timestamps instead of trusting a stale flag written hours ago.
    """
    fresh: list[str] = []
    for source, row in sources.items():
        if not isinstance(source, str) or not isinstance(row, dict):
            continue
        if row.get("trust_tier") not in _CAPABILITY_TIERS or bool(row.get("stale")):
            continue
        max_age_days = next(
            (days for prefix, days in _SOURCE_MAX_AGE_DAYS.items() if source.startswith(prefix)),
            None,
        )
        fetched_at = _parse_timestamp(row.get("fetched_at"))
        if max_age_days is None or fetched_at is None:
            continue
        try:
            normalized = float(row.get("normalized"))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(normalized) or not 0.0 <= normalized <= 1.0:
            continue
        if fetched_at > now or now - fetched_at > timedelta(days=max_age_days):
            continue
        fresh.append(source)
    return sorted(fresh)


def _usable_entry(entry: Any, now: datetime) -> dict[str, Any] | None:
    if not isinstance(entry, dict) or bool(entry.get("no_data")):
        return None
    try:
        score = float(entry.get("arena_score"))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        return None
    confidence = str(entry.get("confidence") or "no_data").lower()
    if confidence not in {"medium", "high"}:
        return None
    sources = entry.get("sources")
    if not isinstance(sources, dict):
        return None
    evidence_sources = _fresh_capability_sources(sources, now)
    if not evidence_sources:
        return None
    return {
        "arena_score": score,
        "confidence": confidence,
        "sources": sources,
        "evidence_sources": evidence_sources,
    }


def resolve_arena_score(
    identifiers: Iterable[Any],
    overlay: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Resolve fresh score evidence by exact model identity, case-insensitively.

    Provider/model alias reconciliation remains the registry ingester's job.
    Runtime routing intentionally accepts only an exact canonical sidecar key,
    avoiding family-level score borrowing between different model releases.
    """
    if (overlay or {}).get("version") != 1:
        return None
    generated_at = _parse_timestamp((overlay or {}).get("generated_at"))
    models = (overlay or {}).get("models")
    if generated_at is None or not isinstance(models, dict):
        return None
    if now is None:
        current_time = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        current_time = now.replace(tzinfo=timezone.utc)
    else:
        current_time = now.astimezone(timezone.utc)
    lower_index = {
        str(key).lower(): (str(key), value)
        for key, value in models.items()
        if isinstance(key, str)
    }
    for raw in identifiers:
        identifier = str(raw or "").strip()
        if not identifier:
            continue
        key, entry = identifier, models.get(identifier)
        if entry is None:
            indexed = lower_index.get(identifier.lower())
            if indexed is None:
                continue
            key, entry = indexed
        usable = _usable_entry(entry, current_time)
        if usable is None:
            continue
        return {
            "key": key,
            "arena_score": usable["arena_score"],
            "confidence": usable["confidence"],
            "sources": usable["sources"],
            "evidence_sources": usable["evidence_sources"],
            "generated_at": (overlay or {}).get("generated_at"),
        }
    return None
