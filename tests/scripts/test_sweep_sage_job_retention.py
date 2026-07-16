from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

import pytest

from nexus_os.sage_gateway import jobs as sage_jobs
from nexus_os.sage_gateway.jobs import (
    SageJobStore,
    sage_job_database_path,
    sweep_expired_sage_jobs,
)
from scripts import sweep_sage_job_retention


def _submit(store: SageJobStore, *, key: str, query: str) -> str:
    result = store.submit_idempotent(
        principal="nexus-sage:sweep-test",
        workflow_type="evidence_search",
        parameters={"query": query, "sources": ["audit"]},
        proposal={"proposal_only": True, "execution_allowed": False},
        idempotency_key=key,
        source_msg_id=None,
    )
    assert result.response is not None
    return str(result.response["job_id"])


def _seed_mixed_expiry_database(database, started: datetime) -> tuple[str, str]:
    old_store = SageJobStore(
        database,
        retention_hours=1,
        now_provider=lambda: started,
    )
    expired_id = _submit(
        old_store,
        key="scheduled-sweep-expired",
        query="EXPIRED_PAYLOAD_MUST_NOT_APPEAR",
    )

    current_store = SageJobStore(
        database,
        retention_hours=24,
        now_provider=lambda: started,
    )
    current_id = _submit(
        current_store,
        key="scheduled-sweep-current",
        query="CURRENT_PAYLOAD_MUST_NOT_APPEAR",
    )
    return expired_id, current_id


def _job_ids(database) -> set[str]:
    with sqlite3.connect(database) as connection:
        return {
            str(row[0])
            for row in connection.execute("SELECT job_id FROM sage_jobs").fetchall()
        }


def _table_count(database, table: str) -> int:
    with sqlite3.connect(database) as connection:
        row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    assert row is not None
    return int(row[0])


def test_retention_sweep_defaults_to_read_only_report_without_payloads(
    tmp_path,
) -> None:
    started = datetime(2026, 7, 13, tzinfo=timezone.utc)
    cutoff = started + timedelta(hours=2)
    database = tmp_path / "sage_jobs.sqlite3"
    expired_id, current_id = _seed_mixed_expiry_database(database, started)

    report = sweep_expired_sage_jobs(database, apply=False, now=cutoff)

    assert report["ok"] is True
    assert report["mode"] == "dry_run"
    assert report["applied"] is False
    assert report["database"] == {
        "filename": "sage_jobs.sqlite3",
        "identity_sha256": report["database"]["identity_sha256"],
        "exists": True,
    }
    assert len(report["database"]["identity_sha256"]) == 64
    assert report["counts"]["before"] == {
        "jobs": {"total": 2, "expired": 1},
        "idempotency": {"total": 2, "expired": 1},
    }
    assert report["counts"]["purged"] == {"jobs": 0, "idempotency": 0}
    assert report["counts"]["after"] == report["counts"]["before"]
    assert _job_ids(database) == {expired_id, current_id}

    serialized = json.dumps(report, sort_keys=True)
    assert expired_id not in serialized
    assert current_id not in serialized
    assert "EXPIRED_PAYLOAD_MUST_NOT_APPEAR" not in serialized
    assert "CURRENT_PAYLOAD_MUST_NOT_APPEAR" not in serialized
    assert str(tmp_path) not in serialized


def test_retention_sweep_apply_purges_only_expired_rows(tmp_path) -> None:
    started = datetime(2026, 7, 13, tzinfo=timezone.utc)
    cutoff = started + timedelta(hours=2)
    database = tmp_path / "sage_jobs.sqlite3"
    expired_id, current_id = _seed_mixed_expiry_database(database, started)

    report = sweep_expired_sage_jobs(database, apply=True, now=cutoff)

    assert report["mode"] == "apply"
    assert report["applied"] is True
    assert report["counts"]["before"]["jobs"] == {"total": 2, "expired": 1}
    assert report["counts"]["purged"] == {"jobs": 1, "idempotency": 1}
    assert report["counts"]["after"] == {
        "jobs": {"total": 1, "expired": 0},
        "idempotency": {"total": 1, "expired": 0},
    }
    assert _job_ids(database) == {current_id}
    assert expired_id not in _job_ids(database)
    assert _table_count(database, "sage_job_idempotency") == 1


