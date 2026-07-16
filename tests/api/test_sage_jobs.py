from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

from nexus_os.sage_gateway.jobs import (
    DEFAULT_SAGE_JOB_RETENTION_HOURS,
    MAX_SAGE_JOB_RETENTION_HOURS,
    MIN_SAGE_JOB_RETENTION_HOURS,
    SageJobStore,
    sage_job_retention_hours,
)


class _MutableClock:
    def __init__(self, now: datetime) -> None:
        self.value = now

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **kwargs: int) -> None:
        self.value += timedelta(**kwargs)


def _submit(store: SageJobStore, *, key: str = "retention-key-001"):
    return store.submit_idempotent(
        principal="nexus-sage:test",
        workflow_type="evidence_search",
        parameters={"query": "Find relay health evidence.", "sources": ["audit"]},
        proposal={"proposal_only": True, "execution_allowed": False},
        idempotency_key=key,
        source_msg_id=None,
    )


def _table_count(path, table: str) -> int:
    with sqlite3.connect(path) as connection:
        row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    assert row is not None
    return int(row[0])


def test_retention_env_is_named_bounded_and_defaults_safely(monkeypatch) -> None:
    monkeypatch.delenv("NEXUS_SAGE_JOB_RETENTION_HOURS", raising=False)
    assert sage_job_retention_hours() == DEFAULT_SAGE_JOB_RETENTION_HOURS

    monkeypatch.setenv("NEXUS_SAGE_JOB_RETENTION_HOURS", "0")
    assert sage_job_retention_hours() == MIN_SAGE_JOB_RETENTION_HOURS

    monkeypatch.setenv("NEXUS_SAGE_JOB_RETENTION_HOURS", "9999")
    assert sage_job_retention_hours() == MAX_SAGE_JOB_RETENTION_HOURS

    monkeypatch.setenv("NEXUS_SAGE_JOB_RETENTION_HOURS", "not-an-integer")
    assert sage_job_retention_hours() == DEFAULT_SAGE_JOB_RETENTION_HOURS


def test_get_purges_job_and_idempotency_at_exact_expiry(tmp_path) -> None:
    started = datetime(2026, 7, 13, 1, 0, tzinfo=timezone.utc)
    clock = _MutableClock(started)
    database = tmp_path / "sage-jobs.sqlite3"
    store = SageJobStore(database, retention_hours=24, now_provider=clock)

    created = _submit(store)
    assert created.response is not None
    job_id = created.response["job_id"]
    assert created.response["expires_at"] == (
        started + timedelta(hours=24)
    ).isoformat()
    assert store.get(job_id, principal="nexus-sage:test") is not None

    clock.advance(hours=24)
    assert store.get(job_id, principal="nexus-sage:test") is None
    assert _table_count(database, "sage_jobs") == 0
    assert _table_count(database, "sage_job_idempotency") == 0

    recreated = _submit(store)
    assert recreated.state == "created"
    assert recreated.response is not None
    assert recreated.response["job_id"] != job_id


def test_submit_operation_purges_all_expired_records(tmp_path) -> None:
    clock = _MutableClock(datetime(2026, 7, 13, tzinfo=timezone.utc))
    database = tmp_path / "sage-jobs.sqlite3"
    store = SageJobStore(database, retention_hours=1, now_provider=clock)

    first = _submit(store, key="retention-key-old")
    assert first.response is not None
    old_job_id = first.response["job_id"]

    clock.advance(hours=1, seconds=1)
    second = _submit(store, key="retention-key-new")
    assert second.state == "created"
    assert store.get(old_job_id, principal="nexus-sage:test") is None
    assert _table_count(database, "sage_jobs") == 1
    assert _table_count(database, "sage_job_idempotency") == 1


def test_legacy_jobs_receive_deterministic_expiry_during_migration(tmp_path) -> None:
    database = tmp_path / "sage-jobs.sqlite3"
    created_at = datetime(2026, 7, 13, tzinfo=timezone.utc)
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE sage_jobs (
                job_id TEXT PRIMARY KEY,
                principal TEXT NOT NULL,
                workflow_type TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                proposal_json TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO sage_jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "sage-job-legacy",
                "nexus-sage:test",
                "evidence_search",
                '{"query":"legacy"}',
                '{"proposal_only":true}',
                "pending_review",
                created_at.isoformat(),
                created_at.isoformat(),
            ),
        )

    clock = _MutableClock(created_at + timedelta(hours=1))
    store = SageJobStore(database, retention_hours=24, now_provider=clock)
    migrated = store.get("sage-job-legacy", principal="nexus-sage:test")

    assert migrated is not None
    assert migrated.expires_at == (created_at + timedelta(hours=24)).isoformat()

