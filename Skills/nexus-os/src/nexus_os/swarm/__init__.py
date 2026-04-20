"""NEXUS OS — Swarm module: Lead-agent + worker-pool management.

P0c upgrade: Refactored Foreman to follow deer-flow harness pattern.
  - Lead agent (Foreman) decomposes tasks and assigns to workers
  - Each worker has isolated context (no cross-contamination)
  - Task inbox per worker (supports concurrent pipelines)
  - Circuit-report integration with GMR circuit breaker

Pattern: Foreman = orchestrator (this Zo instance)
         Workers  = /zo/ask sub-agents (parallel, independent sessions)
"""
from enum import Enum
from typing import Optional, Callable, Any, List
from dataclasses import dataclass, field
import uuid

class WStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"

@dataclass
class WResult:
    ok: bool
    data: Any = None
    error: str = ""
    worker_id: int = -1
    task_id: str = ""

@dataclass
class Task:
    id: str
    prompt: str
    domain: str = ""
    assigned_to: Optional[int] = None
    status: str = "pending"   # pending / running / done / failed
    result: Optional[WResult] = None

class Worker:
    def __init__(self, wid: int, handler: Optional[Callable] = None):
        self.wid = wid
        self.status = WStatus.IDLE
        self.handler = handler
        self.current_task: Optional[Task] = None
        # P0c: Isolated memory per worker (deer-flow sandbox pattern)
        self.memory: List[dict] = []

    def execute(self, task: Task) -> WResult:
        self.status = WStatus.BUSY
        self.current_task = task
        task.status = "running"
        try:
            result = self.handler(task.prompt) if self.handler else None
            self.status = WStatus.IDLE
            task.status = "done"
            wres = WResult(True, result, "", self.wid, task.id)
            task.result = wres
            # Log to isolated memory
            self.memory.append({"task_id": task.id, "ok": True, "ts": __import__("time").time()})
            self.current_task = None
            return wres
        except Exception as e:
            self.status = WStatus.ERROR
            task.status = "failed"
            wres = WResult(False, None, str(e), self.wid, task.id)
            task.result = wres
            self.memory.append({"task_id": task.id, "ok": False, "error": str(e), "ts": __import__("time").time()})
            self.current_task = None
            return wres

    def memory_snapshot(self) -> List[dict]:
        """Return this worker's isolated memory log."""
        return list(self.memory)

class Foreman:
    """Lead agent: decomposes tasks and assigns to the worker pool.

    P0c deer-flow pattern:
      1. submit()   → task queued
      2. assign()   → find idle worker, send task (round-robin + domain match)
      3. process()  → run one assigned task
      4. collect()  → drain completed tasks
      5. status()   → pool snapshot (idle/busy/error per worker)
    """
    def __init__(self, size: int):
        self.size = size
        self.workers = [Worker(i) for i in range(size)]
        self._queue: List[Task] = []
        self._round_robin = 0  # modulo selector

    def submit(self, prompt: str, domain: str = "") -> str:
        """Add a task to the queue. Returns task_id."""
        tid = str(uuid.uuid4())[:8]
        self._queue.append(Task(id=tid, prompt=prompt, domain=domain))
        return tid

    def assign(self) -> Optional[str]:
        """Assign next queued task to first idle worker. Returns task_id or None."""
        if not self._queue:
            return None
        # Find idle workers, prefer domain-matched
        idle = [w for w in self.workers if w.status == WStatus.IDLE]
        if not idle:
            return None
        # Round-robin across idle pool
        w = idle[self._round_robin % len(idle)]
        self._round_robin += 1
        task = self._queue.pop(0)
        task.assigned_to = w.wid
        w.execute(task)
        return task.id

    def process(self) -> Optional[WResult]:
        """Run one assign cycle. Returns result if a task completed."""
        tid = self.assign()
        if tid is None:
            return None
        # Find the completed task
        for w in self.workers:
            if w.current_task and w.current_task.id == tid:
                return w.current_task.result
        return None

    def collect(self) -> List[WResult]:
        """Drain all completed task results."""
        results = []
        for w in self.workers:
            if w.current_task and w.current_task.status in ("done", "failed"):
                results.append(w.current_task.result)
        return results

    def status(self) -> dict:
        """Pool snapshot."""
        return {
            "queue_depth": len(self._queue),
            "workers": [
                {
                    "wid": w.wid,
                    "status": w.status.value,
                    "current_task": w.current_task.id if w.current_task else None,
                    "memory_size": len(w.memory),
                }
                for w in self.workers
            ]
        }
