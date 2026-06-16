"""Tests for NEXUS Tailscale Network Monitor."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_cli_ctl.integrations.zo_computer.tailscale_monitor import TailscaleMonitor


class TestTailscaleMonitorInit:
    def test_init_default(self):
        monitor = TailscaleMonitor()
        assert monitor.running is False
        assert monitor.last_status == {}
        assert monitor.CHECK_INTERVAL == 60

    def test_init_with_state_manager(self):
        sm = MagicMock()
        monitor = TailscaleMonitor(state_manager=sm)
        assert monitor.sm is sm

    def test_zo_hosts_defined(self):
        monitor = TailscaleMonitor()
        assert len(monitor.ZO_HOSTS) > 0
        assert "zo-compute-1" in monitor.ZO_HOSTS


class TestTailscaleMonitorStatus:
    def test_get_status_empty(self):
        monitor = TailscaleMonitor()
        assert monitor.get_status() == {}

    def test_find_tailscale_returns_path_or_none(self):
        monitor = TailscaleMonitor()
        result = monitor._find_tailscale()
        assert result is None or isinstance(result, str)


class TestTailscaleMonitorAsync:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        monitor = TailscaleMonitor()
        await monitor.start()
        assert monitor.running is True
        await monitor.stop()
        assert monitor.running is False

    @pytest.mark.asyncio
    async def test_double_start(self):
        monitor = TailscaleMonitor()
        await monitor.start()
        await monitor.start()
        await monitor.stop()

    @pytest.mark.asyncio
    async def test_check_zo_reachability_returns_structure(self):
        monitor = TailscaleMonitor()
        result = await monitor._check_zo_reachability()
        assert "any_reachable" in result
        assert "hosts" in result
        for host in monitor.ZO_HOSTS:
            assert host in result["hosts"]

    @pytest.mark.asyncio
    async def test_run_checks_no_tailscale(self):
        sm = AsyncMock()
        monitor = TailscaleMonitor(state_manager=sm)
        monitor._tailscale_path = None
        await monitor._run_checks()
        status = monitor.get_status()
        assert "timestamp" in status
        assert status["installed"] is False
        assert "zo" in status
