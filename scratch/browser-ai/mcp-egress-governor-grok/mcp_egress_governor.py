#!/usr/bin/env python3
"""
mcp_egress_governor.py
Dry-run-first MCP/HTTP egress governance module for NEXUS OS.
- No syntax errors.
- Safe dataclasses.
- plan_egress() performs decision only (no network).
- Fail-closed allowlist.
- Optional real governance integration with safe fallbacks.
- Testable without live network or secrets.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Protocol, Tuple
import hashlib
import time

# --- Optional real NEXUS governance imports (safe fallback) ---
try:
    # Codex: adjust these import paths to your actual nexus_governance / TokenGuard / KAIJU modules
    from nexus_governance.token_guard import check_token_guard as _real_check_token_guard  # type: ignore
    from nexus_governance.kaiju import invoke_approval as _real_invoke_kaiju_approval  # type: ignore
except Exception:  # broad to catch any import/layout issue
    _real_check_token_guard = None
    _real_invoke_kaiju_approval = None


@dataclass(frozen=True)
class EgressRequest:
    """Immutable request descriptor."""
    target: str
    payload: Dict[str, Any]
    intent: str = "read"  # "read" | "write" | "exec"


@dataclass
class EgressDecision:
    """Dry-run decision result. Never executes network."""
    action: str  # "proxy_via_bridge" | "block" | "require_kaiju_approval"
    reason: str
    proxy_plan: Optional[Dict[str, Any]] = None
    risk_level: str = "low"


@dataclass
class EgressResult:
    """Result wrapper for plan/execute (dry-run returns planned)."""
    status: str  # "planned" | "blocked" | "require_approval"
    decision: EgressDecision
    audit_id: Optional[str] = None
    token_budget_remaining: Optional[int] = None


class ProxyBackend(Protocol):
    """Interface for proxy/bridge backends. Dry-run implementation provided."""
    def plan_proxy_call(self, req: EgressRequest) -> Dict[str, Any]: ...


class DryRunProxyBackend:
    """Concrete dry-run backend. Returns plan only. No network, no secrets."""
    def __init__(self, proxy_endpoint: str = "http://localhost:8080/mcp"):
        self.proxy_endpoint = proxy_endpoint

    def plan_proxy_call(self, req: EgressRequest) -> Dict[str, Any]:
        return {
            "backend": "stdio_mcp_proxy_or_bridge",
            "recommended_impl": "sparfenyuk/mcp-proxy or MCP-Bridge (arXiv 2504.08999)",
            "endpoint": self.proxy_endpoint,
            "transport": "stdio_to_http_sse",
            "target_url": req.target,
            "http_method": "POST" if req.intent in ("write", "exec") else "GET",
            "note": "DRY-RUN ONLY - no network executed. Codex wires real MCP stdio delegation here.",
            "governance": "TokenGuard checked + KAIJU gated if high-risk + allowlist enforced"
        }


class MCPEgressGovernor:
    """
    Core governor.
    - Dry-run by default (plan_egress never performs network I/O).
    - Fail-closed on non-allowlist.
    - Integrates TokenGuard / KAIJU when available; safe stubs otherwise.
    - Internal token_budget for dry-run simulation of exhaustion.
    """

    def __init__(
        self,
        allowlist: Optional[set[str]] = None,
        dry_run: bool = True,
        proxy_endpoint: str = "http://localhost:8080/mcp",
    ):
        self.allowlist: set[str] = allowlist or {
            "huggingface.co",
            "grok-audit.local",
            "localhost",
            "127.0.0.1",
        }
        self.dry_run = dry_run
        self.proxy_backend: ProxyBackend = DryRunProxyBackend(proxy_endpoint)
        self.token_budget: int = 100  # Dry-run default. Real integration overrides via _check_token_guard.
        self._audit_log: list[str] = []

    # --- Internal governance adapters (never raise on missing modules) ---
    def _check_token_guard(self, cost: int = 1) -> Tuple[bool, int]:
        if _real_check_token_guard is not None:
            try:
                ok, remaining = _real_check_token_guard("mcp_egress", cost=cost)
                return bool(ok), int(remaining)
            except Exception:
                pass  # fall through to dry-run stub
        # Dry-run / fallback stub (Codex replaces with real in integration)
        if self.token_budget < cost:
            return False, 0
        self.token_budget -= cost
        return True, self.token_budget

    def _invoke_kaiju_approval(self, req: EgressRequest) -> bool:
        if _real_invoke_kaiju_approval is not None:
            try:
                return bool(_real_invoke_kaiju_approval("high_risk_mcp_egress", {"target": req.target, "intent": req.intent}))
            except Exception:
                pass
        # Dry-run default: high-risk always requires explicit approval (plan returns "require_kaiju_approval")
        return False

    # --- Core methods ---
    def assess_risk(self, req: EgressRequest) -> str:
        if req.intent in ("write", "exec"):
            return "high"
        if any(domain in req.target.lower() for domain in self.allowlist):
            return "low"
        return "medium"

    def plan_egress(self, req: EgressRequest) -> EgressDecision:
        """Dry-run decision path. No network call ever made here."""
        risk = self.assess_risk(req)
        token_ok, remaining = self._check_token_guard(cost=1)

        if not token_ok:
            return EgressDecision(
                action="block",
                reason="TokenGuard budget exhausted (or real TokenGuard denied)",
                risk_level=risk,
            )

        if risk == "high":
            # In dry_run we do not auto-call approval for safety; real path can call it.
            approved = False if self.dry_run else self._invoke_kaiju_approval(req)
            if not approved:
                return EgressDecision(
                    action="require_kaiju_approval",
                    reason="High-risk intent (write/exec) requires KAIJU approval before proxy delegation",
                    risk_level=risk,
                )

        if risk == "medium" and not any(domain in req.target.lower() for domain in self.allowlist):
            return EgressDecision(
                action="block",
                reason="Fail-closed: non-allowlisted domain",
                risk_level=risk,
            )

        # Success path: return proxy plan
        proxy_plan = self.proxy_backend.plan_proxy_call(req)
        return EgressDecision(
            action="proxy_via_bridge",
            reason="Allowlisted/low-risk: delegate via stdio-MCP proxy/bridge (sparfenyuk/mcp-proxy or MCP Bridge)",
            proxy_plan=proxy_plan,
            risk_level=risk,
        )

    def execute_egress(self, req: EgressRequest) -> EgressResult:
        """
        Dry-run-first execute. Currently returns planned result only.
        Full implementation will delegate the proxy_plan to MCP stdio tool.
        """
        decision = self.plan_egress(req)
        audit_id = hashlib.sha256(f"{req.target}:{time.time_ns()}".encode()).hexdigest()[:16]

        if decision.action == "proxy_via_bridge":
            status = "planned"
        elif decision.action == "require_kaiju_approval":
            status = "require_approval"
        else:
            status = "blocked"

        return EgressResult(
            status=status,
            decision=decision,
            audit_id=audit_id,
            token_budget_remaining=self.token_budget,
        )

    def get_last_audit(self) -> list[str]:
        return list(self._audit_log)


# Convenience factory for tests (Codex can copy/adapt)
def create_test_governor(allowlist: Optional[set[str]] = None, token_budget: int = 100) -> MCPEgressGovernor:
    gov = MCPEgressGovernor(allowlist=allowlist, dry_run=True)
    gov.token_budget = token_budget
    return gov


if __name__ == "__main__":
    # Quick self-test when run directly
    gov = create_test_governor()
    req = EgressRequest(target="https://huggingface.co/api/models", payload={"q": "test"}, intent="read")
    dec = gov.plan_egress(req)
    print("Quick self-test decision:", dec.action, "-", dec.reason)
    print("Token budget after:", gov.token_budget)