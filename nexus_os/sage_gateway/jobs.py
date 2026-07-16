"""Durable proposal jobs for the NEXUS SAGE northbound boundary."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Callable
from uuid import uuid4


ALLOWED_WORKFLOWS = frozenset(
    {
        "grounding_audit",
        "evidence_search",
        "model_health_snapshot",
        "parallel_audit_proposal",
    }
)
DEFAULT_SAGE_JOB_RETENTION_HOURS = 24
MIN_SAGE_JOB_RETENTION_HOURS = 1
MAX_SAGE_JOB_RETENTION_HOURS = 168


def _bounded_retention_hours(value: int) -> int:
    return max(MIN_SAGE_JOB_RETENTION_HOURS, min(value, MAX_SAGE_JOB_RETENTION_HOURS))


def sage_job_retention_hours() -> int:
    """Return the bounded persistence window for SAGE proposal records."""

    raw_value = (
        os.environ.get("NEXUS_SAGE_JOB_RETENTION_HOURS")
        or str(DEFAULT_SAGE_JOB_RETENTION_HOURS)
    )
    try:
        configured = int(raw_value)
    except ValueError:
        configured = DEFAULT_SAGE_JOB_RETENTION_HOURS
    return _bounded_retention_hours(configured)


def _parse_utc_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def _normalized_utc_timestamp(value: str | datetime) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("SAGE timestamp must be timezone-aware")
        parsed = value.astimezone(timezone.utc)
    else:
        parsed = _parse_utc_timestamp(value)
    return parsed.isoformat()





@dataclass(frozen=True)
class SageJob:
    job_id: str
    principal: str
    workflow_type: str
    state: str
    parameters: dict[str, Any]
    proposal: dict[str, Any]
    created_at: str
    expires_at: str
    updated_at: str

@dataclass(frozen=True)
class SageJobSubmissionResult:
    state: str
    response: dict[str, Any] | None = None
    http_status: int | None = None



class SageJobStore:
    def __init__(
        self,
        path: str | Path,
        *,
        retention_hours: int | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = str(path)
        configured_retention = (
            sage_job_retention_hours()
            if retention_hours is None
            else _bounded_retention_hours(retention_hours)
        )
        self.retention_hours = configured_retention
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _now(self) -> datetime:
        current = self._now_provider()
        if current.tzinfo is None:
            raise ValueError("SAGE job clock must return a timezone-aware datetime")
        return current.astimezone(timezone.utc)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sage_jobs (
                    job_id TEXT PRIMARY KEY,
                    principal TEXT NOT NULL,
                    workflow_type TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    proposal_json TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (state IN ('pending_review','accepted','rejected','expired')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sage_job_idempotency (
                    principal TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    http_status INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    PRIMARY KEY (principal, operation, idempotency_key)
                )
                """
            )

            self._migrate_job_expiry(connection)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_sage_jobs_expires_at "
                "ON sage_jobs(expires_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_sage_idempotency_expires_at "
                "ON sage_job_idempotency(expires_at)"
            )
            self._purge_expired(connection, self._now())

    def _migrate_job_expiry(self, connection: sqlite3.Connection) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(sage_jobs)").fetchall()
        }
        if "expires_at" not in columns:
            connection.execute("ALTER TABLE sage_jobs ADD COLUMN expires_at TEXT")

        migration_now = self._now()
        legacy_rows = connection.execute(
            """
            SELECT job_id, created_at
            FROM sage_jobs
            WHERE expires_at IS NULL OR expires_at=''
            """
        ).fetchall()
        for row in legacy_rows:
            try:
                created_at = _parse_utc_timestamp(str(row["created_at"]))
                expires_at = created_at + timedelta(hours=self.retention_hours)
            except (TypeError, ValueError):
                expires_at = migration_now
            connection.execute(
                "UPDATE sage_jobs SET expires_at=? WHERE job_id=?",
                (_normalized_utc_timestamp(expires_at), row["job_id"]),
            )
        self._normalize_stored_timestamps(connection, migration_now)

    @staticmethod
    def _normalize_stored_timestamps(
        connection: sqlite3.Connection,
        migration_now: datetime,
    ) -> None:
        for row in connection.execute(
            "SELECT job_id, created_at, updated_at, expires_at FROM sage_jobs"
        ).fetchall():
            try:
                created_at = _normalized_utc_timestamp(str(row["created_at"]))
            except (TypeError, ValueError):
                created_at = str(row["created_at"])
            try:
                updated_at = _normalized_utc_timestamp(str(row["updated_at"]))
            except (TypeError, ValueError):
                updated_at = str(row["updated_at"])
            try:
                expires_at = _normalized_utc_timestamp(str(row["expires_at"]))
            except (TypeError, ValueError):
                expires_at = _normalized_utc_timestamp(migration_now)
            connection.execute(
                """
                UPDATE sage_jobs
                SET created_at=?, updated_at=?, expires_at=?
                WHERE job_id=?
                """,
                (created_at, updated_at, expires_at, row["job_id"]),
            )

        for row in connection.execute(
            """
            SELECT rowid AS retention_rowid, created_at, expires_at
            FROM sage_job_idempotency
            """
        ).fetchall():
            try:
                created_at = _normalized_utc_timestamp(str(row["created_at"]))
            except (TypeError, ValueError):
                created_at = str(row["created_at"])
            try:
                expires_at = _normalized_utc_timestamp(str(row["expires_at"]))
            except (TypeError, ValueError):
                expires_at = _normalized_utc_timestamp(migration_now)
            connection.execute(
                """
                UPDATE sage_job_idempotency
                SET created_at=?, expires_at=?
                WHERE rowid=?
                """,
                (created_at, expires_at, row["retention_rowid"]),
            )



    @staticmethod
    def _purge_expired(
        connection: sqlite3.Connection,
        now: datetime,
    ) -> None:
        expires_before = _normalized_utc_timestamp(now)
        connection.execute(
            """
            DELETE FROM sage_job_idempotency
            WHERE julianday(expires_at)<=julianday(?)
            """,
            (expires_before,),
        )
        connection.execute(
            "DELETE FROM sage_jobs WHERE julianday(expires_at)<=julianday(?)",
            (expires_before,),
        )
    def submit_idempotent(
        self,
        *,
        principal: str,
        workflow_type: str,
        parameters: dict[str, Any],
        proposal: dict[str, Any],
        idempotency_key: str,
        source_msg_id: str | None,
    ) -> SageJobSubmissionResult:
        if workflow_type not in ALLOWED_WORKFLOWS:
            raise ValueError(f"workflow is not allowlisted: {workflow_type}")
        canonical_payload = json.dumps(
            {
                "workflow_type": workflow_type,
                "parameters": parameters,
                "source_msg_id": source_msg_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        request_hash = hashlib.sha256(canonical_payload).hexdigest()
        job_id = f"sage-job-{uuid4().hex}"
        receipt_id = f"sage-receipt-{uuid4().hex}"
        now_dt = self._now()
        now = _normalized_utc_timestamp(now_dt)
        expires = _normalized_utc_timestamp(
            now_dt + timedelta(hours=self.retention_hours)
        )
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                self._purge_expired(connection, now_dt)
                existing = connection.execute(
                    """
                    SELECT request_hash, response_json, http_status, expires_at
                    FROM sage_job_idempotency
                    WHERE principal=? AND operation='submit_job' AND idempotency_key=?
                    """,
                    (principal, idempotency_key),
                ).fetchone()
                if existing is not None:
                    if existing["request_hash"] != request_hash:
                        connection.execute("COMMIT")
                        return SageJobSubmissionResult("conflict")
                    response = json.loads(existing["response_json"])
                    connection.execute("COMMIT")
                    return SageJobSubmissionResult("duplicate", response, existing["http_status"])
                connection.execute(
                    """
                    INSERT INTO sage_jobs (
                        job_id, principal, workflow_type, parameters_json, proposal_json,
                        state, created_at, updated_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, 'pending_review', ?, ?, ?)
                    """,
                    (
                        job_id,
                        principal,
                        workflow_type,
                        json.dumps(parameters, separators=(",", ":"), ensure_ascii=False),
                        json.dumps(proposal, separators=(",", ":"), ensure_ascii=False),
                        now,
                        now,
                        expires,
                    ),
                )
                response = {
                    "receipt_id": receipt_id,
                    "job_id": job_id,
                    "workflow_type": workflow_type,
                    "status": "pending_review",
                    "proposal": proposal,
                    "proposal_only": True,
                    "execution_allowed": False,
                    "approval_state": "pending",
                    "source_msg_id": source_msg_id,
                    "created_at": now,
                    "updated_at": now,
                    "expires_at": expires,
                }
                connection.execute(
                    """
                    INSERT INTO sage_job_idempotency (
                        principal, operation, idempotency_key, request_hash,
                        response_json, http_status, created_at, expires_at
                    ) VALUES (?, 'submit_job', ?, ?, ?, 202, ?, ?)
                    """,
                    (
                        principal,
                        idempotency_key,
                        request_hash,
                        json.dumps(response, separators=(",", ":"), ensure_ascii=False),
                        now,
                        expires,
                    ),
                )
                connection.execute("COMMIT")
                return SageJobSubmissionResult("created", response, 202)
            except Exception:
                connection.execute("ROLLBACK")
                raise

    def get(self, job_id: str, *, principal: str) -> SageJob | None:
        now = self._now()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                self._purge_expired(connection, now)
                row = connection.execute(
                    "SELECT * FROM sage_jobs WHERE job_id=? AND principal=?",
                    (job_id, principal),
                ).fetchone()
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        if row is None:
            return None
        return SageJob(
            job_id=row["job_id"],
            principal=row["principal"],
            workflow_type=row["workflow_type"],
            state=row["state"],
            parameters=json.loads(row["parameters_json"]),
            proposal=json.loads(row["proposal_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            expires_at=row["expires_at"],
        )


class SageRetentionSweepError(RuntimeError):
    """Raised when the fixed-purpose retention sweep cannot verify its database."""


def _launcher_default_sage_job_database_path() -> Path:
    local_app_data = (os.environ.get("LOCALAPPDATA") or "").strip()
    runtime_base = (
        Path(local_app_data).expanduser()
        if local_app_data
        else Path.home() / ".nexus_pi"
    )
    return (
        runtime_base
        / "NEXUS"
        / "sage_brain"
        / "state"
        / "sage_jobs.sqlite3"
    ).resolve()


def sage_job_database_path() -> Path:
    """Resolve the live SAGE job database without creating it."""

    canonical = _launcher_default_sage_job_database_path()
    configured = (os.environ.get("NEXUS_SAGE_RUNTIME_DIR") or "").strip()
    if not configured:
        return canonical

    configured_database = (
        Path(configured).expanduser() / "sage_jobs.sqlite3"
    ).resolve()
    if canonical.is_file():
        return canonical
    return configured_database


def sage_job_database_identity(path: str | Path) -> dict[str, Any]:
    """Return a non-revealing stable identity for scheduler reports."""

    resolved = Path(path).expanduser().resolve()
    return {
        "filename": resolved.name,
        "identity_sha256": hashlib.sha256(
            os.fsencode(str(resolved))
        ).hexdigest(),
        "exists": resolved.is_file(),
    }


_RETENTION_TABLES = {
    "jobs": "sage_jobs",
    "idempotency": "sage_job_idempotency",
}


def _empty_retention_counts() -> dict[str, dict[str, int]]:
    return {
        "jobs": {"total": 0, "expired": 0},
        "idempotency": {"total": 0, "expired": 0},
    }


def _retention_connection(path: Path, *, apply: bool) -> sqlite3.Connection:
    if apply:
        connection = sqlite3.connect(
            f"{path.as_uri()}?mode=rw",
            timeout=10,
            isolation_level=None,
            uri=True,
        )
    else:
        connection = sqlite3.connect(
            f"{path.as_uri()}?mode=ro",
            timeout=10,
            isolation_level=None,
            uri=True,
        )
        connection.execute("PRAGMA query_only=ON")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=10000")
    return connection


def _validate_retention_schema(connection: sqlite3.Connection) -> None:
    tables = {
        str(row["name"])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if not set(_RETENTION_TABLES.values()).issubset(tables):
        raise SageRetentionSweepError("SAGE retention database schema is incompatible")

    for table in _RETENTION_TABLES.values():
        columns = {
            str(row["name"])
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if "expires_at" not in columns:
            raise SageRetentionSweepError(
                "SAGE retention database schema is incompatible"
            )


def _retention_counts(
    connection: sqlite3.Connection,
    *,
    cutoff_at: str,
) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for label, table in _RETENTION_TABLES.items():
        row = connection.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                COALESCE(
                    SUM(
                        CASE
                            WHEN julianday(expires_at)<=julianday(?) THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS expired
            FROM {table}
            """,
            (cutoff_at,),
        ).fetchone()
        if row is None:
            raise SageRetentionSweepError("SAGE retention count failed")
        counts[label] = {
            "total": int(row["total"]),
            "expired": int(row["expired"]),
        }
    return counts


def sweep_expired_sage_jobs(
    path: str | Path,
    *,
    apply: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Report or purge only expired SAGE job and idempotency records."""

    if not isinstance(apply, bool):
        raise ValueError("apply must be a boolean")
    started = datetime.now(timezone.utc)
    cutoff = now or started
    if cutoff.tzinfo is None:
        raise ValueError("SAGE retention cutoff must be timezone-aware")
    cutoff = cutoff.astimezone(timezone.utc)
    resolved = Path(path).expanduser().resolve()
    identity = sage_job_database_identity(resolved)
    mode = "apply" if apply else "dry_run"
    empty_counts = _empty_retention_counts()

    if not resolved.exists():
        return {
            "schema": "nexus.sage-retention-sweep.v1",
            "ok": True,
            "state": "database_missing",
            "mode": mode,
            "applied": False,
            "started_at": started.isoformat(),
            "cutoff_at": cutoff.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "database": identity,
            "counts": {
                "before": empty_counts,
                "purged": {"jobs": 0, "idempotency": 0},
                "after": _empty_retention_counts(),
            },
        }
    if not resolved.is_file():
        raise SageRetentionSweepError("SAGE retention database is not a file")

    with closing(_retention_connection(resolved, apply=apply)) as connection:
        connection.execute("BEGIN IMMEDIATE" if apply else "BEGIN")
        try:
            _validate_retention_schema(connection)
            before = _retention_counts(
                connection,
                cutoff_at=cutoff.isoformat(),
            )
            if apply:
                SageJobStore._purge_expired(connection, cutoff)
                after = _retention_counts(
                    connection,
                    cutoff_at=cutoff.isoformat(),
                )
            else:
                after = {
                    label: dict(values)
                    for label, values in before.items()
                }
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise

    purged = {
        label: before[label]["total"] - after[label]["total"]
        for label in _RETENTION_TABLES
    }
    return {
        "schema": "nexus.sage-retention-sweep.v1",
        "ok": True,
        "state": "complete",
        "mode": mode,
        "applied": apply,
        "started_at": started.isoformat(),
        "cutoff_at": cutoff.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "database": identity,
        "counts": {
            "before": before,
            "purged": purged,
            "after": after,
        },
    }
