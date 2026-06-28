"""Append-only grounding ledger with a rebuildable single-writer SQLite index."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable

from .models import GroundingEvent


def default_grounding_dir() -> Path:
    configured = os.environ.get("NEXUS_GROUNDING_ROOT")
    if configured:
        return Path(configured)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "NEXUS" / "grounding"
    return Path.home() / ".nexus" / "grounding"


class GroundingStore:
    """Durable event ledger.

    JSONL is authoritative. SQLite is an index and deliberately uses the
    rollback journal with one in-process writer.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root else default_grounding_dir()
        self.root.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.root / "events.jsonl"
        self.index_path = self.root / "grounding_index.sqlite3"
        self.cards_path = self.root / "source_cards.jsonl"
        self.proposals_dir = self.root / "proposals"
        self.proposals_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize_index()

    def _connect(self) -> sqlite3.Connection:
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

    def append(self, event: GroundingEvent) -> None:
        payload = event.to_dict()
        encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        with self._lock:
            with self.ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            with self._connect() as connection:
                connection.execute(
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
                )
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

    def append_card(self, card: dict[str, Any]) -> None:
        with self._lock:
            with self.cards_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(card, ensure_ascii=True, sort_keys=True) + "\n")

    def file_state(self, path: Path) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT size, mtime_ns, content_hash, last_event_id FROM file_state WHERE path=?",
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
        """Remove a deleted path from the rebuildable current-state index."""
        with self._connect() as connection:
            connection.execute("DELETE FROM file_state WHERE path=?", (str(path),))

    def pending_count(self, source_id: str | None = None) -> int:
        query = "SELECT COUNT(*) FROM events WHERE lifecycle_state='queued'"
        params: tuple[Any, ...] = ()
        if source_id:
            query += " AND source_id=?"
            params = (source_id,)
        with self._connect() as connection:
            return int(connection.execute(query, params).fetchone()[0])

    def status(self) -> dict[str, Any]:
        with self._connect() as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])
            files = int(connection.execute("SELECT COUNT(*) FROM file_state").fetchone()[0])
            states = dict(
                connection.execute(
                    "SELECT lifecycle_state, COUNT(*) FROM events GROUP BY lifecycle_state"
                ).fetchall()
            )
        return {
            "root": str(self.root),
            "ledger": str(self.ledger_path),
            "index": str(self.index_path),
            "journal_mode": "delete",
            "events": total,
            "files": files,
            "states": states,
        }

    def create_proposal(self, cards: Iterable[dict[str, Any]]) -> Path | None:
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
