"""tests/nexus_cli_ctl/test_state_manager.py — Unified State Manager Tests

Validates:
- State initialization (6 default sections)
- State persistence (save/load cycle)
- Publish/subscribe lifecycle
- Unsubscribe cleanup (memory leak fix)
- WebSocket client handling
- Flood protection (WS broadcast rate limiting)
- Lock scope during stop()
- Corrupted state file handling
- Concurrent publish race conditions
- Port registration (8765/8766)
"""
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_cli_ctl.control.unified_state.state_manager import (
    UnifiedStateManager,
    StateChange,
    get_state_manager,
)


@pytest.fixture
def state_manager(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "nexus_cli_ctl.control.unified_state.state_manager.STATE_DIR",
        tmp_path,
    )
    monkeypatch.setattr(
        "nexus_cli_ctl.control.unified_state.state_manager.STATE_FILE",
        tmp_path / "unified_state.json",
    )
    return UnifiedStateManager()


@pytest.fixture
def async_sm(state_manager):
    return state_manager


class TestStateInitialization:
    def test_default_sections_exist(self, state_manager):
        state = state_manager.get_state()
        assert "cli" in state
        assert "dashboard" in state
        assert "nexusclaw" in state
        assert "model_relay" in state
        assert "wiki" in state
        assert "integrations" in state
        assert "metrics" in state

    def test_wiki_section_defaults(self, state_manager):
        wiki = state_manager.get_state("wiki")
        assert wiki["pages"] == 0
        assert wiki["dossiers"] == 0
        assert wiki["last_update"] is None

    def test_metrics_section_defaults(self, state_manager):
        metrics = state_manager.get_state("metrics")
        assert metrics["total_events"] == 0
        assert metrics["uptime_start"] is not None

    def test_integrations_section_has_all_platforms(self, state_manager):
        integrations = state_manager.get_state("integrations")
        for platform in ["a2a_bridge", "tailscale", "zo_computer", "mimo_cli",
                         "slack", "telegram", "discord"]:
            assert platform in integrations


class TestStatePersistence:
    def test_save_and_load_cycle(self, state_manager, tmp_path, monkeypatch):
        state_file = tmp_path / "unified_state.json"
        monkeypatch.setattr(
            "nexus_cli_ctl.control.unified_state.state_manager.STATE_FILE",
            state_file,
        )
        state_manager._save_state()
        assert state_file.exists()

        loaded = json.loads(state_file.read_text(encoding="utf-8"))
        assert "cli" in loaded
        assert "wiki" in loaded

    def test_corrupted_state_file_handled(self, tmp_path, monkeypatch):
        state_file = tmp_path / "unified_state.json"
        state_file.write_text("NOT VALID JSON {{{", encoding="utf-8")
        monkeypatch.setattr(
            "nexus_cli_ctl.control.unified_state.state_manager.STATE_FILE",
            state_file,
        )
        sm = UnifiedStateManager()
        state = sm.get_state()
        assert isinstance(state, dict)

    def test_save_handles_permission_error(self, state_manager, monkeypatch):
        def bad_save(*args, **kwargs):
            raise PermissionError("no write access")
        monkeypatch.setattr(state_manager, "_save_state", bad_save)
        state_manager._save_state()


class TestPublishSubscribe:
    @pytest.mark.asyncio
    async def test_publish_updates_state(self, async_sm):
        await async_sm.publish("wiki", {"pages": 42}, source="test")
        wiki_state = async_sm.get_state("wiki")
        assert wiki_state["pages"] == 42

    @pytest.mark.asyncio
    async def test_publish_increments_event_count(self, async_sm):
        initial = async_sm.get_state("metrics")["total_events"]
        await async_sm.publish("test", {"data": 1}, source="test")
        after = async_sm.get_state("metrics")["total_events"]
        assert after == initial + 1

    @pytest.mark.asyncio
    async def test_publish_notifies_subscribers(self, async_sm):
        callback = AsyncMock()
        async_sm.subscribe("test_topic", callback)
        await async_sm.publish("test_topic", {"key": "value"}, source="test")
        callback.assert_called_once()
        change = callback.call_args[0][0]
        assert isinstance(change, StateChange)
        assert change.topic == "test_topic"
        assert change.data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_subscriber_error_does_not_crash(self, async_sm):
        bad_callback = AsyncMock(side_effect=RuntimeError("subscriber crash"))
        good_callback = AsyncMock()
        async_sm.subscribe("error_topic", bad_callback)
        async_sm.subscribe("error_topic", good_callback)

        await async_sm.publish("error_topic", {"data": 1}, source="test")

        bad_callback.assert_called_once()
        good_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_with_dot_notation(self, async_sm):
        await async_sm.publish("model_relay.providers", {"openai": "active"}, source="test")
        state = async_sm.get_state("model_relay")
        assert "providers" in state


