"""NEXUS Frontier Scanner — delta detection."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from tools.frontier_scanner.signals.catalog_puller import (
    PROVIDER_PROFILES,
    ProviderCatalog,
    pull_all_catalogs,
    catalog_summary_text,
)


@dataclass
class DeltaReport:
    provider: str
    baseline_path: str
    new_ids: list[str] = field(default_factory=list)
    disappeared_ids: list[str] = field(default_factory=list)
    stable_ids: list[str] = field(default_factory=list)
    baseline_age_seconds: float = 0.0
    snapshot_age_seconds: float = 0.0
    reason: str = ""

    def to_json(self) -> dict:
        return {
            "provider": self.provider,
            "baseline_path": self.baseline_path,
            "new_ids": self.new_ids,
            "disappeared_ids": self.disappeared_ids,
            "stable_ids": self.stable_ids,
            "baseline_age_seconds": self.baseline_age_seconds,
            "snapshot_age_seconds": self.snapshot_age_seconds,
            "reason": self.reason,
        }


def load_catalog(path: Path) -> ProviderCatalog | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return ProviderCatalog(
        provider=payload.get("provider", ""),
        fetched_at=payload.get("fetched_at", 0.0),
        source_url=payload.get("source_url", ""),
        model_ids=list(payload.get("model_ids", [])),
        error=payload.get("error"),
        status=payload.get("status", "unknown"),
        raw_count=payload.get("raw_count", 0),
    )


def diff_catalogs(prev: ProviderCatalog, current: ProviderCatalog) -> DeltaReport:
    prev_ids = set(prev.model_ids)
    cur_ids = set(current.model_ids)
    return DeltaReport(
        provider=current.provider,
        baseline_path="",
        new_ids=sorted(cur_ids - prev_ids),
        disappeared_ids=sorted(prev_ids - cur_ids),
        stable_ids=sorted(cur_ids & prev_ids),
        baseline_age_seconds=max(0.0, time.time() - prev.fetched_at),
        snapshot_age_seconds=max(0.0, time.time() - current.fetched_at),
    )


def run_delta_pass(
    state_dir: Path,
    providers: Iterable[str] | None = None,
    save_snapshot: bool = True,
) -> dict[str, DeltaReport]:
    selected = list(providers) if providers else list(PROVIDER_PROFILES)
    state_dir.mkdir(parents=True, exist_ok=True)

    snapshot_subdir = state_dir / "_snapshots" / time.strftime("%Y%m%d_%H%M%S")
    snapshot_subdir.mkdir(parents=True, exist_ok=True)

    live = pull_all_catalogs(selected, state_dir=snapshot_subdir)
    reports: dict[str, DeltaReport] = {}
    for name, snapshot_cat in live.items():
        baseline_path = state_dir / f"catalog__{name}.json"
        baseline = load_catalog(baseline_path)
        if baseline is None or baseline.status not in ("ok", "no_list_endpoint"):
            reports[name] = DeltaReport(
                provider=name,
                baseline_path=str(baseline_path),
                reason=f"no_baseline_or_baseline_unhealthy:{baseline.status if baseline else 'missing'}",
            )
            continue
        report = diff_catalogs(baseline, snapshot_cat)
        report.baseline_path = str(baseline_path)
        reports[name] = report
        if save_snapshot:
            (snapshot_subdir / f"diff__{name}.json").write_text(
                json.dumps(report.to_json(), indent=2, sort_keys=True),
                encoding="utf-8",
            )

    return reports


def delta_summary_text(reports: dict[str, DeltaReport]) -> str:
    lines = []
    new_total = 0
    for name, r in sorted(reports.items()):
        new_count = len(r.new_ids)
        new_total += new_count
        if r.reason:
            lines.append(f"{name}: {r.reason}")
        elif new_count or r.disappeared_ids:
            lines.append(
                f"{name}: +{new_count} NEW, {len(r.disappeared_ids)} dropped, {len(r.stable_ids)} stable"
            )
        else:
            lines.append(f"{name}: stable ({len(r.stable_ids)} models, no delta)")
    lines.append(f"-- total new model IDs across providers: {new_total}")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run one delta-detection pass.")
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--providers", nargs="*", default=None)
    args = parser.parse_args()

    reports = run_delta_pass(Path(args.state_dir), args.providers)
    print(delta_summary_text(reports))
