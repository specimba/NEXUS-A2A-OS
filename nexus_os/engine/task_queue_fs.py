"""
engine/task_queue_fs.py — Filesystem Task Queue Mirror

Mirrors the SQLite task queue to the filesystem so that external tools,
agents, and CI pipelines can read/write task state without direct DB access.

Layout:
    <queue_root>/
        pending/   — JSON files for pending tasks
        active/    — JSON files for in-progress tasks
        completed/ — JSON files for completed tasks
        failed/    — JSON files for failed tasks
        index.json — Manifest of all tasks with state + timestamps

Each task file: <task_id>.json with full task metadata.
"""

import json
import os
import time
import logging

from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_ROOT = ".nexus_queue"

STATUS_DIRS = ("pending", "active", "completed", "failed")


class TaskQueueFS:
    """
    Filesystem-backed task queue that mirrors DB state.
    Designed for observability and cross-process coordination.
    """

    def __init__(self, queue_root: Optional[str] = None):
        self.root = Path(queue_root or DEFAULT_QUEUE_ROOT)
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create queue directory structure."""
        for d in STATUS_DIRS:
            (self.root / d).mkdir(parents=True, exist_ok=True)

    def enqueue(self, task_id: str, description: str, context: Dict[str, Any],
                priority: int = 5, project_id: str = "default") -> Dict[str, Any]:
        """Add a new task to the pending queue."""
        task = {
            "task_id": task_id,
            "description": description,
            "context": context,
            "priority": priority,
            "project_id": project_id,
            "status": "pending",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._write_task("pending", task)
        self._update_index()
        logger.info("Task enqueued: %s", task_id)
        return task

    def transition(self, task_id: str, new_status: str,
                   result: Optional[Dict[str, Any]] = None) -> bool:
        """Move a task between status directories."""
        if new_status not in STATUS_DIRS:
            logger.error("Invalid status: %s", new_status)
            return False

        task = self._find_task(task_id)
        if task is None:
            logger.warning("Task not found for transition: %s", task_id)
            return False

        old_status = task["status"]
        old_path = self.root / old_status / f"{task_id}.json"

        task["status"] = new_status
        task["updated_at"] = time.time()
        if result:
            task["result"] = result

        self._write_task(new_status, task)
        if old_path.exists():
            old_path.unlink()

        self._update_index()
        logger.info("Task %s: %s -> %s", task_id, old_status, new_status)
        return True

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a task by ID from any status directory."""
        return self._find_task(task_id)

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered by status."""
        tasks = []
        dirs = [status] if status and status in STATUS_DIRS else STATUS_DIRS
        for d in dirs:
            dir_path = self.root / d
            if not dir_path.exists():
                continue
            for f in sorted(dir_path.glob("*.json")):
                try:
                    tasks.append(json.loads(f.read_text()))
                except (json.JSONDecodeError, OSError):
                    continue
        return tasks

    def get_pending_ordered(self) -> List[Dict[str, Any]]:
        """Get pending tasks ordered by priority (higher first)."""
        pending = self.list_tasks("pending")
        return sorted(pending, key=lambda t: t.get("priority", 5), reverse=True)

    def sync_from_db(self, db_manager) -> int:
        """Pull current task state from DB and sync filesystem mirror."""
        conn = db_manager.get_connection()
        cursor = conn.execute(
            "SELECT task_id, project_id, description, status, priority, "
            "context, heartbeat, created_at FROM tasks"
        )
        synced = 0
        for row in cursor.fetchall():
            task_id, project_id, description, status, priority, context_str, heartbeat, created_at = row
            status_map = {
                "pending": "pending",
                "in_progress": "active",
                "completed": "completed",
                "failed": "failed",
                "blocked": "pending",
                "cancelled": "failed",
            }
            fs_status = status_map.get(status, "pending")
            try:
                context = json.loads(context_str) if context_str else {}
            except json.JSONDecodeError:
                context = {}

            task = {
                "task_id": task_id,
                "project_id": project_id,
                "description": description or "",
                "status": fs_status,
                "priority": priority or 5,
                "context": context,
                "heartbeat": heartbeat,
                "created_at": created_at,
                "updated_at": time.time(),
            }
            self._remove_from_all(task_id)
            self._write_task(fs_status, task)
            synced += 1

        self._update_index()
        logger.info("Synced %d tasks from DB to filesystem", synced)
        return synced

    def sync_to_db(self, db_manager) -> int:
        """Push filesystem task state back to DB (for tasks created externally)."""
        conn = db_manager.get_connection()
        pushed = 0
        status_map = {
            "pending": "pending",
            "active": "in_progress",
            "completed": "completed",
            "failed": "failed",
        }
        for task in self.list_tasks():
            db_status = status_map.get(task["status"], "pending")
            context_str = json.dumps(task.get("context", {}))
            conn.execute(
                """INSERT OR REPLACE INTO tasks
                   (task_id, project_id, description, status, priority, context, heartbeat)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    task["task_id"],
                    task.get("project_id", "default"),
                    task.get("description", ""),
                    db_status,
                    task.get("priority", 5),
                    context_str,
                    task.get("heartbeat", 0),
                ),
            )
            pushed += 1
        conn.commit()
        logger.info("Pushed %d tasks from filesystem to DB", pushed)
        return pushed

    def cleanup_completed(self, max_age_seconds: float = 86400) -> int:
        """Remove completed/failed tasks older than max_age_seconds."""
        cutoff = time.time() - max_age_seconds
        removed = 0
        for status in ("completed", "failed"):
            dir_path = self.root / status
            for f in dir_path.glob("*.json"):
                try:
                    task = json.loads(f.read_text())
                    if task.get("updated_at", 0) < cutoff:
                        f.unlink()
                        removed += 1
                except (json.JSONDecodeError, OSError):
                    continue
        if removed:
            self._update_index()
            logger.info("Cleaned up %d old tasks", removed)
        return removed

    def _write_task(self, status_dir: str, task: Dict[str, Any]):
        path = self.root / status_dir / f"{task['task_id']}.json"
        path.write_text(json.dumps(task, indent=2, default=str))

    def _find_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        for d in STATUS_DIRS:
            path = self.root / d / f"{task_id}.json"
            if path.exists():
                try:
                    return json.loads(path.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
        return None

    def _remove_from_all(self, task_id: str):
        for d in STATUS_DIRS:
            path = self.root / d / f"{task_id}.json"
            if path.exists():
                path.unlink()

    def _update_index(self):
        """Rebuild the index.json manifest."""
        index = {
            "updated_at": time.time(),
            "counts": {},
            "tasks": [],
        }
        for d in STATUS_DIRS:
            dir_path = self.root / d
            count = len(list(dir_path.glob("*.json")))
            index["counts"][d] = count
            for f in sorted(dir_path.glob("*.json")):
                try:
                    task = json.loads(f.read_text())
                    index["tasks"].append({
                        "task_id": task["task_id"],
                        "status": task["status"],
                        "priority": task.get("priority", 5),
                        "updated_at": task.get("updated_at"),
                    })
                except (json.JSONDecodeError, OSError):
                    continue

        index_path = self.root / "index.json"
        index_path.write_text(json.dumps(index, indent=2, default=str))
