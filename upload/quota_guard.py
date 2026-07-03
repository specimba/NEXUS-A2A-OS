"""QuotaGuard — Quota tracking, budget enforcement, and free-tier optimization."""

import time
import threading
import logging
from dataclasses import dataclass
from typing import Dict, Optional, List
from datetime import datetime, timezone

from .config import PROVIDERS, LOGGER
from nexus_os.model_relay.provider_budget import ProviderBudgetLedger

@dataclass
class QuotaInfo:
    """Quota status for a provider."""
    provider_id: str
    quota_type: str              # "messages"|"tokens"|"credits"|"unlimited"|"free_tier"
    remaining: int              # Exact count, -1 for unlimited
    remaining_str: str           # Human-readable: "5 messages", "unlimited"
    reset_at: Optional[float]   # Unix timestamp when quota resets
    is_exhausted: bool = False
    daily_limit: Optional[int] = None
    daily_used: int = 0
    budget_verified: bool = True
    rpm_limit: Optional[int] = None

    def is_available(self) -> bool:
        if self.quota_type == "unlimited":
            return True
        return not self.is_exhausted

class QuotaGuard:
    """Track and enforce quotas across providers.
    
    Ensures we never exhaust a provider's quota without having a fallback ready.
    Tracks daily usage to prevent overuse within a billing cycle.
    """

    # Default quota limits for free tiers (approximate)
    DEFAULT_LIMITS = {
        "minimax": {"messages": 5, "type": "messages"},
        "openrouter": {"credits": 1000000, "type": "credits"},  # Credits-based
        "ollama": {"type": "unlimited"},
        "groq": {"requests_per_min": 30, "type": "requests"},
        "cerebras": {"requests_per_day": 1000, "type": "requests"},
        "together": {"type": "free_tier"},
        "deepseek": {"type": "free_tier"},
        "openmodel": {"requests_per_day": 1000, "type": "free_tier"},
        "sakana": {"requests_per_day": 200, "type": "credits"},
        "internai": {"requests_per_min": 20, "type": "tokens"},
        "longcat": {"requests_per_min": 6, "type": "tokens"},
        "nvidia": {"requests_per_min": 8, "type": "free_tier"},
    }

    GOVERNED_PROVIDERS = {"longcat", "internai", "nvidia"}

    def __init__(self, budget_ledger: ProviderBudgetLedger | None = None):
        self._lock = threading.RLock()
        self._budget_ledger = budget_ledger
        self._quotas: Dict[str, QuotaInfo] = {}
        self._daily_usage: Dict[str, List[float]] = {}  # Timestamps of requests
        self._init_quotas()

    def _init_quotas(self):
        """Initialize quotas from provider config."""
        with self._lock:
            for pid, cfg in PROVIDERS.items():
                limits = self.DEFAULT_LIMITS.get(pid, {"type": "unknown"})
                quota_type = cfg.get("quota_type", limits.get("type", "unknown"))
                
                # Set initial remaining based on known state
                if quota_type == "messages":
                    remaining = cfg.get("quota_remaining", 5)
                elif quota_type == "credits":
                    remaining = -1  # Unknown, assume available
                elif quota_type == "unlimited":
                    remaining = -1
                else:
                    remaining = -1  # Assume available until exhausted

                self._quotas[pid] = QuotaInfo(
                    provider_id=pid,
                    quota_type=quota_type,
                    remaining=remaining,
                    remaining_str=str(remaining) if remaining > 0 else "unlimited",
                    reset_at=None,
                    is_exhausted=remaining == 0,
                    daily_limit=limits.get("requests_per_day"),
                    daily_used=0,
                )
                self._daily_usage[pid] = []

    def _sync_governed(self, provider_id: str) -> None:
        if self._budget_ledger is None or provider_id not in self.GOVERNED_PROVIDERS:
            return
        status = self._budget_ledger.status(provider_id)
        quota = self._quotas.get(provider_id)
        if quota is None:
            return
        remaining = status.get("target_remaining_tokens")
        quota.remaining = -1 if remaining is None else int(remaining)
        quota.remaining_str = "unverified" if not status["balance_verified"] else str(quota.remaining)
        quota.budget_verified = bool(status["balance_verified"])
        quota.rpm_limit = int(status["current_rpm"])
        quota.daily_limit = None
        quota.is_exhausted = (
            not status["balance_verified"]
            or not status["enabled"]
            or status["cooldown_remaining_seconds"] > 0
            or remaining == 0
        )

    def _refresh_governed(self) -> None:
        for provider_id in self.GOVERNED_PROVIDERS:
            self._sync_governed(provider_id)

    def record_request(self, provider_id: str, tokens_used: int = 0):
        """Record a request to track usage."""
        with self._lock:
            if provider_id not in self._quotas:
                return
            if self._budget_ledger is not None and provider_id in self.GOVERNED_PROVIDERS:
                return

            q = self._quotas[provider_id]
            now = time.time()
            
            # Update daily usage
            self._daily_usage[provider_id].append(now)
            
            # Clean up old entries (last 24h)
            cutoff = now - 86400
            self._daily_usage[provider_id] = [
                t for t in self._daily_usage[provider_id] if t > cutoff
            ]
            q.daily_used = len(self._daily_usage[provider_id])
            
            # Decrement remaining if count-based
            if q.remaining > 0:
                q.remaining -= 1
                q.remaining_str = f"{q.remaining} {q.quota_type}"
                if q.remaining <= 0:
                    q.is_exhausted = True
                    q.remaining_str = "exhausted"
                    LOGGER.warning(f"[QuotaGuard] {provider_id} quota EXHAUSTED")

    def mark_exhausted(self, provider_id: str):
        """Mark a provider as quota-exhausted."""
        with self._lock:
            if provider_id in self._quotas:
                q = self._quotas[provider_id]
                q.is_exhausted = True
                q.remaining = 0
                q.remaining_str = "exhausted"
                LOGGER.warning(f"[QuotaGuard] {provider_id} marked EXHAUSTED")

    def get_quota(self, provider_id: str) -> Optional[QuotaInfo]:
        with self._lock:
            self._sync_governed(provider_id)
            return self._quotas.get(provider_id)

    def get_available_providers(self) -> List[str]:
        """Return providers that still have quota."""
        with self._lock:
            self._refresh_governed()
            return [
                pid for pid, q in self._quotas.items()
                if q.is_available() and not q.is_exhausted
            ]

    def get_best_free_provider(self) -> Optional[str]:
        """Get the best free-tier provider with remaining quota."""
        with self._lock:
            self._refresh_governed()
            candidates = []
            for pid, q in self._quotas.items():
                cfg = PROVIDERS.get(pid, {})
                if cfg.get("is_free", False) and q.is_available() and not q.is_exhausted:
                    # Priority: MiniMax > OpenRouter > Ollama
                    priority = cfg.get("priority", 999)
                    candidates.append((priority, pid))
            
            if not candidates:
                return None
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

    def get_routing_priority(self) -> List[str]:
        """Get providers in optimal routing order considering quota."""
        with self._lock:
            self._refresh_governed()
            # 1. Free providers with quota, ordered by priority
            # 2. Local providers (unlimited)
            # 3. Paid providers (if explicitly requested)
            priority_list = []
            
            free_providers = [
                (PROVIDERS.get(pid, {}).get("priority", 999), pid)
                for pid, q in self._quotas.items()
                if PROVIDERS.get(pid, {}).get("is_free", False) and q.is_available()
            ]
            free_providers.sort(key=lambda x: x[0])
            priority_list.extend([pid for _, pid in free_providers])
            
            # Add local providers if not already included
            for pid in ["ollama"]:
                if pid not in priority_list and pid in self._quotas:
                    priority_list.append(pid)
            
            return priority_list

    def check_daily_limit(self, provider_id: str) -> bool:
        """Check if daily limit exceeded."""
        q = self._quotas.get(provider_id)
        if not q or not q.daily_limit:
            return True
        return q.daily_used < q.daily_limit

    def get_status(self) -> Dict:
        """Get full quota status for all providers."""
        with self._lock:
            self._refresh_governed()
            result = {}
            for pid, q in self._quotas.items():
                cfg = PROVIDERS.get(pid, {})
                result[pid] = {
                    "name": cfg.get("name", pid),
                    "quota_type": q.quota_type,
                    "remaining": q.remaining,
                    "remaining_str": q.remaining_str,
                    "is_exhausted": q.is_exhausted,
                    "is_available": q.is_available(),
                    "daily_limit": q.daily_limit,
                    "daily_used": q.daily_used,
                    "reset_at": q.reset_at,
                    "budget_verified": q.budget_verified,
                    "rpm_limit": q.rpm_limit,
                }
            return result

    def reset_provider(self, provider_id: str):
        """Reset quota for a provider (e.g., new billing cycle)."""
        with self._lock:
            if provider_id in self._quotas:
                q = self._quotas[provider_id]
                cfg = PROVIDERS.get(provider_id, {})
                initial = cfg.get("quota_remaining", -1)
                q.remaining = initial if initial > 0 else -1
                q.is_exhausted = False
                q.remaining_str = str(q.remaining) if q.remaining > 0 else "unlimited"
                self._daily_usage[provider_id] = []
                q.daily_used = 0
                LOGGER.info(f"[QuotaGuard] {provider_id} quota RESET")
