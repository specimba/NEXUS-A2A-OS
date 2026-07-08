"""The FI-D1 discovery heartbeat must run independently of the health loop.

Regression guard for the 07-07 wiring defect: the hourly ProviderRefresher
call was embedded in _start_health_loop, which returns early when
RELAY_HEALTH_INTERVAL<=0 (the default) — so the refresh never fired.
"""
from __future__ import annotations

import threading
import time

import pytest

from nexus_os.relay.model_relay import ModelRelay


def _bare_relay() -> ModelRelay:
    relay = ModelRelay.__new__(ModelRelay)  # skip network-touching __init__
    relay._refresh_thread = None
    relay._refresh_stop = threading.Event()
    return relay


def test_scheduler_starts_with_default_env(monkeypatch):
    monkeypatch.delenv("NEXUS_PROVIDER_REFRESH_INTERVAL", raising=False)
    relay = _bare_relay()
    relay._start_provider_refresh_loop()
    try:
        assert relay._refresh_thread is not None
        assert relay._refresh_thread.daemon
        assert relay._refresh_thread.is_alive()
    finally:
        relay._refresh_stop.set()
        relay._refresh_thread.join(timeout=2)


def test_zero_interval_disables(monkeypatch):
    monkeypatch.setenv("NEXUS_PROVIDER_REFRESH_INTERVAL", "0")
    relay = _bare_relay()
    relay._start_provider_refresh_loop()
    assert relay._refresh_thread is None


def test_loop_calls_refresh_all_after_boot_delay(monkeypatch):
    import nexus_os.relay.provider_refresher as pr

    calls: list[str] = []

    class _StubRefresher:
        def refresh_all(self, *, chat_probe):
            calls.append("refreshed" if chat_probe is False else "BAD")

    monkeypatch.setattr(pr, "ProviderRefresher", _StubRefresher)
    monkeypatch.setenv("NEXUS_PROVIDER_REFRESH_INTERVAL", "1")
    relay = _bare_relay()
    relay._start_provider_refresh_loop()
    try:
        deadline = time.time() + 5
        while not calls and time.time() < deadline:
            time.sleep(0.05)
        assert calls and calls[0] == "refreshed"  # chat_probe=False enforced
    finally:
        relay._refresh_stop.set()
        relay._refresh_thread.join(timeout=2)
