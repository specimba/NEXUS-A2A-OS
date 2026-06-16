"""tests/gmr/test_scheduler.py — RefreshScheduler tests"""
import time
import pytest

from nexus_os.gmr.scheduler import RefreshScheduler


class FakeIngest:
    def __init__(self):
        self.fetch_count = 0
        self.cache = {}

    def fetch(self):
        self.fetch_count += 1
        return self.cache


class TestRefreshScheduler:
    def test_initial_state(self):
        ingest = FakeIngest()
        scheduler = RefreshScheduler(ingest, interval_seconds=300)
        assert scheduler._running is False
        assert scheduler._thread is None

    def test_callback_registration(self):
        ingest = FakeIngest()
        scheduler = RefreshScheduler(ingest, interval_seconds=300)
        calls = []
        scheduler.on_refresh(lambda cache: calls.append(1))
        assert len(scheduler._callbacks) == 1

    def test_constructor_callback(self):
        ingest = FakeIngest()
        calls = []
        scheduler = RefreshScheduler(ingest, interval_seconds=300, on_refresh=lambda c: calls.append(1))
        assert len(scheduler._callbacks) == 1

    def test_start_sets_running(self):
        ingest = FakeIngest()
        scheduler = RefreshScheduler(ingest, interval_seconds=60)
        scheduler.start()
        assert scheduler._running is True
        assert scheduler._thread is not None
        scheduler.stop()

    def test_stop_clears_running(self):
        ingest = FakeIngest()
        scheduler = RefreshScheduler(ingest, interval_seconds=60)
        scheduler.start()
        scheduler.stop()
        assert scheduler._running is False

    def test_double_start_is_noop(self):
        ingest = FakeIngest()
        scheduler = RefreshScheduler(ingest, interval_seconds=60)
        scheduler.start()
        thread1 = scheduler._thread
        scheduler.start()
        assert scheduler._thread is thread1
        scheduler.stop()
