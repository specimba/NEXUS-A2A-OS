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


# ── Circuit Breaker with HALF_OPEN State ───────────────────────────────

class CircuitState(Enum):
    """Circuit Breaker States."""
    CLOSED = "closed"     # Normal operation
    HALF_OPEN = "half_open"  # Testing recovery
    OPEN = "open"       # Blocking requests


class AdaptiveCircuitBreaker:
    """
    Circuit breaker with HALF_OPEN state for GMR/execution paths.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - HALF_OPEN: Testing recovery, limited requests allowed
    - OPEN: Circuit tripped, fail fast
    
    Parameters:
    - failure_threshold: failures before tripping to OPEN
    - success_threshold: successes in HALF_OPEN to close
    - half_open_max_calls: max calls allowed in HALF_OPEN
    - timeout_seconds: time before auto-transition to HALF_OPEN
    """
    
    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        success_threshold: int = 2,
        half_open_max_calls: int = 3,
        timeout_seconds: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.half_open_max_calls = half_open_max_calls
        self.timeout_seconds = timeout_seconds
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time = 0.0
        self._lock = threading.RLock()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self._state
    
    def is_available(self) -> bool:
        """Check if requests can pass through."""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.HALF_OPEN:
                return self._half_open_calls < self.half_open_max_calls
            return False  # OPEN
    
    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                self._half_open_calls += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._half_open_calls = 0
                    logger.info(f"Circuit [{self.name}] CLOSED <- HALF_OPEN (recovered)")
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0  # Reset on success
    
    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self._last_failure_time = time.time()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._failure_count = 1
                self._half_open_calls = 0
                logger.warning(f"Circuit [{self.name}] OPEN <- HALF_OPEN (failure during test)")
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(f"Circuit [{self.name}] OPEN <- CLOSED ({self._failure_count} failures)")
    
    def maybe_transition_to_half_open(self) -> bool:
        """
        Check timeout and transition OPEN -> HALF_OPEN.
        Returns True if transition occurred.
        """
        with self._lock:
            if self._state != CircuitState.OPEN:
                return False
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                self._failure_count = 0
                self._success_count = 0
                self._half_open_calls = 0
                logger.info(f"Circuit [{self.name}] HALF_OPEN <- OPEN (timeout: {elapsed:.1f}s)")
                return True
            return False
    
    def call(
        self,
        func: Callable[[], Any],
        fallback: Any = None,
    ) -> Any:
        """
        Execute func with circuit breaker protection.
        
        Returns fallback if circuit is OPEN and not transitioning.
        """
        with self._lock:
            # Check auto-transition
            self.maybe_transition_to_half_open()
            
            if not self.is_available():
                return fallback
        
        try:
            result = func()
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            logger.warning(f"Circuit [{self.name}] call failed: {e}")
            return fallback
    
    def get_status(self) -> dict:
        """Return circuit status for monitoring."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "half_open_calls": self._half_open_calls,
                "available": self.is_available(),
            }


# ── Module-level convenience ────────────────────────────────────────

_circuit_breakers: Dict[str, AdaptiveCircuitBreaker] = {}
_circuit_lock = threading.Lock()


def get_circuit_breaker(name: str = "default") -> AdaptiveCircuitBreaker:
    """Get or create a circuit breaker by name."""
    with _circuit_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = AdaptiveCircuitBreaker(name=name)
        return _circuit_breakers[name]