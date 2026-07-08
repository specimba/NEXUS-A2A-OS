"""Deterministic policy API for the NEXUS Sentinel UiPath Maestro Case."""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

POLICY_VERSION = "sentinel-1.0"
REQUIRED_EVIDENCE = (
    "change_ticket",
    "model_manifest_hash",
    "rollback_plan",
    "test_report_hash",
)
UNTRUSTED_INSTRUCTION_PATTERNS = (
    "ignore previous instructions",
    "reveal credentials",
    "print secrets",
    "disable safety",
    "bypass approval",
)


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    HOLD = "HOLD"
    DENY = "DENY"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReleaseEvidence(StrictModel):
    change_ticket: str | None = None
    model_manifest_hash: str | None = None
    rollback_plan: str | None = None
    test_report_hash: str | None = None


class CaseEvaluationRequest(StrictModel):
    request_id: Annotated[str, Field(min_length=3, max_length=128)]
    case_id: Annotated[str, Field(min_length=3, max_length=128)]
    stage: Annotated[str, Field(min_length=2, max_length=80)]
    requested_model: Annotated[str, Field(min_length=1, max_length=160)]
    observed_model: Annotated[str, Field(min_length=1, max_length=160)]
    privileged_remediation: bool = False
    human_approval: bool = False
    evidence: ReleaseEvidence
    evidence_notes: Annotated[str, Field(max_length=1000)] = ""


class CaseEvaluationResponse(StrictModel):
    case_id: str
    verdict: Verdict
    risk_level: RiskLevel
    reason_codes: list[str]
    evidence_complete: bool
    required_human_role: str | None
    recommended_stage: str
    selected_model: str | None
    audit_id: str
    policy_version: Literal["sentinel-1.0"] = POLICY_VERSION


class VerificationChecks(StrictModel):
    model_identity_matches: bool
    policy_tests_pass: bool
    service_health_pass: bool
    evidence_attached: bool


class CaseVerificationRequest(StrictModel):
    request_id: Annotated[str, Field(min_length=3, max_length=128)]
    case_id: Annotated[str, Field(min_length=3, max_length=128)]
    remediation_id: Annotated[str, Field(min_length=3, max_length=128)]
    checks: VerificationChecks


class CaseVerificationResponse(StrictModel):
    case_id: str
    verified: bool
    reason_codes: list[str]
    recommended_stage: str
    reentry_stage: str | None
    audit_id: str
    policy_version: Literal["sentinel-1.0"] = POLICY_VERSION


class AuditRecord(StrictModel):
    audit_id: str
    request_id: str
    case_id: str
    event_type: Literal["case_evaluation", "case_verification"]
    input_fingerprint: str
    outcome: dict[str, object]
    created_at: str
    policy_version: Literal["sentinel-1.0"] = POLICY_VERSION


