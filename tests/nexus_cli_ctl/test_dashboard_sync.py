"""Tests for NEXUS CLI-CTL dashboard sync integration."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_cli_ctl.integrations.dashboard_sync import (
    DashboardSync,
    get_dashboard_sync,
    DASHBOARD_URL,
    BRAIN_API_WS,
    BRAIN_API_HTTP,
)


class TestDashboardSyncInit:
    def test_init_default(self):
        ds = DashboardSync()
        assert ds.running is False
        assert ds._ws_connected is False
        assert ds._dashboard_reachable is False
        assert ds.SYNC_INTERVAL == 5
        assert ds.PROBE_INTERVAL == 30

    def test_init_with_state_manager(self):
        sm = MagicMock()
        ds = DashboardSync(state_manager=sm)
        assert ds.sm is sm

    def test_topics_set(self):
        ds = DashboardSync()
        assert "system" in ds.TOPICS
        assert "agents" in ds.TOPICS
        assert "tasks" in ds.TOPICS
        assert "model_relay" in ds.TOPICS
        assert "wiki" in ds.TOPICS
        assert "messaging" in ds.TOPICS


class TestDashboardSyncStatus:
    def test_status_structure(self):
        ds = DashboardSync()
        status = ds.get_status()
        assert "running" in status
        assert "ws_connected" in status
        assert "dashboard_reachable" in status
        assert "dashboard_url" in status
        assert "brain_api" in status
        assert "topics" in status
        assert "last_sync" in status
        assert isinstance(status["topics"], list)
        assert status["dashboard_url"] == DASHBOARD_URL


class TestDashboardSyncAsyncLifecycle:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        ds = DashboardSync()
        await ds.start()
        assert ds.running is True
        await ds.stop()
        assert ds.running is False

    @pytest.mark.asyncio
    async def test_double_start_no_op(self):
        ds = DashboardSync()
        await ds.start()
        await ds.start()
        await ds.stop()


class TestDashboardSyncProbeLoop:
    @pytest.mark.asyncio
    async def test_probe_loop_marks_unreachable_on_error(self):
        import asyncio
        from unittest.mock import AsyncMock
        ds = DashboardSync()
        ds.PROBE_INTERVAL = 0.05
        ds.running = True
        with patch("nexus_cli_ctl.integrations.dashboard_sync.httpx.AsyncClient") as mock_client:
            cm = AsyncMock()
            cm.get = AsyncMock(side_effect=Exception("conn fail"))
            cm.__aenter__ = AsyncMock(return_value=cm)
            cm.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = cm
            task = asyncio.create_task(ds._probe_loop())
            await asyncio.sleep(0.3)
            ds.running = False
            try:
                await asyncio.wait_for(task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            assert ds._dashboard_reachable is False
            assert ds._ws_connected is False

    @pytest.mark.asyncio
    async def test_push_to_dashboard_skips_when_unreachable(self):
        ds = DashboardSync()
        ds._dashboard_reachable = False
        # Should not raise
        await ds._push_to_dashboard({"type": "test"})


class TestDashboardSyncSingleton:
    def test_singleton(self):
        a = get_dashboard_sync()
        b = get_dashboard_sync()
        assert a is b

    def test_singleton_attach_state(self):
        sm = MagicMock()
        ds = get_dashboard_sync(state_manager=sm)
        assert ds.sm is sm