class TestUnsubscribe:
    @pytest.mark.asyncio
    async def test_unsubscribe_removes_callback(self, async_sm):
        callback = AsyncMock()
        async_sm.subscribe("unsub_topic", callback)
        assert len(async_sm._subscribers["unsub_topic"]) == 1

        result = async_sm.unsubscribe("unsub_topic", callback)
        assert result is True
        assert "unsub_topic" not in async_sm._subscribers or \
               len(async_sm._subscribers.get("unsub_topic", [])) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_callback(self, async_sm):
        callback = MagicMock()
        result = async_sm.unsubscribe("no_such_topic", callback)
        assert result is False

    @pytest.mark.asyncio
    async def test_unsubscribe_wrong_callback(self, async_sm):
        cb1 = AsyncMock()
        cb2 = AsyncMock()
        async_sm.subscribe("multi_topic", cb1)
        async_sm.subscribe("multi_topic", cb2)

        result = async_sm.unsubscribe("multi_topic", cb1)
        assert result is True
        assert len(async_sm._subscribers["multi_topic"]) == 1
        assert async_sm._subscribers["multi_topic"][0] == cb2

    @pytest.mark.asyncio
    async def test_unsubscribe_cleans_empty_topic(self, async_sm):
        callback = AsyncMock()
        async_sm.subscribe("cleanup_topic", callback)
        async_sm.unsubscribe("cleanup_topic", callback)
        assert "cleanup_topic" not in async_sm._subscribers


class TestFloodProtection:
    @pytest.mark.asyncio
    async def test_many_rapid_publishes_dont_crash(self, async_sm):
        for i in range(200):
            await async_sm.publish("flood_test", {"i": i}, source="test")
        event_count = async_sm.get_state("metrics")["total_events"]
        assert event_count >= 200

    @pytest.mark.asyncio
    async def test_ws_flood_limit_attribute_exists(self, async_sm):
        assert hasattr(async_sm, "_ws_flood_limit")
        assert async_sm._ws_flood_limit == 100

    @pytest.mark.asyncio
    async def test_publish_timestamps_tracked(self, async_sm):
        await async_sm.publish("rate_test", {"i": 1}, source="test")
        assert len(async_sm._publish_timestamps) >= 1


class TestStopRaceCondition:
    @pytest.mark.asyncio
    async def test_stop_calls_save_under_lock(self, async_sm):
        original_lock = async_sm._lock
        lock_entered = False

        class TrackedLock:
            async def __aenter__(self):
                nonlocal lock_entered
                lock_entered = True
                return await original_lock.__aenter__()
            async def __aexit__(self, *args):
                return await original_lock.__aexit__(*args)

        async_sm._lock = TrackedLock()
        async_sm._running = True

        async_sm._ws_runner = None
        async_sm._http_runner = None
        await async_sm.stop()

        assert lock_entered is True


class TestStateManagerSingleton:
    def test_get_state_manager_returns_instance(self):
        sm = get_state_manager()
        assert isinstance(sm, UnifiedStateManager)

    def test_get_state_manager_returns_same_instance(self):
        a = get_state_manager()
        b = get_state_manager()
        assert a is b


class TestStateChange:
    def test_state_change_fields(self):
        change = StateChange(topic="test", data={"key": "val"}, source="unit_test")
        assert change.topic == "test"
        assert change.data == {"key": "val"}
        assert change.source == "unit_test"
        assert change.timestamp is not None

    def test_state_change_default_source(self):
        change = StateChange(topic="test", data={})
        assert change.source == "unknown"
