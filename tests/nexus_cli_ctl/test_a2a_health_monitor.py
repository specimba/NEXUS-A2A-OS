"""Tests for NEXUS A2A Bridge Health Monitor."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_cli_ctl.integrations.a2a.a2a_health_monitor import A2ABridgeHealthMonitor


class TestA2AHealthMonitorInit:
    def test_init_default(self):
        monitor = A2ABridgeHealthMonitor()
        assert monitor.running is False
        assert monitor.local_url == "http://localhost:7354"
        assert monitor.failure_count == 0
        assert monitor.success_count == 0

    def test_init_with_state_manager(self):
        sm = MagicMock()
        monitor = A2ABridgeHealthMonitor(state_manager=sm)
        assert monitor.sm is sm

    def test_check_interval(self):
        monitor = A2ABridgeHealthMonitor()
        assert monitor.CHECK_INTERVAL > 0


class TestA2AHealthMonitorStatus:
    def test_get_status_empty(self):
        monitor = A2ABridgeHealthMonitor()
        assert monitor.get_status() == {}

    def test_set_public_url(self):
        monitor = A2ABridgeHealthMonitor()
        monitor.set_public_url("https://my-tunnel.example.com")
        assert monitor.public_url == "https://my-tunnel.example.com"


class TestA2AHealthMonitorAsync:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        monitor = A2ABridgeHealthMonitor()
        await monitor.start()
        assert monitor.running is True
        await monitor.stop()
        assert monitor.running is False

    @pytest.mark.asyncio
    async def test_double_start(self):
        monitor = A2ABridgeHealthMonitor()
        await monitor.start()
        await monitor.start()
        await monitor.stop()

    @pytest.mark.asyncio
    async def test_monitor_loop_handles_exception(self):
        import asyncio
        monitor = A2ABridgeHealthMonitor()
        monitor.running = True
        monitor.CHECK_INTERVAL = 0.05
        with patch.object(monitor, "_run_checks", side_effect=Exception("fail")):
            task = asyncio.create_task(monitor._monitor_loop())
            await asyncio.sleep(0.2)
            monitor.running = False
            try:
                await asyncio.wait_for(task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

    @pytest.mark.asyncio
    async def test_run_checks_updates_status(self):
        monitor = A2ABridgeHealthMonitor()
        with patch.object(monitor, "_check_endpoint", return_value={"ok": False, "error": "conn", "name": "test"}):
            with patch.object(monitor, "_check_jsonrpc", return_value={"ok": False, "error": "conn", "name": "test"}):
                await monitor._run_checks()
                status = monitor.get_status()
                assert "healthy" in status
                assert "timestamp" in status
