from pathlib import Path

from nexus_os.grounding.service import GroundingService
from nexus_os.grounding.store import GroundingStore


def test_delete_appends_tombstone_and_forgets_current_state(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    target = source / "removed.txt"
    target.write_text("evidence", encoding="utf-8")
    store = GroundingStore(tmp_path / "state")
    service = GroundingService(store=store, roots={"test": source})
    created = service.ingest_path("test", target, stability_delay_seconds=0)

    target.unlink()
    deleted = service.ingest_delete("test", target)

    assert created is not None
    assert deleted is not None
    assert deleted.parent_event_id == created.event_id
    assert deleted.metadata["event_type"] == "delete"
    assert store.file_state(target) is None
