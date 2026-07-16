import hashlib
import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock

from nexus_os.grounding.models import GroundingEvent
from nexus_os.grounding.service import GroundingService
from nexus_os.grounding.store import GroundingStore


def _event(path: Path, event_id: str = "ge-recovery") -> GroundingEvent:
    return GroundingEvent(
        event_id=event_id,
        source_id="test",
        path=str(path),
        size=7,
        mtime_ns=11,
        content_hash="a" * 64,
        source_kind="artifact",
    )


def test_event_lines_are_versioned_and_checksummed(tmp_path: Path):
    store = GroundingStore(tmp_path)
    store.append(_event(tmp_path / "evidence.txt"))

    payload = json.loads(store.ledger_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == 1
    assert payload["record_checksum"].startswith("sha256:")


def test_index_rebuild_skips_and_reports_corrupt_tail(tmp_path: Path):
    store = GroundingStore(tmp_path)
    event = _event(tmp_path / "evidence.txt")
    store.append(event)
    with store.ledger_path.open("ab") as handle:
        handle.write(b'{"event_id":"truncated"')
    with sqlite3.connect(store.index_path) as connection:
        connection.execute("DELETE FROM events")
        connection.execute("DELETE FROM file_state")

    rebuilt = GroundingStore(tmp_path)

    assert rebuilt.status()["events"] == 1
    assert rebuilt.status()["corrupt_lines"] == 1
    assert rebuilt.file_state(Path(event.path))["last_event_id"] == event.event_id


def test_ledger_audit_reports_only_hashed_corruption_metadata(tmp_path: Path):
    store = GroundingStore(tmp_path)
    store.append(_event(tmp_path / "before.txt", event_id="ge-before"))
    corrupt = b'{"broken":'
    with store.ledger_path.open("ab") as handle:
        handle.write(corrupt + b"\n")
    store.append(_event(tmp_path / "after.txt", event_id="ge-after"))
    before = store.ledger_path.read_bytes()

    report = store.audit_ledger()

    assert store.ledger_path.read_bytes() == before
    assert report["snapshot_stable"] is True
    assert report["physical_lines"] == 3
    assert report["invalid_count"] == 1
    record = report["invalid_records"][0]
    assert record == {
        "line_no": 2,
        "byte_length": len(corrupt),
        "sha256": "sha256:" + hashlib.sha256(corrupt).hexdigest(),
        "error": "json_decode",
        "detail": {"pos": 10, "lineno": 1, "colno": 11},
        "line_has_eol": True,
        "is_final_physical_line": False,
    }
    assert corrupt.decode("utf-8") not in json.dumps(report)


def test_ledger_quarantine_is_exact_backed_up_and_rebuilds_cleanly(
    tmp_path: Path,
):
    store = GroundingStore(tmp_path)
    store.append(_event(tmp_path / "before.txt", event_id="ge-before"))
    corrupt = b'{"broken":'
    with store.ledger_path.open("ab") as handle:
        handle.write(corrupt + b"\n")
    store.append(_event(tmp_path / "after.txt", event_id="ge-after"))
    with sqlite3.connect(store.index_path) as connection:
        connection.execute(
            """
            INSERT INTO events
            SELECT ?, source_id, path, size, mtime_ns, content_hash,
                   source_kind, evidence_grade, lifecycle_state, trace_id,
                   parent_event_id, observed_at, metadata_json
            FROM events LIMIT 1
            """,
            ("ge-stale-index-only",),
        )
        connection.execute(
            """
            INSERT INTO file_state
            SELECT ?, source_id, size, mtime_ns, content_hash,
                   last_event_id, observed_at
            FROM file_state LIMIT 1
            """,
            (str(tmp_path / "stale-index-only.txt"),),
        )
    assert store.status()["events"] == 3
    assert store.status()["files"] == 3
    before = store.ledger_path.read_bytes()
    record = store.audit_ledger()["invalid_records"][0]

    result = store.quarantine_ledger_record(
        expected_line=record["line_no"],
        expected_sha256=record["sha256"],
    )

    backup = Path(result["backup"])
    manifest = Path(result["manifest"])
    assert backup.read_bytes() == before
    assert manifest.exists()
    assert json.loads(manifest.read_text(encoding="utf-8")) == result
    assert corrupt not in store.ledger_path.read_bytes()
    assert result["record"]["sha256"] == record["sha256"]
    assert result["remaining_invalid_count"] == 0
    assert result["raw_record_in_manifest"] is False
    assert result["raw_record_preserved_in_backup"] is True
    assert store.audit_ledger()["invalid_count"] == 0
    assert store.status()["corrupt_lines"] == 0
    assert store.status()["events"] == 2
    assert store.status()["files"] == 2


def test_ledger_quarantine_keeps_recovery_manifest_if_rebuild_fails(
    tmp_path: Path,
):
    store = GroundingStore(tmp_path)
    corrupt = b'{"broken":'
    store.ledger_path.write_bytes(corrupt + b"\n")
    before = store.ledger_path.read_bytes()
    record = store.audit_ledger()["invalid_records"][0]
    store.rebuild_index = Mock(
        side_effect=RuntimeError("forced_rebuild_failure")
    )

    try:
        store.quarantine_ledger_record(
            expected_line=record["line_no"],
            expected_sha256=record["sha256"],
        )
    except RuntimeError as exc:
        assert str(exc) == "forced_rebuild_failure"
    else:
        raise AssertionError("forced rebuild failure did not propagate")

    quarantine_dir = tmp_path / "ledger_quarantine"
    manifests = list(quarantine_dir.glob("repair-*.json"))
    backups = list(quarantine_dir.glob("events-*.jsonl.bak"))
    assert len(manifests) == 1
    assert len(backups) == 1
    payload = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert payload["status"] == "prepared"
    assert payload["ledger_before"]["sha256"] == (
        "sha256:" + hashlib.sha256(before).hexdigest()
    )
    assert payload["ledger_after"]["sha256"] == (
        "sha256:" + hashlib.sha256(b"").hexdigest()
    )
    assert Path(payload["backup"]).read_bytes() == before
    assert backups[0].read_bytes() == before
    assert corrupt.decode("utf-8") not in json.dumps(payload)

def test_ledger_quarantine_rejects_wrong_hash_without_mutation(tmp_path: Path):
    store = GroundingStore(tmp_path)
    corrupt = b'{"broken":'
    store.ledger_path.write_bytes(corrupt + b"\n")
    before = store.ledger_path.read_bytes()

    try:
        store.quarantine_ledger_record(
            expected_line=1,
            expected_sha256="sha256:" + ("0" * 64),
        )
    except ValueError as exc:
        assert str(exc) == "expected_record_does_not_match_current_audit"
    else:
        raise AssertionError("wrong hash did not fail closed")

    assert store.ledger_path.read_bytes() == before
    assert not (tmp_path / "ledger_quarantine").exists()


def test_source_card_event_does_not_replace_file_observation_state(tmp_path: Path):
    store = GroundingStore(tmp_path)
    observed = _event(tmp_path / "paper.pdf", event_id="ge-observed")
    card = GroundingEvent(
        event_id="ge-card",
        source_id="test",
        path=observed.path,
        size=observed.size,
        mtime_ns=observed.mtime_ns,
        content_hash=observed.content_hash,
        source_kind="source_card",
        parent_event_id=observed.event_id,
    )

    store.append(observed)
    store.append(card)

    assert store.file_state(Path(observed.path))["last_event_id"] == observed.event_id


def test_reconcile_authorizes_scan_once_not_once_per_file(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "one.txt").write_text("one", encoding="utf-8")
    (source / "two.txt").write_text("two", encoding="utf-8")
    service = GroundingService(
        store=GroundingStore(tmp_path / "state"),
        roots={"test": source},
    )
    service.check_kaiju_authorization = Mock()

    service.reconcile(stability_delay_seconds=0)

    assert service.check_kaiju_authorization.call_count == 2
    service.check_kaiju_authorization.assert_any_call("execute")
    service.check_kaiju_authorization.assert_any_call("write")


def test_reconcile_uses_one_manifest_snapshot_not_per_file_queries(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    for index in range(12):
        (source / f"evidence-{index}.txt").write_text(str(index), encoding="utf-8")
    store = GroundingStore(tmp_path / "state")
    service = GroundingService(store=store, roots={"test": source})
    original_snapshot = store.file_state_snapshot
    store.file_state_snapshot = Mock(wraps=original_snapshot)
    store.file_state = Mock(side_effect=AssertionError("per-file SQLite lookup used"))

    first = service.reconcile(stability_delay_seconds=0)
    second = service.reconcile(stability_delay_seconds=0)

    assert first["ingested"] == 12
    assert second["ingested"] == 0
    assert store.file_state_snapshot.call_count == 2
    store.file_state.assert_not_called()
