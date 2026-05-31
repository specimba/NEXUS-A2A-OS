"""tests/swarm/test_worker.py — Worker agent tests

Covers:
- AgentCard creation and serialization
- Worker initialization and directory setup
- Heartbeat file writing
- Task parsing (plain and frontmatter)
- Task execution (various types)
- Result saving
- Worker lifecycle (start/stop)
- Stats reporting
"""

import json
import pytest

from nexus_os.swarm.worker import AgentCard, Worker


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def worker(tmp_path):
    return Worker(
        worker_id="test-worker-1",
        tasks_dir=str(tmp_path / "tasks"),
        lane="code",
        capabilities=["python", "analysis"],
        heartbeat_interval=1,
    )


# ── AgentCard ────────────────────────────────────────────────────────

class TestAgentCard:
    def test_to_dict(self):
        card = AgentCard(
            agent_id="w1", lane="code",
            trust_band="COMMUNITY_VERIFIED",
            capabilities=["python"],
        )
        d = card.to_dict()
        assert d["agent_id"] == "w1"
        assert d["lane"] == "code"
        assert d["trust_band"] == "COMMUNITY_VERIFIED"
        assert d["capabilities"] == ["python"]
        assert d["availability"] == "ready"

    def test_hold_state(self):
        card = AgentCard(
            agent_id="w1", lane="code",
            trust_band="COMMUNITY_VERIFIED",
            capabilities=[], hold_state="paused",
        )
        assert card.to_dict()["hold_state"] == "paused"


# ── Worker Init ──────────────────────────────────────────────────────

class TestWorkerInit:
    def test_directories_created(self, worker):
        assert worker.pending_dir.exists()
        assert worker.done_dir.exists()
        assert worker.failed_dir.exists()

    def test_initial_state(self, worker):
        assert worker.is_running() is False
        assert worker._tasks_completed == 0
        assert worker._tasks_failed == 0


# ── Agent Card ───────────────────────────────────────────────────────

class TestWorkerAgentCard:
    def test_get_agent_card(self, worker):
        card = worker.get_agent_card()
        assert card["agent_id"] == "test-worker-1"
        assert card["lane"] == "code"
        assert "python" in card["capabilities"]


# ── Heartbeat ────────────────────────────────────────────────────────

class TestHeartbeat:
    def test_send_heartbeat_creates_file(self, worker):
        worker.send_heartbeat()
        hb_file = worker.tasks_dir / ".heartbeats" / "test-worker-1.json"
        assert hb_file.exists()
        data = json.loads(hb_file.read_text())
        assert data["worker_id"] == "test-worker-1"
        assert "timestamp" in data


# ── Task Parsing ─────────────────────────────────────────────────────

class TestTaskParsing:
    def test_parse_plain_task(self, worker):
        task_file = worker.pending_dir / "my-task.task.md"
        task_file.write_text("Do something important")
        task = worker.parse_task(task_file)
        assert task["task_id"] == "my-task"
        assert "Do something important" in task["content"]

    def test_parse_frontmatter_task(self, worker):
        content = "---\ntype: summarize\npriority: high\n---\nSummarize this doc"
        task_file = worker.pending_dir / "fm-task.task.md"
        task_file.write_text(content)
        task = worker.parse_task(task_file)
        assert task["task_id"] == "fm-task"
        assert task.get("type") == "summarize"

    def test_get_next_task_empty(self, worker):
        assert worker.get_next_task() is None

    def test_get_next_task_returns_first(self, worker):
        (worker.pending_dir / "aaa.task.md").write_text("task a")
        (worker.pending_dir / "bbb.task.md").write_text("task b")
        result = worker.get_next_task()
        assert result is not None
        assert "aaa" in result.name


# ── Task Execution ───────────────────────────────────────────────────

class TestTaskExecution:
    def test_execute_summarize(self, worker):
        task = {"task_id": "t1", "type": "summarize", "content": "Long document content here"}
        result = worker.execute_task(task)
        assert result["status"] == "success"
        assert "Summary" in result["output"]

    def test_execute_analyze(self, worker):
        task = {"task_id": "t2", "type": "analyze", "content": "Data to analyze"}
        result = worker.execute_task(task)
        assert result["status"] == "success"

    def test_execute_code(self, worker):
        task = {"task_id": "t3", "type": "code", "content": "Review this code"}
        result = worker.execute_task(task)
        assert result["status"] == "success"

    def test_execute_unknown_type(self, worker):
        task = {"task_id": "t4", "type": "unknown", "content": "Something"}
        result = worker.execute_task(task)
        assert result["status"] == "success"
        assert "Processed" in result["output"]


# ── Result Saving ────────────────────────────────────────────────────

class TestResultSaving:
    def test_save_success_result(self, worker):
        result = {"task_id": "t1", "status": "success", "output": "done"}
        worker.save_result(result)
        assert (worker.done_dir / "t1.result.json").exists()
        assert worker._tasks_completed == 1

    def test_save_failed_result(self, worker):
        result = {"task_id": "t2", "status": "failed", "error": "boom"}
        worker.save_result(result)
        assert (worker.failed_dir / "t2.result.json").exists()
        assert worker._tasks_failed == 1


# ── Stats ────────────────────────────────────────────────────────────

class TestStats:
    def test_get_stats(self, worker):
        stats = worker.get_stats()
        assert stats["worker_id"] == "test-worker-1"
        assert stats["running"] is False
        assert stats["tasks_completed"] == 0
