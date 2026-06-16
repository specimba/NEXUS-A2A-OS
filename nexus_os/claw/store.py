"""Persistent preference and configuration storage for NEXUSCLAW.

Backends:
  - ``MemoryStore`` — ephemeral, process-scoped (default)
  - ``FileTreeStore`` — file-based, survives restarts
  - ``RedisStore`` — cross-process, shared state
"""

from __future__ import annotations

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


class StoreBackend(ABC):
    @abstractmethod
    def load(self, collection: str, key: str) -> Any | None:
        ...

    @abstractmethod
    def save(self, collection: str, key: str, value: Any) -> None:
        ...

    @abstractmethod
    def delete(self, collection: str, key: str) -> None:
        ...

    @abstractmethod
    def list_keys(self, collection: str) -> list[str]:
        ...


class MemoryStore(StoreBackend):
    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def load(self, collection: str, key: str) -> Any | None:
        with self._lock:
            return self._data.get(collection, {}).get(key)

    def save(self, collection: str, key: str, value: Any) -> None:
        with self._lock:
            self._data.setdefault(collection, {})[key] = value

    def delete(self, collection: str, key: str) -> None:
        with self._lock:
            self._data.get(collection, {}).pop(key, None)

    def list_keys(self, collection: str) -> list[str]:
        with self._lock:
            return list(self._data.get(collection, {}).keys())


class FileTreeStore(StoreBackend):
    def __init__(self, base_dir: str | Path = Path.home() / ".openclaw" / "store") -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, collection: str, key: str) -> Path:
        return self._base / collection / f"{key}.json"

    def load(self, collection: str, key: str) -> Any | None:
        p = self._path(collection, key)
        if not p.is_file():
            return None
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            logger.warning("Corrupt store file: %s", p)
            return None

    def save(self, collection: str, key: str, value: Any) -> None:
        p = self._path(collection, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value, indent=2))

    def delete(self, collection: str, key: str) -> None:
        p = self._path(collection, key)
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass

    def list_keys(self, collection: str) -> list[str]:
        d = self._base / collection
        if not d.is_dir():
            return []
        return [f.stem for f in d.iterdir() if f.suffix == ".json"]


class PreferenceStore:
    """High-level preference API over a pluggable backend.

    Collections used:
      - ``preferences`` — general user/agent preferences
      - ``tiers`` — model tier overrides
      - ``trust`` — trust threshold configurations (ERNIE HARDWALL/CAUTION/RESTRICTED)
    """

    def __init__(self, backend: StoreBackend | None = None) -> None:
        self._backend = backend or MemoryStore()

    # ── preferences ────────────────────────────────────────────────────

    def load_preferences(self, agent_id: str = "default") -> dict[str, Any]:
        val = self._backend.load("preferences", agent_id)
        return val if isinstance(val, dict) else {}

    def save_preferences(self, agent_id: str, prefs: dict[str, Any]) -> None:
        self._backend.save("preferences", agent_id, prefs)

    def delete_preferences(self, agent_id: str) -> None:
        self._backend.delete("preferences", agent_id)

    # ── model tiers ────────────────────────────────────────────────────

    def load_model_tiers(self) -> dict[str, str]:
        val = self._backend.load("tiers", "model_map")
        return val if isinstance(val, dict) else {}

    def save_model_tiers(self, tiers: dict[str, str]) -> None:
        self._backend.save("tiers", "model_map", tiers)

    # ── trust thresholds (ERNIE integration) ───────────────────────────

    def load_trust_config(self, agent_id: str = "default") -> dict[str, Any]:
        val = self._backend.load("trust", agent_id)
        return val if isinstance(val, dict) else {}

    def save_trust_config(self, agent_id: str, config: dict[str, Any]) -> None:
        self._backend.save("trust", agent_id, config)

    def delete_trust_config(self, agent_id: str) -> None:
        self._backend.delete("trust", agent_id)

    # ── backend passthrough ────────────────────────────────────────────

    @property
    def backend(self) -> StoreBackend:
        return self._backend
