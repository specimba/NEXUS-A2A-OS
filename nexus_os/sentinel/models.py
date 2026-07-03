"""Strict contracts for native Sentinel cases."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

POLICY_VERSION = "sentinel-native-1.0"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CaseStage(str, Enum):
    INTAKE = "INTAKE"
    INVESTIGATION = "INVESTIGATION"
    HUMAN_DECISION = "HUMAN_DECISION"
    REMEDIATION_PROPOSED = "REMEDIATION_PROPOSED"
    AUTHORIZED_EXECUTION = "AUTHORIZED_EXECUTION"
    VERIFICATION = "VERIFICATION"
    REWORK_REQUIRED = "REWORK_REQUIRED"
    CLOSURE = "CLOSURE"
    ESCALATED = "ESCALATED"


class PolicyVerdict(str, Enum):
    ALLOW = "ALLOW"
    HOLD = "HOLD"
    DENY = "DENY"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RequirementLevel(str, Enum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    INFORMATIONAL = "INFORMATIONAL"


class ClaimMaturity(str, Enum):
    DESIGNED = "DESIGNED"
    IMPLEMENTED = "IMPLEMENTED"
    DEPLOYED = "DEPLOYED"
    LIVE_VERIFIED = "LIVE_VERIFIED"


class EvidenceRef(StrictModel):
    evidence_id: Annotated[str, Field(min_length=3, max_length=128)]
    sha256: Annotated[str, Field(pattern=r"^[a-fA-F0-9]{64}$")]
    source: Annotated[str, Field(min_length=1, max_length=256)]
    grade: Annotated[str, Field(pattern=r"^E[0-3]$")] = "E1"


class ReleaseEvidence(StrictModel):
    change_ticket: str | None = None
    model_manifest_hash: str | None = None
    rollback_plan: str | None = None
    test_report_hash: str | None = None
    refs: list[EvidenceRef] = Field(default_factory=list)


class CreateCaseRequest(StrictModel):
    case_id: Annotated[str, Field(min_length=3, max_length=128)]
    case_type: Annotated[str, Field(min_length=2, max_length=80)] = "ai_release_recovery"
    title: Annotated[str, Field(min_length=3, max_length=200)]
    actor_id: Annotated[str, Field(min_length=2, max_length=128)]
    idempotency_key: Annotated[str, Field(min_length=8, max_length=128)]


class EvaluateCaseRequest(StrictModel):
    expected_version: Annotated[int, Field(ge=1)]
    idempotency_key: Annotated[str, Field(min_length=8, max_length=128)]
    actor_id: Annotated[str, Field(min_length=2, max_length=128)]
    requested_model: Annotated[str, Field(min_length=1, max_length=160)]
    observed_model: Annotated[str, Field(min_length=1, max_length=160)]
    privileged_remediation: bool = False
    evidence: ReleaseEvidence
    evidence_notes: Annotated[str, Field(max_length=2000)] = ""


class ApprovalRequest(StrictModel):
    expected_version: Annotated[int, Field(ge=1)]
    idempotency_key: Annotated[str, Field(min_length=8, max_length=128)]
    approver_id: Annotated[str, Field(min_length=2, max_length=128)]
    approver_role: Annotated[str, Field(min_length=2, max_length=80)]
    approved: bool
    notes: Annotated[str, Field(max_length=1000)] = ""


class ExecuteRequest(StrictModel):
    expected_version: Annotated[int, Field(ge=1)]
    idempotency_key: Annotated[str, Field(min_length=8, max_length=128)]
    actor_id: Annotated[str, Field(min_length=2, max_length=128)]
    description: Annotated[str, Field(min_length=3, max_length=2000)]
    impact: Literal["low", "medium", "high", "critical"] = "high"
    context: dict[str, Any] = Field(default_factory=dict)


class VerificationChecks(StrictModel):
    model_identity_matches: bool
    policy_tests_pass: bool
    service_health_pass: bool
    evidence_attached: bool


class VerifyRequest(StrictModel):
    expected_version: Annotated[int, Field(ge=1)]
    idempotency_key: Annotated[str, Field(min_length=8, max_length=128)]
    actor_id: Annotated[str, Field(min_length=2, max_length=128)]
    remediation_id: Annotated[str, Field(min_length=3, max_length=128)]
    evaluation_event_id: Annotated[str, Field(min_length=8, max_length=128)]
    checks: VerificationChecks


class DeliverableRequirement(StrictModel):
    requirement_id: Annotated[str, Field(min_length=3, max_length=128)]
    description: Annotated[str, Field(min_length=3, max_length=500)]
    level: RequirementLevel
    minimum_maturity: ClaimMaturity = ClaimMaturity.LIVE_VERIFIED
    verifier: Annotated[str, Field(min_length=3, max_length=256)] | None = None
    observed_maturity: ClaimMaturity = ClaimMaturity.DESIGNED
    evidence_refs: list[str] = Field(default_factory=list)


class DeliverableContract(StrictModel):
    contract_id: Annotated[str, Field(min_length=3, max_length=128)]
    name: Annotated[str, Field(min_length=3, max_length=200)]
    requirements: list[DeliverableRequirement]


class CaseRecord(StrictModel):
    case_id: str
    case_type: str
    title: str
    stage: CaseStage
    version: int
    risk_level: RiskLevel
    policy_verdict: PolicyVerdict | None = None
    reason_codes: list[str] = Field(default_factory=list)
    retry_count: int = 0
    trace_id: str
    vap_id: str | None = None
    created_at: str
    updated_at: str


class EventRecord(StrictModel):
    event_id: str
    case_id: str
    case_version: int
    event_type: str
    actor_id: str
    previous_stage: CaseStage | None
    new_stage: CaseStage
    trace_id: str
    vap_id: str | None = None
    policy_version: str = POLICY_VERSION
    evidence_hashes: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    previous_event_hash: str | None = None
    event_hash: str | None = None


class ClaimGateResult(StrictModel):
    promotable: bool
    failed_required: list[str]
    contract_id: str

