"""
NEXUS Provider Health Monitor
Per-provider circuit breaker with health tracking.
Wraps the existing ProviderCircuitBreaker with monitoring, status reporting,
and async health-check loops.
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Optional
from enum import Enum

from nexus_os.relay.circuit_breaker import ProviderCircuitBreaker, ProviderState

logger = logging.getLogger("nexus.provider_health")


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    OFFLINE = "offline"


class ProviderHealthMonitor:
    """Monitors provider health using circuit breaker pattern.
    
    Status flow: HEALTHY → DEGRADED → FAILING → OFFLINE
    
    Each provider has:
    - Circuit breaker (3-fail cooldown)
    - Average latency tracking
    - Failure count and success rate
    - Recommendation generator
    """

    CHECK_INTERVAL = 60
    LATENCY_WINDOW = 10

    def __init__(self):
        self._breaker = ProviderCircuitBreaker()
        self._provider_data: Dict[str, Dict] = {}
        self._running = False
        self._check_task = None

    async def start(self):
        """Start the periodic health monitor"""
        if self._running:
            return
        self._running = True
        self._check_task = asyncio.create_task(self._monitor_loop())
        logger.info("Provider Health Monitor started")

    async def stop(self):
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self):
        """Periodic health refresh loop"""
        while self._running:
            try:
                await self._refresh_all()
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
            await asyncio.sleep(self.CHECK_INTERVAL)

    async def _refresh_all(self):
        """Refresh status for all tracked providers"""
        for provider_id in list(self._provider_data.keys()):
            data = self._provider_data[provider_id]
            state = self._breaker.state(provider_id)
            data["circuit_state"] = state.value
            data["health_status"] = self._compute_health(data)

    def _compute_health(self, data: Dict) -> str:
        """Compute overall health status from provider data"""
        state = data.get("circuit_state", "closed")
        failures = data.get("recent_failures", 0)
        latency = data.get("avg_latency_ms", 0)

        if state == "open":
            if failures >= 10:
                return HealthStatus.OFFLINE.value
            return HealthStatus.FAILING.value
        if state == "half_open":
            return HealthStatus.DEGRADED.value
        if failures >= 2:
            return HealthStatus.DEGRADED.value
        if latency > 5000:
            return HealthStatus.DEGRADED.value
        return HealthStatus.HEALTHY.value

    def record_request(self, provider: str, success: bool, latency_ms: float = 0.0):
        """Record a provider request result"""
        if provider not in self._provider_data:
            self._provider_data[provider] = {
                "total_requests": 0,
                "total_successes": 0,
                "total_failures": 0,
                "recent_failures": 0,
                "latencies": [],
                "avg_latency_ms": 0.0,
                "last_request": None,
                "circuit_state": "closed",
                "health_status": "healthy",
                "recommendation": "normal"
            }

        data = self._provider_data[provider]
        data["total_requests"] += 1
        data["last_request"] = datetime.now().isoformat()

        if success:
            self._breaker.record_success(provider)
            data["total_successes"] += 1
            data["recent_failures"] = max(0, data["recent_failures"] - 1)
        else:
            self._breaker.record_failure(provider)
            data["total_failures"] += 1
            data["recent_failures"] += 1

        if latency_ms > 0:
            data["latencies"].append(latency_ms)
            if len(data["latencies"]) > self.LATENCY_WINDOW:
                data["latencies"] = data["latencies"][-self.LATENCY_WINDOW:]
            data["avg_latency_ms"] = sum(data["latencies"]) / len(data["latencies"])

        data["circuit_state"] = self._breaker.state(provider).value
        data["health_status"] = self._compute_health(data)
        data["recommendation"] = self._get_recommendation(data)

    def _get_recommendation(self, data: Dict) -> str:
        """Generate operational recommendation"""
        status = data.get("health_status", "healthy")
        failures = data.get("recent_failures", 0)
        latency = data.get("avg_latency_ms", 0)

        if status == HealthStatus.OFFLINE.value:
            return "disable - provider non-responsive"
        if status == HealthStatus.FAILING.value:
            return "reduce_load - circuit open"
        if status == HealthStatus.DEGRADED.value:
            if latency > 5000:
                return "high_latency - consider fallback"
            if failures >= 2:
                return "degraded - monitor closely"
            return "degraded"
        return "normal"

    def can_route(self, provider: str) -> bool:
        """Check if provider can accept traffic"""
        return self._breaker.can_execute(provider)

    def get_status(self) -> Dict:
        """Get full health status for all providers"""
        return {
            "providers": dict(self._provider_data),
            "summary": {
                "total_tracked": len(self._provider_data),
                "healthy": sum(
                    1 for d in self._provider_data.values()
                    if d.get("health_status") == HealthStatus.HEALTHY.value
                ),
                "degraded": sum(
                    1 for d in self._provider_data.values()
                    if d.get("health_status") == HealthStatus.DEGRADED.value
                ),
                "failing": sum(
                    1 for d in self._provider_data.values()
                    if d.get("health_status") == HealthStatus.FAILING.value
                ),
                "offline": sum(
                    1 for d in self._provider_data.values()
                    if d.get("health_status") == HealthStatus.OFFLINE.value
                ),
            }
        }

    def get_provider_status(self, provider: str) -> Optional[Dict]:
        """Get status for a single provider"""
        return self._provider_data.get(provider)


_health_monitor: Optional[ProviderHealthMonitor] = None


def get_health_monitor() -> ProviderHealthMonitor:
    """Get the global health monitor singleton"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = ProviderHealthMonitor()
    return _health_monitor
