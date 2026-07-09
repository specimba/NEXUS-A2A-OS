"""Crash-recoverable append-only grounding ledger implementation."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import threading
from pathlib import Path
from typing import Any, Iterable

from .models import GroundingEvent


def _path_is_writable(path: Path) -> bool:
    """Return True if path exists (or can be created) and supports write+sqlite."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / f".write_probe_{os.getpid()}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        # SQLite needs create/write on the directory (journal siblings).
        db_probe = path / f".sqlite_probe_{os.getpid()}.db"
        try:
            with sqlite3.connect(db_probe, timeout=5.0) as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS t (x INTEGER)")
                conn.execute("INSERT INTO t VALUES (1)")
        finally:
            try:
                db_probe.unlink(missing_ok=True)
            except OSError:
                pass
        return True
    except (OSError, sqlite3.Error):
        return False


def grounding_dir_candidates() -> list[Path]:
    """Ordered candidate roots; first writable wins in default_grounding_dir()."""
    candidates: list[Path] = []
    configured = os.environ.get("NEXUS_GROUNDING_ROOT")
    if configured:
        candidates.append(Path(configured))
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "NEXUS" / "grounding")
    candidates.append(Path.home() / ".nexus" / "grounding")
    candidates.append(Path(tempfile.gettempdir()) / "nexus_grounding")
    # Dedup while preserving order
    seen: set[str] = set()
    unique: list[Path] = []
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def default_grounding_dir() -> Path:
    """Pick the first writable grounding root (env override preferred)."""
    candidates = grounding_dir_candidates()
    # If NEXUS_GROUNDING_ROOT is set, try it first but fall through if RO.
    for path in candidates:
        if _path_is_writable(path):
            return path
    # Last resort: still return home path so callers get a stable string;
    # store init will surface degraded/readonly status.
    return Path.home() / ".nexus" / "grounding"


