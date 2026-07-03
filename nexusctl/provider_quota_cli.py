"""Provider quota operator commands for the canonical nexusctl entry point."""

from __future__ import annotations

from typing import Any

from nexus_os.model_relay.provider_budget import ProviderBudgetLedger


def run_quota(args: Any) -> tuple[int, dict]:
    ledger = ProviderBudgetLedger()
    command = args.quota_command

    if command == "status":
        return 0, ledger.all_status()

    provider = args.provider
    if command == "verify":
        if args.remaining_tokens is None or not (args.reset_at or args.expires_at):
            payload = ledger.status(provider)
            payload["error"] = "remaining tokens and reset_at or expires_at are required"
            payload["required_fields"] = ["remaining_tokens", "reset_at|expires_at", "source"]
            return 2, payload
        try:
            return 0, ledger.verify_balance(
                provider,
                args.remaining_tokens,
                source=args.source,
                reset_at=args.reset_at,
                expires_at=args.expires_at,
            )
        except (KeyError, ValueError) as exc:
            return 2, {"provider": provider, "error": str(exc)}

    if command == "plan":
        try:
            payload = ledger.status(provider)
        except KeyError as exc:
            return 2, {"provider": provider, "error": str(exc)}
        payload["utilization_target_pct"] = 90
        payload["protected_reserve_pct"] = 10
        return (0 if payload["balance_verified"] and payload["daily_budget_tokens"] is not None else 2), payload

    return 2, {"error": f"unknown quota command: {command}"}
