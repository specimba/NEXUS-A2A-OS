"""Relay QuotaGuard — Per-provider quota tracking with multiple types."""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class QuotaType(Enum):
    MESSAGES = "messages"
    CREDITS = "credits"
    REQUESTS = "requests"
    UNLIMITED = "unlimited"
    TOKENS = "tokens"


@dataclass
class ProviderQuota:
    provider: str
    quota_type: QuotaType = QuotaType.MESSAGES
    limit: float = 1000.0
    remaining: float = 1000.0
    reset_period_seconds: float = 3600.0
    last_reset: float = 0.0


class QuotaGuard:
    def __init__(self):
        self._quotas: dict[str, ProviderQuota] = {}

    def register(self, provider: str, quota_type: QuotaType = QuotaType.MESSAGES, limit: float = 1000.0, reset_period: float = 3600.0):
        self._quotas[provider] = ProviderQuota(
            provider=provider, quota_type=quota_type,
            limit=limit, remaining=limit,
            reset_period_seconds=reset_period, last_reset=time.time(),
        )

    def consume(self, provider: str, amount: float = 1.0) -> bool:
        q = self._quotas.get(provider)
        if q is None:
            return True
        if q.quota_type == QuotaType.UNLIMITED:
            return True
        if time.time() - q.last_reset >= q.reset_period_seconds:
            q.remaining = q.limit
            q.last_reset = time.time()
        if q.remaining - amount < 0:
            return False
        q.remaining -= amount
        return True

    def remaining(self, provider: str) -> Optional[float]:
        q = self._quotas.get(provider)
        if q is None:
            return None
        if q.quota_type == QuotaType.UNLIMITED:
            return float("inf")
        if time.time() - q.last_reset >= q.reset_period_seconds:
            q.remaining = q.limit
            q.last_reset = time.time()
        return q.remaining

    def reset(self, provider: str):
        q = self._quotas.get(provider)
        if q:
            q.remaining = q.limit
            q.last_reset = time.time()

    def reset_all(self):
        for q in self._quotas.values():
            q.remaining = q.limit
            q.last_reset = time.time()
