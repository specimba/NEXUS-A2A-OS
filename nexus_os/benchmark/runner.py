"""NEXUS-Bench core runner — orchestrates all 5 tracks."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import logging

logger = logging.getLogger(__name__)

BENCH_DB = Path(__file__).parent / "history.db"
REPORTS_DIR = Path(__file__).parent / "reports"


@dataclass
class TrackResult:
    """Result from a single benchmark track."""

    name: str
    score: float
    threshold: float
    status: str  # "PASS" or "FAIL"
    metrics: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


@dataclass
class BenchmarkResult:
    """Aggregated result from all tracks."""

    timestamp: str
    nexus_version: str
    tracks: dict[str, TrackResult]
    overall: str  # "PASS" or "FAIL"
    regressions: list[str] = field(default_factory=list)
    total_duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "nexus_version": self.nexus_version,
            "tracks": {
                name: {
                    "score": tr.score,
                    "threshold": tr.threshold,
                    "status": tr.status,
                    "metrics": tr.metrics,
                    "duration_seconds": tr.duration_seconds,
                    "errors": tr.errors,
                }
                for name, tr in self.tracks.items()
            },
            "overall": self.overall,
            "regressions": self.regressions,
            "total_duration_seconds": self.total_duration_seconds,
        }


class BenchmarkTrack:
    """Base class for a benchmark track."""

    name: str = "abstract"
    threshold: float = 0.0

    def run(self) -> TrackResult:
        raise NotImplementedError


class BenchmarkRunner:
    """Orchestrates benchmark execution across all tracks."""

    def __init__(self, tracks: list[BenchmarkTrack] | None = None):
        self._tracks: dict[str, BenchmarkTrack] = {}
        if tracks is None:
            tracks = self._default_tracks()
        for tr in tracks:
            self._tracks[tr.name] = tr

        self._ensure_db()

    def _default_tracks(self) -> list[BenchmarkTrack]:
        # Lazy import to avoid circular deps
        from .tracks.governance import GovernanceTrack
        from .tracks.security import SecurityTrack
        from .tracks.operations import OperationsTrack
        from .tracks.research import ResearchTrack
        from .tracks.integration import IntegrationTrack

        return [
            GovernanceTrack(),
            SecurityTrack(),
            OperationsTrack(),
            ResearchTrack(),
            IntegrationTrack(),
        ]

    # ── DB ──────────────────────────────────────────────────────────

    def _ensure_db(self) -> None:
        if not BENCH_DB.exists():
            conn = sqlite3.connect(BENCH_DB)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS benchmark_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    nexus_version TEXT,
                    overall TEXT,
                    total_duration_seconds REAL,
                    raw_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS track_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    track_name TEXT NOT NULL,
                    score REAL,
                    threshold REAL,
                    status TEXT,
                    duration_seconds REAL,
                    raw_json TEXT,
                    FOREIGN KEY (run_id) REFERENCES benchmark_runs(id)
                )
                """
            )
            conn.commit()
            conn.close()

    def save_history(self, result: BenchmarkResult) -> int:
        """Persist result to SQLite and return run_id."""
        conn = sqlite3.connect(BENCH_DB)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO benchmark_runs (timestamp, nexus_version, overall, total_duration_seconds, raw_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                result.timestamp,
                result.nexus_version,
                result.overall,
                result.total_duration_seconds,
                json.dumps(result.to_dict(), indent=2),
            ),
        )
        run_id = cur.lastrowid
        for tr in result.tracks.values():
            cur.execute(
                """
                INSERT INTO track_results (run_id, track_name, score, threshold, status, duration_seconds, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    tr.name,
                    tr.score,
                    tr.threshold,
                    tr.status,
                    tr.duration_seconds,
                    json.dumps({
                        "score": tr.score,
                        "threshold": tr.threshold,
                        "status": tr.status,
                        "metrics": tr.metrics,
                        "errors": tr.errors,
                    }),
                ),
            )
        conn.commit()
        conn.close()
        logger.info("Benchmark history saved: run_id=%d", run_id)
        return run_id

    def load_history(self, days: int = 30) -> list[BenchmarkResult]:
        """Load previous benchmark results for trend analysis."""
        conn = sqlite3.connect(BENCH_DB)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT raw_json FROM benchmark_runs
            WHERE timestamp > datetime('now', '-{} days')
            ORDER BY timestamp DESC
            """.format(days)
        )
        rows = cur.fetchall()
        conn.close()
        results = []
        for (raw_json,) in rows:
            d = json.loads(raw_json)
            tracks = {
                name: TrackResult(
                    name=name,
                    score=tr["score"],
                    threshold=tr["threshold"],
                    status=tr["status"],
                    metrics=tr.get("metrics", {}),
                    duration_seconds=tr.get("duration_seconds", 0.0),
                    errors=tr.get("errors", []),
                )
                for name, tr in d["tracks"].items()
            }
            results.append(
                BenchmarkResult(
                    timestamp=d["timestamp"],
                    nexus_version=d["nexus_version"],
                    tracks=tracks,
                    overall=d["overall"],
                    regressions=d.get("regressions", []),
                    total_duration_seconds=d.get("total_duration_seconds", 0.0),
                )
            )
        return results

    # ── Execution ───────────────────────────────────────────────────

    def run_all(self) -> BenchmarkResult:
        """Run all registered tracks."""
        return self.run_tracks(list(self._tracks.keys()))

    def run_track(self, name: str) -> BenchmarkResult:
        """Run a single track by name."""
        return self.run_tracks([name])

    def run_tracks(self, names: list[str]) -> BenchmarkResult:
        """Run a subset of tracks."""
        timestamp = datetime.now(timezone.utc).isoformat()
        version = "3.1.0"  # TODO: read from pyproject.toml or __version__

        tracks: dict[str, TrackResult] = {}
        overall_pass = True
        total_duration = 0.0

        for name in names:
            if name not in self._tracks:
                logger.error("Unknown track: %s", name)
                continue
            track = self._tracks[name]
            logger.info("Running track: %s", name)
            start = time.monotonic()
            try:
                result = track.run()
            except Exception as e:
                logger.exception("Track %s failed: %s", name, e)
                result = TrackResult(
                    name=name,
                    score=0.0,
                    threshold=track.threshold,
                    status="FAIL",
                    errors=[str(e)],
                )
            result.duration_seconds = time.monotonic() - start
            tracks[name] = result
            total_duration += result.duration_seconds
            if result.status == "FAIL":
                overall_pass = False
                logger.warning("Track %s FAILED (score %.3f < threshold %.3f)", name, result.score, result.threshold)

        # Detect regressions
        regressions = self._detect_regressions(tracks)

        result = BenchmarkResult(
            timestamp=timestamp,
            nexus_version=version,
            tracks=tracks,
            overall="PASS" if overall_pass else "FAIL",
            regressions=regressions,
            total_duration_seconds=total_duration,
        )
        return result

    def _detect_regressions(self, current: dict[str, TrackResult]) -> list[str]:
        """Compare current scores against previous run to detect regressions."""
        regressions = []
        try:
            previous = self.load_history(days=7)
            if not previous:
                return regressions
            prev_tracks = previous[0].tracks
            for name, tr in current.items():
                if name in prev_tracks:
                    prev_score = prev_tracks[name].score
                    delta = prev_score - tr.score
                    if delta > 0.10:  # >10% drop
                        regressions.append(
                            f"{name}: {prev_score:.3f} → {tr.score:.3f} (-{delta:.3f})"
                        )
                        logger.warning("Regression detected: %s", regressions[-1])
        except Exception as e:
            logger.warning("Regression detection failed: %s", e)
        return regressions

    # ── Reporting ───────────────────────────────────────────────────

    def generate_report(self, result: BenchmarkResult, format: str = "json") -> str:
        """Generate a report in the specified format."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if format == "json":
            path = REPORTS_DIR / f"benchmark_{ts}.json"
            path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
            return str(path)

        if format == "markdown":
            path = REPORTS_DIR / f"benchmark_{ts}.md"
            path.write_text(self._to_markdown(result), encoding="utf-8")
            return str(path)

        if format == "html":
            path = REPORTS_DIR / f"benchmark_{ts}.html"
            path.write_text(self._to_html(result), encoding="utf-8")
            return str(path)

        raise ValueError(f"Unknown format: {format}")

    def _to_markdown(self, result: BenchmarkResult) -> str:
        lines = [
            "# NEXUS-Bench Report",
            "",
            f"**Timestamp:** {result.timestamp}",
            f"**NEXUS Version:** {result.nexus_version}",
            f"**Overall:** {'PASS ✅' if result.overall == 'PASS' else 'FAIL ❌'}",
            f"**Total Duration:** {result.total_duration_seconds:.1f}s",
            "",
            "## Track Results",
            "",
            "| Track | Score | Threshold | Status | Duration |",
            "|-------|-------|-----------|--------|----------|",
        ]
        for name, tr in result.tracks.items():
            status = "PASS ✅" if tr.status == "PASS" else "FAIL ❌"
            lines.append(
                f"| {name} | {tr.score:.3f} | {tr.threshold:.3f} | {status} | {tr.duration_seconds:.1f}s |"
            )
        lines.append("")
        if result.regressions:
            lines.append("## Regressions ⚠️")
            lines.append("")
            for reg in result.regressions:
                lines.append(f"- {reg}")
            lines.append("")
        lines.append("## Metrics")
        lines.append("")
        for name, tr in result.tracks.items():
            lines.append(f"### {name}")
            lines.append("")
            for k, v in tr.metrics.items():
                lines.append(f"- **{k}:** {v}")
            lines.append("")
        return "\n".join(lines)

    def _to_html(self, result: BenchmarkResult) -> str:
        # Simple HTML report — can be enhanced with charts later
        rows = ""
        for name, tr in result.tracks.items():
            color = "green" if tr.status == "PASS" else "red"
            rows += (
                f"<tr><td>{name}</td><td>{tr.score:.3f}</td>"
                f"<td>{tr.threshold:.3f}</td><td style='color:{color}'>{tr.status}</td>"
                f"<td>{tr.duration_seconds:.1f}s</td></tr>"
            )

        regressions = ""
        if result.regressions:
            regressions = "<h2>Regressions</h2><ul>"
            for reg in result.regressions:
                regressions += f"<li>{reg}</li>"
            regressions += "</ul>"

        metrics = ""
        for name, tr in result.tracks.items():
            metrics += f"<h3>{name}</h3><ul>"
            for k, v in tr.metrics.items():
                metrics += f"<li><b>{k}:</b> {v}</li>"
            metrics += "</ul>"

        overall_color = "green" if result.overall == "PASS" else "red"

        return f"""<!DOCTYPE html>
<html>
<head><title>NEXUS-Bench Report</title>
<style>
body {{ font-family: sans-serif; max-width: 900px; margin: 40px auto; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f2f2f2; }}
</style>
</head>
<body>
<h1>NEXUS-Bench Report</h1>
<p><b>Timestamp:</b> {result.timestamp}</p>
<p><b>NEXUS Version:</b> {result.nexus_version}</p>
<p><b>Overall:</b> <span style='color:{overall_color};font-weight:bold'>{result.overall}</span></p>
<p><b>Total Duration:</b> {result.total_duration_seconds:.1f}s</p>
<h2>Track Results</h2>
<table>
<tr><th>Track</th><th>Score</th><th>Threshold</th><th>Status</th><th>Duration</th></tr>
{rows}
</table>
{regressions}
<h2>Metrics</h2>
{metrics}
</body>
</html>"""
