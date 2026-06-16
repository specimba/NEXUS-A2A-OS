import pytest

from nexus_os.nexusclaw.runner import NexusClawRunner, RunnerConfig
from nexus_os.nexusclaw.worklog import WorklogSystem
from nexus_os.vault.memory_channels import MemoryChannelManager


class TestRunnerConfig:
    def test_default_config_dry_run_only(self):
        config = RunnerConfig()
        assert config.dry_run_only is True
        assert config.heartbeat_interval_seconds == 30
        assert config.max_consecutive_failures == 3


class TestNexusClawRunner:
    def test_runner_initializes_with_default_config(self):
        runner = NexusClawRunner()
        assert runner.config.dry_run_only is True
        assert runner._running is False
        assert runner._failure_count == 0

    def test_runner_initializes_with_custom_config(self):
        config = RunnerConfig(heartbeat_interval_seconds=60, max_consecutive_failures=5)
        runner = NexusClawRunner(config=config)
        assert runner.config.heartbeat_interval_seconds == 60
        assert runner.config.max_consecutive_failures == 5

    @pytest.mark.asyncio
    async def test_heartbeat_returns_status(self):
        runner = NexusClawRunner()
        status = await runner.heartbeat()

        assert "status" in status
        assert status["status"] in ("ok", "halted")
        assert "config" in status
        assert "port_ownership" in status

    @pytest.mark.asyncio
    async def test_process_message_task_skips_non_messaging_intent(self):
        runner = NexusClawRunner()
        task = type(
            "Task",
            (),
            {
                "intent": "not_a_message",
                "resource_budget": {},
            },
        )()
        result = await runner.process_message_task(task)
        assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_process_message_task_returns_error_for_missing_text(self):
        runner = NexusClawRunner()
        task = type(
            "Task",
            (),
            {
                "intent": "send_message",
                "resource_budget": {"platform": "slack"},
            },
        )()
        result = await runner.process_message_task(task)
        assert result["status"] == "skipped"
        assert "no message text" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_process_message_task_returns_error_for_unknown_platform(self):
        runner = NexusClawRunner()
        task = type(
            "Task",
            (),
            {
                "intent": "send_message",
                "resource_budget": {"platform": "unknown", "target": "x", "text": "hi"},
            },
        )()
        result = await runner.process_message_task(task)
        assert result["status"] == "error"
        assert "unknown" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_process_message_task_dry_run(self):
        runner = NexusClawRunner()
        task = type(
            "Task",
            (),
            {
                "intent": "send_message",
                "resource_budget": {"platform": "slack", "target": "#general", "text": "hello"},
            },
        )()
        result = await runner.process_message_task(task)
        assert result["status"] == "dry_run"
        assert result["platform"] == "slack"

    def test_stop_sets_running_false(self):
        runner = NexusClawRunner()
        runner._running = True
        runner.stop()
        assert runner._running is False

    def test_runner_singleton(self):
        from nexus_os.nexusclaw.runner import get_runner
        runner1 = get_runner()
        runner2 = get_runner()
        assert runner1 is runner2

    @pytest.mark.asyncio
    async def test_daemon_sync_uses_queue_depth_without_private_entries(self):
        class QueueOnlyWorklog:
            def queue_depth(self):
                return 101

        runner = NexusClawRunner()
        runner.worklog = QueueOnlyWorklog()

        result = await runner.daemon_sync()

        assert result["synced"] is True
        assert result["records_queued"] == 101
        assert result["fit_triggered"] is True

    @pytest.mark.asyncio
    async def test_daemon_sync_periodic_threshold(self):
        config = RunnerConfig(heartbeat_interval_seconds=10, archivist_sync_interval=20)
        runner = NexusClawRunner(config=config)
        runner.worklog = WorklogSystem(memory_channels=MemoryChannelManager())

        first = await runner.daemon_sync()
        second = await runner.daemon_sync()
        third = await runner.daemon_sync()

        assert first["fit_triggered"] is False
        assert second["fit_triggered"] is False
        assert third["fit_triggered"] is True
        assert third["records_queued"] == 0
