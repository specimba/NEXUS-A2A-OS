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
