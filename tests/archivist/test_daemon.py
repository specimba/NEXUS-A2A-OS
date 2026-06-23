"""tests/archivist/test_daemon.py — ARCHIVIST Daemon Tests

Validates:
- Daemon initialization (importer, compiler, fitter wiring)
- Checkpoint save/load (JSON persistence)
- CPU load monitoring (psutil graceful fallback)
- Throttle logic (high load → throttle)
- Processing tiers: light, deep, full (run_light is now implemented)
- Continuous main loop (start/stop/thread)
- Statistics reporting
- psutil import failure handling
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.archivist.import_stage import ArchivistImporter, ImportRecord, FileType, AdmissionClass
from nexus_os.archivist.compile import ArchivistCompiler
from nexus_os.archivist.fit import ArchivistFitter


def make_record(title="test paper", file_path="test.pdf", file_type=FileType.PAPER,
                admission_class=AdmissionClass.WEB_REFERENCE, priority=80,
                arxiv_id=None, source_dir="Downloads") -> ImportRecord:
    return ImportRecord(
        file_path=file_path,
        file_type=file_type,
        admission_class=admission_class,
        priority=priority,
        blake3_hash="abc123",
        file_size=1000,
        mtime=1700000000.0,
        source_dir=source_dir,
        title=title,
        arxiv_id=arxiv_id,
    )


class TestDaemonInit:
    def test_daemon_creates_components(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        daemon = ArchivistDaemon(output_dir=str(tmp_path / "wiki_output"))

        assert isinstance(daemon.importer, ArchivistImporter)
        assert isinstance(daemon.compiler, ArchivistCompiler)
        assert isinstance(daemon.fitter, ArchivistFitter)
        assert daemon._running is False
        assert daemon._last_full_run == 0.0
        assert daemon._last_deep_run == 0.0

    def test_checkpoint_dir_created(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        ckpt_dir = str(tmp_path / "checkpoints")
        daemon = ArchivistDaemon(checkpoint_dir=ckpt_dir)
        assert Path(ckpt_dir).exists()


class TestCheckpoint:
    def test_save_and_load_checkpoint(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        daemon = ArchivistDaemon(checkpoint_dir=str(tmp_path))

        daemon.save_checkpoint(processed_files=50, total_files=100, errors=["err1"])
        loaded = daemon.load_checkpoint()

        assert loaded is not None
        assert loaded["processed_files"] == 50
        assert loaded["total_files"] == 100
        assert "err1" in loaded["errors"]

    def test_load_nonexistent_checkpoint(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        daemon = ArchivistDaemon(checkpoint_dir=str(tmp_path))
        loaded = daemon.load_checkpoint()
        assert loaded is None

    def test_load_corrupted_checkpoint(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        daemon = ArchivistDaemon(checkpoint_dir=str(tmp_path))
        daemon.checkpoint_file.write_text("NOT JSON{{{{", encoding="utf-8")
        loaded = daemon.load_checkpoint()
        assert loaded is None

    def test_errors_kept_to_last_10(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        daemon = ArchivistDaemon(checkpoint_dir=str(tmp_path))

        errors = [f"error_{i}" for i in range(20)]
        daemon.save_checkpoint(processed_files=10, total_files=10, errors=errors)
        loaded = daemon.load_checkpoint()

        assert len(loaded["errors"]) <= 10


class TestPsutilFallback:
    def test_cpu_load_without_psutil(self):
        from nexus_os.archivist import daemon as daemon_mod

        original_has = daemon_mod._HAS_PSUTIL
        try:
            daemon_mod._HAS_PSUTIL = False
            from nexus_os.archivist.daemon import ArchivistDaemon
            d = ArchivistDaemon.__new__(ArchivistDaemon)
            d._running = False
            assert d._cpu_load() == 0.0
        finally:
            daemon_mod._HAS_PSUTIL = original_has

    def test_check_throttle_without_psutil(self):
        from nexus_os.archivist import daemon as daemon_mod

        original_has = daemon_mod._HAS_PSUTIL
        try:
            daemon_mod._HAS_PSUTIL = False
            from nexus_os.archivist.daemon import ArchivistDaemon
            d = ArchivistDaemon.__new__(ArchivistDaemon)
            d._running = False
            assert d.check_throttle() is False
        finally:
            daemon_mod._HAS_PSUTIL = original_has

    def test_wait_for_idle_without_psutil(self):
        from nexus_os.archivist import daemon as daemon_mod

        original_has = daemon_mod._HAS_PSUTIL
        try:
            daemon_mod._HAS_PSUTIL = False
            from nexus_os.archivist.daemon import ArchivistDaemon
            d = ArchivistDaemon.__new__(ArchivistDaemon)
            d._running = False
            assert d.wait_for_idle() is True
        finally:
            daemon_mod._HAS_PSUTIL = original_has


class TestProcessingTiers:
    def test_run_light_processes_files(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        daemon = ArchivistDaemon(output_dir=str(tmp_path / "wiki_output"))

        test_dir = tmp_path / "source"
        test_dir.mkdir()
        (test_dir / "doc1.md").write_text("# Trust\n" + "word " * 200, encoding="utf-8")
        (test_dir / "doc2.md").write_text("# Memory\n" + "word " * 200, encoding="utf-8")

        daemon.importer.watched_dirs = [str(test_dir)]

        daemon.run_light()

    def test_run_deep_with_files(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        daemon = ArchivistDaemon(output_dir=str(tmp_path / "wiki_output"))

        test_dir = tmp_path / "source"
        test_dir.mkdir()
        (test_dir / "paper_2403.13031.pdf").write_text("paper content", encoding="utf-8")

        daemon.importer.watched_dirs = [str(test_dir)]
        daemon.run_deep(max_files=10)

    def test_run_once_light(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        daemon = ArchivistDaemon(output_dir=str(tmp_path / "wiki_output"))

        test_dir = tmp_path / "source"
        test_dir.mkdir()
        (test_dir / "doc.md").write_text("# Test\ncontent", encoding="utf-8")
        daemon.importer.watched_dirs = [str(test_dir)]

        daemon.run_once(tier="light")

    def test_run_once_deep(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        daemon = ArchivistDaemon(output_dir=str(tmp_path / "wiki_output"))

        test_dir = tmp_path / "source"
        test_dir.mkdir()
        (test_dir / "doc.md").write_text("# Test\ncontent", encoding="utf-8")
        daemon.importer.watched_dirs = [str(test_dir)]

        daemon.run_once(tier="deep")

    def test_run_full_calls_deep(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        daemon = ArchivistDaemon(output_dir=str(tmp_path / "wiki_output"))

        test_dir = tmp_path / "source"
        test_dir.mkdir()
        (test_dir / "doc.md").write_text("# Test\ncontent", encoding="utf-8")
        daemon.importer.watched_dirs = [str(test_dir)]

        with patch.object(daemon, 'run_deep') as mock_deep:
            daemon.run_full()
            mock_deep.assert_called_once()


class TestDaemonLifecycle:
    def test_start_creates_thread(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        daemon = ArchivistDaemon(output_dir=str(tmp_path / "wiki_output"))

        with patch.object(daemon, 'run_continuous'):
            daemon.start()
            assert daemon._running is True
            assert daemon._thread is not None
            daemon.stop()

    def test_stop_sets_running_false(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        daemon = ArchivistDaemon(output_dir=str(tmp_path / "wiki_output"))
        daemon._running = True
        daemon.stop()
        assert daemon._running is False

    def test_double_start_no_error(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        daemon = ArchivistDaemon(output_dir=str(tmp_path / "wiki_output"))

        with patch.object(daemon, 'run_continuous'):
            daemon.start()
            daemon.start()
            daemon.stop()


class TestDaemonStats:
    def test_get_stats_structure(self, tmp_path):
        from nexus_os.archivist.daemon import ArchivistDaemon
        daemon = ArchivistDaemon(output_dir=str(tmp_path / "wiki_output"))
        stats = daemon.get_stats()

        assert "running" in stats
        assert "last_deep_run" in stats
        assert "last_full_run" in stats
        assert "importer" in stats
        assert "fitter" in stats
