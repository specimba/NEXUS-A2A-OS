"""Configuration integrity verification via SHA-256 hash pinning.

Config files (``openclaw.json``, ``auth-profiles.json``, policy YAMLs) can
be hashed at build/deploy time.  At startup the runner verifies the current
file against the pinned hash and either halts or warns on mismatch.
"""

from __future__ import annotations

import enum
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from nexus_os.claw.exceptions import ConfigIntegrityError

logger = logging.getLogger(__name__)


class IntegrityFailureMode(enum.Enum):
    HALT = "halt"
    WARN = "warn"


def hash_file(path: str | Path) -> str:
    """Return the hex SHA-256 digest of the file at *path*."""
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def hash_bytes(data: bytes) -> str:
    """Return the hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


class ConfigIntegrityChecker:
    """Verifies config files against pinned hashes.

    Typical workflow::

        pinned = {
            "openclaw.json": "abc123def456...",
            "auth-profiles.json": "7890abcd...",
        }
        checker = ConfigIntegrityChecker(pinned, base_dir=Path("~/.openclaw"))
        checker.verify_all()
    """

    def __init__(
        self,
        pinned_hashes: dict[str, str],
        base_dir: Path = Path.home() / ".openclaw",
        failure_mode: IntegrityFailureMode = IntegrityFailureMode.HALT,
    ) -> None:
        self._pinned = dict(pinned_hashes)
        self._base_dir = Path(base_dir)
        self._failure_mode = failure_mode

    def verify_all(self) -> bool:
        """Verify all pinned config files.

        Returns ``True`` if all match, ``False`` if any mismatch and mode is
        ``WARN``.  Raises ``ConfigIntegrityError`` if mode is ``HALT``.
        """
        all_ok = True
        for name, expected in self._pinned.items():
            path = self._base_dir / name
            if not path.is_file():
                msg = f"Config file not found: {path}"
                if self._failure_mode == IntegrityFailureMode.HALT:
                    raise ConfigIntegrityError(msg, path=str(path), expected=expected)
                logger.warning(msg)
                all_ok = False
                continue

            actual = hash_file(path)
            if actual != expected:
                msg = (
                    f"Config integrity mismatch for {name}: "
                    f"expected {expected[:16]}..., got {actual[:16]}..."
                )
                if self._failure_mode == IntegrityFailureMode.HALT:
                    raise ConfigIntegrityError(
                        msg, path=str(path), expected=expected, actual=actual
                    )
                logger.warning(msg)
                all_ok = False

        return all_ok

    def verify_one(self, name: str) -> bool:
        """Verify a single config entry by name.

        Returns ``True`` if match, ``False`` if mismatch in WARN mode.
        Raises ``ConfigIntegrityError`` in HALT mode.
        """
        expected = self._pinned.get(name)
        if expected is None:
            logger.warning("No pinned hash for %s, skipping", name)
            return True

        path = self._base_dir / name
        if not path.is_file():
            msg = f"Config file not found: {path}"
            if self._failure_mode == IntegrityFailureMode.HALT:
                raise ConfigIntegrityError(msg, path=str(path), expected=expected)
            logger.warning(msg)
            return False

        actual = hash_file(path)
        if actual != expected:
            msg = (
                f"Config integrity mismatch for {name}: "
                f"expected {expected[:16]}..., got {actual[:16]}..."
            )
            if self._failure_mode == IntegrityFailureMode.HALT:
                raise ConfigIntegrityError(
                    msg, path=str(path), expected=expected, actual=actual
                )
            logger.warning(msg)
            return False

        return True

    def to_snapshot(self, paths: dict[str, str | Path]) -> dict[str, str]:
        """Compute SHA-256 hashes for a set of paths and return a pin dict.

        Useful for generating the initial pin file during build/deploy.
        """
        result: dict[str, str] = {}
        for name, path in paths.items():
            p = Path(path)
            if p.is_file():
                result[name] = hash_file(p)
        return result

    def to_json(self, paths: dict[str, str | Path], indent: int = 2) -> str:
        """Return a JSON string of pinned hashes suitable for storage."""
        return json.dumps(self.to_snapshot(paths), indent=indent)
