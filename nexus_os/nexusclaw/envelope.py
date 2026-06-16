"""Typed NexusClaw task/result envelopes.

NexusClaw V0 is a governed coordinator lane, not an autonomous model loop.
These envelopes are intentionally small, serializable, and validation-heavy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any


_SAFE_TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_ALLOWED_V0_LANES = {"orchestrator"}
# V1 lanes: all NEXUSCLAW operational lanes
_ALLOWED_V1_LANES = {
    "orchestrator",
    "governance",
    "research",
    "memory",
    "audit",
    "security",
    "operations",
    "integration",
    "external",
}


class RiskLevel(str, Enum):
    """Governance risk level for a NexusClaw task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResultStatus(str, Enum):
    """NexusClaw result states."""

    PROPOSED = "proposed"
    DRY_RUN = "dry_run"
    HALTED = "halted"
    REJECTED = "rejected"
    COMPLETED = "completed"


def _enum_value(value: str | Enum) -> str:
    return value.value if isinstance(value, Enum) else str(value)


def _as_risk(value: str | RiskLevel) -> RiskLevel:
    if isinstance(value, RiskLevel):
        return value
    try:
        return RiskLevel(str(value).lower())
    except ValueError as exc:
        allowed = ", ".join(level.value for level in RiskLevel)
        raise ValueError(f"risk_level must be one of: {allowed}") from exc


def _as_status(value: str | ResultStatus) -> ResultStatus:
    if isinstance(value, ResultStatus):
        return value
    try:
        return ResultStatus(str(value).lower())
    except ValueError as exc:
        allowed = ", ".join(status.value for status in ResultStatus)
        raise ValueError(f"status must be one of: {allowed}") from exc


def _validate_string_list(name: str, values: list[str]) -> None:
    if not isinstance(values, list):
        raise ValueError(f"{name} must be a list")
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{name} entries must be non-empty strings")


def _validate_mapping(name: str, value: dict[str, Any]) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")


def _read_string_list(payload: dict[str, Any], name: str) -> list[str]:
    value = payload.get(name, [])
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return value


def _read_mapping(payload: dict[str, Any], name: str) -> dict[str, Any]:
    value = payload.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


@dataclass(frozen=True)
class NexusClawTaskEnvelope:
    """Governed task request accepted by the NexusClaw coordinator."""

    task_id: str
    source: str
    lane: str
    intent: str
    risk_level: RiskLevel | str
    required_capabilities: list[str] = field(default_factory=list)
    resource_budget: dict[str, Any] = field(default_factory=dict)
    egress_policy: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "risk_level", _as_risk(self.risk_level))
        self.validate()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NexusClawTaskEnvelope":
        required = ["task_id", "source", "lane", "intent", "risk_level"]
        missing = [name for name in required if name not in payload]
        if missing:
            raise ValueError(f"missing required task envelope fields: {', '.join(missing)}")
        return cls(
            task_id=str(payload["task_id"]),
            source=str(payload["source"]),
            lane=str(payload["lane"]),
            intent=str(payload["intent"]),
            risk_level=payload["risk_level"],
            required_capabilities=_read_string_list(payload, "required_capabilities"),
            resource_budget=_read_mapping(payload, "resource_budget"),
            egress_policy=_read_mapping(payload, "egress_policy"),
            evidence_refs=_read_string_list(payload, "evidence_refs"),
        )

    def validate(self) -> None:
        if not _SAFE_TASK_ID.match(self.task_id):
            raise ValueError("task_id must be 1-128 safe identifier characters")
        if not self.source.strip():
            raise ValueError("source must be non-empty")
        if self.lane not in _ALLOWED_V1_LANES:
            raise ValueError(f"lane must be one of: {', '.join(sorted(_ALLOWED_V1_LANES))}")
        if not self.intent.strip():
            raise ValueError("intent must be non-empty")

        _validate_string_list("required_capabilities", self.required_capabilities)
        _validate_mapping("resource_budget", self.resource_budget)
        _validate_mapping("egress_policy", self.egress_policy)
        _validate_string_list("evidence_refs", self.evidence_refs)

        if self.egress_policy.get("cloud_fallback") is True:
            raise ValueError("cloud_fallback is disabled by default for NexusClaw V0")
        if self.egress_policy.get("remote_stdio") is True:
            raise ValueError("remote stdio transport is forbidden for NexusClaw V0")
        if self.egress_policy.get("all_filesystem_access") is True:
            raise ValueError("all-filesystem agent access is forbidden for NexusClaw V0")

        _ALLOWED_EGRESS_KEYS = {"cloud_fallback", "remote_stdio", "all_filesystem_access", "network_access", "data_egress"}
        unknown_keys = set(self.egress_policy.keys()) - _ALLOWED_EGRESS_KEYS
        if unknown_keys:
            raise ValueError(
                f"Unknown egress_policy keys: {', '.join(sorted(unknown_keys))}. "
                f"Allowed: {', '.join(sorted(_ALLOWED_EGRESS_KEYS))}"
            )

        max_tokens = self.resource_budget.get("max_tokens")
        if max_tokens is not None and (not isinstance(max_tokens, int) or max_tokens <= 0):
            raise ValueError("resource_budget.max_tokens must be a positive integer when set")
        max_runtime_s = self.resource_budget.get("max_runtime_s")
        if max_runtime_s is not None and (not isinstance(max_runtime_s, int) or max_runtime_s <= 0):
            raise ValueError("resource_budget.max_runtime_s must be a positive integer when set")

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "source": self.source,
            "lane": self.lane,
            "intent": self.intent,
            "risk_level": self.risk_level.value,
            "required_capabilities": list(self.required_capabilities),
            "resource_budget": dict(self.resource_budget),
            "egress_policy": dict(self.egress_policy),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class NexusClawResultEnvelope:
    """Governed task result returned by the NexusClaw coordinator."""

    task_id: str
    status: ResultStatus | str
    executor: str
    evidence: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    vap_record_id: str | None = None
    halt_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", _as_status(self.status))
        self.validate()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NexusClawResultEnvelope":
        required = ["task_id", "status", "executor"]
        missing = [name for name in required if name not in payload]
        if missing:
            raise ValueError(f"missing required result envelope fields: {', '.join(missing)}")
        return cls(
            task_id=str(payload["task_id"]),
            status=payload["status"],
            executor=str(payload["executor"]),
            evidence=_read_string_list(payload, "evidence"),
            metrics=_read_mapping(payload, "metrics"),
            vap_record_id=payload.get("vap_record_id"),
            halt_reason=payload.get("halt_reason"),
        )

    def validate(self) -> None:
        if not _SAFE_TASK_ID.match(self.task_id):
            raise ValueError("task_id must be 1-128 safe identifier characters")
        if not self.executor.strip():
            raise ValueError("executor must be non-empty")
        _validate_string_list("evidence", self.evidence)
        _validate_mapping("metrics", self.metrics)
        if self.status is ResultStatus.HALTED and not self.halt_reason:
            raise ValueError("halted results require halt_reason")
        if self.status is ResultStatus.COMPLETED:
            if not self.evidence:
                raise ValueError("completed results require evidence")
            if not self.vap_record_id:
                raise ValueError("completed results require vap_record_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": _enum_value(self.status),
            "executor": self.executor,
            "evidence": list(self.evidence),
            "metrics": dict(self.metrics),
            "vap_record_id": self.vap_record_id,
            "halt_reason": self.halt_reason,
        }