class _AuditStore:
    """Thread-safe demo store with idempotency and no raw-input retention."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, AuditRecord] = {}
        self._requests: dict[str, tuple[str, str]] = {}

    def find_request(self, request_id: str, fingerprint: str) -> AuditRecord | None:
        with self._lock:
            existing = self._requests.get(request_id)
            if existing is None:
                return None
            prior_fingerprint, audit_id = existing
            if prior_fingerprint != fingerprint:
                raise HTTPException(
                    status_code=409,
                    detail="request_id already used with different content",
                )
            return self._records[audit_id]

    def add(
        self,
        *,
        request_id: str,
        case_id: str,
        event_type: Literal["case_evaluation", "case_verification"],
        fingerprint: str,
        outcome: dict[str, object],
    ) -> AuditRecord:
        audit_id = "audit-" + hashlib.sha256(
            f"{request_id}:{fingerprint}:{POLICY_VERSION}".encode("utf-8")
        ).hexdigest()[:20]
        record = AuditRecord(
            audit_id=audit_id,
            request_id=request_id,
            case_id=case_id,
            event_type=event_type,
            input_fingerprint=fingerprint,
            outcome=outcome,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._records[audit_id] = record
            self._requests[request_id] = (fingerprint, audit_id)
        return record

    def get(self, audit_id: str) -> AuditRecord:
        with self._lock:
            record = self._records.get(audit_id)
        if record is None:
            raise HTTPException(status_code=404, detail="audit record not found")
        return record

    def reset(self) -> None:
        with self._lock:
            self._records.clear()
            self._requests.clear()


audit_store = _AuditStore()

app = FastAPI(
    title="NEXUS Sentinel Policy Adapter",
    description=(
        "Deterministic governance advice for UiPath Maestro Case. "
        "UiPath remains the orchestration and execution authority."
    ),
    version="1.0.0",
)


def _fingerprint(model: BaseModel) -> str:
    canonical = json.dumps(
        model.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _evaluation_outcome(request: CaseEvaluationRequest) -> dict[str, object]:
    notes = request.evidence_notes.casefold()
    unsafe = any(pattern in notes for pattern in UNTRUSTED_INSTRUCTION_PATTERNS)
    missing_evidence = [
        name for name in REQUIRED_EVIDENCE if not getattr(request.evidence, name)
    ]
    model_mismatch = request.requested_model != request.observed_model
    approval_missing = request.privileged_remediation and not request.human_approval

    if unsafe:
        return {
            "case_id": request.case_id,
            "verdict": Verdict.DENY,
            "risk_level": RiskLevel.CRITICAL,
            "reason_codes": ["UNTRUSTED_INSTRUCTION_PATTERN"],
            "evidence_complete": not missing_evidence,
            "required_human_role": "SECURITY_INCIDENT_MANAGER",
            "recommended_stage": "Escalated",
            "selected_model": None,
        }

    reasons: list[str] = []
    if model_mismatch:
        reasons.append("MODEL_ECHO_MISMATCH")
    if missing_evidence:
        reasons.append("EVIDENCE_INCOMPLETE")
    if approval_missing:
        reasons.append("HUMAN_APPROVAL_REQUIRED")

    if reasons:
        if model_mismatch:
            stage = "Safety Hold"
            risk = RiskLevel.HIGH
        elif approval_missing:
            stage = "Human Decision"
            risk = RiskLevel.HIGH
        else:
            stage = "Evidence Missing"
            risk = RiskLevel.MEDIUM
        return {
            "case_id": request.case_id,
            "verdict": Verdict.HOLD,
            "risk_level": risk,
            "reason_codes": reasons,
            "evidence_complete": not missing_evidence,
            "required_human_role": "AI_RELEASE_MANAGER",
            "recommended_stage": stage,
            "selected_model": None,
        }

    return {
        "case_id": request.case_id,
        "verdict": Verdict.ALLOW,
        "risk_level": RiskLevel.LOW,
        "reason_codes": [],
        "evidence_complete": True,
        "required_human_role": None,
        "recommended_stage": "Remediation",
        "selected_model": request.observed_model,
    }


def _verification_outcome(request: CaseVerificationRequest) -> dict[str, object]:
    reasons: list[str] = []
    if not request.checks.model_identity_matches:
        reasons.append("MODEL_IDENTITY_STILL_MISMATCHED")
    if not request.checks.policy_tests_pass:
        reasons.append("POLICY_TESTS_FAILED")
    if not request.checks.service_health_pass:
        reasons.append("SERVICE_HEALTH_FAILED")
    if not request.checks.evidence_attached:
        reasons.append("VERIFICATION_EVIDENCE_MISSING")
    verified = not reasons
    return {
        "case_id": request.case_id,
        "verified": verified,
        "reason_codes": reasons,
        "recommended_stage": "Closure" if verified else "Rework Required",
        "reentry_stage": None if verified else "Investigation",
    }


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "nexus-sentinel-policy-adapter",
        "policy_version": POLICY_VERSION,
        "dependencies": {
            "brain_api": "not_required",
            "ollama": "not_required",
        },
    }


@app.post("/api/v1/case/evaluate", response_model=CaseEvaluationResponse)
def evaluate_case(request: CaseEvaluationRequest) -> CaseEvaluationResponse:
    fingerprint = _fingerprint(request)
    existing = audit_store.find_request(request.request_id, fingerprint)
    if existing is not None:
        return CaseEvaluationResponse(**existing.outcome, audit_id=existing.audit_id)
    outcome = _evaluation_outcome(request)
    record = audit_store.add(
        request_id=request.request_id,
        case_id=request.case_id,
        event_type="case_evaluation",
        fingerprint=fingerprint,
        outcome=outcome,
    )
    return CaseEvaluationResponse(**outcome, audit_id=record.audit_id)


@app.post("/api/v1/case/verify", response_model=CaseVerificationResponse)
def verify_case(request: CaseVerificationRequest) -> CaseVerificationResponse:
    fingerprint = _fingerprint(request)
    existing = audit_store.find_request(request.request_id, fingerprint)
    if existing is not None:
        return CaseVerificationResponse(**existing.outcome, audit_id=existing.audit_id)
    outcome = _verification_outcome(request)
    record = audit_store.add(
        request_id=request.request_id,
        case_id=request.case_id,
        event_type="case_verification",
        fingerprint=fingerprint,
        outcome=outcome,
    )
    return CaseVerificationResponse(**outcome, audit_id=record.audit_id)


@app.get("/api/v1/audit/{audit_id}", response_model=AuditRecord)
def get_audit(audit_id: str) -> AuditRecord:
    return audit_store.get(audit_id)


def reset_audit_store() -> None:
    """Reset process-local demo state; intended for tests and demo reseeding."""
    audit_store.reset()
