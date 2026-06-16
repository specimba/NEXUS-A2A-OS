"""Relay ProviderCircuitBreaker — Per-provider 3-fail cooldown circuit breaker."""

from __future__ import annotations
import time
from enum import Enum


class ProviderState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ProviderCircuitBreaker:
    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 60.0, max_cooldown: float = 3600.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.max_cooldown = max_cooldown
        self._state: dict[str, ProviderState] = {}
        self._failures: dict[str, int] = {}
        self._open_until: dict[str, float] = {}
        self._current_cooldown: dict[str, float] = {}

    def state(self, provider: str) -> ProviderState:
        if provider in self._open_until and time.time() >= self._open_until[provider]:
            self._state[provider] = ProviderState.HALF_OPEN
        return self._state.get(provider, ProviderState.CLOSED)

    def record_failure(self, provider: str):
        self._failures[provider] = self._failures.get(provider, 0) + 1
        if self._state.get(provider) == ProviderState.HALF_OPEN:
            self._state[provider] = ProviderState.OPEN
            cd = self._current_cooldown.get(provider, self.cooldown_seconds) * 2
            cd = min(cd, self.max_cooldown)
            self._current_cooldown[provider] = cd
            self._open_until[provider] = time.time() + cd
        elif self._failures[provider] >= self.failure_threshold:
            self._state[provider] = ProviderState.OPEN
            cd = self._current_cooldown.get(provider, self.cooldown_seconds)
            self._open_until[provider] = time.time() + cd

    def record_success(self, provider: str):
        self._failures[provider] = 0
        self._state[provider] = ProviderState.CLOSED
        self._current_cooldown[provider] = self.cooldown_seconds
        self._open_until.pop(provider, None)

    def can_execute(self, provider: str) -> bool:
        return self.state(provider) in (ProviderState.CLOSED, ProviderState.HALF_OPEN)

    def reset(self, provider: str):
        self._state.pop(provider, None)
        self._failures.pop(provider, None)
        self._open_until.pop(provider, None)
        self._current_cooldown.pop(provider, None)