def test_sweep_uses_sqlite_time_semantics_for_equivalent_utc_forms(tmp_path) -> None:
    started = datetime(2026, 7, 13, tzinfo=timezone.utc)
    cutoff = started + timedelta(hours=24)
    database = tmp_path / "sage_jobs.sqlite3"
    store = SageJobStore(database, retention_hours=24, now_provider=lambda: started)
    _submit(store, key="equivalent-time-forms", query="time equivalence")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE sage_jobs SET expires_at=?",
            ("2026-07-14T00:00:00Z",),
        )
        connection.execute(
            "UPDATE sage_job_idempotency SET expires_at=?",
            ("2026-07-14T02:00:00+02:00",),
        )

    dry_run = sweep_expired_sage_jobs(database, apply=False, now=cutoff)
    assert dry_run["counts"]["before"] == {
        "jobs": {"total": 1, "expired": 1},
        "idempotency": {"total": 1, "expired": 1},
    }

    applied = sweep_expired_sage_jobs(database, apply=True, now=cutoff)
    assert applied["counts"]["purged"] == {"jobs": 1, "idempotency": 1}


def test_store_normalizes_valid_expiry_forms_during_initialization(tmp_path) -> None:
    started = datetime(2026, 7, 13, tzinfo=timezone.utc)
    database = tmp_path / "sage_jobs.sqlite3"
    store = SageJobStore(database, retention_hours=24, now_provider=lambda: started)
    _submit(store, key="normalize-time-forms", query="normalize timestamps")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE sage_jobs SET expires_at=?",
            ("2026-07-14T00:00:00Z",),
        )
        connection.execute(
            "UPDATE sage_job_idempotency SET expires_at=?",
            ("2026-07-14T02:00:00+02:00",),
        )

    SageJobStore(
        database,
        retention_hours=24,
        now_provider=lambda: started + timedelta(hours=1),
    )
    with sqlite3.connect(database) as connection:
        job_expiry = connection.execute("SELECT expires_at FROM sage_jobs").fetchone()
        idempotency_expiry = connection.execute(
            "SELECT expires_at FROM sage_job_idempotency"
        ).fetchone()

    assert job_expiry == ("2026-07-14T00:00:00+00:00",)
    assert idempotency_expiry == ("2026-07-14T00:00:00+00:00",)


