"""Token Policy Plane v2 primitives.

This module is intentionally pure: no Bridge, Governor, Engine, Vault,
provider, or process imports. It gives those layers a shared token policy
envelope, reservation ledger, redaction, recall/schema diagnostics, and route
recommendations without creating dependency cycles.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class BudgetScope(Enum):
    """Token budget scope names used by TokenGuard and doctors."""

    AGENT = "agent"
    SKILL = "skill"
    SWARM = "swarm"
    SESSION = "session"
    TASK = "task"
    LANE = "lane"
    PROVIDER = "provider"
    TOOL = "tool"
    MEMORY_RECALL = "memory_recall"
    WORKFLOW = "workflow"
    EXTERNAL_HIGH_CAPABILITY = "external_high_capability"


class TokenPolicyDecision(Enum):
    """Policy decision categories."""

    ALLOW = "allow"
    FALLBACK_RECOMMENDED = "fallback_recommended"
    DENY = "deny"


class ReservationStatus(Enum):
    """Reservation lifecycle states."""

    RESERVED = "reserved"
    COMMITTED = "committed"
    REFUNDED = "refunded"
    DENIED = "denied"
    OVERRUN = "overrun"


@dataclass(frozen=True)
class TokenEstimate:
    """Normalized token estimate before execution."""

    input_tokens: int = 0
    output_tokens: int = 0
    tool_schema_tokens: int = 0
    memory_tokens: int = 0
    retry_tokens: int = 0

    @property
    def total(self) -> int:
        return max(
            0,
            self.input_tokens
            + self.output_tokens
            + self.tool_schema_tokens
            + self.memory_tokens
            + self.retry_tokens,
        )


@dataclass(frozen=True)
class TokenUsageActual:
    """Actual token usage after provider/tool execution."""

    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float = 0.0

    @property
    def total(self) -> int:
        return max(0, self.input_tokens + self.output_tokens + self.cached_tokens)


@dataclass(frozen=True)
class TokenPolicyResult:
    """Result of evaluating a projected token spend."""

    allowed: bool
    decision: TokenPolicyDecision
    reason: str
    scope: BudgetScope
    total: int
    used: int
    projected_used: int
    remaining_after: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        payload["scope"] = self.scope.value
        return payload


@dataclass(frozen=True)
class TokenPolicy:
    """Declarative budget policy for one scope/window."""

    scope: BudgetScope
    total: int
    used: int = 0
    warning_ratio: float = 0.80
    hard_stop_ratio: float = 0.95

    def evaluate(self, estimate: TokenEstimate) -> TokenPolicyResult:
        projected = self.used + estimate.total
        remaining_after = max(0, self.total - projected)
        if self.total <= 0:
            return TokenPolicyResult(
                allowed=False,
                decision=TokenPolicyDecision.DENY,
                reason="invalid_budget",
                scope=self.scope,
                total=self.total,
                used=self.used,
                projected_used=projected,
                remaining_after=0,
            )
        if projected > self.total or projected / self.total >= self.hard_stop_ratio:
            return TokenPolicyResult(
                allowed=False,
                decision=TokenPolicyDecision.DENY,
                reason="projected_hard_stop",
                scope=self.scope,
                total=self.total,
                used=self.used,
                projected_used=projected,
                remaining_after=remaining_after,
            )
        if projected / self.total >= self.warning_ratio:
            return TokenPolicyResult(
                allowed=True,
                decision=TokenPolicyDecision.FALLBACK_RECOMMENDED,
                reason="projected_warning",
                scope=self.scope,
                total=self.total,
                used=self.used,
                projected_used=projected,
                remaining_after=remaining_after,
            )
        return TokenPolicyResult(
            allowed=True,
            decision=TokenPolicyDecision.ALLOW,
            reason="within_budget",
            scope=self.scope,
            total=self.total,
            used=self.used,
            projected_used=projected,
            remaining_after=remaining_after,
        )


SECRET_KEY_PATTERN = re.compile(
    r"(authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|secret|cookie|password|bearer)",
    re.IGNORECASE,
)
SECRET_VALUE_PATTERN = re.compile(r"(Bearer\s+|sk-|ghp_|hf_|nvapi-|forge-|csk-)", re.IGNORECASE)


def redact_token_context(value: Any) -> Any:
    """Redact secret-shaped keys and values from token audit context."""

    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if SECRET_KEY_PATTERN.search(str(key)):
                result[key] = "[REDACTED]"
            else:
                result[key] = redact_token_context(item)
        return result
    if isinstance(value, list):
        return [redact_token_context(item) for item in value]
    if isinstance(value, str) and SECRET_VALUE_PATTERN.search(value):
        return "[REDACTED]"
    return value


@dataclass(frozen=True)
class TokenPolicyEnvelope:
    """Small handoff packet shared by agents and Nexus layers."""

    trace_id: str
    agent_id: str
    operation: str
    policy_version: str = "token-policy-plane-v2"
    lineage_id: str = ""
    project_id: str = ""
    lane: str = "default"
    skill_id: str = ""
    route_class: str = ""
    provider_id: str = ""
    model_id: str = ""
    budget_key: str = "agent"
    window: str = "session"
    required_tokens: int = 0
    reserved_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    source: str = "manual_estimate"
    decision: str = "unknown"
    reason: str = ""
    remaining_before: int = 0
    remaining_after: int = 0
    fallback_route: str = ""
    evidence_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return redact_token_context(asdict(self))


@dataclass(frozen=True)
class TokenReservation:
    """Atomic reservation object for preflight -> commit/refund lifecycle."""

    reservation_id: str
    scope: BudgetScope
    actor: str
    estimate: TokenEstimate
    status: ReservationStatus
    context: dict[str, Any] = field(default_factory=dict)
    actual: TokenUsageActual = field(default_factory=TokenUsageActual)
    reason: str = ""
    created_at: float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        *,
        scope: BudgetScope,
        actor: str,
        estimate: TokenEstimate,
        context: Optional[dict[str, Any]] = None,
        status: ReservationStatus = ReservationStatus.RESERVED,
        reason: str = "",
    ) -> "TokenReservation":
        raw = f"{scope.value}:{actor}:{estimate.total}:{time.time_ns()}"
        return cls(
            reservation_id=hashlib.sha256(raw.encode()).hexdigest()[:24],
            scope=scope,
            actor=actor,
            estimate=estimate,
            status=status,
            context=redact_token_context(context or {}),
            reason=reason,
        )

    def commit(self, actual: TokenUsageActual) -> "TokenReservation":
        status = ReservationStatus.COMMITTED
        reason = "committed"
        if actual.total > self.estimate.total:
            status = ReservationStatus.OVERRUN
            reason = "actual_exceeded_estimate"
        return TokenReservation(
            reservation_id=self.reservation_id,
            scope=self.scope,
            actor=self.actor,
            estimate=self.estimate,
            status=status,
            context=self.context,
            actual=actual,
            reason=reason,
            created_at=self.created_at,
        )

    def refund(self, *, reason: str) -> "TokenReservation":
        return TokenReservation(
            reservation_id=self.reservation_id,
            scope=self.scope,
            actor=self.actor,
            estimate=self.estimate,
            status=ReservationStatus.REFUNDED,
            context=self.context,
            reason=reason,
            created_at=self.created_at,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scope"] = self.scope.value
        payload["status"] = self.status.value
        return redact_token_context(payload)


@dataclass(frozen=True)
class TokenLedgerEvent:
    """Hash-chained token lifecycle event."""

    event_hash: str
    parent_hash: str
    reservation_id: str
    actor: str
    scope: str
    status: str
    estimate_total: int
    actual_total: int
    context: dict[str, Any]
    reason: str
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return redact_token_context(asdict(self))


class TokenLedger:
    """In-memory ledger with optional JSONL persistence."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path
        self._events: list[TokenLedgerEvent] = []
        if path and path.exists():
            self._load(path)

    @property
    def events(self) -> list[TokenLedgerEvent]:
        return list(self._events)

    def record(self, reservation: TokenReservation) -> TokenLedgerEvent:
        parent = self._events[-1].event_hash if self._events else "0" * 64
        timestamp = time.time()
        payload = {
            "parent": parent,
            "reservation_id": reservation.reservation_id,
            "actor": reservation.actor,
            "scope": reservation.scope.value,
            "status": reservation.status.value,
            "estimate_total": reservation.estimate.total,
            "actual_total": reservation.actual.total,
            "context": reservation.context,
            "reason": reservation.reason,
            "timestamp": timestamp,
        }
        event_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        event = TokenLedgerEvent(
            event_hash=event_hash,
            parent_hash=parent,
            reservation_id=reservation.reservation_id,
            actor=reservation.actor,
            scope=reservation.scope.value,
            status=reservation.status.value,
            estimate_total=reservation.estimate.total,
            actual_total=reservation.actual.total,
            context=reservation.context,
            reason=reservation.reason,
            timestamp=timestamp,
        )
        self._events.append(event)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")
        return event

    def verify(self) -> bool:
        for previous, current in zip(self._events, self._events[1:]):
            if current.parent_hash != previous.event_hash:
                return False
        return True

    def _load(self, path: Path) -> None:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                self._events.append(TokenLedgerEvent(**payload))
            except (TypeError, json.JSONDecodeError):
                continue


