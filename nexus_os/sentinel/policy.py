"""Deterministic Sentinel policy findings and claim gates."""

from __future__ import annotations

import unicodedata

from nexus_os.sentinel.models import (
    ClaimGateResult,
    DeliverableContract,
    EvaluateCaseRequest,
    PolicyVerdict,
    RiskLevel,
)

REQUIRED_EVIDENCE = (
    "change_ticket",
    "model_manifest_hash",
    "rollback_plan",
    "test_report_hash",
)
UNTRUSTED_PATTERNS = (
    "ignore previous instructions",
    "reveal credentials",
    "print secrets",
    "disable safety",
    "bypass approval",
)
_CONFUSABLES = str.maketrans(
    {
        "\u0430": "a",
        "\u0435": "e",
        "\u043e": "o",
        "\u0440": "p",
        "\u0441": "c",
        "\u0445": "x",
        "\u0456": "i",
    }
)


def normalize_untrusted_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).translate(_CONFUSABLES)
    return "".join(ch for ch in normalized.casefold() if not unicodedata.category(ch).startswith("C"))


def evaluate_release(request: EvaluateCaseRequest, *, human_approved: bool) -> dict:
    notes = normalize_untrusted_text(request.evidence_notes)
    if any(pattern in notes for pattern in UNTRUSTED_PATTERNS):
        return {
            "verdict": PolicyVerdict.DENY,
            "risk_level": RiskLevel.CRITICAL,
            "reason_codes": ["UNTRUSTED_INSTRUCTION_PATTERN"],
        }

    reasons: list[str] = []
    if request.requested_model != request.observed_model:
        reasons.append("MODEL_ECHO_MISMATCH")
    missing = [name for name in REQUIRED_EVIDENCE if not getattr(request.evidence, name)]
    if missing:
        reasons.append("EVIDENCE_INCOMPLETE")
    if request.privileged_remediation and not human_approved:
        reasons.append("HUMAN_APPROVAL_REQUIRED")

    if reasons:
        return {
            "verdict": PolicyVerdict.HOLD,
            "risk_level": RiskLevel.HIGH if len(reasons) > 1 or "HUMAN_APPROVAL_REQUIRED" in reasons else RiskLevel.MEDIUM,
            "reason_codes": reasons,
        }
    return {
        "verdict": PolicyVerdict.ALLOW,
        "risk_level": RiskLevel.LOW,
        "reason_codes": [],
    }


def evaluate_deliverable_contract(contract: DeliverableContract) -> ClaimGateResult:
    maturity_rank = {"DESIGNED": 0, "IMPLEMENTED": 1, "DEPLOYED": 2, "LIVE_VERIFIED": 3}
    failed = []
    for requirement in contract.requirements:
        if requirement.level.value != "REQUIRED":
            continue
        insufficient = maturity_rank[requirement.observed_maturity.value] < maturity_rank[requirement.minimum_maturity.value]
        unverifiable = not requirement.verifier or not requirement.evidence_refs
        if insufficient or unverifiable:
            failed.append(requirement.requirement_id)
    return ClaimGateResult(
        promotable=not failed,
        failed_required=failed,
        contract_id=contract.contract_id,
    )
