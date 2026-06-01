"""NEXUS OS — Swarm module: deer-flow harness + P2b auction allocation."""
from enum import Enum
from typing import Optional, Callable, Any, List
from dataclasses import dataclass, field
import time, uuid

# ── Auction model (ArXiv 2604.11478) ─────────────────────────────────────────
# bid = (capability × 0.4) + (trust × 0.3) + ((1−load) × 0.2) + (spec_match × 0.1)
_DOMAIN_SPEC_SCORES = {
    "code": {"code": 0.9, "reason": 0.5, "research": 0.4},
    "reason": {"reason": 0.9, "sec": 0.6, "code": 0.5},
    "research": {"research": 0.9, "fast": 0.4},
    "fast": {"fast": 0.9, "code": 0.3},
    "sec": {"sec": 0.9, "reason": 0.5, "code": 0.6},
}

@dataclass
class WStatus(Enum):
    IDLE = "idle"; BUSY = "busy"; ERROR = "error"

@dataclass
class WResult:
    ok: bool; data: Any = None; error: str = ""
    task_id: str = ""; duration_ms: float = 0.0

@dataclass
class Task:
    id: str; prompt: str; domain: str = "reason"
    priority: float = 0.5; metadata: dict = field(default_factory=dict)
    submitted_at: float = field(default_factory=time.time)

@dataclass
class Bid:
    worker_id: int; capability: float; trust: float
    load: float; spec_match: float; final_bid: float

class Worker:
    def __init__(self, wid: int, domain: str = "reason", trust: float = 0.8):
        self.wid = wid; self.domain = domain; self.trust = trust
        self.status = WStatus.IDLE; self.handler: Optional[Callable] = None
        self._memory: List[dict] = []; self._load = 0.0

    def execute(self, task: Task) -> WResult:
        self.status = WStatus.BUSY; t0 = time.time()
        try:
            result = self.handler(task.prompt) if self.handler else None
            self.status = WStatus.IDLE; dur = (time.time() - t0) * 1000
            entry = {"ok": True, "task_id": task.id, "result": result, "duration_ms": dur}
            self._memory.append(entry); self._load = max(0, self._load - 0.1)
            return WResult(ok=True, data=result, task_id=task.id, duration_ms=dur)
        except Exception as e:
            self.status = WStatus.ERROR; self._load = min(1.0, self._load + 0.2)
            entry = {"ok": False, "task_id": task.id, "error": str(e)}
            self._memory.append(entry)
            return WResult(ok=False, error=str(e), task_id=task.id)

    def memory_snapshot(self) -> List[dict]:
        return list(self._memory[-10:])

    def bid_on(self, task: Task) -> Bid:
        cap = self._capability_for(task.domain)
        spec = _DOMAIN_SPEC_SCORES.get(task.domain, {}).get(self.domain, 0.1)
        load = min(1.0, self._load)
        bid_val = (cap * 0.4) + (self.trust * 0.3) + ((1 - load) * 0.2) + (spec * 0.1)
        return Bid(worker_id=self.wid, capability=cap, trust=self.trust, load=load, spec_match=spec, final_bid=bid_val)

    def _capability_for(self, domain: str) -> float:
        return 0.9 if domain == self.domain else 0.5

class Foreman:
    """Lead agent: owns task queue, runs auction, assigns to winner."""
    def __init__(self, size: int = 2):
        self.tasks: List[Task] = []
        self.workers = [Worker(i, domain=["code", "reason", "research", "fast", "sec"][i % 5]) for i in range(size)]
        self._assignments: Dict[str, int] = {}   # task_id → worker_id
        self._completed: List[WResult] = []

    def submit(self, prompt: str, domain: str = "reason", priority: float = 0.5) -> str:
        tid = str(uuid.uuid4())[:8]
        self.tasks.append(Task(id=tid, prompt=prompt, domain=domain, priority=priority))
        return tid

    def process(self) -> Optional[WResult]:
        if not self.tasks: return None
        task = self.tasks.pop(0)
        # Auction: all idle workers bid, highest wins
        idle = [w for w in self.workers if w.status == WStatus.IDLE]
        if not idle:
            self.tasks.insert(0, task); return None
        bids = [w.bid_on(task) for w in idle]
        winner = max(bids, key=lambda b: b.final_bid).worker_id
        self._assignments[task.id] = winner
        worker = self.workers[winner]
        worker._load = min(1.0, worker._load + 0.3)
        result = worker.execute(task)
        self._completed.append(result)
        return result

    def status(self) -> dict:
        return {
            "queue_depth": len(self.tasks),
            "workers": [{"id": w.wid, "status": w.status.value, "domain": w.domain, "load": round(w._load, 2)} for w in self.workers],
            "assignments": len(self._assignments), "completed": len(self._completed),
        }

    def collect(self) -> List[WResult]: return list(self._completed)
    def assign(self, task_id: str) -> Optional[int]: return self._assignments.get(task_id)