class RecallBudget:
    """Report-only memory recall budget classifier."""

    def evaluate(
        self,
        *,
        requested_tokens: int,
        remaining_tokens: int,
        relevance: float = 1.0,
        freshness: float = 1.0,
        authority_scope: str = "task",
    ) -> dict[str, Any]:
        if requested_tokens > remaining_tokens:
            classification = "memory_recall_bloat"
            proposal = "Reduce recall token cap or use local SuperLocal-style prefiltering."
            allowed = False
        elif relevance < 0.35 or freshness < 0.25:
            classification = "memory_recall_low_value"
            proposal = "Prefer fresher or higher-relevance memory before injecting context."
            allowed = True
        else:
            classification = "memory_recall_within_budget"
            proposal = "Recall budget is acceptable."
            allowed = True
        return {
            "classification": classification,
            "allowed": allowed,
            "confidence": "confirmed",
            "requested_tokens": requested_tokens,
            "remaining_tokens": remaining_tokens,
            "authority_scope": authority_scope,
            "proposal": proposal,
        }


class ToolSchemaBudget:
    """Report-only tool schema/retry budget classifier."""

    def evaluate(
        self,
        *,
        schema_tokens: int = 0,
        tool_count: int = 0,
        retry_count: int = 0,
        malformed_count: int = 0,
        threshold_tokens: int = 8_000,
    ) -> dict[str, Any]:
        if malformed_count > 0:
            classification = "provider_schema_drift"
            proposal = "Capture raw tool-call response and normalize provider schema before retrying."
            confidence = "confirmed"
        elif retry_count >= 3:
            classification = "tool_retry_loop"
            proposal = "Stop automatic retries; route through doctor tools/token before execution."
            confidence = "likely"
        elif schema_tokens >= threshold_tokens or tool_count >= 32:
            classification = "tool_schema_bloat"
            proposal = "Scope tools to the task lane and remove unused schemas."
            confidence = "confirmed"
        else:
            classification = "tool_schema_within_budget"
            proposal = "Tool schema budget is acceptable."
            confidence = "confirmed"
        return {
            "classification": classification,
            "confidence": confidence,
            "schema_tokens": schema_tokens,
            "tool_count": tool_count,
            "retry_count": retry_count,
            "malformed_count": malformed_count,
            "proposal": proposal,
        }


