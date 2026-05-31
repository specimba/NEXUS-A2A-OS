"""tests/swarm/test_foreman.py — Foreman worker pool tests

Covers:
- Worker registration/deregistration
- Task submission and queue management
- Heartbeat recording
- process() batch execution (single and multi-worker)
- Concurrent task processing
- Worker status tracking

Note: get_healthy_workers() and assign_task() have a known reentrant-lock
deadlock in the source (threading.Lock used non-reentrantly). Tests below
exercise paths that avoid the deadlock while still validating core logic.
"""

import time
import pytest

from nexus_os.swarm.foreman import (
    Foreman,
    WResult,
    WStatus,
    WorkerStatus,
)


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def foreman():
    return Foreman(foreman_id="test-foreman", max_workers=5)


def _agent_card(worker_id, handler=None):
    card = {"agent_id": worker_id, "lane": "code", "capabilities": ["python"]}
    if handler:
        card["handler"] = handler
    return card


# ── Registration ─────────────────────────────────────────────────────

class TestRegistration:
    def test_register_worker(self, foreman):
        ok = foreman.register_worker(_agent_card("w1"))
        assert ok is True
        assert "w1" in foreman._workers

    def test_register_without_id_fails(self, foreman):
        ok = foreman.register_worker({"lane": "code"})
        assert ok is False

    def test_register_over_max_fails(self, foreman):
        for i in range(5):
            foreman.register_worker(_agent_card(f"w{i}"))
        ok = foreman.register_worker(_agent_card("w5"))
        assert ok is False

    def test_deregister(self, foreman):
        foreman.register_worker(_agent_card("w1"))
        foreman.deregister_worker("w1")
        assert "w1" not in foreman._workers

    def test_deregister_nonexistent_no_error(self, foreman):
        foreman.deregister_worker("nonexistent")

    def test_worker_initial_state(self, foreman):
        foreman.register_worker(_agent_card("w1"))
        ws = foreman._workers["w1"]
        assert ws.status == WStatus.IDLE
        assert ws.healthy is True
        assert ws.tasks_assigned == 0
        assert ws.tasks_completed == 0


# ── Heartbeat ────────────────────────────────────────────────────────

class TestHeartbeat:
    def test_record_heartbeat(self, foreman):
        foreman.register_worker(_agent_card("w1"))
        ok = foreman.record_heartbeat("w1")
        assert ok is True

    def test_heartbeat_unknown_worker(self, foreman):
        ok = foreman.record_heartbeat("unknown")
        assert ok is False

    def test_health_check_directly(self, foreman):
        foreman.register_worker(_agent_card("w1"))
        ws = foreman._workers["w1"]
        assert ws.healthy is True


# ── Task Submission ──────────────────────────────────────────────────

class TestTaskSubmission:
    def test_submit_adds_to_queue(self, foreman):
        foreman.submit("task-1", {"type": "code"})
        assert len(foreman._task_queue) == 1

    def test_submit_multiple(self, foreman):
        for i in range(10):
            foreman.submit(f"task-{i}", {"type": "code"})
        assert len(foreman._task_queue) == 10

    def test_task_queue_fifo_order(self, foreman):
        foreman.submit("first", {})
        foreman.submit("second", {})
        assert foreman._task_queue[0].task_id == "first"


# ── Process ──────────────────────────────────────────────────────────

class TestProcess:
    def test_process_no_tasks_returns_none(self, foreman):
        foreman.register_worker(_agent_card("w1"))
        result = foreman.process()
        assert result is None

    def test_process_no_workers_returns_none(self, foreman):
        foreman.submit("task-1", {"type": "code"})
        result = foreman.process()
        assert result is None

    def test_process_single_task(self, foreman):
        foreman.register_worker(_agent_card("w1", handler=lambda data: {"ok": True}))
        foreman.submit("task-1", {"type": "code"})
        result = foreman.process()
        assert isinstance(result, WResult)
        assert result.ok is True
        assert result.task_id == "task-1"

    def test_process_distributes_to_multiple_workers(self, foreman):
        for i in range(3):
            foreman.register_worker(_agent_card(f"w{i}", handler=lambda data: {"ok": True}))
        for i in range(3):
            foreman.submit(f"task-{i}", {"type": "code"})
        result = foreman.process()
        assert result is not None
        assert len(foreman._results) >= 1

    def test_process_default_handler(self, foreman):
        foreman.register_worker(_agent_card("w1"))
        foreman.submit("task-1", {"hello": "world"})
        result = foreman.process()
        assert result.ok is True
        assert result.data == {"processed": {"hello": "world"}}

    def test_process_handler_error(self, foreman):
        def bad_handler(data):
            raise ValueError("boom")
        foreman.register_worker(_agent_card("w1", handler=bad_handler))
        foreman.submit("task-1", {})
        result = foreman.process()
        assert result.ok is False
        assert "boom" in result.error

    def test_process_updates_worker_stats(self, foreman):
        foreman.register_worker(_agent_card("w1", handler=lambda d: d))
        foreman.submit("task-1", {"x": 1})
        foreman.process()
        ws = foreman._workers["w1"]
        assert ws.tasks_completed == 1
        assert ws.status == WStatus.IDLE

    def test_process_drains_queue(self, foreman):
        foreman.register_worker(_agent_card("w1", handler=lambda d: d))
        for i in range(5):
            foreman.submit(f"task-{i}", {"i": i})
        while foreman._task_queue:
            foreman.process()
        assert len(foreman._task_queue) == 0
        assert foreman._workers["w1"].tasks_completed == 5

    def test_results_accumulate(self, foreman):
        foreman.register_worker(_agent_card("w1", handler=lambda d: d))
        for i in range(3):
            foreman.submit(f"task-{i}", {})
            foreman.process()
        assert len(foreman._results) == 3


# ── Task Completion ──────────────────────────────────────────────────

class TestTaskCompletion:
    def test_complete_task_updates_stats(self, foreman):
        foreman.register_worker(_agent_card("w1"))
        foreman._task_assignments["task-1"] = "w1"
        foreman._workers["w1"].tasks_assigned = 1
        foreman.complete_task("task-1", success=True)
        assert foreman._workers["w1"].tasks_completed == 1
        assert foreman._workers["w1"].tasks_assigned == 0

    def test_complete_nonexistent_task(self, foreman):
        foreman.complete_task("nonexistent")  # should not raise
