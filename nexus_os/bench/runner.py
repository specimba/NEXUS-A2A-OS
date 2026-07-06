"""NEXUS-BENCH thin runner — FI-B1 Trust Ledger aggregation.

Not the Shadow Arena (deferred): this is the objective substrate — a
Beta-posterior leaderboard over verified outcomes that already exist on
disk, with zero new model calls:

- REASONS-DB trace records (~/.nexus/reasons_db/{trainable,reference});
  bench is EVALUATION, so reference-partition traces are legal here —
  the license partition only gates training.
- The hallucination-verdict ledger (~/.nexus/hallucination_verdicts.jsonl,
  live since P2-1), keyed by model.

Posterior per (model, domain) cell: Beta(1 + successes, 1 + failures);
the 95% interval is a Wilson score interval on the counts — closed form,
no scipy. Probe-replay scoring (scorer.score_set over live calls) is the
next FI-B increment, not this one.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

VERDICTS_PATH = Path.home() / ".nexus" / "hallucination_verdicts.jsonl"
_Z95 = 1.959963984540054

#: verdict risk levels that count as a failed outcome
RISKY_LEVELS = {"medium", "high"}


@dataclass
class TrustCell:
    model_id: str
    domain: str
    successes: int = 0
    failures: int = 0

    @property
    def n(self) -> int:
        return self.successes + self.failures

    @property
    def posterior_mean(self) -> float:
        return (1 + self.successes) / (2 + self.n)

    def interval(self) -> tuple[float, float]:
        """Wilson 95% interval over the observed counts."""
        n = self.n
        if n == 0:
            return (0.0, 1.0)
        p = self.successes / n
        z2 = _Z95 * _Z95
        denom = 1 + z2 / n
        center = (p + z2 / (2 * n)) / denom
        margin = (_Z95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
        return (max(0.0, center - margin), min(1.0, center + margin))

    def to_dict(self) -> dict:
        low, high = self.interval()
        return {
            "model_id": self.model_id,
            "domain": self.domain,
            "successes": self.successes,
            "failures": self.failures,
            "n": self.n,
            "posterior_mean": round(self.posterior_mean, 4),
            "ci95_low": round(low, 4),
            "ci95_high": round(high, 4),
        }


def _reasons_db_base() -> Path:
    return Path(os.environ.get(
        "NEXUS_REASONS_DB", Path.home() / ".nexus" / "reasons_db"
    ))


def iter_trace_outcomes(base_dir: Path | None = None) -> Iterator[tuple[str, str, bool]]:
    """(model_id, domain, ok) per model attempt across BOTH partitions."""
    from nexus_os.relay.tracing.record import TraceWriter

    base = base_dir or _reasons_db_base()
    for partition in ("trainable", "reference"):
        pdir = base / partition
        if not pdir.exists():
            continue
        writer = TraceWriter(base_dir=pdir)
        try:
            for rec in writer.iter_all():
                for attempt in rec.models_tried:
                    ok = attempt.outcome == "ok" and rec.outcome not in ("suspect", "error")
                    yield attempt.model_id, rec.domain or "general", ok
        finally:
            writer.close()


def iter_verdict_outcomes(path: Path | None = None) -> Iterator[tuple[str, str, bool]]:
    """(model, 'verdicts', ok) per hallucination-verdict ledger line.

    A verdict is a failure when its risk level is medium/high; unknown
    risk with zero score carries no signal and is skipped.
    """
    vpath = path or VERDICTS_PATH
    if not vpath.exists():
        return
    with vpath.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                v = json.loads(line)
            except ValueError:
                continue
            model = v.get("model")
            if not model:
                continue
            level = v.get("risk_level", "unknown")
            score = float(v.get("risk_score") or 0.0)
            if level == "unknown" and score == 0.0:
                continue  # no-signal placeholder rows
            yield str(model), "verdicts", level not in RISKY_LEVELS


def trust_leaderboard(
    *,
    domain: str | None = None,
    base_dir: Path | None = None,
    verdicts_path: Path | None = None,
) -> list[dict]:
    """Beta-posterior leaderboard rows, best posterior mean first."""
    cells: dict[tuple[str, str], TrustCell] = {}
    for source in (
        iter_trace_outcomes(base_dir),
        iter_verdict_outcomes(verdicts_path),
    ):
        for model_id, dom, ok in source:
            if domain and dom != domain:
                continue
            cell = cells.setdefault(
                (model_id, dom), TrustCell(model_id=model_id, domain=dom)
            )
            if ok:
                cell.successes += 1
            else:
                cell.failures += 1
    rows = [c.to_dict() for c in cells.values()]
    rows.sort(key=lambda r: (-r["posterior_mean"], -r["n"], r["model_id"]))
    return rows


def render_leaderboard(rows: list[dict]) -> str:
    if not rows:
        return ("No bench data yet — trust rows accrue from REASONS-DB traces "
                "and the hallucination-verdict ledger as the relay serves traffic.")
    lines = [f"{'MODEL':<42} {'DOMAIN':<10} {'N':>4} {'TRUST':>6}  95% CI"]
    for r in rows:
        lines.append(
            f"{r['model_id']:<42} {r['domain']:<10} {r['n']:>4} "
            f"{r['posterior_mean']:>6.3f}  [{r['ci95_low']:.3f}, {r['ci95_high']:.3f}]"
        )
    return "\n".join(lines)