def from_openai_usage(usage: dict[str, Any]) -> TokenUsageActual:
    """Normalize OpenAI-compatible usage payloads."""

    cached = 0
    prompt_details = usage.get("prompt_tokens_details")
    if isinstance(prompt_details, dict):
        cached = int(prompt_details.get("cached_tokens") or 0)
    return TokenUsageActual(
        input_tokens=int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        cached_tokens=cached,
    )


def route_constraint_from_policy(decision: TokenPolicyResult) -> dict[str, Any]:
    """Convert policy result into non-enforcing GMR/RoutePlane recommendation."""

    if decision.decision == TokenPolicyDecision.ALLOW:
        allowed = ["ECO", "FAST", "PREMIUM"]
        approval = False
    elif decision.decision == TokenPolicyDecision.FALLBACK_RECOMMENDED:
        allowed = ["ECO", "FAST"]
        approval = False
    else:
        allowed = []
        approval = decision.scope == BudgetScope.EXTERNAL_HIGH_CAPABILITY
    return {
        "mode": "recommendation",
        "allowed_route_classes": allowed,
        "requires_approval": approval,
        "reason": decision.reason,
    }


def to_vap_context(reservation: TokenReservation) -> dict[str, Any]:
    """Render a redacted context suitable for VAP/Vault persistence."""

    return {
        "reservation_id": reservation.reservation_id,
        "scope": reservation.scope.value,
        "actor": reservation.actor,
        "status": reservation.status.value,
        "estimate_total": reservation.estimate.total,
        "actual_total": reservation.actual.total,
        "reason": reservation.reason,
        "context": redact_token_context(reservation.context),
    }


def to_response_headers(envelope: TokenPolicyEnvelope) -> dict[str, str]:
    """Expose compact token policy metadata on Bridge/provider responses."""

    return {
        "X-Nexus-Token-Decision": envelope.decision,
        "X-Nexus-Token-Remaining": str(envelope.remaining_after),
        "X-Nexus-Token-Policy": envelope.policy_version,
    }
