"""gmr/circuit_breaker.py — Adaptive Circuit Breaker for API Failovers (persistent)"""
import json
import os
import time
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CIRCUIT_STATE_FILE = Path(os.path.expanduser("~")) / ".gmr_circuit.json"

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, blocking requests
    HALF_OPEN = "half_open" # Testing recovery

class AdaptiveCircuitBreaker:
    def __init__(self, failure_threshold=3, base_cooldown=60, persist_path=None, persist=None):
        self.failure_threshold = failure_threshold
        self.base_cooldown = base_cooldown
        # Persistence is opt-in (mirrors relay ProviderCircuitBreaker.persist=False).
        # When disabled, the breaker is purely in-memory and never touches disk,
        # so tests and independent production singletons stay isolated.
        if persist is not None:
            self._persist = bool(persist)
        else:
            self._persist = persist_path is not None
        self._persist_path = Path(persist_path) if persist_path else CIRCUIT_STATE_FILE

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._cooldown = base_cooldown
        self._open_until = 0.0
        if self._persist:
            self._load()

    def _save(self):
        if not self._persist:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._persist_path.write_text(json.dumps({
            "state": self._state.value,
            "failure_count": self._failure_count,
            "cooldown": self._cooldown,
            "open_until": self._open_until,
        }), encoding="utf-8")

    def _load(self):
        if not self._persist or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))
            self._state = CircuitState(data.get("state", "closed"))
            self._failure_count = data.get("failure_count", 0)
            self._cooldown = data.get("cooldown", self.base_cooldown)
            self._open_until = data.get("open_until", 0.0)
            logger.info("Circuit breaker restored from %s (state=%s)", self._persist_path, self._state.value)
        except Exception:
            pass

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
        self._save()

    def record_success(self):
        """Record a successful API call and reset state."""
        if self.state == CircuitState.HALF_OPEN or self._failure_count > 0:
            logger.info("Circuit RECOVERED. State reset to CLOSED.")
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._cooldown = self.base_cooldown
        self._open_until = 0.0
        self._save()

    def can_execute(self) -> bool:
        """Returns True only if circuit is CLOSED.

        VATS (STACK error-path injection) exploits the HALF_OPEN probe window:
        during recovery testing, injected content in error messages reaches the
        fallback model in a more susceptible reasoning state. Blocking HALF_OPEN
        eliminates the predictable timed injection window entirely.
        """
        return self.state == CircuitState.CLOSED

    def sync_from_relay(self, relay_state_file: str | Path | None = None) -> dict:
        """Sync GMR state from relay circuit breaker's dead providers.

        Reads ~/.modelrelay.circuit.json (relay breaker persistence) and
        opens GMR circuit if the relay has open circuits. Returns sync report.
        """
        relay_path = Path(relay_state_file) if relay_state_file else \
            Path(os.path.expanduser("~")) / ".modelrelay.circuit.json"
        if not relay_path.exists():
            return {"synced": False, "reason": "relay_state_not_found", "path": str(relay_path)}
        try:
            relay_data = json.loads(relay_path.read_text(encoding="utf-8"))
            dead_providers = {}
            for provider_id, info in relay_data.items():
                if isinstance(info, dict) and info.get("state") == "open":
                    dead_providers[provider_id] = info
            if dead_providers and self.state == CircuitState.CLOSED:
                self._state = CircuitState.OPEN
                self._open_until = time.time() + self._cooldown
                self._failure_count = self.failure_threshold
                self._save()
                logger.warning(
                    "GMR circuit opened by relay sync (%d dead providers)",
                    len(dead_providers),
                )
            return {
                "synced": True,
                "dead_providers": dead_providers,
                "gmr_state": self.state.value,
            }
        except Exception as exc:
            return {"synced": False, "error": str(exc)}
