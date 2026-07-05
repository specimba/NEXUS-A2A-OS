"""NEXUS Frontier Scanner — watchlist maintenance.

After a model ID passes 1-shot validation, it is added to the watchlist. Each
candidate is probed once per day for 3 days. After 3 consecutive passes, the
candidate is marked `graduated: true` and queued for stable registration.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Iterable

from tools.frontier_scanner.validate.probe import (
    ValidationResult,
    run_probe,
)


WATCHLIST_BASENAME = "watchlist.json"


@dataclass
class WatchEntry:
    provider: str
    model_id: str
    first_seen: float
    last_probed: float = 0.0
    probes: int = 0
    passes: int = 0
    failures: int = 0
    graduated: bool = False
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return asdict(self)


def _load_entries(state_path: Path) -> dict[str, WatchEntry]:
    if not state_path.exists():
        return {}
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, WatchEntry] = {}
    for key, entry in payload.items():
        out[key] = WatchEntry(
            provider=entry["provider"],
            model_id=entry["model_id"],
            first_seen=entry["first_seen"],
            last_probed=entry.get("last_probed", 0.0),
            probes=entry.get("probes", 0),
            passes=entry.get("passes", 0),
            failures=entry.get("failures", 0),
            graduated=entry.get("graduated", False),
            notes=list(entry.get("notes", [])),
        )
    return out


def _persist(state_path: Path, entries: dict[str, WatchEntry]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({k: v.to_json() for k, v in entries.items()}, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _key(provider: str, model_id: str) -> str:
    return f"{provider}::{model_id}"


def add_to_watchlist(
    state_dir: Path,
    provider: str,
    model_id: str,
    initial_validation: ValidationResult | None = None,
) -> WatchEntry:
    state_path = state_dir / WATCHLIST_BASENAME
    entries = _load_entries(state_path)
    key = _key(provider, model_id)
    if key in entries:
        return entries[key]
    entry = WatchEntry(
        provider=provider,
        model_id=model_id,
        first_seen=time.time(),
        last_probed=initial_validation.finished_at if initial_validation else 0.0,
        probes=1 if initial_validation else 0,
        passes=1 if initial_validation and initial_validation.decision.startswith("pass") else 0,
        failures=1 if initial_validation and not initial_validation.decision.startswith("pass") else 0,
    )
    entries[key] = entry
    _persist(state_path, entries)
    return entry


def probe_watchlist(
    state_dir: Path,
    providers: Iterable[str] | None = None,
    min_interval_seconds: int = 20 * 3600,
) -> list[ValidationResult]:
    """Probe each watchlist entry at most once per min_interval."""
    state_path = state_dir / WATCHLIST_BASENAME
    entries = _load_entries(state_path)
    results: list[ValidationResult] = []
    now = time.time()
    for key, entry in entries.items():
        if providers is not None and entry.provider not in providers:
            continue
        if entry.graduated:
            continue
        if entry.last_probed > 0 and (now - entry.last_probed) < min_interval_seconds:
            continue
        val = run_probe(entry.provider, entry.model_id, state_dir)
        entry.last_probed = val.finished_at
        entry.probes += 1
        if val.decision.startswith("pass"):
            entry.passes += 1
            if entry.passes >= 3:
                entry.graduated = True
                entry.notes.append(f"graduated at probe {entry.probes}")
        else:
            entry.failures += 1
            if entry.failures >= 3:
                entry.notes.append(f"retiring: {val.decision} @ probe {entry.probes}")
        results.append(val)
    _persist(state_path, entries)
    return results


def list_watchlist(state_dir: Path) -> list[WatchEntry]:
    return list(_load_entries(state_dir / WATCHLIST_BASENAME).values())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Maintain frontier watchlist.")
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--providers", nargs="*", default=None)
    args = parser.parse_args()

    state_dir = Path(args.state_dir)
    if args.probe:
        results = probe_watchlist(state_dir, providers=args.providers)
        for r in results:
            print(json.dumps(r.to_json(), indent=2, sort_keys=True))
    else:
        for entry in list_watchlist(state_dir):
            line = f"{entry.provider}/{entry.model_id} probes={entry.probes} passes={entry.passes} fails={entry.failures} graduated={entry.graduated}"
            print(line)
