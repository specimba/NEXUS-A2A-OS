"""Tests for the Filesystem Task Queue Mirror."""

import json
import os
import pytest

from nexus_os.engine.task_queue_fs import TaskQueueFS


class TestTaskQueueFS:
    """Test filesystem task queue operations."""

    @pytest.fixture(autouse=True)
    def setup_queue(self, tmp_path):
        self.tmpdir = str(tmp_path)
        self.queue = TaskQueueFS(queue_root=self.tmpdir)

    def test_enqueue_creates_file(self):
        task = self.queue.enqueue("task-001", "Build project", {"type": "build"})
        assert task["task_id"] == "task-001"
        assert task["status"] == "pending"
        path = os.path.join(self.tmpdir, "pending", "task-001.json")
        assert os.path.exists(path)

    def test_transition_moves_file(self):
        self.queue.enqueue("task-002", "Run tests", {})
        assert self.queue.transition("task-002", "active")
        assert not os.path.exists(os.path.join(self.tmpdir, "pending", "task-002.json"))
        assert os.path.exists(os.path.join(self.tmpdir, "active", "task-002.json"))

    def test_transition_to_completed(self):
        self.queue.enqueue("task-003", "Deploy", {})
        self.queue.transition("task-003", "active")
        self.queue.transition("task-003", "completed", result={"output": "success"})
        task = self.queue.get_task("task-003")
        assert task["status"] == "completed"
        assert task["result"]["output"] == "success"

    def test_get_task_returns_none_for_missing(self):
        assert self.queue.get_task("nonexistent") is None

    def test_list_tasks_all(self):
        self.queue.enqueue("t1", "A", {})
        self.queue.enqueue("t2", "B", {})
        self.queue.transition("t2", "active")
        tasks = self.queue.list_tasks()
        assert len(tasks) == 2

    def test_list_tasks_filtered(self):
        self.queue.enqueue("t1", "A", {})
        self.queue.enqueue("t2", "B", {})
        self.queue.transition("t2", "active")
        pending = self.queue.list_tasks(status="pending")
        assert len(pending) == 1
        assert pending[0]["task_id"] == "t1"

    def test_get_pending_ordered_by_priority(self):
        self.queue.enqueue("t-low", "Low", {}, priority=1)
        self.queue.enqueue("t-high", "High", {}, priority=10)
        self.queue.enqueue("t-med", "Med", {}, priority=5)
        ordered = self.queue.get_pending_ordered()
        assert ordered[0]["task_id"] == "t-high"
        assert ordered[-1]["task_id"] == "t-low"

    def test_index_json_updated(self):
        self.queue.enqueue("t1", "Test", {})
        index_path = os.path.join(self.tmpdir, "index.json")
        assert os.path.exists(index_path)
        with open(index_path) as f:
            index = json.load(f)
        assert index["counts"]["pending"] == 1
        assert len(index["tasks"]) == 1

    def test_cleanup_completed(self):
        self.queue.enqueue("t-old", "Old", {})
        self.queue.transition("t-old", "completed")
        # Force old timestamp
        path = os.path.join(self.tmpdir, "completed", "t-old.json")
        with open(path) as f:
            data = json.load(f)
        data["updated_at"] = 0  # epoch = very old
        with open(path, "w") as f:
            json.dump(data, f)
        removed = self.queue.cleanup_completed(max_age_seconds=1)
        assert removed == 1
        assert self.queue.get_task("t-old") is None

    def test_invalid_status_transition_rejected(self):
        self.queue.enqueue("t1", "Test", {})
        assert self.queue.transition("t1", "invalid_status") is False

    def test_path_traversal_rejected(self):
        with pytest.raises(ValueError, match="Invalid task_id format"):
            self.queue.enqueue("../bad_id", "Attack", {})

        with pytest.raises(ValueError, match="Invalid task_id format"):
            self.queue._get_safe_path("pending", "some/../../../etc/passwd")

        assert self.queue.get_task("bad/id") is None

    def test_out_of_workspace_root_rejected(self):
        # Path outside CWD and temp directory should be rejected
        bad_path = "/usr/local/bin" if os.name != "nt" else "C:\\Windows\\System32"
        with pytest.raises(ValueError, match="Queue root must be located within the workspace or temporary directory"):
            TaskQueueFS(queue_root=bad_path)

    def test_src_directory_rejected(self):
        # Any path containing "src" as a directory segment should be rejected
        src_path = os.path.join(self.tmpdir, "src", "my_queue")
        with pytest.raises(ValueError, match="Queue root cannot be under 'src/' directory"):
            TaskQueueFS(queue_root=src_path)

    def test_empty_dict_result_preserved(self):
        self.queue.enqueue("t_empty", "Test empty result", {})
        self.queue.transition("t_empty", "active")
        self.queue.transition("t_empty", "completed", result={})
        task = self.queue.get_task("t_empty")
        assert task["status"] == "completed"
        assert task["result"] == {}

