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


class TestMasterDaemonBrainBinding:
    @pytest.mark.asyncio
    async def test_non_loopback_bind_requires_explicit_unsafe_opt_in(
        self,
        monkeypatch,
    ):
        import uvicorn

        daemon = NEXUSMasterDaemon()
        config_called = False

        def fake_config(*args, **kwargs):
            nonlocal config_called
            config_called = True
            raise AssertionError("Uvicorn config created for rejected bind")

        monkeypatch.setenv("NEXUS_BRAIN_BIND", "0.0.0.0")
        monkeypatch.setenv("NEXUS_BRAIN_TOKEN", "configured-token")
        monkeypatch.delenv(
            "NEXUS_UNSAFE_ALLOW_NON_LOOPBACK_BRAIN_BIND",
            raising=False,
        )
        monkeypatch.setattr(uvicorn, "Config", fake_config)

        task = await daemon._start_brain_api()

        assert task is None
        assert config_called is False
        assert "brain_api_server" not in daemon.services

    @pytest.mark.asyncio
    async def test_explicit_unsafe_opt_in_allows_non_loopback_bind(
        self,
        monkeypatch,
    ):
        import uvicorn

        daemon = NEXUSMasterDaemon()
        config_calls = []
        serve_called = False

        class FakeServer:
            def __init__(self, config):
                self.config = config
                self.should_exit = False

            async def serve(self):
                nonlocal serve_called
                serve_called = True

        def fake_config(app, **kwargs):
            config_calls.append((app, kwargs))
            return object()

        monkeypatch.setenv("NEXUS_BRAIN_BIND", "0.0.0.0")
        monkeypatch.setenv(
            "NEXUS_UNSAFE_ALLOW_NON_LOOPBACK_BRAIN_BIND",
            "1",
        )
        monkeypatch.setattr(uvicorn, "Config", fake_config)
        monkeypatch.setattr(uvicorn, "Server", FakeServer)

        task = await daemon._start_brain_api()
        assert task is not None
        await task

        assert config_calls
        assert config_calls[0][1]["host"] == "0.0.0.0"
        assert config_calls[0][1]["port"] == 7352
        assert serve_called is True
        assert "brain_api_server" in daemon.services
