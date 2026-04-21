"""
Foreman - Worker Pool Manager with Heartbeat Monitoring
Manages workers, distributes tasks, monitors health

v3.1: Refactored process() to distribute tasks across ALL idle workers
concurrently instead of just the first one, improving task throughput
and ensuring even load distribution across the worker pool.
"""

import json
import time
import logging
import threading
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class WStatus(Enum):
    """Worker status enum"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class WResult:
    """Result from a worker execution"""
    ok: bool
    task_id: str = ""
    worker_id: str = ""
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class WorkerStatus:
    """Worker health status"""
    worker_id: str
    last_heartbeat: datetime
    healthy: bool
    status: WStatus = WStatus.IDLE
    tasks_assigned: int = 0
    tasks_completed: int = 0
    agent_card: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Any] = None  # Callable for task execution


@dataclass
class Task:
    """Pending task in the queue"""
    task_id: str
    data: Any
    submitted_at: datetime = field(default_factory=datetime.now)
    assigned_worker: Optional[str] = None


class Foreman:
    """
    Worker pool management with 15-minute heartbeat monitoring.
    Task distribution, health checks, dead worker cleanup.

    v3.1: process() now distributes tasks to ALL idle workers
    concurrently instead of only the first one. This improves:
    - Task throughput: multiple tasks execute in parallel
    - Load distribution: even spread across idle workers
    - Fairness: no single worker hogs all tasks
    """
    
    def __init__(self, 
                 foreman_id: str = "foreman-0",
                 max_workers: int = 5,
                 heartbeat_interval: int = 900,  # 15 minutes
                 missed_heartbeats_threshold: int = 2):
        self.foreman_id = foreman_id
        self.max_workers = max_workers
        self.heartbeat_interval = heartbeat_interval
        self.missed_threshold = missed_heartbeats_threshold
        
        # Worker registry
        self._workers: Dict[str, WorkerStatus] = {}
        self._lock = threading.Lock()
        
        # Monitoring
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Task tracking
        self._task_assignments: Dict[str, str] = {}  # task_id -> worker_id
        self._task_queue: List[Task] = []  # Pending tasks FIFO
        self._results: List[WResult] = []  # Completed results
    
    def submit(self, task_id: str, data: Any) -> None:
        """Submit a task to the queue for processing."""
        task = Task(task_id=task_id, data=data)
        with self._lock:
            self._task_queue.append(task)
        logger.info("[Foreman] Submitted task %s (queue depth: %d)", task_id, len(self._task_queue))

    def process(self) -> Optional[WResult]:
        """
        Process pending tasks by distributing them across ALL idle workers.

        PREVIOUS BEHAVIOR (v3.0):
            Only assigned the first queued task to the first idle worker.
            This left other idle workers unused and created a sequential bottleneck.

        NEW BEHAVIOR (v3.1):
            Distributes tasks to ALL idle workers concurrently:
            1. Collect all idle, healthy workers
            2. For each idle worker, dequeue a task and assign it
            3. Execute assigned tasks concurrently via threads
            4. Collect all results and return the first one (for API compat)

        Returns the first WResult from this batch, or None if no tasks
        were processed. All results are stored in self._results.
        """
        # ── Step 1: Collect idle workers and pending tasks ──────
        with self._lock:
            idle_workers: List[Tuple[str, WorkerStatus]] = [
                (wid, ws) for wid, ws in self._workers.items()
                if ws.status == WStatus.IDLE and ws.healthy
            ]
            pending_tasks: List[Task] = list(self._task_queue)

        if not idle_workers or not pending_tasks:
            logger.debug(
                "[Foreman] process: idle_workers=%d pending_tasks=%d — nothing to do",
                len(idle_workers), len(pending_tasks),
            )
            return None

        # ── Step 2: Assign tasks to idle workers (one per worker) ──
        assignments: List[Tuple[str, Task, WorkerStatus]] = []
        assigned_count = 0

        with self._lock:
            for worker_id, worker_status in idle_workers:
                if not self._task_queue:
                    break  # No more tasks to assign

                task = self._task_queue.pop(0)  # Dequeue first task
                task.assigned_worker = worker_id
                worker_status.status = WStatus.BUSY
                worker_status.tasks_assigned += 1
                self._task_assignments[task.task_id] = worker_id
                assignments.append((worker_id, task, worker_status))
                assigned_count += 1

        logger.info(
            "[Foreman] process: assigned %d tasks to %d idle workers "
            "(remaining queue: %d)",
            assigned_count, len(idle_workers), len(self._task_queue),
        )

        # ── Step 3: Execute tasks concurrently via threads ──────
        batch_results: List[WResult] = []
        execution_errors: List[str] = []

        if assigned_count == 1:
            # Single task: execute directly (no thread overhead)
            worker_id, task, worker_status = assignments[0]
            result = self._execute_task(worker_id, task, worker_status)
            batch_results.append(result)
        else:
            # Multiple tasks: execute concurrently
            threads: List[threading.Thread] = []
            result_lock = threading.Lock()

            def _run_task(wid: str, t: Task, ws: WorkerStatus):
                try:
                    r = self._execute_task(wid, t, ws)
                    with result_lock:
                        batch_results.append(r)
                except Exception as exc:
                    error_result = WResult(
                        ok=False, task_id=t.task_id, worker_id=wid,
                        error=f"Execution exception: {exc}",
                    )
                    with result_lock:
                        batch_results.append(r)
                        execution_errors.append(f"{wid}:{t.task_id} — {exc}")

            for worker_id, task, worker_status in assignments:
                t = threading.Thread(
                    target=_run_task,
                    args=(worker_id, task, worker_status),
                    daemon=True,
                )
                threads.append(t)
                t.start()

            # Wait for all threads to complete
            for t in threads:
                t.join(timeout=60)  # 60s timeout per task

            if execution_errors:
                logger.warning(
                    "[Foreman] process: %d execution errors: %s",
                    len(execution_errors), "; ".join(execution_errors),
                )

        # ── Step 4: Store results and return ────────────────────
        with self._lock:
            self._results.extend(batch_results)

        logger.info(
            "[Foreman] process: batch complete — %d results (%d ok, %d failed)",
            len(batch_results),
            sum(1 for r in batch_results if r.ok),
            sum(1 for r in batch_results if not r.ok),
        )

        # Return first result for backward compatibility
        return batch_results[0] if batch_results else None

    def _execute_task(self, worker_id: str, task: Task, worker_status: WorkerStatus) -> WResult:
        """Execute a single task on a worker and update status."""
        start_time = time.monotonic()
        try:
            if worker_status.handler:
                result_data = worker_status.handler(task.data)
            else:
                result_data = {"processed": task.data}

            duration_ms = (time.monotonic() - start_time) * 1000

            with self._lock:
                worker_status.status = WStatus.IDLE
                worker_status.tasks_assigned -= 1
                worker_status.tasks_completed += 1
                self._task_assignments.pop(task.task_id, None)

            return WResult(
                ok=True,
                task_id=task.task_id,
                worker_id=worker_id,
                data=result_data,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "[Foreman] Task %s failed on worker %s: %s",
                task.task_id, worker_id, exc,
            )
            with self._lock:
                worker_status.status = WStatus.ERROR
                worker_status.tasks_assigned -= 1
                self._task_assignments.pop(task.task_id, None)

            return WResult(
                ok=False,
                task_id=task.task_id,
                worker_id=worker_id,
                error=str(exc),
                duration_ms=duration_ms,
            )
    
    def register_worker(self, agent_card: Dict[str, Any]) -> bool:
        """Register a new worker with the foreman"""
        worker_id = agent_card.get("agent_id")
        if not worker_id:
            return False
        
        with self._lock:
            if len(self._workers) >= self.max_workers:
                return False
            
            self._workers[worker_id] = WorkerStatus(
                worker_id=worker_id,
                last_heartbeat=datetime.now(),
                healthy=True,
                status=WStatus.IDLE,
                tasks_assigned=0,
                tasks_completed=0,
                agent_card=agent_card,
                handler=agent_card.get("handler"),
            )
        
        logger.info("[Foreman] Registered worker: %s", worker_id)
        return True
    
    def deregister_worker(self, worker_id: str):
        """Remove a worker from the pool"""
        with self._lock:
            if worker_id in self._workers:
                del self._workers[worker_id]
                print(f"[Foreman] Deregistered worker: {worker_id}")
    
    def record_heartbeat(self, worker_id: str) -> bool:
        """Record heartbeat from a worker"""
        with self._lock:
            if worker_id not in self._workers:
                return False
            
            worker = self._workers[worker_id]
            worker.last_heartbeat = datetime.now()
            worker.healthy = True
            return True
    
    def check_worker_health(self, worker_id: str) -> bool:
        """Check if worker is healthy based on last heartbeat"""
        with self._lock:
            if worker_id not in self._workers:
                return False
            
            worker = self._workers[worker_id]
            elapsed = (datetime.now() - worker.last_heartbeat).total_seconds()
            
            # Mark unhealthy if missed too many heartbeats
            if elapsed > self.heartbeat_interval * self.missed_threshold:
                worker.healthy = False
                return False
            
            return worker.healthy
    
    def get_healthy_workers(self) -> List[str]:
        """Get list of healthy worker IDs"""
        with self._lock:
            return [
                wid for wid, status in self._workers.items()
                if self.check_worker_health(wid)
            ]
    
    def assign_task(self, task_id: str, worker_id: Optional[str] = None) -> Optional[str]:
        """
        Assign task to a worker
        If worker_id not specified, uses round-robin selection
        Returns assigned worker_id or None if no workers available
        """
        healthy_workers = self.get_healthy_workers()
        
        if not healthy_workers:
            return None
        
        if worker_id and worker_id in healthy_workers:
            assigned = worker_id
        else:
            # Round-robin: pick worker with fewest tasks
            with self._lock:
                worker_loads = [
                    (wid, self._workers[wid].tasks_assigned)
                    for wid in healthy_workers
                ]
                assigned = min(worker_loads, key=lambda x: x[1])[0]
        
        with self._lock:
            self._task_assignments[task_id] = assigned
            self._workers[assigned].tasks_assigned += 1
        
        return assigned
    
    def complete_task(self, task_id: str, success: bool = True):
        """Mark task as completed and update worker stats"""
        with self._lock:
            if task_id not in self._task_assignments:
                return
            
            worker_id = self._task_assignments[task_id]
            del self._task_assignments[task_id]
            
            if worker_id in self._workers:
                worker = self._workers[worker_id]
                worker.tasks_assigned -= 1
                if success:
                    worker.tasks_completed += 1
    
    def monitor_loop(self):
        """Background heartbeat monitoring loop"""
        while self._running:
            try:
                # Check all workers
                with self._lock:
                    for worker_id, status in list(self._workers.items()):
                        elapsed = (datetime.now() - status.last_heartbeat).total_seconds()
                        
                        if elapsed > self.heartbeat_interval * self.missed_threshold:
                            if status.healthy:
                                print(f"[Foreman] Worker {worker_id} missed heartbeats, marking unhealthy")
                                status.healthy = False
                        
                        # Remove dead workers after extended timeout
                        if elapsed > self.heartbeat_interval * (self.missed_threshold + 2):
                            print(f"[Foreman] Removing dead worker: {worker_id}")
                            del self._workers[worker_id]
                
                # Sleep for heartbeat interval
                time.sleep(self.heartbeat_interval / 4)  # Check 4x per interval
                
            except Exception as e:
                print(f"[Foreman] Monitor error: {e}")
                time.sleep(60)
    
    def start_monitoring(self):
        """Start the heartbeat monitoring thread"""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self._monitor_thread.start()
        print(f"[Foreman] Started monitoring (interval={self.heartbeat_interval}s)")
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        print("[Foreman] Stopped monitoring")
    
    def get_status(self) -> Dict[str, Any]:
        """Get foreman status report"""
        with self._lock:
            return {
                "foreman_id": self.foreman_id,
                "running": self._running,
                "total_workers": len(self._workers),
                "healthy_workers": len(self.get_healthy_workers()),
                "active_tasks": len(self._task_assignments),
                "workers": [
                    {
                        "worker_id": w.worker_id,
                        "healthy": w.healthy,
                        "last_heartbeat": w.last_heartbeat.isoformat(),
                        "tasks_assigned": w.tasks_assigned,
                        "tasks_completed": w.tasks_completed
                    }
                    for w in self._workers.values()
                ]
            }
    
    def get_worker_capabilities(self, worker_id: str) -> List[str]:
        """Get capabilities for a specific worker"""
        with self._lock:
            if worker_id not in self._workers:
                return []
            return self._workers[worker_id].agent_card.get("capabilities", [])
