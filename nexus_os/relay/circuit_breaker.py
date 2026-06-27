"""Relay ProviderCircuitBreaker — Per-provider 3-fail cooldown circuit breaker with optional persistence."""

from __future__ import annotations
import json
import os
import time
from enum import Enum
from pathlib import Path
from typing import Any


HOME = Path(os.path.expanduser("~"))
CIRCUIT_STATE_FILE = HOME / ".modelrelay.circuit.json"


class ProviderState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ProviderCircuitBreaker:
    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 60.0, max_cooldown: float = 3600.0, persist: bool = False):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.max_cooldown = max_cooldown
        self.persist = persist
        self._state: dict[str, ProviderState] = {}
        self._failures: dict[str, int] = {}
        self._open_until: dict[str, float] = {}
        self._current_cooldown: dict[str, float] = {}
        if persist:
            self._load()

    def _load(self):
        if CIRCUIT_STATE_FILE.exists():
            try:
                data = json.loads(CIRCUIT_STATE_FILE.read_text(encoding="utf-8"))
                now = time.time()
                for pid, info in data.get("dead_providers", {}).items():
                    self._failures[pid] = info.get("fail_count", 0)
                    cd_info = data.get("cooldowns", {}).get(pid)
                    if cd_info:
                        until = cd_info.get("until_epoch", cd_info.get("until", 0))
                        if isinstance(until, str):
                            from datetime import datetime
                            try:
                                until = datetime.fromisoformat(until).timestamp()
                            except Exception:
                                continue
                        remaining = until - now
                        if remaining > 0:
                            self._state[pid] = ProviderState.OPEN
                            self._open_until[pid] = until
                            self._current_cooldown[pid] = cd_info.get("cooldown_minutes", 1) * 60
            except Exception:
                pass

    def _save(self):
        if not self.persist:
            return
        now = time.time()
        dead = {}
        cooldowns = {}
        for pid, st in self._state.items():
            if st == ProviderState.OPEN:
                until = self._open_until.get(pid, 0)
                if until > now:
                    dead[pid] = {
                        "status": 0,
                        "detail": "circuit open",
                        "fail_count": self._failures.get(pid, 0),
                    }
                    cd_sec = self._current_cooldown.get(pid, self.cooldown_seconds)
                    cooldowns[pid] = {
                        "until_epoch": until,
                        "cooldown_minutes": int(cd_sec / 60),
                        "fail_count": self._failures.get(pid, 0),
                    }
        try:
            CIRCUIT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CIRCUIT_STATE_FILE.write_text(json.dumps({
                "dead_providers": dead,
                "cooldowns": cooldowns,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def state(self, provider: str) -> ProviderState:
        if provider in self._open_until and time.time() >= self._open_until[provider]:
            self._state[provider] = ProviderState.HALF_OPEN
        return self._state.get(provider, ProviderState.CLOSED)

    def record_failure(self, provider: str):
        self._failures[provider] = self._failures.get(provider, 0) + 1
        if self._state.get(provider) == ProviderState.HALF_OPEN:
            self._state[provider] = ProviderState.OPEN
            cd = self._current_cooldown.get(provider, self.cooldown_seconds) * 2
            cd = min(cd, self.max_cooldown)
            self._current_cooldown[provider] = cd
            self._open_until[provider] = time.time() + cd
        elif self._failures[provider] >= self.failure_threshold:
            self._state[provider] = ProviderState.OPEN
            cd = self._current_cooldown.get(provider, self.cooldown_seconds)
            if cd == 0:
                cd = self.cooldown_seconds
            self._open_until[provider] = time.time() + cd
        self._save()

    def record_success(self, provider: str):
        self._failures[provider] = 0
        self._state[provider] = ProviderState.CLOSED
        self._current_cooldown[provider] = self.cooldown_seconds
        self._open_until.pop(provider, None)
        self._save()

    def can_execute(self, provider: str) -> bool:
        return self.state(provider) in (ProviderState.CLOSED, ProviderState.HALF_OPEN)

    def get_dead_providers(self) -> dict[str, dict[str, Any]]:
        now = time.time()
        dead = {}
        for pid, st in self._state.items():
            if st == ProviderState.OPEN:
                until = self._open_until.get(pid, 0)
                remaining = max(0, int((until - now) / 60))
                dead[pid] = {
                    "state": st.value,
                    "fail_count": self._failures.get(pid, 0),
                    "remaining_minutes": remaining,
                    "cooldown_minutes": int(self._current_cooldown.get(pid, self.cooldown_seconds) / 60),
                }
        return dead

    def reset(self, provider: str):
        self._state.pop(provider, None)
        self._failures.pop(provider, None)
        self._open_until.pop(provider, None)
        self._current_cooldown.pop(provider, None)
        self._save()
