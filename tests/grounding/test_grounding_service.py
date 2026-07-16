import json
import os
from pathlib import Path

import nexus_os.grounding.service as service_module
from nexus_os.grounding.service import GroundingService, is_sensitive_or_excluded
from nexus_os.grounding.store import GroundingStore


def test_incremental_scan_ingests_once_and_reingests_changed_content(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    target = source / "report.txt"
    target.write_text("first", encoding="utf-8")
    store = GroundingStore(tmp_path / "state")
    service = GroundingService(store=store, roots={"test": source})

    first = service.reconcile(stability_delay_seconds=0)
    unchanged = service.reconcile(stability_delay_seconds=0)
    target.write_text("second version", encoding="utf-8")
    changed = service.reconcile(stability_delay_seconds=0)

    assert first["ingested"] == 1
    assert unchanged["ingested"] == 0
    assert changed["ingested"] == 1
    assert store.status()["events"] == 2


def test_sensitive_and_generated_paths_are_excluded(tmp_path: Path):
    assert is_sensitive_or_excluded(Path(".env"))
    assert is_sensitive_or_excluded(Path("secret.pem"))
    assert is_sensitive_or_excluded(Path(".git") / "config")
    assert is_sensitive_or_excluded(Path("tests_tmp") / "generated.bin")
    assert is_sensitive_or_excluded(Path("pytest-cache-files-abc123") / "nodeids")
    assert is_sensitive_or_excluded(Path(".ruff_cache") / "cache.db")
    assert not is_sensitive_or_excluded(Path("paper.pdf"))


def test_grounding_kaiju_authorization_success(tmp_path: Path):
    from nexus_os.grounding.service import GroundingService
    from nexus_os.grounding.store import GroundingStore
    
    store = GroundingStore(tmp_path / "state")
    service = GroundingService(store=store, roots={})
    
    # Should not raise exception
    service.check_kaiju_authorization("execute")
    service.check_kaiju_authorization("write")
    service.check_kaiju_authorization("delete")


def test_grounding_kaiju_authorization_denied(tmp_path: Path):
    import pytest
    from nexus_os.grounding.service import GroundingService
    from nexus_os.grounding.store import GroundingStore
    
    store = GroundingStore(tmp_path / "state")
    
    # Denied due to low clearance (reader cannot do write/delete)
    service_low_clearance = GroundingService(store=store, roots={}, clearance="reader")
    with pytest.raises(PermissionError) as excinfo:
        service_low_clearance.reconcile()
    assert "KAIJU authorization denied" in str(excinfo.value)
    
    # Denied due to intent mismatch / too short intent
    service_bad_intent = GroundingService(
        store=store, 
        roots={}, 
        intent="ab"
    )
    with pytest.raises(PermissionError) as excinfo:
        service_bad_intent.reconcile()
    assert "KAIJU authorization denied" in str(excinfo.value)


def test_unknown_clearance_hard_fails(tmp_path: Path):
    """An unrecognized clearance string must deny, never silently upgrade
    to MAINTAINER (audit: fail-open at service clearance parsing)."""
    import pytest

    store = GroundingStore(tmp_path / "state")
    service = GroundingService(store=store, roots={}, clearance="garbage")
    with pytest.raises(PermissionError) as excinfo:
        service.check_kaiju_authorization("write")
    assert "unknown clearance" in str(excinfo.value)


def test_public_ingest_path_has_no_authorization_bypass(tmp_path: Path):
    """ingest_path must always pass the KAIJU write gate — the old
    authorized=True kwarg allowed any caller to skip it entirely."""
    import inspect
    import pytest

    store = GroundingStore(tmp_path / "state")
    source = tmp_path / "source"
    source.mkdir()
    target = source / "report.txt"
    target.write_text("data", encoding="utf-8")

    service = GroundingService(store=store, roots={"test": source}, clearance="reader")
    with pytest.raises(PermissionError):
        service.ingest_path("test", target, stability_delay_seconds=0)

    sig = inspect.signature(GroundingService.ingest_path)
    assert "authorized" not in sig.parameters


def test_reconcile_prunes_excluded_directories_before_scandir(tmp_path, monkeypatch):
    source = tmp_path / "source"
    excluded = source / "node_modules"
    excluded.mkdir(parents=True)
    (excluded / "never-read.txt").write_text("dependency", encoding="utf-8")
    (source / "keep.txt").write_text("evidence", encoding="utf-8")
    real_scandir = os.scandir

    def guarded(path):
        if Path(path).name == "node_modules":
            raise AssertionError("excluded directory was traversed")
        return real_scandir(path)

    monkeypatch.setattr(service_module.os, "scandir", guarded)
    service = GroundingService(
        store=GroundingStore(tmp_path / "state"),
        roots={"test": source},
    )

    result = service.reconcile(stability_delay_seconds=0)

    assert result["discovered"] == 1
    assert result["ingested"] == 1
    assert result["scan_errors"] == 0


def test_reconcile_contains_denied_directory_and_keeps_scanning(tmp_path, monkeypatch):
    source = tmp_path / "source"
    blocked = source / "blocked-cache"
    blocked.mkdir(parents=True)
    (blocked / "hidden.txt").write_text("hidden", encoding="utf-8")
    (source / "visible.txt").write_text("visible", encoding="utf-8")
    real_scandir = os.scandir

    def guarded(path):
        if Path(path) == blocked:
            raise PermissionError("synthetic denied directory")
        return real_scandir(path)

    monkeypatch.setattr(service_module.os, "scandir", guarded)
    service = GroundingService(
        store=GroundingStore(tmp_path / "state"),
        roots={"test": source},
    )

    result = service.reconcile(stability_delay_seconds=0)

    assert result["discovered"] == 1
    assert result["ingested"] == 1
    assert result["scan_errors"] == 1


def test_nested_source_root_is_owned_once_by_its_specific_source(tmp_path):
    archivist = tmp_path / "ARCHIVIST"
    papers = archivist / "PAPERS"
    papers.mkdir(parents=True)
    (archivist / "general.txt").write_text("general", encoding="utf-8")
    nested = papers / "paper-notes.txt"
    nested.write_text("paper notes", encoding="utf-8")
    store = GroundingStore(tmp_path / "state")
    service = GroundingService(
        store=store,
        roots={"archivist": archivist, "papers": papers},
    )

    result = service.reconcile(stability_delay_seconds=0)

    assert result["discovered"] == 2
    assert result["ingested"] == 2
    events = [json.loads(line) for line in store.ledger_path.read_text(encoding="utf-8").splitlines()]
    nested_events = [event for event in events if event["path"] == str(nested)]
    assert len(nested_events) == 1
    assert nested_events[0]["source_id"] == "papers"
