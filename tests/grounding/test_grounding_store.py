import json
import sqlite3
from pathlib import Path

from nexus_os.grounding.models import GroundingEvent
from nexus_os.grounding.reliable_store import (
    ReliableGroundingStore,
    default_grounding_dir,
    grounding_dir_candidates,
)
from nexus_os.grounding.store import GroundingStore


def _event(path: Path, event_id: str = "ge-test") -> GroundingEvent:
    return GroundingEvent(
        event_id=event_id,
        source_id="test",
        path=str(path),
        size=4,
        mtime_ns=1,
        content_hash="abcd",
        source_kind="artifact",
    )


def test_store_appends_jsonl_and_indexes_with_delete_journal(tmp_path: Path):
    store = GroundingStore(tmp_path)
    store.append(_event(tmp_path / "a.txt"))

    line = json.loads(store.ledger_path.read_text(encoding="utf-8"))
    assert line["event_id"] == "ge-test"
    assert store.file_state(tmp_path / "a.txt")["content_hash"] == "abcd"
    with sqlite3.connect(store.index_path) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete"


def test_pending_count_is_source_scoped(tmp_path: Path):
    store = GroundingStore(tmp_path)
    event = _event(tmp_path / "queued.txt")
    object.__setattr__(event, "lifecycle_state", "queued")
    object.__setattr__(event, "source_id", "nexusclaw.worklog")
    store.append(event)

    assert store.pending_count("nexusclaw.worklog") == 1
    assert store.pending_count("other") == 0


def test_readonly_root_degrades_without_raising(tmp_path: Path, monkeypatch):
    """Doctor must not crash when the preferred root is not writable."""
    ro = tmp_path / "readonly_root"
    ro.mkdir()
    # Force probe failure for every candidate so explicit root degrades.
    monkeypatch.setattr(
        "nexus_os.grounding.reliable_store._path_is_writable",
        lambda path: False,
    )
    store = ReliableGroundingStore(ro)
    status = store.status()
    assert store.read_only is True
    assert status["read_only"] is True
    assert status["writable"] is False
    assert status["init_error"]


def test_default_grounding_dir_honors_writable_env(tmp_path: Path, monkeypatch):
    target = tmp_path / "env_grounding"
    monkeypatch.setenv("NEXUS_GROUNDING_ROOT", str(target))
    resolved = default_grounding_dir()
    assert resolved == target
    assert target.exists()
    assert any(p == target for p in grounding_dir_candidates())
