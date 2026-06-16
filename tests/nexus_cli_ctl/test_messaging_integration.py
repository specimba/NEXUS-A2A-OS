"""Tests for NEXUS CLI-CTL messaging integration."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_cli_ctl.integrations.messaging.messaging_integration import (
    MessagingIntegration,
    get_messaging_integration,
)
from nexus_os.nexusclaw.messaging import MessageResult


class TestMessagingIntegrationInit:
    def test_init_default(self):
        mi = MessagingIntegration()
        assert mi.running is False
        assert mi._history == []
        assert mi._max_history == 200
        assert mi.SYNC_INTERVAL == 60

    def test_init_with_state_manager(self):
        sm = MagicMock()
        mi = MessagingIntegration(state_manager=sm)
        assert mi.sm is sm

    def test_hub_initialized(self):
        mi = MessagingIntegration()
        assert mi.hub is not None
        assert mi.hub.telegram is not None
        assert mi.hub.slack is not None
        assert mi.hub.discord is not None


class TestMessagingIntegrationGetStatus:
    def test_status_structure(self):
        mi = MessagingIntegration()
        status = mi.get_status()
        assert "running" in status
        assert "enabled_platforms" in status
        assert "telegram" in status
        assert "slack" in status
        assert "discord" in status
        assert "history_size" in status
        assert isinstance(status["enabled_platforms"], list)

    def test_status_history_size(self):
        mi = MessagingIntegration()
        mi._history.append({"success": True, "platform": "telegram", "message_id": "1"})
        status = mi.get_status()
        assert status["history_size"] == 1


class TestMessagingIntegrationSend:
    @pytest.mark.asyncio
    async def test_send_unknown_platform(self):
        mi = MessagingIntegration()
        result = await mi.send("unknown", "x", "hello")
        assert result["success"] is False
        assert "Unknown platform" in result["error"]

    @pytest.mark.asyncio
    async def test_send_telegram_disabled(self):
        mi = MessagingIntegration()
        result = await mi.send("telegram", "123", "hello")
        assert result["success"] is False
        assert "not enabled" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_send_slack_disabled(self):
        mi = MessagingIntegration()
        result = await mi.send("slack", "#general", "hello")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_send_discord_disabled(self):
        mi = MessagingIntegration()
        result = await mi.send("discord", "12345", "hello")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_send_records_in_history(self):
        mi = MessagingIntegration()
        await mi.send("telegram", "123", "hello")
        history = mi.get_history()
        assert len(history) == 1
        assert history[0]["platform"] == "telegram"

    @pytest.mark.asyncio
    async def test_send_publishes_to_state(self):
        sm = AsyncMock()
        sm.publish = AsyncMock()
        mi = MessagingIntegration(state_manager=sm)
        await mi.send("telegram", "123", "hello")
        assert sm.publish.called
        call = sm.publish.call_args
        assert call[0][0] == "messaging.last_send"


class TestMessagingIntegrationBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_no_channels(self):
        mi = MessagingIntegration()
        results = await mi.broadcast("hello")
        assert results == []

    @pytest.mark.asyncio
    async def test_broadcast_with_channels_no_enabled(self):
        mi = MessagingIntegration()
        results = await mi.broadcast("hello", channels={"telegram": ["123"]})
        assert len(results) == 1
        assert results[0]["success"] is False

    @pytest.mark.asyncio
    async def test_broadcast_publishes_to_state(self):
        sm = AsyncMock()
        sm.publish = AsyncMock()
        mi = MessagingIntegration(state_manager=sm)
        await mi.broadcast("test", channels={"telegram": []})
        assert sm.publish.called


class TestMessagingIntegrationHistory:
    def test_history_empty(self):
        mi = MessagingIntegration()
        assert mi.get_history() == []

    def test_history_with_limit(self):
        mi = MessagingIntegration()
        for i in range(5):
            mi._history.append({"success": True, "platform": "telegram", "message_id": str(i)})
        assert len(mi.get_history(limit=3)) == 3
        assert len(mi.get_history(limit=10)) == 5

    def test_history_max_enforced(self):
        mi = MessagingIntegration()
        mi._max_history = 10
        for i in range(20):
            mi._history.append({"i": i})
        mi._record({"i": 100})
        assert len(mi._history) == 10
        assert mi._history[-1]["i"] == 100


class TestMessagingIntegrationAsyncLifecycle:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        mi = MessagingIntegration()
        await mi.start()
        assert mi.running is True
        await mi.stop()
        assert mi.running is False

    @pytest.mark.asyncio
    async def test_double_start_no_op(self):
        mi = MessagingIntegration()
        await mi.start()
        await mi.start()
        await mi.stop()


class TestMessagingIntegrationSingleton:
    def test_singleton_same_instance(self):
        a = get_messaging_integration()
        b = get_messaging_integration()
        assert a is b

    def test_singleton_state_manager_attached(self):
        sm = MagicMock()
        mi = get_messaging_integration(state_manager=sm)
        assert mi.sm is sm


class TestMessagingIntegrationStatusLoop:
    @pytest.mark.asyncio
    async def test_status_loop_publishes(self):
        import asyncio
        sm = AsyncMock()
        sm.publish = AsyncMock()
        mi = MessagingIntegration(state_manager=sm)
        mi.SYNC_INTERVAL = 0.05
        mi.running = True
        loop_task = asyncio.create_task(mi._status_loop())
        await asyncio.sleep(0.2)
        mi.running = False
        try:
            await asyncio.wait_for(loop_task, timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        assert sm.publish.called

    @pytest.mark.asyncio
    async def test_status_loop_handles_exception(self):
        import asyncio
        sm = AsyncMock()
        sm.publish = AsyncMock(side_effect=Exception("fail"))
        mi = MessagingIntegration(state_manager=sm)
        mi.SYNC_INTERVAL = 0.05
        mi.running = True
        loop_task = asyncio.create_task(mi._status_loop())
        await asyncio.sleep(0.2)
        mi.running = False
        try:
            await asyncio.wait_for(loop_task, timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
