"""Tests for NEXUS Provider Health Monitor."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.monitoring.provider_health import (
    ProviderHealthMonitor,
    HealthStatus,
    get_health_monitor,
)


class TestHealthStatusEnum:
    def test_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.FAILING.value == "failing"
        assert HealthStatus.OFFLINE.value == "offline"


class TestProviderHealthMonitorInit:
    def test_init(self):
        monitor = ProviderHealthMonitor()
        assert monitor._running is False
        assert monitor._provider_data == {}
        assert monitor.CHECK_INTERVAL == 0

    def test_get_status_empty(self):
        monitor = ProviderHealthMonitor()
        status = monitor.get_status()
        assert "providers" in status
        assert "summary" in status
        assert status["summary"]["total_tracked"] == 0

    def test_get_provider_status_missing(self):
        monitor = ProviderHealthMonitor()
        assert monitor.get_provider_status("nonexistent") is None


class TestProviderHealthMonitorRecord:
    def test_record_success(self):
        monitor = ProviderHealthMonitor()
        monitor.record_request("test_provider", success=True, latency_ms=100)
        data = monitor.get_provider_status("test_provider")
        assert data is not None
        assert data["total_requests"] == 1
        assert data["total_successes"] == 1
        assert data["health_status"] == HealthStatus.HEALTHY.value

    def test_record_failure(self):
        monitor = ProviderHealthMonitor()
        monitor.record_request("test_provider", success=False, latency_ms=500)
        data = monitor.get_provider_status("test_provider")
        assert data["total_failures"] == 1
        assert data["recent_failures"] == 1

    def test_record_multiple_successes(self):
        monitor = ProviderHealthMonitor()
        for i in range(5):
            monitor.record_request("p1", success=True, latency_ms=50)
        data = monitor.get_provider_status("p1")
        assert data["total_requests"] == 5
        assert data["total_successes"] == 5

    def test_record_latency_tracking(self):
        monitor = ProviderHealthMonitor()
        monitor.record_request("p1", success=True, latency_ms=100)
        monitor.record_request("p1", success=True, latency_ms=200)
        data = monitor.get_provider_status("p1")
        assert data["avg_latency_ms"] == 150.0

    def test_record_latency_window(self):
        monitor = ProviderHealthMonitor()
        monitor.LATENCY_WINDOW = 3
        for lat in [100, 200, 300, 400, 500]:
            monitor.record_request("p1", success=True, latency_ms=lat)
        data = monitor.get_provider_status("p1")
        assert len(data["latencies"]) == 3
        assert data["avg_latency_ms"] == 400.0

    def test_success_reduces_recent_failures(self):
        monitor = ProviderHealthMonitor()
        monitor.record_request("p1", success=False)
        monitor.record_request("p1", success=False)
        assert monitor.get_provider_status("p1")["recent_failures"] == 2
        monitor.record_request("p1", success=True)
        assert monitor.get_provider_status("p1")["recent_failures"] == 1


class TestProviderHealthMonitorComputeHealth:
    def test_healthy_closed_no_failures(self):
        monitor = ProviderHealthMonitor()
        monitor.record_request("p1", success=True, latency_ms=100)
        data = monitor.get_provider_status("p1")
        assert data["health_status"] == "healthy"

    def test_degraded_multiple_failures(self):
        monitor = ProviderHealthMonitor()
        for _ in range(3):
            monitor.record_request("p1", success=False)
        data = monitor.get_provider_status("p1")
        assert data["health_status"] in ("degraded", "failing")

    def test_failing_circuit_open(self):
        monitor = ProviderHealthMonitor()
        for _ in range(4):
            monitor.record_request("p1", success=False)
        data = monitor.get_provider_status("p1")
        assert data["health_status"] in ("failing", "offline")

    def test_high_latency_degraded(self):
        monitor = ProviderHealthMonitor()
        monitor.record_request("p1", success=True, latency_ms=6000)
        data = monitor.get_provider_status("p1")
        assert data["health_status"] == "degraded"


class TestProviderHealthMonitorCanRoute:
    def test_can_route_healthy(self):
        monitor = ProviderHealthMonitor()
        monitor.record_request("p1", success=True)
        assert monitor.can_route("p1") is True

    def test_can_route_unknown_provider(self):
        monitor = ProviderHealthMonitor()
        assert monitor.can_route("unknown") is True


class TestProviderHealthMonitorSummary:
    def test_summary_counts(self):
        monitor = ProviderHealthMonitor()
        monitor.record_request("healthy1", success=True, latency_ms=50)
        monitor.record_request("healthy2", success=True, latency_ms=50)
        monitor.record_request("fail1", success=False)
        monitor.record_request("fail1", success=False)
        monitor.record_request("fail1", success=False)
        status = monitor.get_status()
        assert status["summary"]["total_tracked"] == 3
        assert status["summary"]["healthy"] >= 1


class TestProviderHealthMonitorAsync:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        monitor = ProviderHealthMonitor()
        monitor.CHECK_INTERVAL = 1
        await monitor.start()
        assert monitor._running is True
        await monitor.stop()
        assert monitor._running is False

    @pytest.mark.asyncio
    async def test_double_start(self):
        monitor = ProviderHealthMonitor()
        monitor.CHECK_INTERVAL = 1
        await monitor.start()
        await monitor.start()
        await monitor.stop()

    @pytest.mark.asyncio
    async def test_start_noops_when_interval_disabled(self):
        monitor = ProviderHealthMonitor()
        monitor.CHECK_INTERVAL = 0
        await monitor.start()
        assert monitor._running is False


    @pytest.mark.asyncio
    async def test_refresh_relay_updates_existing_provider(self, monkeypatch):
        payloads = [
            {"status": "ok", "models_healthy": 1, "discovered_models": 2, "uptime_s": 10},
            {"status": "ok", "models_healthy": 3, "discovered_models": 4, "uptime_s": 20},
        ]

        class FakeResponse:
            status_code = 200

            def __init__(self, payload):
                self._payload = payload

            def json(self):
                return self._payload

        class FakeClient:
            def __init__(self, timeout):
                self.timeout = timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, url):
                return FakeResponse(payloads.pop(0))

        monkeypatch.setattr("httpx.AsyncClient", FakeClient)

        monitor = ProviderHealthMonitor()
        await monitor.refresh_relay()
        assert monitor.get_provider_status("modelrelay_nexus")["models_healthy"] == 1

        await monitor.refresh_relay()
        status = monitor.get_provider_status("modelrelay_nexus")
        assert status["models_healthy"] == 3
        assert status["models_total"] == 4
        assert status["uptime_s"] == 20

class TestProviderHealthMonitorSingleton:
    def test_get_health_monitor(self):
        a = get_health_monitor()
        b = get_health_monitor()
        assert a is b

