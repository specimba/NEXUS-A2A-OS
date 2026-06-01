"""tests/gmr/test_latency_monitor.py — LiveLatencyMonitor tests"""
import time
import pytest

from nexus_os.gmr.latency_monitor import LiveLatencyMonitor


class TestLiveLatencyMonitor:
    def test_initial_stats_none(self):
        mon = LiveLatencyMonitor()
        assert mon.get_stats("unknown-model") is None

    def test_record_and_get_stats(self):
        mon = LiveLatencyMonitor()
        mon.record("m1", 100.0)
        mon.record("m1", 200.0)
        mon.record("m1", 150.0)
        stats = mon.get_stats("m1")
        assert stats is not None
        assert stats["samples"] == 3
        assert stats["model"] == "m1"
        assert stats["min"] == 100.0
        assert stats["max"] == 200.0

    def test_percentile_values(self):
        mon = LiveLatencyMonitor()
        for i in range(100):
            mon.record("m1", float(i))
        stats = mon.get_stats("m1")
        assert stats["p50"] == 50.0
        assert stats["p95"] == 95.0
        assert stats["p99"] == 99.0

    def test_window_size_enforced(self):
        mon = LiveLatencyMonitor(window_size=10)
        for i in range(20):
            mon.record("m1", float(i))
        stats = mon.get_stats("m1")
        assert stats["samples"] == 10
        assert stats["min"] == 10.0

    def test_ttl_expiry(self):
        mon = LiveLatencyMonitor(ttl_seconds=1)
        mon.record("m1", 100.0)
        # Manually expire all entries
        mon._data["m1"] = [(time.time() - 10, 100.0)]
        stats = mon.get_stats("m1")
        assert stats is None

    def test_all_stats_multiple_models(self):
        mon = LiveLatencyMonitor()
        mon.record("m1", 100.0)
        mon.record("m2", 200.0)
        all_s = mon.all_stats()
        assert "m1" in all_s
        assert "m2" in all_s

    def test_clear_single_model(self):
        mon = LiveLatencyMonitor()
        mon.record("m1", 100.0)
        mon.record("m2", 200.0)
        mon.clear("m1")
        assert mon.get_stats("m1") is None
        assert mon.get_stats("m2") is not None

    def test_clear_all(self):
        mon = LiveLatencyMonitor()
        mon.record("m1", 100.0)
        mon.record("m2", 200.0)
        mon.clear()
        assert mon.get_stats("m1") is None
        assert mon.get_stats("m2") is None

    def test_mean_calculation(self):
        mon = LiveLatencyMonitor()
        mon.record("m1", 100.0)
        mon.record("m1", 300.0)
        stats = mon.get_stats("m1")
        assert stats["mean"] == 200.0
