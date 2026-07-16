"""Governance adapters for the NEXUS SAGE Custom GPT boundary.

SAGE is an external request-response reasoning lane.  It may submit bounded
proposals, but it cannot turn caller-supplied programs or swarm requests into
live execution.  These helpers deliberately return serializable proposal
evidence and never persist or execute the supplied program text.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from nexus_os.bridge.a2a_governance import build_governed_a2a_proposal
from nexus_os.nexusclaw.envelope import ApprovalState, NexusClawResultEnvelope, NexusClawTaskEnvelope, ResultStatus


MAX_SAGE_PROGRAM_CHARS = 50_000
SAGE_WORKFLOW_SKILLS = {
    "grounding_audit": "audit_log",
    "evidence_search": "phase2_probe",
    "model_health_snapshot": "browser_http_diagnostic",
    "parallel_audit_proposal": "swarm_dispatch",
}

MAX_SAGE_PROGRAM_TIMEOUT_S = 45
_SAFE_SAGE_JOB_ID = re.compile(r"^sage-job-[0-9a-f]{32}$")
_SAFE_SAGE_PRINCIPAL = re.compile(r"^nexus-sage:[0-9a-f]{12}$")


@dataclass(frozen=True)
class SageNexusClawHandoff:
    """A verified, receipt-bound SAGE proposal for NexusClaw intake.

    This Bridge contract carries only the envelope needed for a NexusClaw
    dry-run. It intentionally omits raw SAGE parameters and the authenticated
    principal; the latter is checked at handoff construction and never echoed.
    The embedded envelope remains pending and is therefore refused by the
    governed live path.
    """

    job_id: str
    workflow_type: str
    proposal_sha256: str
    parameters_sha256: str
    envelope: NexusClawTaskEnvelope

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "nexus.sage-nexusclaw-handoff.v1",
            "job_id": self.job_id,
            "receipt": {
                "state": "pending_review",
                "workflow_type": self.workflow_type,
                "proposal_sha256": self.proposal_sha256,
                "parameters_sha256": self.parameters_sha256,
                "principal_verified": True,
            },
            "envelope": self.envelope.to_dict(),
            "proposal_only": True,
            "execution_allowed": False,
            "operator_next_step": (
                "Review the pending SAGE receipt and use the NexusClaw "
                "governed approval path before any separate execution."
            ),
        }


def _canonical_json_bytes(value: Any, *, label: str) -> bytes:
    try:
        # SQLite stores JSON, which converts otherwise valid non-string mapping
        # keys (for example, numeric port identifiers) into strings. Normalize
        # through that same JSON data model before sorting so the receipt digest
        # remains stable across create, persistence, and idempotent replay.
        json_value = json.loads(
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        )
        return json.dumps(
            json_value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"SAGE handoff {label} must be JSON-serializable") from exc


def build_sage_job_handoff(
    *,
    job_id: str,
    principal: str,
    workflow_type: str,
    state: str,
    parameters: dict[str, Any],
    proposal: dict[str, Any],
) -> SageNexusClawHandoff:
    """Verify a persisted SAGE proposal before NexusClaw can consume it.

    The gateway is responsible for authenticating and storing the SAGE job.
    This Bridge adapter binds the stored workflow and parameters to the
    proposal's typed NexusClaw envelope, then preserves the proposal-only
    state. It never calls an executor, creates approval, or upgrades a
    receipt beyond ``pending_review``.
    """

    if not isinstance(job_id, str) or _SAFE_SAGE_JOB_ID.fullmatch(job_id) is None:
        raise ValueError("SAGE handoff requires a canonical job id")
    if (
        not isinstance(principal, str)
        or _SAFE_SAGE_PRINCIPAL.fullmatch(principal) is None
    ):
        raise ValueError("SAGE handoff requires an authenticated nexus-sage principal")
    if not isinstance(workflow_type, str):
        raise ValueError("SAGE handoff requires an allowlisted workflow")
    normalized_workflow = workflow_type.strip().lower()
    expected_skill = SAGE_WORKFLOW_SKILLS.get(normalized_workflow)
    if expected_skill is None:
        raise ValueError("SAGE handoff requires an allowlisted workflow")
    if state != "pending_review":
        raise ValueError("SAGE handoff requires a pending_review receipt")
    if not isinstance(parameters, dict):
        raise ValueError("SAGE handoff parameters must be an object")
    if not isinstance(proposal, dict):
        raise ValueError("SAGE handoff proposal must be an object")

    parameter_bytes = _canonical_json_bytes(parameters, label="parameters")
    parameters_sha256 = hashlib.sha256(parameter_bytes).hexdigest()
    if proposal.get("schema") != "nexus.sage-job-proposal.v1":
        raise ValueError("SAGE handoff requires a canonical proposal schema")
    if proposal.get("workflow_type") != normalized_workflow:
        raise ValueError("SAGE handoff workflow does not match the receipt")
    if proposal.get("parameters_sha256") != parameters_sha256:
        raise ValueError("SAGE handoff parameters hash does not match the receipt")
    if proposal.get("parameters_bytes") != len(parameter_bytes):
        raise ValueError("SAGE handoff parameters size does not match the receipt")
    if (
        proposal.get("proposal_only") is not True
        or proposal.get("execution_allowed") is not False
    ):
        raise ValueError("SAGE handoff requires a proposal-only execution-disabled receipt")

    raw_envelope = proposal.get("envelope")
    if not isinstance(raw_envelope, dict):
        raise ValueError("SAGE handoff proposal has no NexusClaw envelope")
    try:
        envelope = NexusClawTaskEnvelope.from_dict(raw_envelope)
    except ValueError as exc:
        raise ValueError("SAGE handoff has an invalid NexusClaw envelope") from exc
    if proposal.get("task_id") != envelope.task_id:
        raise ValueError("SAGE handoff proposal task id does not match its envelope")
    if envelope.source != "a2a:nexus-sage":
        raise ValueError("SAGE handoff requires the canonical SAGE source")
    if envelope.lane != "external":
        raise ValueError("SAGE handoff requires the external NexusClaw lane")
    if envelope.intent != expected_skill:
        raise ValueError("SAGE handoff intent does not match the workflow")
    if envelope.required_capabilities != [expected_skill]:
        raise ValueError("SAGE handoff capabilities do not match the workflow")
    if (
        envelope.approval_state is not ApprovalState.PENDING
        or envelope.human_approved
    ):
        raise ValueError("SAGE handoff may not contain approval")

    raw_dry_run = proposal.get("nexusclaw")
    if not isinstance(raw_dry_run, dict):
        raise ValueError("SAGE handoff proposal has no NexusClaw dry-run receipt")
    try:
        dry_run = NexusClawResultEnvelope.from_dict(raw_dry_run)
    except ValueError as exc:
        raise ValueError("SAGE handoff has an invalid NexusClaw dry-run receipt") from exc
    if dry_run.task_id != envelope.task_id or dry_run.status is not ResultStatus.DRY_RUN:
        raise ValueError("SAGE handoff requires a matching NexusClaw dry-run receipt")

    proposal_sha256 = hashlib.sha256(
        _canonical_json_bytes(proposal, label="proposal")
    ).hexdigest()
    return SageNexusClawHandoff(
        job_id=job_id,
        workflow_type=normalized_workflow,
        proposal_sha256=proposal_sha256,
        parameters_sha256=parameters_sha256,
        envelope=envelope,
    )


def build_sage_program_proposal(
    *,
    task_id: str,
    program: str,
    timeout_s: int = 30,
    sender: str = "nexus-sage",
    requested_mode: str = "dry_run",
) -> dict[str, Any]:
    """Return a proposal-only envelope for a SAGE program submission.

    The raw program is validated and hashed, then discarded from the returned
    contract.  HERMES/operator review is required before any separate executor
    can materialize or run it in an approved sandbox.
    """

    if not isinstance(program, str) or not program.strip():
        raise ValueError("program must be a non-empty string")
    if len(program) > MAX_SAGE_PROGRAM_CHARS:
        raise ValueError(
            f"program must be at most {MAX_SAGE_PROGRAM_CHARS} characters"
        )
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, int):
        raise ValueError("timeout_s must be an integer")
    if timeout_s < 1 or timeout_s > MAX_SAGE_PROGRAM_TIMEOUT_S:
        raise ValueError(
            f"timeout_s must be between 1 and {MAX_SAGE_PROGRAM_TIMEOUT_S}"
        )

    encoded = program.encode("utf-8")
    proposal = build_governed_a2a_proposal(
        task_id=task_id,
        skill_id="program_execution",
        params={
            "sender": sender,
            "mode": requested_mode,
            "approval_state": "pending",
            "max_tokens": 4096,
        },
    )
    proposal.update(
        {
            "schema": "nexus.sage-program-proposal.v1",
            "program_sha256": hashlib.sha256(encoded).hexdigest(),
            "program_bytes": len(encoded),
            "requested_timeout_s": timeout_s,
            "program_persisted": False,
            "program_executed": False,
            "executor_required": "hermes-governed-sandbox",
        }
    )
    return proposal


def build_sage_job_proposal(
    *,
    task_id: str,
    workflow_type: str,
    parameters: dict[str, Any] | None = None,
    sender: str = "nexus-sage",
) -> dict[str, Any]:
    """Map one allowlisted SAGE job to the canonical proposal-only gates."""

    normalized = str(workflow_type or "").strip().lower()
    skill_id = SAGE_WORKFLOW_SKILLS.get(normalized)
    if skill_id is None:
        allowed = ", ".join(sorted(SAGE_WORKFLOW_SKILLS))
        raise ValueError(f"workflow_type must be one of: {allowed}")
    if parameters is not None and not isinstance(parameters, dict):
        raise ValueError("parameters must be an object")

    safe_parameters = dict(parameters or {})
    encoded = json.dumps(
        safe_parameters,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    proposal = build_governed_a2a_proposal(
        task_id=task_id,
        skill_id=skill_id,
        params={
            "sender": sender,
            "mode": "dry_run",
            "approval_state": "pending",
            "max_tokens": 4096,
        },
    )
    proposal.update(
        {
            "schema": "nexus.sage-job-proposal.v1",
            "workflow_type": normalized,
            "parameters_sha256": hashlib.sha256(encoded).hexdigest(),
            "parameters_bytes": len(encoded),
            "parameters_persisted_in_job_store": True,
            "execution_allowed": False,
        }
    )
    return proposal
