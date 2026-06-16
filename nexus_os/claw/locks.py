"""Session write locks with file-based, process-aware locking.

Uses OS-level file locking (``msvcrt`` on Windows, ``fcntl`` on POSIX) so
writers in separate processes are also blocked.

Lock path convention: ``~/.openclaw/agents/<agent_id>/sessions/<session_key>.lock``
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
import time
from pathlib import Path

from nexus_os.claw.exceptions import LockError

logger = logging.getLogger(__name__)

_LOCK_DIR = Path.home() / ".openclaw" / "agents"

_PathLike = str | Path


def _acquire_os_lock(fd: int) -> bool:
    """Try to acquire a blocking OS-level lock on *fd*.

    Returns ``True`` immediately if the lock is held, ``False`` on timeout.
    """
    if sys.platform == "win32":
        import msvcrt
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    else:
        import fcntl
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False


def _release_os_lock(fd: int) -> None:
    """Release the OS-level lock on *fd*."""
    if sys.platform == "win32":
        import msvcrt
        try:
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    else:
        import fcntl
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass


def _lock_path(agent_id: str, session_key: str) -> Path:
    return _LOCK_DIR / agent_id / "sessions" / f"{session_key}.lock"


class SessionWriteLock:
    """A file-based, process-aware write lock for CLAW sessions.

    Usage::

        lock = SessionWriteLock("claw-orch-001", "sess-abc")
        if lock.acquire(timeout_ms=30_000):
            try:
                ...  # critical section
            finally:
                lock.release()
    """

    def __init__(
        self,
        agent_id: str,
        session_key: str,
        lock_dir: _PathLike | None = None,
        allow_reentrant: bool = False,
    ) -> None:
        self._held = False
        self._reentrant_count = 0
        self._fd: int | None = None
        self._path = Path(lock_dir) / f"{session_key}.lock" if lock_dir else _lock_path(agent_id, session_key)
        self._agent_id = agent_id
        self._session_key = session_key
        self._allow_reentrant = allow_reentrant

    @property
    def path(self) -> Path:
        return self._path

    @property
    def held(self) -> bool:
        return self._held

    def acquire(self, timeout_ms: int = 60000) -> bool:
        """Try to acquire the lock within *timeout_ms* milliseconds.

        Returns ``True`` if acquired, raises ``LockError`` on timeout.
        """
        if self._held:
            if self._allow_reentrant:
                self._reentrant_count += 1
                return True
            raise LockError(
                "Lock already held by this thread",
                agent_id=self._agent_id,
                session_key=self._session_key,
                lock_path=str(self._path),
            )

        self._path.parent.mkdir(parents=True, exist_ok=True)

        fd = os.open(str(self._path), os.O_CREAT | os.O_RDWR, 0o600)

        deadline = time.monotonic() + timeout_ms / 1000.0
        while time.monotonic() < deadline:
            if _acquire_os_lock(fd):
                self._fd = fd
                self._held = True
                return True
            time.sleep(0.05)

        os.close(fd)
        raise LockError(
            f"Could not acquire lock within {timeout_ms}ms",
            agent_id=self._agent_id,
            session_key=self._session_key,
            lock_path=str(self._path),
            timeout_ms=timeout_ms,
        )

    def release(self) -> None:
        """Release the lock."""
        if not self._held or self._fd is None:
            return
        if self._allow_reentrant and self._reentrant_count > 0:
            self._reentrant_count -= 1
            return
        self._reentrant_count = 0
        _release_os_lock(self._fd)
        os.close(self._fd)
        self._fd = None
        self._held = False
        try:
            self._path.unlink(missing_ok=True)
        except OSError:
            pass

    def __enter__(self) -> SessionWriteLock:
        self.acquire()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()

    def __del__(self) -> None:
        if self._held:
            try:
                self.release()
            except Exception:
                pass
