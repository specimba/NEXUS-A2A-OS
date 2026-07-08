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


# ── Probe-replay (FI-B increment 2 — log-28 Week-4e spec) ─────────────
#
# Replays the V1 probe sets through the relay adapter, scores with the
# rubric scorer, and persists per-dimension JSONL under ~/.nexus/bench/.
# Serial and RPM-paced from the registry v3 quota windows — NIM
# discipline (8 RPM, no parallelism) is enforced by construction.

import time as _time

BENCH_RESULTS_DIR = Path.home() / ".nexus" / "bench"
_DEFAULT_PACE_SECONDS = 10.0  # conservative when the provider RPM is unknown


def provider_pace_seconds(provider: str | None) -> float:
    """Seconds to wait between probe calls, from registry v3 quota windows."""
    if not provider:
        return _DEFAULT_PACE_SECONDS
    try:
        from nexus_os.model_relay.known_quotas_generated import KNOWN_QUOTAS_GENERATED
        rpm = (KNOWN_QUOTAS_GENERATED.get(provider) or {}).get("windows", {}).get("rpm")
        if rpm:
            return max(60.0 / float(rpm), 1.0)
    except ImportError:
        pass
    return _DEFAULT_PACE_SECONDS


def default_executor(prompt: str, *, model: str, provider: str | None = None,
                     temperature: float = 0.2, max_tokens: int = 1024):
    """One serial relay call. Returns response text ('' on failure)."""
    from nexus_os.relay.model_relay_adapter import ModelRelayAdapter, RelayRequest

    adapter = ModelRelayAdapter()
    result = adapter.execute(RelayRequest(
        model=model, prompt=prompt,
        temperature=temperature, max_tokens=max_tokens,
    ))
    return result.raw or ""


def run_probes(
    *,
    probeset: str = "v1",
    model: str = "auto",
    provider: str | None = None,
    executor=None,
    pace: bool = True,
    results_dir: Path | None = None,
    dimensions: list[str] | None = None,
) -> dict:
    """Replay a probe set against one model; score; persist; return a report.

    executor(prompt, model=..., provider=...) -> response text. Injectable
    for tests; defaults to the serial relay adapter. Probes run strictly
    serially with provider-RPM pacing (never parallel — NIM discipline).
    """
    if probeset != "v1":
        raise ValueError(f"unknown probeset: {probeset!r} (only 'v1' exists)")
    from nexus_os.bench.probes.probes_v1 import PROBE_SETS
    from nexus_os.bench.scorer import score_set

    run_executor = executor or default_executor
    out_dir = results_dir or BENCH_RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    delay = provider_pace_seconds(provider) if pace else 0.0

    report: dict = {
        "probeset": probeset, "model": model, "provider": provider,
        "dimensions": {}, "probes_run": 0,
    }
    started = _time.time()
    out_path = out_dir / f"probe_run_{model.replace('/', '_').replace(':', '_')}.jsonl"
    with out_path.open("a", encoding="utf-8") as fh:
        for pset in PROBE_SETS:
            if dimensions and pset.dimension_id not in dimensions:
                continue
            responses: dict[str, str] = {}
            for probe in pset.probes:
                try:
                    responses[probe["id"]] = run_executor(
                        probe["prompt"], model=model, provider=provider,
                    ) or ""
                except Exception:
                    responses[probe["id"]] = ""
                report["probes_run"] += 1
                if delay:
                    _time.sleep(delay)
            dim_score, details = score_set(
                pset.probes, responses, dimension_id=pset.dimension_id,
            )
            row = {
                "ts": _time.time(), "model": model, "provider": provider,
                "probeset": probeset, "dimension": pset.dimension_id,
                "title": pset.title, "score": dim_score.to_dict(),
                "details": [d.to_dict() for d in details],
            }
            fh.write(json.dumps(row, ensure_ascii=False) + chr(10))
            report["dimensions"][pset.dimension_id] = dim_score.to_dict()
    report["elapsed_s"] = round(_time.time() - started, 1)
    report["results_path"] = str(out_path)
    return report


def render_probe_report(report: dict) -> str:
    lines = [
        f"probeset={report['probeset']} model={report['model']} "
        f"provider={report['provider'] or '-'} probes={report['probes_run']} "
        f"elapsed={report.get('elapsed_s', '?')}s",
        f"{'DIM':<5} {'RAW':>6} {'BAND':<12} TITLE",
    ]
    from nexus_os.bench.probes.probes_v1 import PROBE_SETS
    titles = {p.dimension_id: p.title for p in PROBE_SETS}
    for dim, score in sorted(report["dimensions"].items()):
        lines.append(
            f"{dim:<5} {score.get('raw_score', 0.0):>6.3f} "
            f"{str(score.get('band', '?')):<12} {titles.get(dim, '')}"
        )
    lines.append(f"results: {report.get('results_path', '-')}")
    return chr(10).join(lines)
