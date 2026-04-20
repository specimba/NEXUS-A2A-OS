"""NEXUS OS — Swarm module: Worker pool management."""
from enum import Enum
from typing import Optional, Callable, Any

class WStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"

class WResult:
    def __init__(self, ok: bool, data: Any = None, error: str = ""):
        self.ok = ok
        self.data = data
        self.error = error

class Worker:
    def __init__(self, wid: int, handler: Optional[Callable] = None):
        self.wid = wid
        self.status = WStatus.IDLE
        self.handler = handler

    def execute(self, tid: str, data: Any) -> WResult:
        self.status = WStatus.BUSY
        try:
            result = self.handler(data) if self.handler else None
            self.status = WStatus.IDLE
            return WResult(True, result)
        except Exception as e:
            self.status = WStatus.ERROR
            return WResult(False, None, str(e))

class Foreman:
    def __init__(self, size: int):
        self.workers = [Worker(i) for i in range(size)]
        self._queue: list = []

    def submit(self, tid: str, data: Any):
        self._queue.append((tid, data))

    def process(self) -> Optional[WResult]:
        if not self._queue:
            return None
        tid, data = self._queue.pop(0)
        for w in self.workers:
            if w.status == WStatus.IDLE:
                return w.execute(tid, data)
        return None