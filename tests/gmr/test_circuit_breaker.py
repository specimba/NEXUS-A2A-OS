"""tests/gmr/test_circuit_breaker.py — AdaptiveCircuitBreaker state machine tests"""
import time
import pytest
from unittest.mock import patch

from nexus_os.gmr.circuit_breaker import AdaptiveCircuitBreaker, CircuitState


class TestCircuitBreakerInitialState:
    def test_initial_state_is_closed(self):
        cb = AdaptiveCircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_initial_failure_count_zero(self):
        cb = AdaptiveCircuitBreaker()
        assert cb._failure_count == 0

    def test_can_execute_when_closed(self):
        cb = AdaptiveCircuitBreaker()
        assert cb.can_execute() is True

    def test_custom_threshold_and_cooldown(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=5, base_cooldown=120)
        assert cb.failure_threshold == 5
        assert cb.base_cooldown == 120


class TestClosedToOpen:
    def test_failures_below_threshold_stay_closed(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_threshold_failures_trip_to_open(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb._state == CircuitState.OPEN

    def test_cannot_execute_when_open(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert cb.can_execute() is False

    def test_open_sets_cooldown_timer(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=1, base_cooldown=60)
        before = time.time()
        cb.record_failure()
        assert cb._open_until >= before + 60


class TestOpenToHalfOpen:
    def test_transitions_to_half_open_after_cooldown(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=1, base_cooldown=60)
        cb.record_failure()
        assert cb._state == CircuitState.OPEN
        # Simulate cooldown expiry
        cb._open_until = time.time() - 1
        assert cb.state == CircuitState.HALF_OPEN

    def test_can_execute_when_half_open(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=1, base_cooldown=60)
        cb.record_failure()
        cb._open_until = time.time() - 1
        assert cb.can_execute() is True


class TestHalfOpenRecovery:
    def test_success_in_half_open_recovers_to_closed(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=1, base_cooldown=60)
        cb.record_failure()
        cb._open_until = time.time() - 1
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0

    def test_success_resets_cooldown_to_base(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=1, base_cooldown=60)
        cb.record_failure()
        cb._cooldown = 240  # simulate previous backoff
        cb._open_until = time.time() - 1
        cb.record_success()
        assert cb._cooldown == 60

    def test_success_resets_open_until(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=1, base_cooldown=60)
        cb.record_failure()
        cb._open_until = time.time() - 1
        cb.record_success()
        assert cb._open_until == 0.0


class TestHalfOpenFailureBackoff:
    def test_failure_in_half_open_returns_to_open(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=1, base_cooldown=60)
        cb.record_failure()
        cb._open_until = time.time() - 1
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb._state == CircuitState.OPEN

    def test_exponential_backoff_doubles_cooldown(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=1, base_cooldown=60)
        cb.record_failure()
        cb._open_until = time.time() - 1
        _ = cb.state  # trigger HALF_OPEN
        cb.record_failure()
        assert cb._cooldown == 120

    def test_exponential_backoff_caps_at_3600(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=1, base_cooldown=2000)
        cb.record_failure()
        cb._open_until = time.time() - 1
        _ = cb.state
        cb.record_failure()
        assert cb._cooldown == 3600

    def test_repeated_half_open_failures_keep_doubling(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=1, base_cooldown=30)
        # Trip to OPEN
        cb.record_failure()
        # HALF_OPEN -> fail -> OPEN (cooldown 60)
        cb._open_until = time.time() - 1
        _ = cb.state
        cb.record_failure()
        assert cb._cooldown == 60
        # HALF_OPEN -> fail -> OPEN (cooldown 120)
        cb._open_until = time.time() - 1
        _ = cb.state
        cb.record_failure()
        assert cb._cooldown == 120


class TestSuccessWhileClosed:
    def test_success_resets_partial_failures(self):
        cb = AdaptiveCircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_success_on_fresh_breaker_stays_closed(self):
        cb = AdaptiveCircuitBreaker()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0
