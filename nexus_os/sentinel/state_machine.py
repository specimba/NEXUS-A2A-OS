"""Sentinel stage transition enforcement."""

from __future__ import annotations

from nexus_os.sentinel.models import CaseStage


class InvalidTransition(ValueError):
    pass


TRANSITIONS = {
    CaseStage.INTAKE: {CaseStage.INVESTIGATION},
    CaseStage.INVESTIGATION: {
        CaseStage.HUMAN_DECISION,
        CaseStage.REMEDIATION_PROPOSED,
        CaseStage.ESCALATED,
    },
    CaseStage.HUMAN_DECISION: {CaseStage.INVESTIGATION, CaseStage.ESCALATED},
    CaseStage.REMEDIATION_PROPOSED: {
        CaseStage.AUTHORIZED_EXECUTION,
        CaseStage.HUMAN_DECISION,
        CaseStage.ESCALATED,
    },
    CaseStage.AUTHORIZED_EXECUTION: {CaseStage.VERIFICATION, CaseStage.ESCALATED},
    CaseStage.VERIFICATION: {
        CaseStage.CLOSURE,
        CaseStage.REWORK_REQUIRED,
        CaseStage.ESCALATED,
    },
    CaseStage.REWORK_REQUIRED: {CaseStage.INVESTIGATION, CaseStage.ESCALATED},
    CaseStage.CLOSURE: set(),
    CaseStage.ESCALATED: set(),
}


def require_transition(current: CaseStage, target: CaseStage) -> None:
    if target not in TRANSITIONS[current]:
        raise InvalidTransition(f"invalid Sentinel transition: {current.value} -> {target.value}")
