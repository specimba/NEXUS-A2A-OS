"""tests/claw/test_locks.py — Session write lock tests."""

from __future__ import annotations

import sys
import os
import threading
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from nexus_os.claw.exceptions import LockError
from nexus_os.claw.locks import SessionWriteLock


@pytest.fixture
def tmp_lock_dir(tmp_path: Path) -> str:
    return str(tmp_path)


def test_lock_acquire_release(tmp_lock_dir: str) -> None:
    lock = SessionWriteLock("agent-1", "sess-abc", lock_dir=tmp_lock_dir)
    assert not lock.held
    lock.acquire(timeout_ms=1000)
    assert lock.held
    lock.release()
    assert not lock.held


def test_lock_blocks_concurrent_writers(tmp_lock_dir: str) -> None:
    lock1 = SessionWriteLock("agent-1", "sess-abc", lock_dir=tmp_lock_dir)
    lock2 = SessionWriteLock("agent-1", "sess-abc", lock_dir=tmp_lock_dir)

    lock1.acquire(timeout_ms=1000)
    assert lock1.held

    acquired = threading.Event()

    def try_lock() -> None:
        try:
            lock2.acquire(timeout_ms=3000)
            acquired.set()
        except LockError:
            pass

    t = threading.Thread(target=try_lock, daemon=True)
    t.start()
    time.sleep(0.2)

    # second writer should be blocked
    assert not acquired.is_set()

    lock1.release()
    t.join(timeout=2)
    assert acquired.is_set()
    lock2.release()


def test_lock_timeout_raises(tmp_lock_dir: str) -> None:
    lock1 = SessionWriteLock("agent-1", "sess-abc", lock_dir=tmp_lock_dir)
    lock2 = SessionWriteLock("agent-1", "sess-abc", lock_dir=tmp_lock_dir)

    lock1.acquire(timeout_ms=1000)
    with pytest.raises(LockError):
        lock2.acquire(timeout_ms=100)


def test_lock_non_reentrant_blocked(tmp_lock_dir: str) -> None:
    lock = SessionWriteLock("agent-1", "sess-abc", lock_dir=tmp_lock_dir, allow_reentrant=False)
    lock.acquire(timeout_ms=1000)
    with pytest.raises(LockError):
        lock.acquire(timeout_ms=1000)


def test_lock_reentrant_allowed(tmp_lock_dir: str) -> None:
    lock = SessionWriteLock("agent-1", "sess-abc", lock_dir=tmp_lock_dir, allow_reentrant=True)
    lock.acquire(timeout_ms=1000)
    assert lock.held
    lock.acquire(timeout_ms=1000)  # reentrant — should not raise
    assert lock.held
    lock.release()
    assert lock.held  # still held once
    lock.release()
    assert not lock.held


def test_lock_path_created(tmp_lock_dir: str) -> None:
    lock = SessionWriteLock("agent-1", "sess-abc", lock_dir=tmp_lock_dir)
    assert not lock.path.exists()
    lock.acquire(timeout_ms=1000)
    assert lock.path.exists()
    lock.release()
    # release cleans up the lock file
    assert not lock.path.exists()


def test_lock_context_manager(tmp_lock_dir: str) -> None:
    lock = SessionWriteLock("agent-1", "sess-abc", lock_dir=tmp_lock_dir)
    with lock:
        assert lock.held
    assert not lock.held


def test_lock_concurrent_sessions(tmp_lock_dir: str) -> None:
    lock_a = SessionWriteLock("agent-1", "sess-a", lock_dir=tmp_lock_dir)
    lock_b = SessionWriteLock("agent-1", "sess-b", lock_dir=tmp_lock_dir)

    lock_a.acquire(timeout_ms=1000)
    lock_b.acquire(timeout_ms=1000)  # different key — should succeed
    assert lock_a.held
    assert lock_b.held
    lock_a.release()
    lock_b.release()


if __name__ == "__main__":
    pytest.main([__file__])
