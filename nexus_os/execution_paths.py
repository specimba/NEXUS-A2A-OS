"""execution_paths.py — Execution Paths & Speculative Routing

Added speculative routing for multiple endpoint fan-out.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future, wait
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ExecutionPath(Enum):
    """3-Path Execution Model."""
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


PATH_LATENCY_SLA = {
    ExecutionPath.HOT: 0.020,
    ExecutionPath.WARM: 50.0,
    ExecutionPath.COLD: 1000.0,
}


@dataclass
class PathConfig:
    path: ExecutionPath
    max_workers: int = 1
    timeout_ms: float = 0.0


class PathRouter:
    """Routes operations to execution paths."""

    _executor: Optional[ThreadPoolExecutor] = None
    _executor_lock = threading.Lock()

    def route(self, operation: str, **kwargs) -> ExecutionPath:
        op = operation.lower()
        if any(kw in op for kw in ["check", "get", "lookup", "retrieve", "circuit"]):
            return ExecutionPath.HOT
        if any(kw in op for kw in ["write", "save", "persist", "batch", "reconcile", "commit"]):
            return ExecutionPath.COLD
        if any(kw in op for kw in ["append", "update", "add", "increment"]):
            return ExecutionPath.WARM
        logger.warning(f"Unknown operation: {operation}, defaulting to WARM")
        return ExecutionPath.WARM

    def execute_hot(self, func: Callable[[], Any]) -> Any:
        return func()

    def execute_warm(self, func: Callable[[], Any], id: Optional[str] = None, timeout_ms: float = 50.0) -> Future:
        if not hasattr(self, '_warm_executor'):
            self._warm_executor = ThreadPoolExecutor(max_workers=4)
        return self._warm_executor.submit(func)

    def execute_cold(self, func: Callable[[], Any]) -> Future:
        with self._executor_lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(max_workers=2)
        return self._executor.submit(func)

    def execute_cold_batch(self, funcs: List[Callable[[], Any]]) -> List[Future]:
        for func in funcs:
            self.execute_cold(func)
        logger.debug(f"COLD: flushed {len(funcs)} operations")
        return len(funcs)

    def _get_executor(self, max_workers: int) -> ThreadPoolExecutor:
        if self._executor is None:
            with self._executor_lock:
                if self._executor is None:
                    self._executor = ThreadPoolExecutor(max_workers=max_workers)
        return self._executor

    @classmethod
    def shutdown(cls):
        with cls._executor_lock:
            if cls._executor is not None:
                cls._executor.shutdown(wait=True)
                cls._executor = None


_router_instance: Optional[PathRouter] = None
_router_lock = threading.Lock()


def get_router() -> PathRouter:
    global _router_instance
    with _router_lock:
        if _router_instance is None:
            _router_instance = PathRouter()
        return _router_instance


def route_to_path(operation: str):
    """Decorator to route function to execution path."""
    def wrapper(func: Callable) -> Callable:
        def run(*args, **kwargs):
            return get_router().execute_hot(lambda: func(*args, **kwargs))
        return run if get_router().route(operation) == ExecutionPath.HOT else get_router().execute_warm(lambda: func(*args, **kwargs))
    return wrapper


class CircuitState(Enum):
    CLOSED = "closed"
    HALF_OPEN = "half_open"
    OPEN = "open"


class AdaptiveCircuitBreaker:
    """Circuit breaker with HALF_OPEN state."""

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
        with self._lock:
            return self._state

    def is_available(self) -> bool:
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.HALF_OPEN:
                return self._half_open_calls < self.half_open_max_calls
            return False

    def record_success(self) -> None:
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
                self._failure_count = 0

    def record_failure(self) -> None:
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

    def call(self, func: Callable[[], Any], fallback: Any = None) -> Any:
        with self._lock:
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
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "half_open_calls": self._half_open_calls,
                "available": self.is_available(),
            }


_circuit_breakers: Dict[str, AdaptiveCircuitBreaker] = {}
_circuit_lock = threading.Lock()


def get_circuit_breaker(name: str = "default") -> AdaptiveCircuitBreaker:
    with _circuit_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = AdaptiveCircuitBreaker(name=name)
        return _circuit_breakers[name]


# ── Speculative Routing Proxy ────────────────────────────────────────────────

class SpeculativeRouter:
    """
    Fan-out requests to multiple endpoints, return first successful response.
    
    Use for: parallel model queries, multi-source data retrieval,
    redundant execution paths where any success is sufficient.
    """
    
    def __init__(
        self,
        max_parallel: int = 3,
        timeout_seconds: float = 5.0,
    ):
        self.max_parallel = max_parallel
        self.timeout_seconds = timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=max_parallel)
    
    def route(
        self,
        candidates: List[Tuple[str, Callable[[], Any]]],
    ) -> Tuple[Optional[str], Optional[Any]]:
        """
        Execute all candidates in parallel.
        
        Args:
            candidates: List of (name, callable) tuples
            
        Returns:
            (winning_name, result) or (None, None) if all fail
        """
        if not candidates:
            return None, None
        
        # Submit all to executor
        futures = {}
        for name, func in candidates:
            future = self._executor.submit(func)
            futures[future] = name
        
        # Wait for first completion or timeout
        done, _ = wait(futures.keys(), timeout=self.timeout_seconds, return_when="FIRST_COMPLETED")
        
        # Check results
        for future in done:
            name = futures[future]
            try:
                result = future.result()
                # Cancel remaining
                for f in futures:
                    f.cancel()
                return name, result
            except Exception as e:
                logger.warning(f"Speculative route [{name}] failed: {e}")
                continue
        
        # All failed
        return None, None
    
    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)


def speculative_route(
    candidates: List[Tuple[str, Callable[[], Any]]],
    timeout: float = 5.0,
) -> Tuple[Optional[str], Optional[Any]]:
    """
    Convenience function for speculative routing.
    
    Example:
        name, result = speculative_route([
            ("fast-model", lambda: query_fast()),
            ("quality-model", lambda: query_quality()),
        ])
    """
    router = SpeculativeRouter(
        max_parallel=len(candidates),
        timeout_seconds=timeout,
    )
    try:
        return router.route(candidates)
    finally:
        router.shutdown()