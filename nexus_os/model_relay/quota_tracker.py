"""NEXUS Model Relay — Quota Tracker.

Tracks daily usage of rate-limited providers (OpenCode, KiloCode, GitHub, etc.)
so we can prioritize quota-heavy providers early in the day and rotate before
they run out. Persists state to ~/.nexus_pi/state/quota_tracker.json.

Usage:
    from nexus_os.model_relay.quota_tracker import QuotaTracker

    qt = QuotaTracker()
    qt.record_call("opencode", "deepseek-v4-flash-free", tokens=200)
    qt.record_call("kilocode", "minimax/minimax-m3", tokens=350)
    print(qt.get_status("opencode"))
    print(qt.get_remaining_for_today("kilocode"))
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from nexus_os.model_relay.provider_budget import ProviderBudgetLedger

QUOTA_STATE_PATH = Path("~/.nexus_pi/state/quota_tracker.json").expanduser()

# Known daily quota limits (estimated from docs/observations)
# OpenCode Zen: daily tokens per provider
# KiloCode: free models have hourly rate limits
# GitHub Models: 1500/day (observed earlier)
# GoogleAI: 1500/day free tier
KNOWN_QUOTAS = {
    "opencode": {
        "daily_token_limit": 50000,
        "daily_call_limit": 200,
        "reset_at_utc": "00:00",
        "burst_tokens_per_call": 8000,
    },
    "kilocode": {
        "hourly_call_limit": 60,
        "daily_call_limit": 500,
        "reset_at_utc": "00:00",
        "burst_tokens_per_call": 4000,
    },
    "openai-compatible:github": {
        "daily_call_limit": 1500,
        "daily_token_limit": 50000,
        "reset_at_utc": "00:00",
    },
    "googleai": {
        "daily_call_limit": 1500,
        "daily_token_limit": 1000000,
        "reset_at_utc": "00:00",
    },
    "longcat": {"note": "delegated to durable provider budget ledger"},
    "internai": {"note": "delegated to durable provider budget ledger"},
    "nvidia": {"note": "delegated to durable provider budget ledger"},
    "siliconflow": {
        "note": "DEAD — key invalid 2026-06-22",
    },
    "openai-compatible:fireworks": {
        "note": "DEAD — billing suspended 2026-06-18",
    },
}

GOVERNED_PROVIDER_ALIASES = {
    "longcat": "longcat",
    "internai": "internai",
    "nvidia": "nvidia",
    "nim": "nvidia",
}


@dataclass
class ProviderUsage:
    provider: str
    calls_today: int = 0
    tokens_today: int = 0
    last_call_ts: float = 0.0
    last_call_model: str = ""
    last_error: str = ""
    last_error_ts: float = 0.0


class QuotaTracker:
    """Track daily usage and rotation priority for rate-limited providers."""

    def __init__(
        self,
        state_path: Path = QUOTA_STATE_PATH,
        budget_ledger: ProviderBudgetLedger | None = None,
    ):
        self.state_path = state_path
        self.budget_ledger = budget_ledger or ProviderBudgetLedger()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.usage: Dict[str, ProviderUsage] = {}
        self._load()

    def _load(self) -> None:
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text())
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                for provider, entry in data.items():
                    if entry.get("date") == today:
                        self.usage[provider] = ProviderUsage(
                            provider=provider,
                            calls_today=entry.get("calls", 0),
                            tokens_today=entry.get("tokens", 0),
                            last_call_ts=entry.get("last_ts", 0.0),
                            last_call_model=entry.get("last_model", ""),
                            last_error=entry.get("last_error", ""),
                            last_error_ts=entry.get("last_error_ts", 0.0),
                        )
            except Exception:
                self.usage = {}

    def _save(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data = {}
        for provider, u in self.usage.items():
            data[provider] = {
                "date": today,
                "calls": u.calls_today,
                "tokens": u.tokens_today,
                "last_ts": u.last_call_ts,
                "last_model": u.last_call_model,
                "last_error": u.last_error,
                "last_error_ts": u.last_error_ts,
            }
        self.state_path.write_text(json.dumps(data, indent=2))

    def record_call(
        self, provider: str, model: str, tokens: int = 0, error: Optional[str] = None
    ) -> None:
        """Record legacy provider usage; governed calls are reconciled at dispatch."""
        if provider in GOVERNED_PROVIDER_ALIASES:
            return
        if provider not in self.usage:
            self.usage[provider] = ProviderUsage(provider=provider)
        u = self.usage[provider]
        u.calls_today += 1
        u.tokens_today += tokens
        u.last_call_ts = time.time()
        u.last_call_model = model
        if error:
            u.last_error = error
            u.last_error_ts = time.time()
        self._save()

    def get_status(self, provider: str) -> Dict[str, Any]:
        """Return usage stats for a provider."""
        governed = GOVERNED_PROVIDER_ALIASES.get(provider)
        if governed:
            status = self.budget_ledger.status(governed)
            available = (
                status["enabled"]
                and status["balance_verified"]
                and status["cooldown_remaining_seconds"] == 0
                and (status["target_remaining_tokens"] is None or status["target_remaining_tokens"] > 0)
            )
            return {
                **status,
                "provider": provider,
                "durable_provider": governed,
                "selection_available": available,
                "selection_only": True,
            }
        u = self.usage.get(provider)
        if u is None:
            return {"provider": provider, "calls_today": 0, "tokens_today": 0}
        limits = KNOWN_QUOTAS.get(provider, {})
        return {
            "provider": provider,
            "calls_today": u.calls_today,
            "tokens_today": u.tokens_today,
            "call_limit": limits.get("daily_call_limit"),
            "token_limit": limits.get("daily_token_limit"),
            "calls_remaining": (
                limits.get("daily_call_limit", float("inf")) - u.calls_today
                if limits.get("daily_call_limit") else None
            ),
            "tokens_remaining": (
                limits.get("daily_token_limit", float("inf")) - u.tokens_today
                if limits.get("daily_token_limit") else None
            ),
            "reset_at_utc": limits.get("reset_at_utc"),
            "last_call_model": u.last_call_model,
            "last_error": u.last_error,
        }

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        return {p: self.get_status(p) for p in KNOWN_QUOTAS}

    def get_remaining_for_today(self, provider: str) -> int:
        """Returns remaining selection capacity; dispatch owns reservations."""
        governed = GOVERNED_PROVIDER_ALIASES.get(provider)
        if governed:
            status = self.get_status(provider)
            if not status["selection_available"]:
                return 0
            remaining = status["target_remaining_tokens"]
            return int(remaining if remaining is not None else status["current_rpm"])
        limits = KNOWN_QUOTAS.get(provider, {})
        cap = limits.get("daily_call_limit")
        if cap is None:
            return -1
        u = self.usage.get(provider)
        return max(0, cap - (u.calls_today if u else 0))

    def is_quota_exhausted(self, provider: str) -> bool:
        rem = self.get_remaining_for_today(provider)
        return rem == 0

    def get_priority_order(self) -> List[str]:
        """Return providers ordered by quota freshness (most remaining first)."""
        scored = []
        for provider in KNOWN_QUOTAS:
            rem = self.get_remaining_for_today(provider)
            if rem == 0:
                scored.append((provider, -1))
            elif rem == -1:
                scored.append((provider, float("inf")))
            else:
                scored.append((provider, rem))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in scored]

    def get_time_to_utc_reset(self) -> str:
        """Return time remaining until UTC midnight (daily quota reset)."""
        now = datetime.now(timezone.utc)
        midnight = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        delta = midnight - now
        hours, remainder = divmod(delta.seconds, 3600)
        minutes = remainder // 60
        return f"{hours}h {minutes}m until UTC midnight reset"

    def should_use_opencode_first(self) -> bool:
        """Use OpenCode free models early in the day to maximize daily quota."""
        # Use OpenCode if less than 50% of daily calls consumed
        u = self.usage.get("opencode")
        if u is None:
            return True
        cap = KNOWN_QUOTAS.get("opencode", {}).get("daily_call_limit", 200)
        return u.calls_today < (cap * 0.5)

    def summary(self) -> str:
        lines = ["=== Quota Tracker Summary ==="]
        for provider, limits in KNOWN_QUOTAS.items():
            s = self.get_status(provider)
            if "note" in limits:
                lines.append(f"  [{provider}] {limits['note']}")
                continue
            used = s.get("calls_today", 0)
            cap = s.get("call_limit", "?")
            lines.append(f"  [{provider:30s}] {used}/{cap} calls | {s.get('tokens_today', 0)}/{s.get('token_limit', '?')} tokens")
        lines.append("")
        lines.append(f"  {self.get_time_to_utc_reset()}")
        lines.append(f"  Priority order: {self.get_priority_order()}")
        return "\n".join(lines)


if __name__ == "__main__":
    qt = QuotaTracker()
    print(qt.summary())
