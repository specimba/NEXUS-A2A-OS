"""Native Sentinel orchestration service."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import urlparse

from nexus_os.sentinel.models import (
    ApprovalRequest,
    CaseRecord,
    CaseStage,
    CreateCaseRequest,
    EvaluateCaseRequest,
    EventRecord,
    ExecuteRequest,
    PolicyVerdict,
    RiskLevel,
    VerifyRequest,
)
from nexus_os.sentinel.policy import evaluate_release
from nexus_os.sentinel.repository import SentinelRepository
from nexus_os.sentinel.state_machine import TRANSITIONS, require_transition

logger = logging.getLogger("nexus.sentinel")


class GovernorProtocol(Protocol):
    def check_access(self, **kwargs: Any) -> Any: ...


class ExecutorProtocol(Protocol):
    def execute(self, *, case_id: str, actor_id: str, request: ExecuteRequest, trace_id: str) -> dict[str, Any]: ...


class BridgeExecutionError(RuntimeError):
    pass


class BridgeExecutor:
    """Signed execution through the canonical A2A bridge on port 8000."""

    def __init__(self, bridge_url: str = "http://127.0.0.1:8000") -> None:
        if urlparse(bridge_url).port != 8000:
            raise ValueError("Sentinel execution bridge must use canonical port 8000")
        self.bridge_url = bridge_url

    def execute(self, *, case_id: str, actor_id: str, request: ExecuteRequest, trace_id: str) -> dict[str, Any]:
        secret = os.getenv("NEXUS_SENTINEL_BRIDGE_SECRET")
        if not secret:
            raise BridgeExecutionError("NEXUS_SENTINEL_BRIDGE_SECRET is not configured")
        from nexus_os.bridge.sdk import NexusClient

        client = NexusClient(self.bridge_url, actor_id, secret)
        response = client.submit_task(
            project_id=case_id,
            description=request.description,
            context={**request.context, "sentinel_case_id": case_id, "trace_id": trace_id},
            lineage_id=trace_id,
            intent="sentinel approved remediation",
            impact=request.impact,
        )
        if response.status_code != 200 or response.body.get("status") != "completed":
            raise BridgeExecutionError(
                response.body.get("error") or f"bridge returned {response.status_code}"
            )
        return response.body


class SentinelService:
    def __init__(
        self,
        repository: SentinelRepository,
        governor: GovernorProtocol,
        executor: ExecutorProtocol | None = None,
        memory_manager: Any | None = None,
    ) -> None:
        self.repository = repository
        self.governor = governor
        self.executor = executor or BridgeExecutor()
        self.memory = memory_manager

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _trace() -> str:
        return f"sentinel-{uuid.uuid4().hex[:20]}"

    @staticmethod
    def _event_id() -> str:
        return f"sevt-{uuid.uuid4().hex[:20]}"

    @staticmethod
    def _fingerprint(model: Any) -> str:
        payload = model.model_dump(mode="json")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _vap_id(trace_id: str, event_type: str) -> str:
        return "vap-" + hashlib.sha256(f"{trace_id}:{event_type}".encode()).hexdigest()[:20]

    def _idempotent(self, model: Any, case_id: str, operation: str) -> tuple[str, dict[str, Any] | None]:
        request_hash = self._fingerprint(model)
        found = self.repository.get_idempotent(
            model.idempotency_key, case_id, operation, request_hash
        )
        return request_hash, found

    def _save_idempotent(
        self, model: Any, case_id: str, operation: str, request_hash: str, response: dict[str, Any]
    ) -> dict[str, Any]:
        self.repository.save_idempotent(
            model.idempotency_key, case_id, operation, request_hash, response
        )
        return response

    def _event(
        self,
        *,
        case: CaseRecord,
        actor_id: str,
        event_type: str,
        previous_stage: CaseStage | None,
        details: dict[str, Any],
        evidence_hashes: list[str] | None = None,
    ) -> EventRecord:
        return EventRecord(
            event_id=self._event_id(),
            case_id=case.case_id,
            case_version=case.version,
            event_type=event_type,
            actor_id=actor_id,
            previous_stage=previous_stage,
            new_stage=case.stage,
            trace_id=case.trace_id,
            vap_id=case.vap_id,
            evidence_hashes=evidence_hashes or [],
            details=details,
            created_at=case.updated_at,
        )

    def _transition(
        self,
        case: CaseRecord,
        target: CaseStage,
        *,
        actor_id: str,
        event_type: str,
        details: dict[str, Any],
        risk_level: RiskLevel | None = None,
        verdict: PolicyVerdict | None = None,
        reason_codes: list[str] | None = None,
        retry_count: int | None = None,
        evidence_hashes: list[str] | None = None,
        trace_id: str | None = None,
    ) -> tuple[CaseRecord, EventRecord]:
        require_transition(case.stage, target)
        trace_id = trace_id or self._trace()
        updated = case.model_copy(
            update={
                "stage": target,
                "version": case.version + 1,
                "risk_level": risk_level or case.risk_level,
                "policy_verdict": verdict if verdict is not None else case.policy_verdict,
                "reason_codes": reason_codes if reason_codes is not None else case.reason_codes,
                "retry_count": retry_count if retry_count is not None else case.retry_count,
                "trace_id": trace_id,
                "vap_id": self._vap_id(trace_id, event_type),
                "updated_at": self._now(),
            }
        )
        event = self._event(
            case=updated,
            actor_id=actor_id,
            event_type=event_type,
            previous_stage=case.stage,
            details=details,
            evidence_hashes=evidence_hashes,
        )
        self.repository.update_case(updated, case.version, event)
        self._write_memory(updated, event)
        self._emit_alert(updated, event)
        return updated, event

    def _writer_trust(self) -> float:
        """Sentinel's canonical write authority, from the TrustKernel singleton.

        Audit fix (adoption review): every vault mirror used to stamp a
        hardcoded trust_score=100.0 regardless of case outcome, polluting
        the trust-gated channels with perfect-authority writes. The
        sentinel principal now carries a 90.0 bootstrap prior that real
        evidence can degrade; kernel failure returns 0.0 so gated
        channels refuse the write (fail-closed).
        """
        try:
            from nexus_os.governor.trust_kernel import get_trust_kernel
            snap = get_trust_kernel().ensure_bootstrap_prior(
                "nexus-sentinel", "governance", prior_trust=90.0,
            )
            return round(snap.trust * 100.0, 2)
        except Exception:
            logger.warning("TrustKernel unavailable for sentinel writer trust", exc_info=True)
            return 0.0

    def _write_memory(self, case: CaseRecord, event: EventRecord) -> None:
        if self.memory is None:
            return
        content = json.dumps(
            {
                "case_id": case.case_id,
                "event": event.event_type,
                "stage": case.stage.value,
                "version": case.version,
                "trace_id": case.trace_id,
            },
            sort_keys=True,
        )
        writer_trust = self._writer_trust()
        try:
            self.memory.append_episodic(
                "sentinel",
                content,
                outcome="success" if case.stage not in {CaseStage.ESCALATED, CaseStage.REWORK_REQUIRED} else "failure",
                trace_id=case.trace_id,
                project_id=case.case_id,
                trust_score=writer_trust,
            )
            self.memory.append_task(
                "sentinel",
                content,
                task_id=case.case_id,
                task_status="completed" if case.stage == CaseStage.CLOSURE else "active",
                trust_score=writer_trust,
                trace_id=case.trace_id,
            )
            self.memory.append_meta(
                "sentinel",
                "health",
                float(case.retry_count),
                content=content,
                trust_score=writer_trust,
                trace_id=case.trace_id,
            )
        except Exception:
            # The durable Sentinel ledger remains authoritative when memory is
            # degraded — but the degradation must be VISIBLE, not swallowed.
            logger.warning(
                "Sentinel memory mirror failed for case %s (ledger remains authoritative)",
                case.case_id, exc_info=True,
            )

    #: stages/events worth an operator-facing A2A alert
    _ALERT_STAGES = {CaseStage.ESCALATED}
    _ALERT_EVENTS = {"governor_blocked_execution"}

    def _emit_alert(self, case: CaseRecord, event: EventRecord) -> None:
        """High-signal Sentinel outcomes reach the A2A bus (monitor parity).

        Escalations and governor blocks used to land only in the Sentinel
        ledger; the monitor daemon and operator dashboards never saw them.
        """
        if case.stage not in self._ALERT_STAGES and event.event_type not in self._ALERT_EVENTS:
            return
        try:
            from nexus_os.bridge.a2a_channels import A2AChannelBus
            A2AChannelBus().publish(
                channel_id="sentinel-alerts",
                sender="nexus-sentinel",
                message=json.dumps({
                    "type": "sentinel-alert",
                    "case_id": case.case_id,
                    "stage": case.stage.value,
                    "event": event.event_type,
                    "risk_level": case.risk_level.value if case.risk_level else None,
                    "retry_count": case.retry_count,
                    "trace_id": case.trace_id,
                }),
                topic="sentinel",
            )
        except Exception:
            logger.warning("Sentinel A2A alert emit failed", exc_info=True)

    def create_case(self, request: CreateCaseRequest) -> CaseRecord:
        request_hash, found = self._idempotent(request, request.case_id, "create")
        if found:
            return CaseRecord.model_validate(found)
        now = self._now()
        trace_id = self._trace()
        record = CaseRecord(
            case_id=request.case_id,
            case_type=request.case_type,
            title=request.title,
            stage=CaseStage.INVESTIGATION,
            version=1,
            risk_level=RiskLevel.LOW,
            trace_id=trace_id,
            vap_id=self._vap_id(trace_id, "case_created"),
            created_at=now,
            updated_at=now,
        )
        event = self._event(
            case=record,
            actor_id=request.actor_id,
            event_type="case_created",
            previous_stage=CaseStage.INTAKE,
            details={"case_type": request.case_type},
        )
        self.repository.create_case(record, event)
        self._write_memory(record, event)
        self._save_idempotent(
            request, request.case_id, "create", request_hash, record.model_dump(mode="json")
        )
        return record

    def evaluate(self, case_id: str, request: EvaluateCaseRequest) -> dict[str, Any]:
        request_hash, found = self._idempotent(request, case_id, "evaluate")
        if found:
            return found
        case = self.repository.get_case(case_id)
        if case.version != request.expected_version:
            from nexus_os.sentinel.repository import VersionConflict
            raise VersionConflict(f"case {case_id} expected version {request.expected_version}")
        if case.stage != CaseStage.INVESTIGATION:
            raise ValueError(f"case must be in INVESTIGATION, found {case.stage.value}")
        approval = self.repository.latest_approval(case_id)
        result = evaluate_release(request, human_approved=bool(approval and approval["approved"]))
        target = {
            PolicyVerdict.ALLOW: CaseStage.REMEDIATION_PROPOSED,
            PolicyVerdict.HOLD: CaseStage.HUMAN_DECISION,
            PolicyVerdict.DENY: CaseStage.ESCALATED,
        }[result["verdict"]]
        hashes = [ref.sha256 for ref in request.evidence.refs]
        updated, event = self._transition(
            case,
            target,
            actor_id=request.actor_id,
            event_type="case_evaluated",
            details={
                "requested_model": request.requested_model,
                "observed_model": request.observed_model,
                "verdict": result["verdict"].value,
                "reason_codes": result["reason_codes"],
            },
            risk_level=result["risk_level"],
            verdict=result["verdict"],
            reason_codes=result["reason_codes"],
            evidence_hashes=hashes,
        )
        self.repository.add_evidence(case_id, request.evidence.refs, updated.updated_at)
        response = {
            "case": updated.model_dump(mode="json"),
            "evaluation_event_id": event.event_id,
        }
        return self._save_idempotent(request, case_id, "evaluate", request_hash, response)

    def approve(self, case_id: str, request: ApprovalRequest) -> CaseRecord:
        request_hash, found = self._idempotent(request, case_id, "approval")
        if found:
            return CaseRecord.model_validate(found)
        case = self.repository.get_case(case_id)
        if case.version != request.expected_version:
            from nexus_os.sentinel.repository import VersionConflict
            raise VersionConflict(f"case {case_id} expected version {request.expected_version}")
        if case.stage != CaseStage.HUMAN_DECISION:
            raise ValueError("approval is accepted only in HUMAN_DECISION")
        if request.approver_role != "AI_RELEASE_MANAGER":
            raise PermissionError("AI_RELEASE_MANAGER role required")
        trace_id = self._trace()
        self.repository.add_approval(
            {
                "approval_id": f"approval-{uuid.uuid4().hex[:16]}",
                "case_id": case_id,
                "approver_id": request.approver_id,
                "approver_role": request.approver_role,
                "approved": request.approved,
                "notes_hash": hashlib.sha256(request.notes.encode()).hexdigest(),
                "trace_id": trace_id,
                "created_at": self._now(),
            }
        )
        target = CaseStage.INVESTIGATION if request.approved else CaseStage.ESCALATED
        updated, _ = self._transition(
            case,
            target,
            actor_id=request.approver_id,
            event_type="approval_recorded",
            details={"approved": request.approved, "role": request.approver_role},
            risk_level=case.risk_level if request.approved else RiskLevel.HIGH,
        )
        return CaseRecord.model_validate(
            self._save_idempotent(
                request, case_id, "approval", request_hash, updated.model_dump(mode="json")
            )
        )

    @staticmethod
    def _governor_verdict(result: Any) -> PolicyVerdict:
        value = getattr(getattr(result, "decision", result), "value", getattr(result, "decision", result))
        normalized = str(value).upper()
        try:
            return PolicyVerdict(normalized)
        except ValueError:
            # Unknown governor verdicts (escalate/quarantine/...) fail closed
            # instead of raising into an HTTP 422.
            logger.warning("Unmapped governor verdict %r -> DENY (fail-closed)", normalized)
            return PolicyVerdict.DENY

    def execute(self, case_id: str, request: ExecuteRequest) -> dict[str, Any]:
        request_hash, found = self._idempotent(request, case_id, "execute")
        if found:
            return found
        case = self.repository.get_case(case_id)
        if case.version != request.expected_version:
            from nexus_os.sentinel.repository import VersionConflict
            raise VersionConflict(f"case {case_id} expected version {request.expected_version}")
        if case.stage != CaseStage.REMEDIATION_PROPOSED:
            raise ValueError("execution requires REMEDIATION_PROPOSED")
        trace_id = self._trace()
        auth = self.governor.check_access(
            agent_id=request.actor_id,
            project_id=case_id,
            action="execute",
            scope="project",
            intent="execute Sentinel-approved remediation",
            impact=request.impact,
            trace_id=trace_id,
            context={"lane": "sentinel", "case_id": case_id},
        )
        verdict = self._governor_verdict(auth)
        if verdict != PolicyVerdict.ALLOW:
            target = CaseStage.HUMAN_DECISION if verdict == PolicyVerdict.HOLD else CaseStage.ESCALATED
            updated, _ = self._transition(
                case,
                target,
                actor_id=request.actor_id,
                event_type="governor_blocked_execution",
                details={"governor_verdict": verdict.value},
                verdict=verdict,
                risk_level=RiskLevel.HIGH,
                reason_codes=[f"GOVERNOR_{verdict.value}"],
            )
            response = {"case": updated.model_dump(mode="json"), "execution": None}
            return self._save_idempotent(request, case_id, "execute", request_hash, response)


        authorized, _ = self._transition(
            case,
            CaseStage.AUTHORIZED_EXECUTION,
            actor_id=request.actor_id,
            event_type="execution_authorized",
            details={"governor_verdict": "ALLOW"},
            verdict=PolicyVerdict.ALLOW,
            trace_id=trace_id,
        )
        execution = self.executor.execute(
            case_id=case_id,
            actor_id=request.actor_id,
            request=request,
            trace_id=authorized.trace_id,
        )
        verifying, event = self._transition(
            authorized,
            CaseStage.VERIFICATION,
            actor_id=request.actor_id,
            event_type="execution_completed",
            details={"task_id": execution.get("task_id"), "status": execution.get("status")},
        )
        response = {
            "case": verifying.model_dump(mode="json"),
            "execution": execution,
            "execution_event_id": event.event_id,
        }
        return self._save_idempotent(request, case_id, "execute", request_hash, response)

    def verify(self, case_id: str, request: VerifyRequest) -> dict[str, Any]:
        request_hash, found = self._idempotent(request, case_id, "verify")
        if found:
            return found
        case = self.repository.get_case(case_id)
        if case.version != request.expected_version:
            from nexus_os.sentinel.repository import VersionConflict
            raise VersionConflict(f"case {case_id} expected version {request.expected_version}")
        if case.stage != CaseStage.VERIFICATION:
            raise ValueError("verification requires VERIFICATION stage")
        evaluation = self.repository.get_event(request.evaluation_event_id)
        if not evaluation or evaluation.case_id != case_id or evaluation.event_type != "case_evaluated":
            raise ValueError("evaluation event does not belong to this case")
        reasons = []
        for field, code in (
            ("model_identity_matches", "MODEL_IDENTITY_STILL_MISMATCHED"),
            ("policy_tests_pass", "POLICY_TESTS_FAILED"),
            ("service_health_pass", "SERVICE_HEALTH_FAILED"),
            ("evidence_attached", "VERIFICATION_EVIDENCE_MISSING"),
        ):
            if not getattr(request.checks, field):
                reasons.append(code)
        attempt = case.retry_count + 1
        verified = not reasons
        target = CaseStage.CLOSURE if verified else CaseStage.ESCALATED if attempt >= 3 else CaseStage.REWORK_REQUIRED
        updated, event = self._transition(
            case,
            target,
            actor_id=request.actor_id,
            event_type="case_verified",
            details={"verified": verified, "reason_codes": reasons, "attempt": attempt},
            retry_count=attempt,
            reason_codes=reasons,
            risk_level=RiskLevel.LOW if verified else RiskLevel.HIGH,
        )
        self.repository.add_verification(
            {
                "verification_id": event.event_id,
                "case_id": case_id,
                "evaluation_event_id": request.evaluation_event_id,
                "remediation_id": request.remediation_id,
                "attempt": attempt,
                "verified": verified,
                "reason_codes": reasons,
                "trace_id": updated.trace_id,
                "created_at": updated.updated_at,
            }
        )
        if target == CaseStage.REWORK_REQUIRED:
            updated, _ = self._transition(
                updated,
                CaseStage.INVESTIGATION,
                actor_id=request.actor_id,
                event_type="case_reentered",
                details={"attempt": attempt},
            )
        response = {"case": updated.model_dump(mode="json"), "verified": verified}
        return self._save_idempotent(request, case_id, "verify", request_hash, response)

    def replay(self, case_id: str) -> dict[str, Any]:
        events = self.repository.timeline(case_id)
        issues: list[str] = []
        previous = None
        expected_version = 1
        previous_hash = None
        for event in events:
            calculated_hash = self.repository._calculate_event_hash(event, previous_hash)
            if event.previous_event_hash != previous_hash or event.event_hash != calculated_hash:
                issues.append(f"event hash mismatch at {event.event_id}")
            previous_hash = event.event_hash
            if event.case_version != expected_version:
                issues.append(f"version gap at {event.event_id}")
            if previous is not None and event.previous_stage != previous:
                issues.append(f"stage lineage mismatch at {event.event_id}")
            if event.previous_stage and event.new_stage not in TRANSITIONS[event.previous_stage]:
                issues.append(f"invalid transition at {event.event_id}")
            previous = event.new_stage
            expected_version += 1
        return {
            "case_id": case_id,
            "valid": not issues,
            "issues": issues,
            "event_count": len(events),
            "events": [event.model_dump(mode="json") for event in events],
        }
