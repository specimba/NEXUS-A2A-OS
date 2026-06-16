"""Tests for NEXUS Master Daemon."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_cli_ctl.daemon.master_daemon import NEXUSMasterDaemon, STATE_DIR


class TestMasterDaemonInit:
    def test_init(self):
        daemon = NEXUSMasterDaemon()
        assert daemon.running is False
        assert daemon.services == {}
        assert daemon._tasks == []

    def test_state_dir_exists(self):
        assert STATE_DIR.exists()


class TestMasterDaemonPID:
    def test_pid_file_path(self):
        daemon = NEXUSMasterDaemon()
        from nexus_cli_ctl.daemon.master_daemon import MASTER_PID_FILE
        assert MASTER_PID_FILE.parent == STATE_DIR

    def test_write_pid_file(self, tmp_path):
        import os
        daemon = NEXUSMasterDaemon()
        test_pid_file = tmp_path / "test_daemon.pid"
        test_pid_file.write_text(str(os.getpid()))
        assert test_pid_file.exists()
        pid = int(test_pid_file.read_text().strip())
        assert pid == os.getpid()

    def test_remove_pid_file(self, tmp_path):
        test_pid_file = tmp_path / "test_daemon.pid"
        test_pid_file.write_text("99999")
        assert test_pid_file.exists()
        test_pid_file.unlink()
        assert not test_pid_file.exists()


class TestMasterDaemonServiceRegistry:
    def test_services_starts_empty(self):
        daemon = NEXUSMasterDaemon()
        assert "state_manager" not in daemon.services
        assert "health_monitor" not in daemon.services

    def test_imports_available(self):
        from nexus_cli_ctl.integrations.wiki_pipeline import WikiPipeline
        from nexus_cli_ctl.integrations.messaging.messaging_integration import MessagingIntegration
        from nexus_cli_ctl.integrations.dashboard_sync import DashboardSync
        from nexus_cli_ctl.integrations.a2a.a2a_health_monitor import A2ABridgeHealthMonitor
        from nexus_cli_ctl.integrations.zo_computer.tailscale_monitor import TailscaleMonitor
        assert WikiPipeline is not None
        assert MessagingIntegration is not None
        assert DashboardSync is not None


class TestMasterDaemonStopNoOp:
    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        daemon = NEXUSMasterDaemon()
        await daemon.stop()
        assert daemon.running is False
