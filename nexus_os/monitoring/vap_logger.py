"""
nexus_os/monitoring/vap_logger.py

Verifiable Audit Protocol (VAP) Event Logger.

Provides persistent, append-only SQLite logging for compliance events
across NEXUS OS subsystems: guard triggers, block decisions, trust
score changes, CSI verdicts, TokenGuard events.

Design:
  - Append-only: INSERT only, no UPDATE/DELETE methods.
  - Uses CURRENT_TIMESTAMP for all time fields.
  - Thread-safe via check_same_thread=False + WAL journal mode.
  - Schema: event_id (autoincrement), timestamp, event_type,
    source_agent, target, verdict, details_json.
"""

import json
import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = str(Path.cwd() / ".nexus" / "vap_events.db")


class VAPLogger:
    """Append-only VAP event logger backed by SQLite.

    All writes are INSERT-only.  There are no update or delete methods
    by design — the audit channel is immutable once written.
    """

    def __init__(self, db_path: Optional[str] = None):
        resolved = db_path or os.environ.get("NEXUS_VAP_DB") or _DEFAULT_DB_PATH
        self.db_path = str(Path(resolved).resolve())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(
            self.db_path, check_same_thread=False, timeout=30.0
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._setup_schema()

    def _setup_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vap_events (
                event_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                source_agent TEXT NOT NULL,
                target     TEXT NOT NULL DEFAULT '',
                verdict    TEXT NOT NULL DEFAULT '',
                details_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        self.conn.commit()

    # ── Append-only write ─────────────────────────────────────────────

    def log_event(
        self,
        event_type: str,
        source_agent: str,
        target: str = "",
        verdict: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Insert a single VAP event.  Returns the new event_id."""
        details_json = json.dumps(details or {}, sort_keys=True, default=str)
        with self._lock:
            cursor = self.conn.execute(
                """
                INSERT INTO vap_events
                    (event_type, source_agent, target, verdict, details_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event_type, source_agent, target, verdict, details_json),
            )
            self.conn.commit()
            return cursor.lastrowid or 0

    # ── Read helpers (no mutation) ────────────────────────────────────

    def query_events(
        self,
        event_type: Optional[str] = None,
        source_agent: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return recent events matching optional filters."""
        clauses: List[str] = []
        params: List[Any] = []
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        if source_agent:
            clauses.append("source_agent = ?")
            params.append(source_agent)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        rows = self.conn.execute(
            f"SELECT * FROM vap_events{where} ORDER BY event_id DESC LIMIT ?",
            tuple(params),
        ).fetchall()
        return [dict(row) for row in rows]

    def count_events(self, event_type: Optional[str] = None) -> int:
        if event_type:
            row = self.conn.execute(
                "SELECT COUNT(*) FROM vap_events WHERE event_type = ?",
                (event_type,),
            ).fetchone()
        else:
            row = self.conn.execute("SELECT COUNT(*) FROM vap_events").fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            logger.warning("VAPLogger close failed")
