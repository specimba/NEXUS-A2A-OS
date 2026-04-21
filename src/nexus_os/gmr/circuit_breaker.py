"""gmr/circuit_breaker.py — Adaptive Circuit Breaker for API Failovers"""
import time
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, blocking requests
    HALF_OPEN = "half_open" # Testing recovery

class AdaptiveCircuitBreaker:
    def __init__(self, failure_threshold=3, base_cooldown=60):
        self.failure_threshold = failure_threshold
        self.base_cooldown = base_cooldown
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._cooldown = base_cooldown
        self._open_until = 0.0

    @property
    def state(self) -> CircuitState:
        """Evaluate temporal state before returning."""
        if self._state == CircuitState.OPEN:
            if time.time() >= self._open_until:
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit entered HALF_OPEN state for recovery testing.")
        return self._state

    def record_failure(self):
        """Record an API failure and trip circuit if threshold reached."""
        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery test, backoff exponentially
            self._cooldown = min(self._cooldown * 2, 3600)
            self._open_until = time.time() + self._cooldown
            self._state = CircuitState.OPEN
            logger.warning(f"Recovery failed. Circuit OPEN. Cooldown: {self._cooldown}s")
        else:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._open_until = time.time() + self._cooldown
                logger.error("Failure threshold reached. Circuit TRIPPED (OPEN).")

    def record_success(self):
        """Record a successful API call and reset state."""
        if self.state == CircuitState.HALF_OPEN or self._failure_count > 0:
            logger.info("Circuit RECOVERED. State reset to CLOSED.")
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._cooldown = self.base_cooldown
        self._open_until = 0.0

    def can_execute(self) -> bool:
        """Returns True if the circuit allows requests."""
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)
