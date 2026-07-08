"""Relay QuotaGuard — Per-provider quota tracking with sliding-window RPM and proactive backoff."""


from __future__ import annotations
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class QuotaType(Enum):
    MESSAGES = "messages"
    CREDITS = "credits"
    REQUESTS = "requests"
    UNLIMITED = "unlimited"
    TOKENS = "tokens"
    RPM = "rpm"


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


class SlidingWindowRPMTracker:
    """Tracks requests-per-minute using a sliding window for providers like
    NVIDIA NIM (operator-conservative 8 RPM serial lane).

    Key behavior:
    - Proactive backoff at 80% utilization (e.g. 6/8 for NIM)
    - Returns (can_proceed, backoff_seconds, utilization_pct)
    - Backoff_seconds = 0 means go ahead immediately
    """

    def __init__(self, rpm_limit: int = 8, window_seconds: float = 60.0, backoff_threshold: float = 0.80):
        self.rpm_limit = rpm_limit
        self.window_seconds = window_seconds
        self.backoff_threshold = backoff_threshold
        self._timestamps: deque[float] = deque()
        self._header_reported_remaining: Optional[int] = None
        self._header_reset_epoch: Optional[float] = None

    def _prune(self):
        cutoff = time.time() - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def record_request(self):
        self._timestamps.append(time.time())
        self._prune()

    def update_from_headers(self, remaining: Optional[int] = None, reset_epoch: Optional[float] = None):
        """Ingest X-RateLimit-Remaining / X-RateLimit-Reset from response headers."""
        if remaining is not None:
            self._header_reported_remaining = remaining
        if reset_epoch is not None:
            self._header_reset_epoch = reset_epoch

    def can_proceed(self) -> tuple[bool, float, float]:
        """Returns (allowed, backoff_seconds, utilization_pct).

        backoff_seconds = 0 means no delay needed.
        utilization_pct = fraction of RPM window used.
        """
        self._prune()
        current_count = len(self._timestamps)
        utilization = current_count / self.rpm_limit

        if current_count >= self.rpm_limit:
            oldest = self._timestamps[0]
            wait = (oldest + self.window_seconds) - time.time()
            return (False, max(0.0, wait), utilization)

        if utilization >= self.backoff_threshold:
            headroom_requests = self.rpm_limit - current_count
            remaining_window = self.window_seconds - (time.time() - (self._timestamps[0] if self._timestamps else time.time() - self.window_seconds))
            if headroom_requests > 0 and remaining_window > 0:
                spacing = remaining_window / (headroom_requests + 1) * (utilization / self.backoff_threshold)
                return (True, spacing, utilization)

        return (True, 0.0, utilization)

    def state(self) -> dict:
        self._prune()
        return {
            "current_count": len(self._timestamps),
            "rpm_limit": self.rpm_limit,
            "utilization_pct": round(len(self._timestamps) / self.rpm_limit * 100, 1),
            "header_remaining": self._header_reported_remaining,
            "backoff_active": len(self._timestamps) / self.rpm_limit >= self.backoff_threshold,
        }


from nexus_os.relay.quota_limits_generated import (
    KNOWN_CONTEXT_LIMITS as _GENERATED_LIMITS,
)

# Hand-authored entries predating the canonical registry
# (config/models.registry.json). On collision the SMALLER window wins —
# a conservative clamp can never overshoot the provider's real limit.
_LEGACY_LIMITS: dict[str, int] = {
    "z-ai/glm-5.1": 202752,
    "zai-org/GLM-5.1": 202752,
    "minimaxai/minimax-m3": 524288,
    "MiniMaxAI/MiniMax-M3": 524288,
    "moonshotai/kimi-k2-thinking": 262144,
    "moonshotai/Kimi-K2-Thinking": 262144,
    "nvidia/devstral-2-123b": 131072,
    "zai-org/GLM-5": 32768,
    "nvidia/nemotron-3-ultra-550b-a55b": 1048576,
}

KNOWN_CONTEXT_LIMITS: dict[str, int] = {
    key: min(
        v
        for v in (_LEGACY_LIMITS.get(key), _GENERATED_LIMITS.get(key))
        if v is not None
    )
    for key in {*_LEGACY_LIMITS, *_GENERATED_LIMITS}
}


CONTEXT_SAFETY_MARGIN = 100


def max_completion_budget(model_id: str, input_tokens: int) -> Optional[int]:
    """Largest completion budget that fits the model's context window.

    Returns None when the model has no known limit (caller should not clamp).
    Returns 0 when the input alone already exceeds the window (caller must
    fail over — retrying the same model is guaranteed to be rejected).
    """
    max_ctx = KNOWN_CONTEXT_LIMITS.get(model_id)
    if max_ctx is None:
        return None
    return max(0, max_ctx - input_tokens - CONTEXT_SAFETY_MARGIN)


def check_context_fit(model_id: str, input_tokens: int, completion_budget: int) -> tuple[bool, str]:
    """Check if input + completion fits within model's context limit.

    Returns (fits, advice).
    advice is empty string if fits, otherwise suggests reduction or failover.
    """
    max_ctx = KNOWN_CONTEXT_LIMITS.get(model_id)
    if max_ctx is None:
        return (True, "")

    total = input_tokens + completion_budget
    if total <= max_ctx:
        return (True, "")

    slack = max_ctx - input_tokens
    if slack <= 0:
        return (False, f"input alone ({input_tokens}) exceeds {model_id} context limit ({max_ctx}). Fail over to higher-context model.")

    new_budget = max(1, slack - CONTEXT_SAFETY_MARGIN)
    return (False, f"total {total} > {max_ctx}. Reduce completion budget to <={new_budget} or fail over to higher-context model (e.g. MiniMax M3 512K).")
