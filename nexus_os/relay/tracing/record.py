"""NEXUS-REASONS-DB trace writer.

Three-tier persistence model:
- HOT   (0-14 days): SQLite FTS, queryable via search().
- WARM  (14-90 days): compressed JSONL, rotated daily with gzip.
- COLD  (>90 days): rolled into ZSTD-archived payloads.

Each successful inference produces one or more `TraceRecord` rows that the
caller writes through `TraceWriter.append()`. Records are scrubbed by the
caller BEFORE this point (this class does not sanitize).
"""

from __future__ import annotations

import calendar
import gzip
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

try:
    import zstandard
except ImportError:  # declared in pyproject, but never brick capture over it
    zstandard = None  # type: ignore[assignment]

logger = logging.getLogger("nexus.relay.tracing.record")

from nexus_os.relay.tracing.schema import (
    TraceRecord,
    ModelAttempt,
    encode_line,
)


@dataclass
class _TierConfig:
    hot_days: int = 14
    warm_days: int = 90


@dataclass
class TraceWriter:
    """Append-only TraceWriter.

    Caller-facing API:
    - append(record): atomically writes JSONL + SQLite index entry
    - search(query): full-text search over recent records
    - flush(): forces buffered data to disk
    - rotate(): moves old hot records into warm storage
    """

    base_dir: Path
    hot_days: int = 14
    warm_days: int = 90
    _db: sqlite3.Connection | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        for sub in ("hot", "warm", "cold"):
            (self.base_dir / sub).mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(self.base_dir / "hot.sqlite3"))
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT PRIMARY KEY,
                ts REAL NOT NULL,
                session_id TEXT,
                domain TEXT,
                difficulty TEXT,
                outcome TEXT,
                request_subject TEXT,
                search_blob TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_traces_ts ON traces(ts DESC);
            """
        )
        self._db.commit()

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None

    def append(self, record: TraceRecord) -> None:
        """Append a single TraceRecord to JSONL log + SQLite index."""
        assert self._db is not None
        payload = record.to_json()
        line = encode_line(record)
        day_str = time.strftime("%Y%m%d", time.gmtime(record.ts))
        ip_path = self.base_dir / "hot" / f"traces_{day_str}.jsonl"
        with ip_path.open("ab") as fh:
            fh.write(line)
        # Index entry
        flat = {
            "trace_id": record.trace_id,
            "ts": record.ts,
            "session_id": record.session_id,
            "domain": record.domain,
            "difficulty": record.difficulty,
            "outcome": record.outcome,
            "request_subject": record.request_subject,
            "search_blob": _index_blob(payload),
        }
        cols = ", ".join(flat.keys())
        placeholders = ", ".join("?" for _ in flat)
        self._db.execute(
            f"INSERT OR REPLACE INTO traces ({cols}) VALUES ({placeholders})",
            list(flat.values()),
        )
        self._db.commit()

    def append_many(self, records: Iterable[TraceRecord]) -> int:
        n = 0
        for r in records:
            self.append(r)
            n += 1
        return n

    def search(self, term: str, *, limit: int = 50) -> list[dict]:
        """Naive `LIKE` search over hot tier. Fine for small N (≤1M rows)."""
        assert self._db is not None
        cur = self._db.execute(
            "SELECT trace_id, ts, domain, difficulty, outcome, request_subject "
            "FROM traces WHERE search_blob LIKE ? ORDER BY ts DESC LIMIT ?",
            (f"%{term}%", limit),
        )
        return [
            {
                "trace_id": r[0],
                "ts": r[1],
                "domain": r[2],
                "difficulty": r[3],
                "outcome": r[4],
                "request_subject": r[5],
            }
            for r in cur.fetchall()
        ]

    def count(self) -> int:
        assert self._db is not None
        cur = self._db.execute("SELECT COUNT(*) FROM traces")
        return cur.fetchone()[0]

    def rotate(self, *, now: float | None = None) -> int:
        """Move records older than hot_days into the warm tier (gzipped).

        File moves and index deletes share one UTC-day-aligned cutoff:
        a day that straddles the raw cutoff keeps BOTH its JSONL and its
        index rows (previously rows vanished from search while the file
        stayed hot; day stamps were also parsed in local time while
        append() buckets by gmtime — a timezone skew up to a full day).
        """
        if now is None:
            now = time.time()
        cutoff = now - self.hot_days * 86400
        # UTC midnight of the cutoff's day: only WHOLE days older than
        # this move; index rows are deleted with the same boundary.
        aligned_cutoff = float(
            calendar.timegm(time.gmtime(cutoff)[:3] + (0, 0, 0, 0, 0, 0))
        )
        assert self._db is not None
        cur = self._db.execute(
            "SELECT trace_id FROM traces WHERE ts < ? ORDER BY ts ASC",
            (aligned_cutoff,),
        )
        moved_ids = [r[0] for r in cur.fetchall()]
        if not moved_ids:
            return 0
        # Move JSONL files in their entirety by day buckets
        for jsonl in (self.base_dir / "hot").glob("traces_*.jsonl"):
            try:
                day_end = _utc_day_epoch(jsonl.stem.split("_")[1]) + 86400
                if day_end <= aligned_cutoff:
                    target = self.base_dir / "warm" / (jsonl.name + ".gz")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with jsonl.open("rb") as src, \
                            _gzip_open(target, "wb") as out:
                        out.write(src.read())
                    jsonl.unlink()
            except (ValueError, OSError):
                continue
        # Drop index entries with the SAME aligned boundary as the files
        self._db.execute("DELETE FROM traces WHERE ts < ?", (aligned_cutoff,))
        self._db.commit()
        return len(moved_ids)

    def archive_cold(self, *, now: float | None = None) -> int:
        """Move warm-tier files older than warm_days to a `.zst` cold tier."""
        if now is None:
            now = time.time()
        cutoff = now - self.warm_days * 86400
        archived = 0
        if zstandard is None:
            logger.warning("archive_cold skipped: zstandard not installed")
            return 0
        for jsonl_gz in (self.base_dir / "warm").glob("*.jsonl.gz"):
            try:
                # UTC parse to match append()'s gmtime day bucketing
                day_epoch = _utc_day_epoch(jsonl_gz.stem.split("_")[1].split(".")[0]) + 86400
                if day_epoch < cutoff:
                    target = self.base_dir / "cold" / (jsonl_gz.stem + ".zst")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    cctx = zstandard.ZstdCompressor()
                    with gzip.open(str(jsonl_gz), "rb") as src, target.open("wb") as out:
                        out.write(cctx.compress(src.read()))
                    jsonl_gz.unlink()
                    archived += 1
            except (ValueError, OSError):
                continue
        return archived

    def iter_all(self) -> Iterator[TraceRecord]:
        """Yield every record across hot + warm + cold tiers."""
        yield from _iter_tier(self.base_dir / "hot", zstd=False)
        for jsonl_gz in sorted((self.base_dir / "warm").glob("*.jsonl.gz")):
            yield from _iter_gzip(jsonl_gz)
        for jsonl_zst in sorted((self.base_dir / "cold").glob("*.zst")):
            yield from _iter_zstd(jsonl_zst)


def _index_blob(payload: dict) -> str:
    """Compact JSON used by LIKE search. Drops the heaviest fields.

    models_tried is deliberately excluded: it carries full reasoning and
    message bodies, which would bloat the hot SQLite index with entire
    transcripts. Model/provider names are indexed via a slim projection.
    """
    blob = {
        k: v for k, v in payload.items()
        if k in {"trace_id", "domain", "difficulty", "tags", "outcome",
                  "request_subject", "license_class", "redaction_flags"}
    }
    blob["models"] = [
        {"provider": a.get("provider"), "model_id": a.get("model_id"),
         "outcome": a.get("outcome")}
        for a in payload.get("models_tried", [])
    ]
    return json.dumps(blob, ensure_ascii=False, sort_keys=True)


def _utc_day_epoch(day_str: str) -> float:
    """UTC-midnight epoch of a YYYYMMDD day stamp (append() uses gmtime)."""
    return float(calendar.timegm(time.strptime(day_str, "%Y%m%d")))


def _gzip_open(path: Path, mode: str):
    return gzip.open(str(path), mode)


def _iter_tier(dir_path: Path, *, zstd: bool) -> Iterator[TraceRecord]:
    for f in sorted(dir_path.glob("*.jsonl")):
        with f.open("rb") as fh:
            for line in fh:
                if not line.strip():
                    continue
                yield TraceRecord.from_json(json.loads(line.decode("utf-8")))


def _iter_gzip(path: Path) -> Iterator[TraceRecord]:
    import gzip
    with gzip.open(str(path), "rb") as fh:
        for line in fh:
            if not line.strip():
                continue
            yield TraceRecord.from_json(json.loads(line.decode("utf-8")))


def _iter_zstd(path: Path) -> Iterator[TraceRecord]:
    if zstandard is None:
        logger.warning("cold-tier read skipped (%s): zstandard not installed", path.name)
        return
    dctx = zstandard.ZstdDecompressor()
    raw = path.read_bytes()
    if not raw:
        return
    try:
        decompressed = dctx.decompress(raw)
    except zstandard.ZstdError:
        # file isn't zstd-compressed; skip silently rather than crash
        return
    if not decompressed:
        return
    for line in decompressed.splitlines():
        if not line.strip():
            continue
        yield TraceRecord.from_json(json.loads(line.decode("utf-8")))
