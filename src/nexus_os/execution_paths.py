"""execution_paths.py — Hot/Warm/Cold Execution Paths

Defines the 3-path execution model:
- HOT: <20μs, inline, must not block
- WARM: ~ms, async append  
- COLD: ~s, deferred reconciliation

Use for routing operations to appropriate execution paths.
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, Any, Dict
from concurrent.futures import ThreadPoolExecutor, Future
import threading
import time

logger = logging.getLogger(__name__)


class ExecutionPath(Enum):
    """3-Path Execution Model.
    
    HOT  — Inline, <20μs, no blocking
    WARM — Async, ~ms, fire-and-forget  
    COLD — Deferred, ~s, batch reconciliation
    """
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


# Path characteristics (in milliseconds for reference)
PATH_LATENCY_SLA = {
    ExecutionPath.HOT: 0.020,   # 20μs
    ExecutionPath.WARM: 50.0,    # 50ms
    ExecutionPath.COLD: 1000.0,  # 1000ms
}


@dataclass
class PathConfig:
    """Configuration for an execution path."""
    path: ExecutionPath
    max_workers: int = 1
    timeout_ms: float = 0.0
    
    def __post_init__(self):
        if self.timeout_ms == 0.0:
            self.timeout_ms = PATH_LATENCY_SLA[self.path]


class PathRouter:
    """
    Routes operations to appropriate execution paths.
    
    Automatically determines path based on operation characteristics:
    - Check budget, trust lookup, circuit breaker → HOT
    - Event append, capability update → WARM  
    - DB writes, batch jobs, reconciliation → COLD
    
    Can also be used directly for specific routing.
    """
    
    # Thread pool for WARM/COLD operations
    _executor: Optional[ThreadPoolExecutor] = None
    _executor_lock = threading.Lock()
    
    def __init__(self):
        self._warm_queue: Dict[str, list] = {}
        self._cold_queue: Dict[str, list] = {}
    
    # ── Auto-Route ───────────────────────────────────────────
    
    def route(
        self,
        operation: str,
        **kwargs,
    ) -> ExecutionPath:
        """
        Auto-route based on operation type.
        
        Common operations:
        - "check_budget", "get_trust", "circuit_breaker" → HOT
        - "append_event", "update_capability" → WARM
        - "write_db", "reconcile", "batch" → COLD
        """
        op = operation.lower()
        
        # HOT paths
        if any(kw in op for kw in ["check", "get", "lookup", "retrieve", "circuit"]):
            return ExecutionPath.HOT
        
        # COLD paths  
        if any(kw in op for kw in ["write", "save", "persist", "batch", "reconcile", "commit"]):
            return ExecutionPath.COLD
        
        # WARM is default for append/update operations
        if any(kw in op for kw in ["append", "update", "add", "increment"]):
            return ExecutionPath.WARM
        
        # Default to WARM for unknown
        logger.warning(f"Unknown operation: {operation}, defaulting to WARM")
        return ExecutionPath.WARM
    
    # ── Execution ──────────────────────────────────────────
    
    def execute_hot(
        self,
        func: Callable[[], Any],
    ) -> Any:
        """
        Execute in HOT path (inline, must not block).
        
        Used for: budget checks, trust lookups, circuit breaker checks.
        """
        # Direct call - no threading
        return func()
    
    def execute_warm(
        self,
        func: Callable[[], Any],
        id: Optional[str] = None,
        timeout_ms: float = 50.0,
    ) -> Future:
        """
        Execute in WARM path (async, fire-and-forget).
        
        Used for: event appends, capability updates.
        Returns a Future for optional async result handling.
        """
        executor = self._get_executor(max_workers=4)
        
        future = executor.submit(func)
        
        # Don't wait - fire and forget
        # Caller can optionally .result() if needed
        
        logger.debug(f"WARM: submitted (timeout={timeout_ms}ms)")
        return future
    
    def execute_cold(
        self,
        func: Callable[[], Any],
        id: Optional[str] = None,
        timeout_ms: float = 1000.0,
    ) -> Future:
        """
        Execute in COLD path (deferred, batch).
        
        Used for: DB writes, batch jobs, reconciliation.
        """
        executor = self._get_executor(max_workers=2)
        
        future = executor.submit(func)
        
        logger.debug(f"COLD: submitted (timeout={timeout_ms}ms)")
        return future
    
    # ── Batch Operations ─────────────────────────────────
    
    def queue_warm(self, operation_id: str, func: Callable[[], Any]):
        """Queue operation for WARM batch execution."""
        if operation_id not in self._warm_queue:
            self._warm_queue[operation_id] = []
        self._warm_queue[operation_id].append(func)
    
    def flush_warm(self, operation_id: str) -> int:
        """Execute all queued WARM operations."""
        if operation_id not in self._warm_queue:
            return 0
        
        funcs = self._warm_queue.pop(operation_id)
        
        for func in funcs:
            self.execute_warm(func)
        
        logger.debug(f"WARM: flushed {len(funcs)} operations")
        return len(funcs)
    
    def queue_cold(self, operation_id: str, func: Callable[[], Any]):
        """Queue operation for COLD batch execution."""
        if operation_id not in self._cold_queue:
            self._cold_queue[operation_id] = []
        self._cold_queue[operation_id].append(func)
    
    def flush_cold(self, operation_id: str) -> int:
        """Execute all queued COLD operations."""
        if operation_id not in self._cold_queue:
            return 0
        
        funcs = self._cold_queue.pop(operation_id)
        
        for func in funcs:
            self.execute_cold(func)
        
        logger.debug(f"COLD: flushed {len(funcs)} operations")
        return len(funcs)
    
    # ── Utility ───────────────────────────────────────────
    
    def _get_executor(self, max_workers: int) -> ThreadPoolExecutor:
        """Get or create thread pool executor."""
        if self._executor is None:
            with self._executor_lock:
                if self._executor is None:
                    self._executor = ThreadPoolExecutor(max_workers=max_workers)
        return self._executor
    
    @classmethod
    def shutdown(cls):
        """Shutdown executor pool."""
        with cls._executor_lock:
            if cls._executor is not None:
                cls._executor.shutdown(wait=True)
                cls._executor = None
    
    def get_stats(self) -> Dict[str, int]:
        """Get path routing statistics."""
        return {
            "warm_queued": sum(len(q) for q in self._warm_queue.values()),
            "cold_queued": sum(len(q) for q in self._cold_queue.values()),
        }


# Default router instance
_router: Optional[PathRouter] = None
_router_lock = threading.Lock()


def get_router() -> PathRouter:
    """Get the singleton PathRouter instance."""
    global _router
    if _router is None:
        with _router_lock:
            if _router is None:
                _router = PathRouter()
    return _router


# Decorator for path routing
def hot_path(func: Callable) -> Callable:
    """Decorator to execute in HOT path."""
    def wrapper(*args, **kwargs):
        return get_router().execute_hot(lambda: func(*args, **kwargs))
    return wrapper


def warm_path(func: Callable) -> Callable:
    """Decorator to execute in WARM path."""
    def wrapper(*args, **kwargs):
        return get_router().execute_warm(lambda: func(*args, **kwargs))
    return wrapper


def cold_path(func: Callable) -> Callable:
    """Decorator to execute in COLD path."""
    def wrapper(*args, **kwargs):
        return get_router().execute_cold(lambda: func(*args, **kwargs))
    return wrapper