def test_default_database_path_matches_launcher_state_root(
    monkeypatch,
    tmp_path,
) -> None:
    local_app_data = tmp_path / "LocalAppData"
    monkeypatch.delenv("NEXUS_SAGE_RUNTIME_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))

    expected = (
        local_app_data / "NEXUS" / "sage_brain" / "state" / "sage_jobs.sqlite3"
    ).resolve()
    assert sage_job_database_path() == expected

    repo_root = Path(__file__).resolve().parents[2]
    launcher = (repo_root / "scripts" / "start_sage_brain.ps1").read_text(
        encoding="utf-8"
    )
    assert r'$runtimeRoot = Join-Path $localAppData "NEXUS\sage_brain"' in launcher
    assert '$stateRoot = Join-Path $runtimeRoot "state"' in launcher


def test_standalone_cli_finds_live_launcher_default_without_runtime_env(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    local_app_data = tmp_path / "LocalAppData"
    monkeypatch.delenv("NEXUS_SAGE_RUNTIME_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    database = local_app_data / "NEXUS" / "sage_brain" / "state" / "sage_jobs.sqlite3"
    started = datetime.now(timezone.utc) - timedelta(hours=2)
    _seed_mixed_expiry_database(database, started)

    assert sweep_sage_job_retention.main([]) == 0
    report = json.loads(capsys.readouterr().out)

    assert report["database"]["exists"] is True
    assert report["state"] == "complete"
    assert report["counts"]["before"]["jobs"] == {"total": 2, "expired": 1}


def test_missing_override_cannot_hide_live_launcher_database(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    local_app_data = tmp_path / "LocalAppData"
    canonical = local_app_data / "NEXUS" / "sage_brain" / "state" / "sage_jobs.sqlite3"
    started = datetime.now(timezone.utc) - timedelta(hours=2)
    _seed_mixed_expiry_database(canonical, started)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setenv(
        "NEXUS_SAGE_RUNTIME_DIR",
        str(tmp_path / "stale-missing-runtime"),
    )

    assert sage_job_database_path() == canonical.resolve()
    assert sweep_sage_job_retention.main([]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["database"]["exists"] is True
    assert report["state"] == "complete"


def test_existing_override_cannot_hide_live_launcher_database(
    monkeypatch,
    tmp_path,
) -> None:
    local_app_data = tmp_path / "LocalAppData"
    canonical = local_app_data / "NEXUS" / "sage_brain" / "state" / "sage_jobs.sqlite3"
    stale_runtime = tmp_path / "stale-runtime"
    stale_database = stale_runtime / "sage_jobs.sqlite3"
    started = datetime(2026, 7, 13, tzinfo=timezone.utc)
    _seed_mixed_expiry_database(canonical, started)
    _seed_mixed_expiry_database(stale_database, started)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setenv("NEXUS_SAGE_RUNTIME_DIR", str(stale_runtime))

    assert sage_job_database_path() == canonical.resolve()


@pytest.mark.parametrize("apply", [False, True])
def test_retention_sweep_missing_database_is_noop_and_never_creates_it(
    tmp_path,
    apply: bool,
) -> None:
    database = tmp_path / "missing" / "sage_jobs.sqlite3"

    report = sweep_expired_sage_jobs(database, apply=apply)

    assert report["ok"] is True
    assert report["database"]["exists"] is False
    assert report["state"] == "database_missing"
    assert report["counts"]["before"] == {
        "jobs": {"total": 0, "expired": 0},
        "idempotency": {"total": 0, "expired": 0},
    }
    assert report["counts"]["purged"] == {"jobs": 0, "idempotency": 0}
    assert not database.exists()


def test_apply_never_recreates_database_if_it_disappears_before_open(
    monkeypatch,
    tmp_path,
) -> None:
    started = datetime(2026, 7, 13, tzinfo=timezone.utc)
    database = tmp_path / "sage_jobs.sqlite3"
    _seed_mixed_expiry_database(database, started)
    real_connect = sage_jobs.sqlite3.connect

    def disappear_then_connect(*args, **kwargs):
        database.unlink()
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(sage_jobs.sqlite3, "connect", disappear_then_connect)

    with pytest.raises(sqlite3.OperationalError):
        sweep_expired_sage_jobs(
            database,
            apply=True,
            now=started + timedelta(hours=2),
        )
    assert not database.exists()


def test_cli_is_dry_run_by_default_and_apply_is_explicit(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    runtime_dir = tmp_path / "sage-runtime"
    database = runtime_dir / "sage_jobs.sqlite3"
    started = datetime.now(timezone.utc) - timedelta(hours=2)
    expired_id, current_id = _seed_mixed_expiry_database(database, started)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.setenv("NEXUS_SAGE_RUNTIME_DIR", str(runtime_dir))

    assert sweep_sage_job_retention.main([]) == 0
    dry_run = json.loads(capsys.readouterr().out)
    assert dry_run["mode"] == "dry_run"
    assert dry_run["counts"]["purged"] == {"jobs": 0, "idempotency": 0}
    assert _job_ids(database) == {expired_id, current_id}

    assert sweep_sage_job_retention.main(["--apply"]) == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["mode"] == "apply"
    assert applied["counts"]["purged"] == {"jobs": 1, "idempotency": 1}
    assert _job_ids(database) == {current_id}
    assert str(runtime_dir) not in json.dumps(applied)


def test_cli_has_no_operator_job_or_database_delete_selector() -> None:
    with pytest.raises(SystemExit):
        sweep_sage_job_retention.main(["--job-id", "sage-job-forbidden"])
    with pytest.raises(SystemExit):
        sweep_sage_job_retention.main(["--database", "other.sqlite3", "--apply"])


def test_cli_schema_failure_is_generic_json_without_database_path(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    runtime_dir = tmp_path / "sage-runtime"
    runtime_dir.mkdir()
    database = runtime_dir / "sage_jobs.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE unrelated (value TEXT)")
    monkeypatch.setenv("NEXUS_SAGE_RUNTIME_DIR", str(runtime_dir))

    assert sweep_sage_job_retention.main([]) == 2
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is False
    assert payload["error_code"] == "sage_retention_sweep_failed"
    assert payload["database"]["filename"] == "sage_jobs.sqlite3"
    assert str(runtime_dir) not in json.dumps(payload)
    assert "unrelated" not in json.dumps(payload)
