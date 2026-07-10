"""Arena/leaderboard score ingestion for the canonical model registry (Track A1).

Fuses external capability signals into a runtime scores sidecar
(~/.nexus/arena/scores.json), NEVER into the committed registry —
config/models.registry.json stays deterministic; the sidecar carries the
live truth (same doctrine as provider_refresher's health sidecar).

Sources and trust tiers per docs/handoff/BENCHMARK_TRUST_REGISTRY.md:

- LMArena elo boards (text + code) via the MIT-licensed daily-snapshot
  mirror at api.wulong.dev/arena-ai-leaderboards — dynamic live human
  preference, no public static test text: Tier 1 (weight 1.0).
- ArtificialAnalysis v2 language-models API — the coding index tracks
  LiveCodeBench-class dynamic evals: Tier 1 (1.0); the blended
  intelligence index folds in periodically-rotated material: Tier 2
  (0.85).
- OpenRouter rankings-daily — USAGE, not capability. Weight 0.10, and
  fusion NEVER lets usage raise a score (tie-break / confidence only).
- Tier 3 static benches (GSM8K, HumanEval, MMLU, ...) are never
  ingested: no adapter exists for them, by design.

NO-DATA DOCTRINE: a registry model absent from every source gets no
entry (or an explicit no_data:true entry when requested) — a score is
never synthesized. Known coverage gaps are documented in KNOWN_GAPS.

API keys resolve via nexus_os.security.secrets (env -> vault ->
~/.modelrelay.json apiKeys); no literals. Raw payloads are cached
verbatim under ~/.nexus/arena/raw/<source>/<YYYY-MM-DD>.json so
offline=True runs (and tests, via an injected cache_dir) never touch
the network. No side effects on import.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple

import requests

from nexus_os.relay.discovery_rules import _family_stem
from nexus_os.security.secrets import get_secret

logger = logging.getLogger("nexus.relay.arena_ingest")

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "config" / "models.registry.json"
OVERRIDES_PATH = REPO_ROOT / "config" / "arena_name_overrides.json"
ARENA_DIR = Path.home() / ".nexus" / "arena"
DEFAULT_CACHE_DIR = ARENA_DIR / "raw"
SCORES_PATH = ARENA_DIR / "scores.json"

FETCH_TIMEOUT_S = 15

AA_URL = "https://artificialanalysis.ai/api/v2/language/models"
LMARENA_URL = "https://api.wulong.dev/arena-ai-leaderboards/v1/"
OPENROUTER_RANKINGS_URL = "https://openrouter.ai/api/v1/rankings-daily"

# Usage is a popularity signal, not a capability signal. It gets a small
# fixed weight for reporting, and fuse_signals() excludes it from the
# capability mean entirely so it can never RAISE a model's score.
USAGE_SIGNAL_WEIGHT = 0.10

# Trust weights per docs/handoff/BENCHMARK_TRUST_REGISTRY.md (taxonomy
# section 2): Tier 1 dynamic/live boards score 1.0, Tier 2
# rotated/blended indices score 0.85, usage is confidence-only at 0.10.
# Tier 3 static public benches (GSM8K, HumanEval, MMLU, AdvBench, ...)
# are deliberately absent — never ingested, no adapter.
TRUST_WEIGHTS: Dict[str, float] = {
    "lmarena_elo": 1.0,             # Tier 1: live human-preference elo (text)
    "lmarena_code_elo": 1.0,        # Tier 1: live human-preference elo (code)
    "aa_coding": 1.0,               # Tier 1: LiveCodeBench-class coding index
    "aa_intelligence_index": 0.85,  # Tier 2: blended, periodically rotated
    "openrouter_usage": USAGE_SIGNAL_WEIGHT,  # usage: never raises a score
}

# Sources whose signals are usage-only (excluded from capability fusion).
USAGE_SOURCES = frozenset({"openrouter_usage"})

# Per-adapter freshness horizon: older signals are flagged stale and
# excluded from fusion; anything past DROP_AFTER_DAYS is dropped even
# from the overlay's sources map.
MAX_AGE_DAYS: Dict[str, int] = {
    "artificialanalysis": 7,
    "lmarena": 7,
    "openrouter": 3,
}
DROP_AFTER_DAYS = 30

# Registry models with known board-coverage gaps: their absence is
# expected and documented, never papered over with a synthetic score.
KNOWN_GAPS: Dict[str, str] = {
    "intern-s2-preview": "vendor-only preview distribution; no AA/LMArena coverage yet",
    "stepfun-ai/step-3.5-flash": "not tracked by AA or LMArena boards (3.7 superseded it on boards)",
    "qwen/qwen3.5-122b-a10b": "board coverage gap; only the 397b sibling is ranked",
    "moonshotai/Kimi-K2.7-Code": "vendor-only code variant; boards list base K2.7 only",
    "LongCat-2.0": "too new; daily board snapshots not yet updated",
}


@dataclass
class ArenaSignal:
    """One normalized observation of one model from one external source."""

    source: str                  # signal key, e.g. "lmarena_elo", "aa_coding"
    raw: Dict[str, Any]          # verbatim excerpt of the source row
    normalized: Optional[float]  # 0-1 capability/usage value, None if n/a
    trust_tier: str              # "tier1" | "tier2" | "usage" | "meta"
    fetched_at: str              # ISO-8601 UTC timestamp of the snapshot
    stale: bool = False          # past the source's MAX_AGE_DAYS horizon


# ── Normalization ──────────────────────────────────────────────────


def _clamp01(value: float) -> float:
    return min(max(float(value), 0.0), 1.0)


def normalize_elo(elo: float, lo: float = 1000.0, hi: float = 1500.0) -> float:
    """Linear elo -> 0-1, clamped to the [lo, hi] band."""
    if hi <= lo:
        raise ValueError("normalize_elo requires hi > lo")
    return _clamp01((float(elo) - lo) / (hi - lo))


def normalize_index(value: float) -> float:
    """AA-style 0-100 index -> 0-1, clamped."""
    return _clamp01(float(value) / 100.0)


def normalize_speed(tok_per_s: Optional[float], lo: float = 20.0, hi: float = 300.0) -> Optional[float]:
    """Log-normalize output tokens/s over the [20, 300] band -> 0-1.

    Log scale because perceived latency gains flatten out: 20->40 tok/s
    matters far more than 260->280.
    """
    if tok_per_s is None:
        return None
    value = float(tok_per_s)
    if value <= 0:
        return None
    clamped = min(max(value, lo), hi)
    return (math.log(clamped) - math.log(lo)) / (math.log(hi) - math.log(lo))


# ── Time / cache helpers ───────────────────────────────────────────


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.isoformat()


_DAY_STEM = re.compile("^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def _write_cache(cache_dir: Path, source: str, payload: Any, day: Optional[str] = None) -> Path:
    """Cache one verbatim payload as <cache_dir>/<source>/<YYYY-MM-DD>.json."""
    target_dir = Path(cache_dir) / source
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = day or _utc_now().strftime("%Y-%m-%d")
    path = target_dir / (stem + ".json")
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _read_latest_cache(cache_dir: Path, source: str) -> Tuple[Any, str]:
    """(payload, fetched_at_iso) of the newest dated snapshot, or (None, '')."""
    target_dir = Path(cache_dir) / source
    if not target_dir.is_dir():
        return None, ""
    snapshots = sorted(p for p in target_dir.glob("*.json") if _DAY_STEM.match(p.stem))
    if not snapshots:
        return None, ""
    latest = snapshots[-1]
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("unreadable cache snapshot: %s", latest)
        return None, ""
    fetched = datetime.strptime(latest.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return payload, _iso(fetched)


# ── Staleness ──────────────────────────────────────────────────────


def source_of_signal(signal_key: str) -> str:
    """Adapter name owning a signal key (drives MAX_AGE_DAYS lookup)."""
    if signal_key.startswith("aa_"):
        return "artificialanalysis"
    if signal_key.startswith("lmarena"):
        return "lmarena"
    if signal_key.startswith("openrouter"):
        return "openrouter"
    return ""


def signal_age_days(signal: ArenaSignal, now: Optional[datetime] = None) -> float:
    try:
        fetched = datetime.fromisoformat(signal.fetched_at)
    except (TypeError, ValueError):
        return math.inf
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    moment = now or _utc_now()
    return (moment - fetched).total_seconds() / 86400.0


def filter_stale(signals: List[ArenaSignal], now: Optional[datetime] = None) -> List[ArenaSignal]:
    """Drop signals older than DROP_AFTER_DAYS; flag the rest stale/fresh.

    Stale signals stay visible in the overlay's sources map but are
    excluded from fusion by fuse_signals().
    """
    kept: List[ArenaSignal] = []
    for signal in signals:
        age = signal_age_days(signal, now)
        if age > DROP_AFTER_DAYS:
            continue
        horizon = MAX_AGE_DAYS.get(source_of_signal(signal.source), 7)
        signal.stale = age > horizon
        kept.append(signal)
    return kept


# ── Source adapters ────────────────────────────────────────────────


class SourceAdapter(Protocol):
    """One external board/aggregator: fetch (or replay cache) and parse."""

    name: str

    def fetch(self, *, offline: bool = False, cache_dir: Optional[Path] = None) -> Dict[str, List[ArenaSignal]]:
        ...

    def parse(self, payload: Any, fetched_at: str) -> Dict[str, List[ArenaSignal]]:
        ...


class _BaseAdapter:
    """Shared fetch/cache/replay plumbing. Subclasses implement
    _fetch_remote() and parse()."""

    name = ""

    def fetch(self, *, offline: bool = False, cache_dir: Optional[Path] = None) -> Dict[str, List[ArenaSignal]]:
        cache_root = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
        if offline:
            payload, fetched_at = _read_latest_cache(cache_root, self.name)
            if payload is None:
                logger.warning("offline: no cache for %s under %s", self.name, cache_root)
                return {}
        else:
            payload = self._fetch_remote()
            fetched_at = _iso(_utc_now())
            _write_cache(cache_root, self.name, payload)
        return self.parse(payload, fetched_at)

    def _fetch_remote(self) -> Any:
        raise NotImplementedError

    def parse(self, payload: Any, fetched_at: str) -> Dict[str, List[ArenaSignal]]:
        raise NotImplementedError


class ArtificialAnalysisAdapter(_BaseAdapter):
    """artificialanalysis.ai v2 language-models API.

    Rows are keyed (model_slug, reasoning_effort or "default") — the
    effort variant rides the external id as "<slug>::<effort>" and is
    stripped again before registry matching.
    """

    name = "artificialanalysis"

    def _fetch_remote(self) -> Any:
        key = get_secret("ARTIFICIALANALYSIS_API_KEY", provider="artificialanalysis")
        if not key:
            raise RuntimeError("no key resolvable for ARTIFICIALANALYSIS_API_KEY")
        resp = requests.get(AA_URL, headers={"x-api-key": key}, timeout=FETCH_TIMEOUT_S)
        resp.raise_for_status()
        return resp.json()

    def parse(self, payload: Any, fetched_at: str) -> Dict[str, List[ArenaSignal]]:
        rows = payload.get("data", []) if isinstance(payload, dict) else payload
        out: Dict[str, List[ArenaSignal]] = {}
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            slug = row.get("model_slug") or row.get("slug") or row.get("id") or row.get("name")
            if not slug:
                continue
            effort = str(row.get("reasoning_effort") or "default")
            ext_id = slug if effort == "default" else slug + "::" + effort
            evals = row.get("evaluations") or {}
            signals: List[ArenaSignal] = []
            index = evals.get("artificial_analysis_intelligence_index", row.get("intelligence_index"))
            if index is not None:
                signals.append(ArenaSignal(
                    "aa_intelligence_index",
                    {"model_slug": slug, "reasoning_effort": effort, "value": index},
                    normalize_index(index), "tier2", fetched_at,
                ))
            coding = evals.get(
                "artificial_analysis_coding_index",
                evals.get("livecodebench", row.get("coding_index")),
            )
            if coding is not None:
                signals.append(ArenaSignal(
                    "aa_coding",
                    {"model_slug": slug, "reasoning_effort": effort, "value": coding},
                    normalize_index(coding), "tier1", fetched_at,
                ))
            speed = row.get("median_output_tokens_per_second", row.get("output_tokens_per_second"))
            if speed is not None:
                signals.append(ArenaSignal(
                    "aa_speed",
                    {"model_slug": slug, "reasoning_effort": effort, "value": speed},
                    normalize_speed(speed), "meta", fetched_at,
                ))
            pricing = row.get("pricing")
            if pricing:
                signals.append(ArenaSignal(
                    "aa_price",
                    {"model_slug": slug, "reasoning_effort": effort, "pricing": pricing},
                    None, "meta", fetched_at,
                ))
            if signals:
                out.setdefault(ext_id, []).extend(signals)
        return out


class LMArenaAdapter(_BaseAdapter):
    """LMArena daily snapshots via the MIT mirror (api.wulong.dev).

    Text and code category boards; elo normalized over the 1000-1500
    band, clamped 0-1. No API key required.
    """

    name = "lmarena"
    CATEGORY_SIGNALS = {"text": "lmarena_elo", "code": "lmarena_code_elo"}

    def _fetch_remote(self) -> Any:
        resp = requests.get(LMARENA_URL, timeout=FETCH_TIMEOUT_S)
        resp.raise_for_status()
        return resp.json()

    def parse(self, payload: Any, fetched_at: str) -> Dict[str, List[ArenaSignal]]:
        categories = payload.get("categories", payload) if isinstance(payload, dict) else {}
        out: Dict[str, List[ArenaSignal]] = {}
        for category, signal_key in self.CATEGORY_SIGNALS.items():
            board = categories.get(category) or {}
            entries = board.get("entries", board if isinstance(board, list) else [])
            for entry in entries or []:
                if not isinstance(entry, dict):
                    continue
                model = entry.get("model") or entry.get("model_name") or entry.get("name")
                elo = entry.get("elo", entry.get("rating", entry.get("score")))
                if not model or elo is None:
                    continue
                out.setdefault(model, []).append(ArenaSignal(
                    signal_key,
                    {"model": model, "category": category, "elo": elo},
                    normalize_elo(float(elo)), "tier1", fetched_at,
                ))
        return out


class OpenRouterAdapter(_BaseAdapter):
    """OpenRouter rankings-daily: token-volume share, USAGE-ONLY.

    Normalized as share-of-peak tokens. Carries trust tier "usage";
    fuse_signals() excludes it from the capability mean, so usage can
    never raise a score — tie-break / confidence context only.
    """

    name = "openrouter"

    def _fetch_remote(self) -> Any:
        key = get_secret("OPENROUTER_API_KEY", provider="openrouter")
        headers = {"Authorization": "Bearer " + key} if key else {}
        resp = requests.get(OPENROUTER_RANKINGS_URL, headers=headers, timeout=FETCH_TIMEOUT_S)
        resp.raise_for_status()
        return resp.json()

    def parse(self, payload: Any, fetched_at: str) -> Dict[str, List[ArenaSignal]]:
        rows = payload.get("data", []) if isinstance(payload, dict) else payload
        usable: List[Tuple[str, float]] = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            model_id = row.get("model_id") or row.get("model") or row.get("id")
            tokens = row.get("total_tokens", row.get("tokens", row.get("count")))
            if model_id and tokens:
                usable.append((model_id, float(tokens)))
        if not usable:
            return {}
        peak = max(tokens for _, tokens in usable)
        out: Dict[str, List[ArenaSignal]] = {}
        for model_id, tokens in usable:
            share = tokens / peak if peak > 0 else 0.0
            out.setdefault(model_id, []).append(ArenaSignal(
                "openrouter_usage",
                {"model_id": model_id, "total_tokens": tokens},
                _clamp01(share), "usage", fetched_at,
            ))
        return out


ADAPTERS: Dict[str, type] = {
    ArtificialAnalysisAdapter.name: ArtificialAnalysisAdapter,
    LMArenaAdapter.name: LMArenaAdapter,
    OpenRouterAdapter.name: OpenRouterAdapter,
}


# ── Registry matching ──────────────────────────────────────────────


def _bare(name: str) -> str:
    """Bare lowercase model name with any org prefix stripped."""
    return name.split("/")[-1].strip().lower()


_VERSION_RUNS = re.compile("[0-9]+(?:[.][0-9]+)*")


def _stem_version_key(name: str) -> str:
    """Family stem + full digit-run sequence, e.g. "glm-5-2" -> "glm:5.2".

    Joins ALL digit runs so "glm-5-2" and "glm-5.2" collide with each
    other but not with plain "glm-5".
    """
    bare = _bare(name)
    stem = _family_stem(bare)
    runs = _VERSION_RUNS.findall(bare)
    if not stem or not runs:
        return ""
    return stem + ":" + ".".join(runs)


def load_overrides(path: Path = OVERRIDES_PATH) -> Dict[str, str]:
    """Flat {external_name: registry_id} map from the overrides file."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if isinstance(data, dict):
        overrides = data.get("overrides", data)
        if isinstance(overrides, dict):
            return {k: v for k, v in overrides.items() if isinstance(v, str)}
    return {}


