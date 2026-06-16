"""nexus_os/nexusclaw/worker_pool.py — Persistent Worker Lanes

The WorkerPool manages stateful worker lifecycles for NEXUSCLAW agents.
Each worker is a persistent lane that transitions through a 6-state machine:
  IDLE -> RUNNING -> (PAUSED | STOPPED | FAILED)

Workers support health checks and auto-restart for resilience.
The pool integrates with TaskRouter for task-aware dispatch.

Usage:
    pool = WorkerPool()
    pool.register_worker("worker-1", lane="research")
    pool.start_worker("worker-1")
    pool.assign_task("worker-1", task_id="task-001")
    stats = pool.stats()
"""

from __future__ import annotations

import logging
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("nexusclaw.worker_pool")


class WorkerState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    FAILED = "failed"
    HALTED = "halted"


_VALID_TRANSITIONS: Dict[WorkerState, Set[WorkerState]] = {
    WorkerState.IDLE: {WorkerState.RUNNING, WorkerState.STOPPED, WorkerState.HALTED},
    WorkerState.RUNNING: {WorkerState.IDLE, WorkerState.PAUSED, WorkerState.STOPPED, WorkerState.FAILED, WorkerState.HALTED},
    WorkerState.PAUSED: {WorkerState.IDLE, WorkerState.RUNNING, WorkerState.STOPPED, WorkerState.HALTED},
    WorkerState.STOPPED: {WorkerState.IDLE, WorkerState.HALTED},
    WorkerState.FAILED: {WorkerState.IDLE, WorkerState.STOPPED, WorkerState.HALTED},
    WorkerState.HALTED: set(),
}


def _valid_transition(from_state: WorkerState, to_state: WorkerState) -> bool:
    """Check if a state transition is valid."""
    return to_state in _VALID_TRANSITIONS.get(from_state, set())


@dataclass
class WorkerRecord:
    worker_id: str
    lane: str
    state: WorkerState = WorkerState.IDLE
    current_task_id: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    spawned_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_heartbeat: Optional[str] = None
    max_restarts: int = 3
    restart_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.state in {WorkerState.IDLE, WorkerState.RUNNING, WorkerState.PAUSED}

    @property
    def task_success_rate(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 0.0
        return self.tasks_completed / total

    def heartbeat(self) -> None:
        self.last_heartbeat = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "lane": self.lane,
            "state": self.state.value,
            "current_task_id": self.current_task_id,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "task_success_rate": self.task_success_rate,
            "spawned_at": self.spawned_at,
            "last_heartbeat": self.last_heartbeat,
            "restart_count": self.restart_count,
            "max_restarts": self.max_restarts,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }


