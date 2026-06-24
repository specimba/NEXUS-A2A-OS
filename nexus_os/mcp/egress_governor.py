"""Governed MCP egress planning for browser-agent internet reach.

This is the local NEXUS version of the Grok-proposed ``mcp-egress-governor``:
it does not grant broad network access. It wraps the existing browser HTTP
diagnostic relay with explicit policy, dry-run defaults, approval hooks, and
small memory records so Grok/GPT browser agents can request public read-only
egress without bypassing NEXUS controls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from nexus_os.bridge.browser_http_diagnostic import BrowserHTTPDiagnosticRelay


MemorySink = Callable[[Mapping[str, Any]], None]
Gate = Callable[[Mapping[str, Any]], bool]


@dataclass(frozen=True)
class EgressRequest:
    url: str
    method: str = "HEAD"
    audit_id: str = "mcp-egress-governor"
    operator: str = "nexus"
    dry_run: bool = True
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EgressDecision:
    allowed: bool
    reason: str
    plan: str = "browser_http_diagnostic"
    bridge_tool: str = "http_diagnostic"
    risk_level: str = "low"
    gross_arguments: dict[str, Any] | None = None


@dataclass(frozen=True)
class EgressResult:
    decision: EgressDecision
    executed: bool
    result: dict[str, Any]


class McpEgressGovernor:
    """Policy wrapper for safe browser-agent egress via the 7354 bridge."""

    def __init__(
        self,
        *,
        relay: BrowserHTTPDiagnosticRelay | None = None,
        token_budget_checker: Gate | None = None,
        approval_checker: Gate | None = None,
        memory_sink: MemorySink | None = None,
    ) -> None:
        self.relay = relay or BrowserHTTPDiagnosticRelay()
        self.token_budget_checker = token_budget_checker
        self.approval_checker = approval_checker
        self.memory_sink = memory_sink

    def plan(self, request: EgressRequest) -> EgressDecision:
        prepared = self.relay.prepare(
            request.url,
            method=request.method,
            headers=request.headers,
            audit_id=request.audit_id,
            operator=request.operator,
            mode="dry_run" if request.dry_run else "live",
        )
        if not prepared.allowed:
            return EgressDecision(False, prepared.reason, risk_level="blocked")
        return EgressDecision(
            True,
            "planned_public_read_only_egress",
            risk_level="low",
            gross_arguments=prepared.gross_arguments,
        )

    def execute(self, request: EgressRequest) -> EgressResult:
        decision = self.plan(request)
        self._remember("before", request, decision, None)
        if not decision.allowed:
            result = {"blocked": True, "reason": decision.reason}
            self._remember("after", request, decision, result)
            return EgressResult(decision, False, result)

        gate_payload = {
            "url": request.url,
            "method": request.method.upper(),
            "audit_id": request.audit_id,
            "operator": request.operator,
            "bridge_tool": decision.bridge_tool,
            "risk_level": decision.risk_level,
            "dry_run": request.dry_run,
        }
        if self.token_budget_checker is not None and not self.token_budget_checker(gate_payload):
            blocked = {"blocked": True, "reason": "token_budget_denied"}
            self._remember("after", request, decision, blocked)
            return EgressResult(decision, False, blocked)
        if not request.dry_run and self.approval_checker is not None and not self.approval_checker(gate_payload):
            blocked = {"blocked": True, "reason": "approval_denied"}
            self._remember("after", request, decision, blocked)
            return EgressResult(decision, False, blocked)

        if request.dry_run:
            result = {
                "blocked": False,
                "dry_run": True,
                "access_result": "planned",
                "side_effects_enabled": False,
                "gross_arguments": decision.gross_arguments,
            }
            self._remember("after", request, decision, result)
            return EgressResult(decision, False, result)

        result = self.relay.invoke(
            request.url,
            method=request.method,
            headers=request.headers,
            audit_id=request.audit_id,
            operator=request.operator,
            mode="live",
        )
        result.setdefault("side_effects_enabled", False)
        self._remember("after", request, decision, result)
        return EgressResult(decision, True, result)

    def _remember(
        self,
        phase: str,
        request: EgressRequest,
        decision: EgressDecision,
        result: Mapping[str, Any] | None,
    ) -> None:
        if self.memory_sink is None:
            return
        self.memory_sink(
            {
                "phase": phase,
                "url": request.url,
                "method": request.method.upper(),
                "audit_id": request.audit_id,
                "operator": request.operator,
                "allowed": decision.allowed,
                "reason": decision.reason,
                "bridge_tool": decision.bridge_tool,
                "dry_run": request.dry_run,
                "result": dict(result) if result is not None else None,
            }
        )