def match_registry_model(
    external_id: str,
    registry_models: List[Dict[str, Any]],
    overrides: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """Map an external board name to a canonical registry model id.

    Order: overrides -> exact id -> case-insensitive id -> alias ->
    bare name (org prefix stripped) -> family-stem+version. Ambiguity
    (same bare name under several registry ids) resolves to the first
    active entry in registry order; pin with an override when that is
    not the intended canonical id.
    """
    if not external_id:
        return None
    ext = external_id.split("::", 1)[0].strip()  # drop reasoning-effort suffix
    if not ext:
        return None

    flat = overrides or {}
    if "overrides" in flat and isinstance(flat.get("overrides"), dict):
        flat = flat["overrides"]
    pinned = flat.get(ext) or flat.get(ext.lower())
    if pinned:
        return pinned

    def pick(candidates: List[Dict[str, Any]]) -> Optional[str]:
        if not candidates:
            return None
        for model in candidates:
            if model.get("status") == "active":
                return model.get("id")
        return candidates[0].get("id")

    exact = [m for m in registry_models if m.get("id") == ext]
    if exact:
        return pick(exact)

    low = ext.lower()
    ci = [m for m in registry_models if (m.get("id") or "").lower() == low]
    if ci:
        return pick(ci)

    alias_hits = [
        m for m in registry_models
        if any(alias.lower() == low for alias in (m.get("aliases") or []))
    ]
    if alias_hits:
        return pick(alias_hits)

    bare = _bare(ext)
    bare_hits = [
        m for m in registry_models
        if _bare(m.get("id") or "") == bare
        or any(_bare(alias) == bare for alias in (m.get("aliases") or []))
    ]
    if bare_hits:
        return pick(bare_hits)

    key = _stem_version_key(ext)
    if key:
        stem_hits = [
            m for m in registry_models
            if _stem_version_key(m.get("id") or "") == key
            or any(_stem_version_key(alias) == key for alias in (m.get("aliases") or []))
        ]
        if stem_hits:
            return pick(stem_hits)

    return None


def match_signals(
    per_source: Dict[str, Dict[str, List[ArenaSignal]]],
    registry_models: List[Dict[str, Any]],
    overrides: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, List[ArenaSignal]], Dict[str, List[str]]]:
    """({registry_id: signals}, {source: [unmatched external ids]})."""
    merged: Dict[str, List[ArenaSignal]] = {}
    unmatched: Dict[str, List[str]] = {}
    for source_name, by_ext in per_source.items():
        for ext_id, signals in by_ext.items():
            registry_id = match_registry_model(ext_id, registry_models, overrides)
            if registry_id is None:
                unmatched.setdefault(source_name, []).append(ext_id)
                continue
            for signal in signals:
                signal.raw.setdefault("external_id", ext_id)
            merged.setdefault(registry_id, []).extend(signals)
    for ids in unmatched.values():
        ids.sort()
    return merged, unmatched