class WorkerPool:
    """Stateful pool of persistent worker lanes with automatic health management."""

    HEALTH_CHECK_INTERVAL = 30.0
    HEARTBEAT_TIMEOUT = 120.0

    def __init__(self, health_check_interval: float = HEALTH_CHECK_INTERVAL) -> None:
        self._workers: Dict[str, WorkerRecord] = {}
        self._lock = threading.RLock()
        self._health_thread: Optional[threading.Thread] = None
        self._health_running = False
        self._health_check_interval = health_check_interval

    def register_worker(
        self,
        worker_id: str,
        lane: str,
        max_restarts: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkerRecord:
        """Register a new worker lane."""
        with self._lock:
            if worker_id in self._workers:
                raise ValueError(f"Worker {worker_id} already registered")
            worker = WorkerRecord(
                worker_id=worker_id,
                lane=lane,
                max_restarts=max_restarts,
                metadata=metadata or {},
            )
            self._workers[worker_id] = worker
            logger.info("Worker registered: %s (lane=%s)", worker_id, lane)
            return worker

    def unregister_worker(self, worker_id: str) -> Optional[WorkerRecord]:
        """Remove a worker from the pool."""
        with self._lock:
            worker = self._workers.pop(worker_id, None)
            if worker:
                logger.info("Worker unregistered: %s", worker_id)
            return worker

    def transition(
        self, worker_id: str, to_state: WorkerState, reason: Optional[str] = None
    ) -> Optional[WorkerRecord]:
        """Transition a worker to a new state with validation."""
        with self._lock:
            worker = self._workers.get(worker_id)
            if not worker:
                logger.warning("Worker %s not found for transition", worker_id)
                return None
            if not _valid_transition(worker.state, to_state):
                logger.warning(
                    "Invalid transition %s -> %s for worker %s",
                    worker.state.value, to_state.value, worker_id,
                )
                return None
            old_state = worker.state
            worker.state = to_state
            worker.heartbeat()
            if to_state == WorkerState.FAILED:
                worker.tasks_failed += 1
                if worker.current_task_id:
                    worker.current_task_id = None
            if to_state == WorkerState.RUNNING:
                worker.restart_count = 0
            if to_state == WorkerState.IDLE:
                worker.current_task_id = None
            logger.info(
                "Worker %s: %s -> %s%s",
                worker_id, old_state.value, to_state.value,
                f" ({reason})" if reason else "",
            )
            return worker

    def assign_task(self, worker_id: str, task_id: str) -> Optional[WorkerRecord]:
        """Assign a task to a worker, transitioning it to RUNNING if idle."""
        with self._lock:
            worker = self._workers.get(worker_id)
            if not worker:
                return None
            if worker.state not in (WorkerState.IDLE, WorkerState.RUNNING):
                logger.warning("Cannot assign task to worker %s in state %s", worker_id, worker.state.value)
                return None
            if worker.state == WorkerState.IDLE:
                self.transition(worker_id, WorkerState.RUNNING)
            worker.current_task_id = task_id
            worker.heartbeat()
            return worker

    def complete_task(self, worker_id: str, task_id: str, success: bool) -> Optional[WorkerRecord]:
        """Mark a task as complete and transition worker back to IDLE."""
        with self._lock:
            worker = self._workers.get(worker_id)
            if not worker:
                return None
            if success:
                worker.tasks_completed += 1
            else:
                worker.tasks_failed += 1
            worker.current_task_id = None
            self.transition(worker_id, WorkerState.IDLE)
            worker.heartbeat()
            return worker

    def start_health_checks(self) -> None:
        """Start the background health check thread."""
        with self._lock:
            if self._health_running:
                return
            self._health_running = True
            self._health_thread = threading.Thread(
                target=self._health_loop, daemon=True, name="worker-pool-health"
            )
            self._health_thread.start()
            logger.info("WorkerPool health check thread started")

    def stop_health_checks(self) -> None:
        """Stop the background health check thread."""
        with self._lock:
            self._health_running = False

    def _health_loop(self) -> None:
        """Background loop that checks worker health periodically."""
        while self._health_running:
            self._check_all()
            time.sleep(self._health_check_interval)

    def _check_all(self) -> None:
        """Check all workers for heartbeat timeouts and auto-restart failed workers."""
        with self._lock:
            now = datetime.now(timezone.utc)
            for worker in list(self._workers.values()):
                self._check_worker(worker, now)

    def _check_worker(self, worker: WorkerRecord, now: datetime) -> None:
        """Check a single worker's health."""
        if worker.state == WorkerState.FAILED and worker.restart_count < worker.max_restarts:
            worker.restart_count += 1
            logger.info("Auto-restarting worker %s (attempt %d/%d)", worker.worker_id, worker.restart_count, worker.max_restarts)
            worker.state = WorkerState.IDLE
            worker.current_task_id = None
            worker.heartbeat()
        elif worker.state == WorkerState.FAILED and worker.restart_count >= worker.max_restarts:
            logger.warning("Worker %s exceeded max restarts (%d), transitioning to STOPPED", worker.worker_id, worker.max_restarts)
            worker.state = WorkerState.STOPPED
        elif worker.state.is_active and worker.last_heartbeat:
            last_hb = datetime.fromisoformat(worker.last_heartbeat)
            if (now - last_hb).total_seconds() > self.HEARTBEAT_TIMEOUT:
                logger.warning("Worker %s heartbeat timeout, marking as FAILED", worker.worker_id)
                worker.state = WorkerState.FAILED
                worker.current_task_id = None

    def get_worker(self, worker_id: str) -> Optional[WorkerRecord]:
        """Get a worker by ID."""
        with self._lock:
            return self._workers.get(worker_id)

    def list_workers(self, lane: Optional[str] = None, state: Optional[WorkerState] = None) -> List[WorkerRecord]:
        """List workers, optionally filtered by lane or state."""
        with self._lock:
            workers = list(self._workers.values())
            if lane:
                workers = [w for w in workers if w.lane == lane]
            if state:
                workers = [w for w in workers if w.state == state]
            return workers

    def list_available(self, lane: Optional[str] = None) -> List[WorkerRecord]:
        """List workers available for task assignment (IDLE state)."""
        return self.list_workers(lane=lane, state=WorkerState.IDLE)

    def stats(self) -> Dict[str, Any]:
        """Return pool statistics."""
        with self._lock:
            all_workers = list(self._workers.values())
            state_counts: Dict[str, int] = dict(Counter(w.state.value for w in all_workers))
            total_tasks = sum(w.tasks_completed + w.tasks_failed for w in all_workers)
            total_success = sum(w.tasks_completed for w in all_workers)
            return {
                "total_workers": len(all_workers),
                "available_workers": len(self.list_available()),
                "by_state": state_counts,
                "total_tasks_processed": total_tasks,
                "overall_success_rate": total_success / total_tasks if total_tasks > 0 else 0.0,
                "health_checks_running": self._health_running,
            }
