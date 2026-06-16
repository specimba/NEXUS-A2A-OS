from datetime import datetime, timedelta, timezone
import os

from nexus_os.nexusclaw import gross
from nexus_os.nexusclaw.gross import MATERIAL_QUEUE_BYTES, collect_gross_sentinel_snapshot, should_read_deep_gross_files


def test_should_read_deep_gross_files_is_quiet_for_stale_small_queue():
    assert should_read_deep_gross_files(
        grok_process_running=False,
        upload_queue_bytes=MATERIAL_QUEUE_BYTES - 1,
        win_native_run_recent=False,
        new_evidence_report=False,
    ) is False


def test_should_read_deep_gross_files_notifies_on_material_triggers():
    assert should_read_deep_gross_files(
        grok_process_running=True,
        upload_queue_bytes=0,
        win_native_run_recent=False,
        new_evidence_report=False,
    ) is True
    assert should_read_deep_gross_files(
        grok_process_running=False,
        upload_queue_bytes=MATERIAL_QUEUE_BYTES,
        win_native_run_recent=False,
        new_evidence_report=False,
    ) is True
    assert should_read_deep_gross_files(
        grok_process_running=False,
        upload_queue_bytes=0,
        win_native_run_recent=True,
        new_evidence_report=False,
    ) is True


def test_collect_snapshot_does_not_touch_real_gross_when_tmp_roots_used(tmp_path, monkeypatch):
    monkeypatch.setattr(gross, "_is_process_running", lambda _name: False)
    grok_root = tmp_path / "grok"
    queue = grok_root / "upload_queue"
    queue.mkdir(parents=True)
    (queue / "small.bin").write_bytes(b"small")

    snapshot = collect_gross_sentinel_snapshot(
        gross_root=tmp_path / "gross",
        grok_root=grok_root,
        downloads_root=tmp_path / "downloads",
        now=datetime(2026, 6, 3, tzinfo=timezone.utc),
    )

    assert snapshot.decision == "DONT_NOTIFY"
    assert snapshot.upload_queue_file_count == 1
    assert snapshot.upload_queue_bytes == 5
    assert snapshot.material_change is False


def test_collect_snapshot_notifies_on_recent_win_native_run(tmp_path, monkeypatch):
    monkeypatch.setattr(gross, "_is_process_running", lambda _name: False)
    now = datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)
    run_dir = tmp_path / "gross" / "runs" / "win-native-001"
    run_dir.mkdir(parents=True)
    recent_ts = (now - timedelta(minutes=5)).timestamp()
    os.utime(run_dir, (recent_ts, recent_ts))

    snapshot = collect_gross_sentinel_snapshot(
        gross_root=tmp_path / "gross",
        grok_root=tmp_path / "grok",
        downloads_root=tmp_path / "downloads",
        now=now,
    )

    assert snapshot.decision == "NOTIFY"
    assert snapshot.material_change is True
    assert snapshot.newest_win_native_run is not None


def test_collect_snapshot_notifies_on_new_downloads_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(gross, "_is_process_running", lambda _name: False)
    now = datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    report = downloads / "GROSS-new-report.txt"
    report.write_text("secret-free marker", encoding="utf-8")
    report_ts = (now - timedelta(minutes=1)).timestamp()
    os.utime(report, (report_ts, report_ts))

    snapshot = collect_gross_sentinel_snapshot(
        gross_root=tmp_path / "gross",
        grok_root=tmp_path / "grok",
        downloads_root=downloads,
        now=now,
        previous_evidence_check=now - timedelta(minutes=10),
    )

    assert snapshot.decision == "NOTIFY"
    assert snapshot.newest_downloads_evidence is not None