# ── Fusion ─────────────────────────────────────────────────────────


def fuse_signals(
    signals: List[ArenaSignal],
    weights: Optional[Dict[str, float]] = None,
) -> Tuple[Optional[float], str]:
    """Trust-weighted mean over non-stale CAPABILITY signals.

    Usage signals (USAGE_SOURCES) are excluded from the mean and from
    the confidence count, so usage can never raise a score and a
    usage-only model reports (None, "no_data") — the no-data doctrine.
    Confidence: "high" for 2+ distinct capability sources, "medium"
    for exactly 1, "no_data" for 0.
    """
    table = TRUST_WEIGHTS if weights is None else weights
    capability = [
        s for s in signals
        if not s.stale
        and s.normalized is not None
        and s.source not in USAGE_SOURCES
        and table.get(s.source, 0.0) > 0.0
    ]
    if not capability:
        return None, "no_data"
    total_weight = sum(table[s.source] for s in capability)
    score = sum(table[s.source] * s.normalized for s in capability) / total_weight
    distinct_sources = {s.source for s in capability}
    confidence = "high" if len(distinct_sources) >= 2 else "medium"
    return score, confidence


# ── Scores overlay ─────────────────────────────────────────────────


def build_scores_overlay(
    registry: Dict[str, Any],
    per_source: Dict[str, Dict[str, List[ArenaSignal]]],
    overrides: Optional[Dict[str, str]] = None,
    *,
    include_no_data: bool = False,
    now: Optional[datetime] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Runtime scores overlay for ~/.nexus/arena/scores.json.

    NO-DATA DOCTRINE: a registry model absent from every source gets no
    entry, or — with include_no_data — an explicit no_data:true entry
    (reason attached for KNOWN_GAPS). A score is never synthesized.
    """
    registry_models = registry.get("models", []) if isinstance(registry, dict) else list(registry)
    merged, unmatched = match_signals(per_source, registry_models, overrides)

    models_out: Dict[str, Any] = {}
    for registry_id in sorted(merged):
        live = filter_stale(list(merged[registry_id]), now)
        score, confidence = fuse_signals(live, weights)
        sources: Dict[str, Any] = {}
        for signal in live:
            existing = sources.get(signal.source)
            candidate = {
                "normalized": None if signal.normalized is None else round(signal.normalized, 4),
                "trust_tier": signal.trust_tier,
                "fetched_at": signal.fetched_at,
                "stale": signal.stale,
                "external_id": signal.raw.get("external_id"),
            }
            if existing is None or (
                candidate["normalized"] is not None
                and (existing.get("normalized") or -1.0) < candidate["normalized"]
            ):
                sources[signal.source] = candidate
        entry: Dict[str, Any] = {
            "key": registry_id,
            "sources": sources,
            "arena_score": None if score is None else round(score, 4),
            "confidence": confidence,
            "no_data": score is None,
        }
        if score is None and registry_id in KNOWN_GAPS:
            entry["reason"] = KNOWN_GAPS[registry_id]
        if score is None and not sources and not include_no_data:
            continue  # everything dropped for age; nothing to report
        models_out[registry_id] = entry

    if include_no_data:
        for model in registry_models:
            registry_id = model.get("id")
            if not registry_id or registry_id in models_out:
                continue
            entry = {
                "key": registry_id,
                "sources": {},
                "arena_score": None,
                "confidence": "no_data",
                "no_data": True,
            }
            if registry_id in KNOWN_GAPS:
                entry["reason"] = KNOWN_GAPS[registry_id]
            models_out[registry_id] = entry

    overlay: Dict[str, Any] = {
        "version": 1,
        "generated_at": _iso(now or _utc_now()),
        "models": models_out,
    }
    if unmatched:
        overlay["unmatched"] = unmatched
    return overlay


def write_scores(overlay: Dict[str, Any], out_path: Path = SCORES_PATH) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(overlay, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


# ── CLI ────────────────────────────────────────────────────────────


def build_adapters(spec: Optional[str] = None) -> List[SourceAdapter]:
    if not spec or spec == "all":
        names = list(ADAPTERS)
    else:
        names = [part.strip() for part in spec.split(",") if part.strip()]
    unknown = [n for n in names if n not in ADAPTERS]
    if unknown:
        raise ValueError("unknown source(s): " + ", ".join(unknown) + " (known: " + ", ".join(ADAPTERS) + ")")
    return [ADAPTERS[name]() for name in names]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="arena_ingest",
        description="Ingest arena/leaderboard scores into the ~/.nexus/arena/scores.json sidecar.",
    )
    parser.add_argument("--source", default="all", help="comma-separated subset of: " + ", ".join(ADAPTERS))
    parser.add_argument("--offline", action="store_true", help="replay latest cached snapshots; no network")
    parser.add_argument("--cache-dir", default=None, help="raw snapshot cache root (default ~/.nexus/arena/raw)")
    parser.add_argument("--registry", default=str(REGISTRY_PATH), help="registry JSON path (read-only)")
    parser.add_argument("--overrides", default=str(OVERRIDES_PATH), help="name-overrides JSON path")
    parser.add_argument("--out", default=str(SCORES_PATH), help="scores overlay output path")
    parser.add_argument("--include-no-data", action="store_true", help="emit explicit no_data entries for uncovered registry models")
    args = parser.parse_args(argv)

    cache_dir = Path(args.cache_dir) if args.cache_dir else DEFAULT_CACHE_DIR
    per_source: Dict[str, Dict[str, List[ArenaSignal]]] = {}
    for adapter in build_adapters(args.source):
        try:
            per_source[adapter.name] = adapter.fetch(offline=args.offline, cache_dir=cache_dir)
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            logger.warning("%s fetch failed: %s", adapter.name, exc)
            per_source[adapter.name] = {}

    registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    overrides = load_overrides(Path(args.overrides))
    overlay = build_scores_overlay(registry, per_source, overrides, include_no_data=args.include_no_data)
    out_path = write_scores(overlay, Path(args.out))

    scored = [m for m in overlay["models"].values() if not m["no_data"]]
    no_data = [m for m in overlay["models"].values() if m["no_data"]]
    print("arena_ingest: " + str(len(scored)) + " scored, " + str(len(no_data)) + " no_data -> " + str(out_path))
    for source_name, ids in sorted((overlay.get("unmatched") or {}).items()):
        print("  unmatched[" + source_name + "]: " + str(len(ids)) + " (" + ", ".join(ids[:5]) + ")")
    top = sorted(scored, key=lambda m: -(m["arena_score"] or 0.0))[:10]
    for model in top:
        print("  " + format(model["arena_score"], ".4f") + "  " + model["confidence"].ljust(6) + "  " + model["key"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
