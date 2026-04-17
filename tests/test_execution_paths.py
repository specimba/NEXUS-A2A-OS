"""tests/test_execution_paths.py — Execution Paths & Circuit Breaker Tests"""

import pytest
import time
import threading

from nexus_os.execution_paths import (
    ExecutionPath,
    PathRouter,
    AdaptiveCircuitBreaker,
    CircuitState,
    get_circuit_breaker,
)


class TestExecutionPathRouting:
    """Test PathRouter auto-routing."""

    def test_route_hot_keywords(self):
        router = PathRouter()
        assert router.route("check_budget") == ExecutionPath.HOT
        assert router.route("get_trust") == ExecutionPath.HOT
        assert router.route("circuit_breaker_status") == ExecutionPath.HOT

    def test_route_warm_keywords(self):
        router = PathRouter()
        assert router.route("append_event") == ExecutionPath.WARM
        assert router.route("update_capability") == ExecutionPath.WARM

    def test_route_cold_keywords(self):
        router = PathRouter()
        assert router.route("write_db") == ExecutionPath.COLD
        assert router.route("persist_state") == ExecutionPath.COLD


class TestAdaptiveCircuitBreaker:
    """Test Circuit Breaker with HALF_OPEN state."""

    def test_initial_closed_state(self):
        cb = AdaptiveCircuitBreaker(name="test-init")
        assert cb.state == CircuitState.CLOSED
        assert cb.is_available() is True

    def test_failure_trips_circuit(self):
        cb = AdaptiveCircuitBreaker(
            name="test-fail",
            failure_threshold=3,
        )
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.is_available() is False

    def test_half_open_transition(self):
        cb = AdaptiveCircuitBreaker(
            name="test-half",
            failure_threshold=3,
            timeout_seconds=0.1,
        )
        # Trip the circuit
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(0.15)
        cb.maybe_transition_to_half_open()
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.is_available() is True

    def test_recovery_from_half_open(self):
        cb = AdaptiveCircuitBreaker(
            name="test-recovery",
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=0.1,
        )
        # Trip then transition to half-open
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.15)
        cb.maybe_transition_to_half_open()
        
        # Record successes
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        # Should recover to CLOSED
        assert cb.state == CircuitState.CLOSED

    def test_failure_during_half_open_reopens(self):
        cb = AdaptiveCircuitBreaker(
            name="test-restore",
            failure_threshold=3,
            timeout_seconds=0.1,
        )
        # Trip then transition
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.15)
        cb.maybe_transition_to_half_open()
        
        # Failure during half-open
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_circuit_call_success(self):
        cb = AdaptiveCircuitBreaker(name="test-call")
        
        def success_func():
            return "success"
        
        result = cb.call(success_func, fallback="fallback")
        assert result == "success"
        assert cb.state == CircuitState.CLOSED

    def test_circuit_call_failure(self):
        cb = AdaptiveCircuitBreaker(name="test-fail-call")
        
        def fail_func():
            raise RuntimeError("boom")
        
        result = cb.call(fail_func, fallback="fallback")
        assert result == "fallback"

    def test_circuit_call_blocked(self):
        cb = AdaptiveCircuitBreaker(
            name="test-blocked",
            failure_threshold=1,
        )
        cb.record_failure()  # Trip to OPEN
        
        def should_not_run():
            assert False, "Should not reach here"
        
        result = cb.call(should_not_run, fallback="blocked")
        assert result == "blocked"

    def test_get_circuit_breaker_singleton(self):
        cb1 = get_circuit_breaker("shared")
        cb2 = get_circuit_breaker("shared")
        assert cb1 is cb2

    def test_get_status(self):
        cb = AdaptiveCircuitBreaker(name="test-status")
        status = cb.get_status()
        assert status["name"] == "test-status"
        assert status["state"] == "closed"
        assert "failure_count" in status
        assert "available" in status
class TestSpeculativeRouting:
    """Test speculative routing proxy."""

    def test_first_succeeds(self):
        from nexus_os.execution_paths import SpeculativeRouter
        sr = SpeculativeRouter(max_parallel=3, timeout_seconds=1.0)
        candidates = [
            ("fast", lambda: "success"),
            ("slow", lambda: time.sleep(0.5) or "late"),
        ]
        name, result = sr.route(candidates)
        assert name == "fast"
        assert result == "success"
        sr.shutdown()

    def test_all_fail_returns_none(self):
        from nexus_os.execution_paths import SpeculativeRouter
        sr = SpeculativeRouter(max_parallel=2, timeout_seconds=1.0)
        candidates = [
            ("fail1", lambda: (_ for _ in ()).throw(RuntimeError("e1"))),
            ("fail2", lambda: (_ for _ in ()).throw(RuntimeError("e2"))),
        ]
        name, result = sr.route(candidates)
        assert name is None
        assert result is None
        sr.shutdown()

    def test_convenience_function(self):
        from nexus_os.execution_paths import speculative_route
        name, result = speculative_route([
            ("quick", lambda: "ok"),
        ], timeout=1.0)
        assert name == "quick"
        assert result == "ok"

    def test_timeout_protection(self):
        from nexus_os.execution_paths import SpeculativeRouter
        sr = SpeculativeRouter(max_parallel=2, timeout_seconds=0.2)
        candidates = [
            ("slow", lambda: time.sleep(1.0) or "too late"),
            ("fast", lambda: "fast ok"),
        ]
        name, result = sr.route(candidates)
        # Either hits timeout or fast succeeds
        assert name in ("slow", "fast")
        sr.shutdown()
