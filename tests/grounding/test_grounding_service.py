from pathlib import Path

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
