"""ProviderManager — Health monitoring, latency tracking, and circuit breaker."""

import time
import threading
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable
from collections import deque

from .config import PROVIDERS, HEALTH_CHECK_INTERVAL, LATENCY_SAMPLE_SIZE, CIRCUIT_BREAKER_THRESHOLD, CIRCUIT_BREAKER_COOLDOWN, LOGGER

class ProviderState(Enum):
    UP = "up"
    DEGRADED = "degraded"
    DOWN = "down"
    COOLDOWN = "cooldown"  # Circuit breaker open

ProviderStatus = ProviderState


@dataclass
class ProviderHealth:
    """Real-time health status for a provider."""
    provider_id: str
    state: ProviderState = ProviderState.UP
    latency_ms: int = 9999
    latency_history: List[int] = field(default_factory=list)  # Rolling window
    failure_count: int = 0
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    last_check: Optional[float] = None
    cooldown_until: Optional[float] = None
    consecutive_failures: int = 0

    def avg_latency(self) -> float:
        if not self.latency_history:
            return 9999
        return sum(self.latency_history) / len(self.latency_history)

    def is_available(self) -> bool:
        if self.state == ProviderState.COOLDOWN:
            if self.cooldown_until and time.time() < self.cooldown_until:
                return False
            # Cooldown expired, try to reset
            self.state = ProviderState.UP
            self.consecutive_failures = 0
        return self.state in (ProviderState.UP, ProviderState.DEGRADED)

class ProviderManager:
    """Manages provider health, latency, and circuit breakers."""

    def __init__(self, health_check_fn: Optional[Callable] = None):
        self._health: Dict[str, ProviderHealth] = {}
        self._check_fn = health_check_fn or self._default_health_check
        self._lock = threading.RLock()
        self._checkers: Dict[str, threading.Timer] = {}
        self._running = False

        # Initialize from config
        for pid, cfg in PROVIDERS.items():
            self._health[pid] = ProviderHealth(
                provider_id=pid,
                state=ProviderState.UP if cfg.get("status") == "up" else ProviderState.DOWN,
                latency_ms=cfg.get("latency_ms", 9999),
            )

    def _default_health_check(self, provider_id: str, config: dict) -> bool:
        """Default health check using requests HEAD/fetch."""
        try:
            import requests
            url = config["base_url"]
            timeout = 5
            resp = requests.head(url, timeout=timeout)
            return resp.status_code < 500
        except Exception:
            return False

    def record_success(self, provider_id: str, latency_ms: int):
        """Record successful request."""
        with self._lock:
            if provider_id not in self._health:
                self._health[provider_id] = ProviderHealth(provider_id=provider_id)
            
            h = self._health[provider_id]
            h.state = ProviderState.UP
            h.consecutive_failures = 0
            h.last_success = time.time()
            h.latency_ms = latency_ms
            h.latency_history.append(latency_ms)
            if len(h.latency_history) > LATENCY_SAMPLE_SIZE:
                h.latency_history.pop(0)

    def record_failure(self, provider_id: str, error: Optional[str] = None):
        """Record failed request."""
        with self._lock:
            if provider_id not in self._health:
                self._health[provider_id] = ProviderHealth(provider_id=provider_id)
            
            h = self._health[provider_id]
            h.consecutive_failures += 1
            h.failure_count += 1
            h.last_failure = time.time()

            LOGGER.warning(f"[ProviderManager] {provider_id} failure #{h.consecutive_failures}: {error}")

            # Circuit breaker
            if h.consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
                h.state = ProviderState.COOLDOWN
                h.cooldown_until = time.time() + CIRCUIT_BREAKER_COOLDOWN
                LOGGER.warning(f"[ProviderManager] Circuit breaker OPEN for {provider_id}, cooling down for {CIRCUIT_BREAKER_COOLDOWN}s")

    def get_health(self, provider_id: str) -> Optional[ProviderHealth]:
        return self._health.get(provider_id)

    def get_state(self, provider_id: str) -> ProviderState:
        h = self._health.get(provider_id)
        if not h:
            return ProviderState.DOWN
        if h.state == ProviderState.COOLDOWN and h.cooldown_until and time.time() < h.cooldown_until:
            return ProviderState.COOLDOWN
        return h.state

    def get_available_providers(self) -> List[str]:
        """Return list of available provider IDs."""
        with self._lock:
            return [pid for pid, h in self._health.items() if h.is_available()]

    def get_sorted_providers(self, strategy: str = "latency") -> List[str]:
        """Return providers sorted by strategy (latency|quality|priority)."""
        with self._lock:
            available = [(pid, h) for pid, h in self._health.items() if h.is_available()]
            if strategy == "latency":
                available.sort(key=lambda x: x[1].avg_latency())
            elif strategy == "quality":
                available.sort(key=lambda x: PROVIDERS.get(x[0], {}).get("tier", 0), reverse=True)
            elif strategy == "priority":
                available.sort(key=lambda x: PROVIDERS.get(x[0], {}).get("priority", 999))
            return [pid for pid, _ in available]

    def check_provider(self, provider_id: str) -> bool:
        """Perform health check on a single provider."""
        config = PROVIDERS.get(provider_id)
        if not config:
            return False
        try:
            result = self._check_fn(provider_id, config)
            with self._lock:
                h = self._health.get(provider_id)
                if h:
                    h.last_check = time.time()
                    if result:
                        h.state = ProviderState.UP
                    else:
                        h.state = ProviderState.DOWN
            return result
        except Exception as e:
            LOGGER.error(f"[ProviderManager] Health check failed for {provider_id}: {e}")
            with self._lock:
                h = self._health.get(provider_id)
                if h:
                    h.state = ProviderState.DOWN
            return False

    def start_monitoring(self, interval: int = HEALTH_CHECK_INTERVAL):
        """Start background health monitoring."""
        self._running = True
        self._schedule_checks(interval)

    def _schedule_checks(self, interval: int):
        if not self._running:
            return
        # Check all providers
        for pid in PROVIDERS:
            self.check_provider(pid)
        # Schedule next round
        with self._lock:
            self._checkers["monitor"] = threading.Timer(interval, self._schedule_checks, [interval])
            self._checkers["monitor"].daemon = True
            self._checkers["monitor"].start()

    def stop_monitoring(self):
        """Stop background monitoring."""
        self._running = False
        with self._lock:
            for t in self._checkers.values():
                t.cancel()
            self._checkers.clear()

    def get_status_summary(self) -> Dict:
        """Get summary of all provider statuses."""
        with self._lock:
            result = {}
            for pid, cfg in PROVIDERS.items():
                h = self._health.get(pid)
                result[pid] = {
                    "name": cfg["name"],
                    "state": h.state.value if h else "unknown",
                    "latency_ms": h.avg_latency() if h else 9999,
                    "tier": cfg.get("tier", 0),
                    "priority": cfg.get("priority", 999),
                    "is_free": cfg.get("is_free", False),
                    "is_local": cfg.get("is_local", False),
                    "quota_type": cfg.get("quota_type", "unknown"),
                    "failure_count": h.failure_count if h else 0,
                    "last_check": h.last_check if h else None,
                }
            return result