class ReliableGroundingStore:
    """JSONL source of truth with a rebuildable rollback-journal index."""

    NON_FILE_KINDS = {
        "source_card",
        "tombstone",
        "worklog",
        "browser_ai_cycle",
        "browser_ai_collaboration",
    }

    def __init__(self, root: Path | None = None) -> None:
        self._lock = threading.RLock()
        self._corrupt_lines = 0
        self.read_only = False
        self.init_error: str | None = None
        self.root = Path(root) if root is not None else default_grounding_dir()
        self._bind_paths()
        if not self._try_open_writable(self.root):
            # Explicit root (tests/callers) — degrade to read-only diagnostics
            # rather than crash. Env-selected root already fell through candidates.
            if root is not None:
                self.read_only = True
                self.init_error = (
                    f"grounding root not writable: {self.root}"
                )
                return
            for candidate in grounding_dir_candidates():
                if candidate == self.root:
                    continue
                if self._try_open_writable(candidate):
                    self.root = candidate
                    self._bind_paths()
                    self.init_error = None
                    self.read_only = False
                    break
            else:
                self.read_only = True
                self.init_error = (
                    f"no writable grounding root among "
                    f"{[str(p) for p in grounding_dir_candidates()]}"
                )
                return
        try:
            self._initialize_index()
            self.rebuild_index()
        except (OSError, sqlite3.Error) as exc:
            self.read_only = True
            self.init_error = f"{type(exc).__name__}: {exc}"

    def _bind_paths(self) -> None:
        self.ledger_path = self.root / "events.jsonl"
        self.index_path = self.root / "grounding_index.sqlite3"
        self.cards_path = self.root / "source_cards.jsonl"
        self.proposals_dir = self.root / "proposals"

    def _try_open_writable(self, root: Path) -> bool:
        """Create root layout if possible. Returns False on permission/IO failure."""
        try:
            root.mkdir(parents=True, exist_ok=True)
            (root / "proposals").mkdir(parents=True, exist_ok=True)
            if not _path_is_writable(root):
                return False
            return True
        except OSError:
            return False

    def _connect(self) -> sqlite3.Connection:
        if self.read_only and not self.index_path.exists():
            # Ephemeral in-memory index for doctor diagnostics only.
            connection = sqlite3.connect(":memory:", timeout=5.0)
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    mtime_ns INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    evidence_grade TEXT NOT NULL,
                    lifecycle_state TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    parent_event_id TEXT,
                    observed_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS file_state (
                    path TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    mtime_ns INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    last_event_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
                """
            )
            return connection
        connection = sqlite3.connect(self.index_path, timeout=30.0)
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _initialize_index(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    mtime_ns INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    evidence_grade TEXT NOT NULL,
                    lifecycle_state TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    parent_event_id TEXT,
                    observed_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_source_state
                    ON events(source_id, lifecycle_state);
                CREATE TABLE IF NOT EXISTS file_state (
                    path TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    mtime_ns INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    last_event_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
                """
            )

    def _require_writable(self) -> None:
        if self.read_only:
            raise PermissionError(
                self.init_error
                or f"grounding store is read-only at {self.root}"
            )

    @staticmethod
    def _encoded_payload(event: GroundingEvent) -> str:
        payload = event.to_dict()
        canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        payload["record_checksum"] = (
            "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        )
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)

    @staticmethod
    def _checksum_is_valid(payload: dict[str, Any]) -> bool:
        expected = payload.get("record_checksum")
        if expected is None:
            return True
        unsigned = dict(payload)
        unsigned.pop("record_checksum", None)
        canonical = json.dumps(unsigned, ensure_ascii=True, sort_keys=True)
        actual = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return expected == actual

    @classmethod
    def _tracks_file_state(cls, event: GroundingEvent) -> bool:
        return event.source_kind not in cls.NON_FILE_KINDS and "://" not in event.path

    def append(self, event: GroundingEvent) -> None:
        self._require_writable()
        encoded = self._encoded_payload(event)
        with self._lock:
            with self.ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            with self._connect() as connection:
                self._index_event(connection, event)

    def _index_event(
        self, connection: sqlite3.Connection, event: GroundingEvent
    ) -> None:
        inserted = connection.execute(
            """
            INSERT OR IGNORE INTO events VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.source_id,
                event.path,
                event.size,
                event.mtime_ns,
                event.content_hash,
                event.source_kind,
                event.evidence_grade,
                event.lifecycle_state,
                event.trace_id,
                event.parent_event_id,
                event.observed_at,
                json.dumps(event.metadata, ensure_ascii=True, sort_keys=True),
            ),
        ).rowcount
        if not inserted:
            return
        if event.source_kind == "tombstone":
            connection.execute("DELETE FROM file_state WHERE path=?", (event.path,))
            return
        if not self._tracks_file_state(event):
            return
        connection.execute(
            """
            INSERT INTO file_state VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                source_id=excluded.source_id,
                size=excluded.size,
                mtime_ns=excluded.mtime_ns,
                content_hash=excluded.content_hash,
                last_event_id=excluded.last_event_id,
                observed_at=excluded.observed_at
            """,
            (
                event.path,
                event.source_id,
                event.size,
                event.mtime_ns,
                event.content_hash,
                event.event_id,
                event.observed_at,
            ),
        )

    def rebuild_index(self) -> dict[str, int]:
        """Replay valid ledger records and report malformed/checksum-failed lines."""
        corrupt = 0
        recovered = 0
        if not self.ledger_path.exists():
            self._corrupt_lines = 0
            return {"recovered": 0, "corrupt_lines": 0}
        with self._lock, self._connect() as connection:
            for raw_line in self.ledger_path.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines():
                if not raw_line.strip():
                    continue
                try:
                    payload = json.loads(raw_line)
                    if not self._checksum_is_valid(payload):
                        raise ValueError("record checksum mismatch")
                    event = GroundingEvent.from_dict(payload)
                except (json.JSONDecodeError, TypeError, ValueError):
                    corrupt += 1
                    continue
                before = connection.total_changes
                self._index_event(connection, event)
                if connection.total_changes > before:
                    recovered += 1
        self._corrupt_lines = corrupt
        return {"recovered": recovered, "corrupt_lines": corrupt}

    def append_card(self, card: dict[str, Any]) -> None:
        self._require_writable()
        encoded = json.dumps(card, ensure_ascii=True, sort_keys=True)
        with self._lock:
            with self.cards_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded + "\n")
                handle.flush()
                os.fsync(handle.fileno())

    def file_state(self, path: Path) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT size, mtime_ns, content_hash, last_event_id "
                "FROM file_state WHERE path=?",
                (str(path),),
            ).fetchone()
        if row is None:
            return None
        return {
            "size": row[0],
            "mtime_ns": row[1],
            "content_hash": row[2],
            "last_event_id": row[3],
        }

    def forget_path(self, path: Path) -> None:
        self._require_writable()
        with self._connect() as connection:
            connection.execute("DELETE FROM file_state WHERE path=?", (str(path),))

    def pending_count(self, source_id: str | None = None) -> int:
        query = "SELECT COUNT(*) FROM events WHERE lifecycle_state='queued'"
        params: tuple[Any, ...] = ()
        if source_id:
            query += " AND source_id=?"
            params = (source_id,)
        try:
            with self._connect() as connection:
                return int(connection.execute(query, params).fetchone()[0])
        except (OSError, sqlite3.Error):
            return 0

    def status(self) -> dict[str, Any]:
        total = 0
        files = 0
        states: dict[str, int] = {}
        try:
            with self._connect() as connection:
                total = int(connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])
                files = int(connection.execute("SELECT COUNT(*) FROM file_state").fetchone()[0])
                states = dict(
                    connection.execute(
                        "SELECT lifecycle_state, COUNT(*) FROM events GROUP BY lifecycle_state"
                    ).fetchall()
                )
        except (OSError, sqlite3.Error) as exc:
            if self.init_error is None:
                self.init_error = f"{type(exc).__name__}: {exc}"
        return {
            "root": str(self.root),
            "ledger": str(self.ledger_path),
            "index": str(self.index_path),
            "journal_mode": "delete",
            "events": total,
            "files": files,
            "states": states,
            "corrupt_lines": self._corrupt_lines,
            "read_only": self.read_only,
            "writable": not self.read_only,
            "init_error": self.init_error,
        }

    def create_proposal(self, cards: Iterable[dict[str, Any]]) -> Path | None:
        self._require_writable()
        selected = [card for card in cards if card.get("evidence_grade") != "E0"]
        if not selected:
            return None
        proposal_id = f"grounding-{selected[0]['event_id']}"
        path = self.proposals_dir / f"{proposal_id}.json"
        payload = {
            "proposal_id": proposal_id,
            "status": "review_required",
            "canonical_mutation_allowed": False,
            "source_cards": selected,
            "required_checks": [
                "source_hash_verified",
                "contradictions_reviewed",
                "focused_tests_passed",
                "operator_approval",
            ],
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        return path
