"""Durable SQLite repository for Sentinel cases."""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any

from nexus_os.db.manager import DatabaseManager
from nexus_os.sentinel.models import CaseRecord, EventRecord


class CaseNotFound(KeyError):
    pass


class VersionConflict(RuntimeError):
    pass


class IdempotencyConflict(RuntimeError):
    pass


class SentinelRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        self.conn = db.get_connection()
        self._lock = threading.RLock()
        self._setup_schema()

    def _setup_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sentinel_cases (
                case_id TEXT PRIMARY KEY,
                case_type TEXT NOT NULL,
                title TEXT NOT NULL,
                stage TEXT NOT NULL,
                version INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                policy_verdict TEXT,
                reason_codes TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0,
                trace_id TEXT NOT NULL,
                vap_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sentinel_events (
                event_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                case_version INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                previous_stage TEXT,
                new_stage TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                vap_id TEXT,
                policy_version TEXT NOT NULL,
                evidence_hashes TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL,
                previous_event_hash TEXT,
                event_hash TEXT,
                FOREIGN KEY(case_id) REFERENCES sentinel_cases(case_id)
            );
            CREATE TABLE IF NOT EXISTS sentinel_evidence (
                evidence_id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                source TEXT NOT NULL,
                grade TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(case_id, evidence_id)
            );
            CREATE TABLE IF NOT EXISTS sentinel_approvals (
                approval_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                approver_id TEXT NOT NULL,
                approver_role TEXT NOT NULL,
                approved INTEGER NOT NULL,
                notes_hash TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sentinel_verifications (
                verification_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                evaluation_event_id TEXT NOT NULL,
                remediation_id TEXT NOT NULL,
                attempt INTEGER NOT NULL,
                verified INTEGER NOT NULL,
                reason_codes TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sentinel_idempotency (
                idempotency_key TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_sentinel_events_case
                ON sentinel_events(case_id, case_version);
            """
        )
        columns = {
            row[1] for row in self.conn.execute("PRAGMA table_info(sentinel_events)").fetchall()
        }
        for name in ("previous_event_hash", "event_hash"):
            if name not in columns:
                self.conn.execute(f"ALTER TABLE sentinel_events ADD COLUMN {name} TEXT")
        self.conn.commit()

    @staticmethod
    def _case_from_row(row: tuple[Any, ...]) -> CaseRecord:
        return CaseRecord(
            case_id=row[0],
            case_type=row[1],
            title=row[2],
            stage=row[3],
            version=row[4],
            risk_level=row[5],
            policy_verdict=row[6],
            reason_codes=json.loads(row[7]),
            retry_count=row[8],
            trace_id=row[9],
            vap_id=row[10],
            created_at=row[11],
            updated_at=row[12],
        )

    def create_case(self, record: CaseRecord, event: EventRecord) -> None:
        with self._lock:
            try:
                self.conn.execute("BEGIN IMMEDIATE")
                self.conn.execute(
                    """INSERT INTO sentinel_cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record.case_id,
                        record.case_type,
                        record.title,
                        record.stage.value,
                        record.version,
                        record.risk_level.value,
                        record.policy_verdict.value if record.policy_verdict else None,
                        json.dumps(record.reason_codes),
                        record.retry_count,
                        record.trace_id,
                        record.vap_id,
                        record.created_at,
                        record.updated_at,
                    ),
                )
                self._insert_event(event)
                self.conn.commit()
            except Exception:
                self.conn.execute("ROLLBACK")
                raise

    def get_case(self, case_id: str) -> CaseRecord:
        cursor = self.conn.execute(
            """SELECT case_id, case_type, title, stage, version, risk_level,
                      policy_verdict, reason_codes, retry_count, trace_id, vap_id,
                      created_at, updated_at
               FROM sentinel_cases WHERE case_id = ?""",
            (case_id,),
        )
        row = self.conn.fetchone(cursor)
        if row is None:
            raise CaseNotFound(case_id)
        return self._case_from_row(row)

    def list_cases(self, limit: int = 100) -> list[CaseRecord]:
        cursor = self.conn.execute(
            """SELECT case_id, case_type, title, stage, version, risk_level,
                      policy_verdict, reason_codes, retry_count, trace_id, vap_id,
                      created_at, updated_at
               FROM sentinel_cases ORDER BY updated_at DESC LIMIT ?""",
            (limit,),
        )
        return [self._case_from_row(row) for row in self.conn.fetchall(cursor)]

    def update_case(self, record: CaseRecord, expected_version: int, event: EventRecord) -> None:
        with self._lock:
            try:
                self.conn.execute("BEGIN IMMEDIATE")
                cursor = self.conn.execute(
                    """UPDATE sentinel_cases
                       SET stage = ?, version = ?, risk_level = ?, policy_verdict = ?,
                           reason_codes = ?, retry_count = ?, trace_id = ?, vap_id = ?,
                           updated_at = ?
                       WHERE case_id = ? AND version = ?""",
                    (
                        record.stage.value,
                        record.version,
                        record.risk_level.value,
                        record.policy_verdict.value if record.policy_verdict else None,
                        json.dumps(record.reason_codes),
                        record.retry_count,
                        record.trace_id,
                        record.vap_id,
                        record.updated_at,
                        record.case_id,
                        expected_version,
                    ),
                )
                if cursor.rowcount != 1:
                    raise VersionConflict(
                        f"case {record.case_id} expected version {expected_version}"
                    )
                self._insert_event(event)
                self.conn.commit()
            except Exception:
                self.conn.execute("ROLLBACK")
                raise

    @staticmethod
    def _calculate_event_hash(event: EventRecord, previous_hash: str | None) -> str:
        payload = event.model_dump(mode="json", exclude={"event_hash", "previous_event_hash"})
        payload["previous_event_hash"] = previous_hash
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _latest_event_hash(self, case_id: str) -> str | None:
        cursor = self.conn.execute(
            """SELECT event_hash FROM sentinel_events
               WHERE case_id = ? ORDER BY case_version DESC, created_at DESC LIMIT 1""",
            (case_id,),
        )
        row = self.conn.fetchone(cursor)
        return row[0] if row else None

    def _insert_event(self, event: EventRecord) -> None:
        previous_hash = self._latest_event_hash(event.case_id)
        event_hash = self._calculate_event_hash(event, previous_hash)
        self.conn.execute(
            """INSERT INTO sentinel_events
               (event_id, case_id, case_version, event_type, actor_id,
                previous_stage, new_stage, trace_id, vap_id, policy_version,
                evidence_hashes, details, created_at, previous_event_hash, event_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_id,
                event.case_id,
                event.case_version,
                event.event_type,
                event.actor_id,
                event.previous_stage.value if event.previous_stage else None,
                event.new_stage.value,
                event.trace_id,
                event.vap_id,
                event.policy_version,
                json.dumps(event.evidence_hashes),
                json.dumps(event.details, sort_keys=True),
                event.created_at,
                previous_hash,
                event_hash,
            ),
        )
    def add_evidence(self, case_id: str, refs: list, created_at: str) -> None:
        with self._lock:
            for ref in refs:
                self.conn.execute(
                    """INSERT OR IGNORE INTO sentinel_evidence
                       (evidence_id, case_id, sha256, source, grade, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (ref.evidence_id, case_id, ref.sha256, ref.source, ref.grade, created_at),
                )
            self.conn.commit()

    def add_approval(self, values: dict[str, Any]) -> None:
        with self._lock:
            self.conn.execute(
                """INSERT INTO sentinel_approvals
                   (approval_id, case_id, approver_id, approver_role, approved,
                    notes_hash, trace_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    values["approval_id"],
                    values["case_id"],
                    values["approver_id"],
                    values["approver_role"],
                    int(values["approved"]),
                    values["notes_hash"],
                    values["trace_id"],
                    values["created_at"],
                ),
            )
            self.conn.commit()

    def latest_approval(self, case_id: str) -> dict[str, Any] | None:
        cursor = self.conn.execute(
            """SELECT approver_id, approver_role, approved, trace_id, created_at
               FROM sentinel_approvals WHERE case_id = ?
               ORDER BY created_at DESC LIMIT 1""",
            (case_id,),
        )
        row = self.conn.fetchone(cursor)
        if row is None:
            return None
        return {
            "approver_id": row[0],
            "approver_role": row[1],
            "approved": bool(row[2]),
            "trace_id": row[3],
            "created_at": row[4],
        }

    def add_verification(self, values: dict[str, Any]) -> None:
        with self._lock:
            self.conn.execute(
                """INSERT INTO sentinel_verifications
                   (verification_id, case_id, evaluation_event_id, remediation_id,
                    attempt, verified, reason_codes, trace_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    values["verification_id"],
                    values["case_id"],
                    values["evaluation_event_id"],
                    values["remediation_id"],
                    values["attempt"],
                    int(values["verified"]),
                    json.dumps(values["reason_codes"]),
                    values["trace_id"],
                    values["created_at"],
                ),
            )
            self.conn.commit()

    def get_event(self, event_id: str) -> EventRecord | None:
        cursor = self.conn.execute(
            """SELECT event_id, case_id, case_version, event_type, actor_id,
                      previous_stage, new_stage, trace_id, vap_id, policy_version,
                      evidence_hashes, details, created_at, previous_event_hash, event_hash
               FROM sentinel_events WHERE event_id = ?""",
            (event_id,),
        )
        row = self.conn.fetchone(cursor)
        return self._event_from_row(row) if row else None

    @staticmethod
    def _event_from_row(row: tuple[Any, ...]) -> EventRecord:
        return EventRecord(
            event_id=row[0],
            case_id=row[1],
            case_version=row[2],
            event_type=row[3],
            actor_id=row[4],
            previous_stage=row[5],
            new_stage=row[6],
            trace_id=row[7],
            vap_id=row[8],
            policy_version=row[9],
            evidence_hashes=json.loads(row[10]),
            details=json.loads(row[11]),
            created_at=row[12],
            previous_event_hash=row[13],
            event_hash=row[14],
        )

    def timeline(self, case_id: str) -> list[EventRecord]:
        self.get_case(case_id)
        cursor = self.conn.execute(
            """SELECT event_id, case_id, case_version, event_type, actor_id,
                      previous_stage, new_stage, trace_id, vap_id, policy_version,
                      evidence_hashes, details, created_at, previous_event_hash, event_hash
               FROM sentinel_events WHERE case_id = ?
               ORDER BY case_version, created_at, event_id""",
            (case_id,),
        )
        return [self._event_from_row(row) for row in self.conn.fetchall(cursor)]

    def case_metrics(self, case_id: str) -> dict[str, int]:
        tables = {
            "evidence_count": "sentinel_evidence",
            "approval_count": "sentinel_approvals",
            "verification_count": "sentinel_verifications",
            "event_count": "sentinel_events",
        }
        metrics = {}
        for key, table in tables.items():
            cursor = self.conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE case_id = ?", (case_id,)
            )
            metrics[key] = int(self.conn.fetchone(cursor)[0])
        return metrics
    def get_idempotent(
        self, key: str, case_id: str, operation: str, request_hash: str
    ) -> dict[str, Any] | None:
        cursor = self.conn.execute(
            """SELECT case_id, operation, request_hash, response_json
               FROM sentinel_idempotency WHERE idempotency_key = ?""",
            (key,),
        )
        row = self.conn.fetchone(cursor)
        if row is None:
            return None
        if row[:3] != (case_id, operation, request_hash):
            raise IdempotencyConflict("idempotency key reused with different request")
        return json.loads(row[3])

    def save_idempotent(
        self,
        key: str,
        case_id: str,
        operation: str,
        request_hash: str,
        response: dict[str, Any],
    ) -> None:
        with self._lock:
            self.conn.execute(
                """INSERT INTO sentinel_idempotency
                   (idempotency_key, case_id, operation, request_hash, response_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (key, case_id, operation, request_hash, json.dumps(response, sort_keys=True)),
            )
            self.conn.commit()

    def close(self) -> None:
        self.db.close()
