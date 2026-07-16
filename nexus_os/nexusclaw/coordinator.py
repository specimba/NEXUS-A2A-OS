"""NexusClaw Core V0 coordinator.

The coordinator is deliberately thin. It validates a task envelope, routes it
through dry-run governance metadata, and returns a result envelope. It does not
start autonomous loops, probe every model, or call cloud fallbacks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from nexus_os.continuity.records import (
    VERIFICATION_UNVERIFIED,
    VERIFICATION_VERIFIED,
    ContinuityRunRecord,
    ProgressClass,
    append_record,
    utc_now,
)
from nexus_os.governor.privilege_control import ProgentPrivilegeControl
from nexus_os.nexusclaw.envelope import (
    ApprovalState,
    NexusClawResultEnvelope,
    NexusClawTaskEnvelope,
    ResultStatus,
    RiskLevel,
)
from nexus_os.vault.governed_memory_broker import GovernedMemoryBroker


PORT_OWNERSHIP = {
    7350: "modelrelay_npm",
    7352: "nexus_governance",  # Brain API — never ModelRelay
    7353: "twave",
    7354: "gross_bridge",  # live process: nexus-grok-bridge-v2
    7355: "modelrelay_python",
    7356: "static_dashboard",
    7357: "god_mode_proxy",
    11436: "nexusclaw_ollama_lane",
}

# HIGH/CRITICAL risk envelopes require an explicit human approval marker
# before live execution (HELD semantics from the task router, P1-7).
_HUMAN_GATED_RISK_LEVELS = frozenset({RiskLevel.HIGH, RiskLevel.CRITICAL})


@dataclass(frozen=True)
class NexusClawRuntimeConfig:
    """Immutable NexusClaw V0 runtime defaults."""

    governance_port: int = 7352
    twave_port: int = 7353
    gross_bridge_port: int = 7354
    modelrelay_internal_port: int = 7355
    nexusclaw_ollama_port: int = 11436
    cloud_fallback_enabled: bool = False
    background_model_polling_enabled: bool = False
    per_service_ngrok_tunnels_enabled: bool = False
    remote_stdio_enabled: bool = False
    all_filesystem_access_enabled: bool = False
    default_lane: str = "orchestrator"

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        expected = {
            "governance_port": 7352,
            "twave_port": 7353,
            "gross_bridge_port": 7354,
            "modelrelay_internal_port": 7355,
            "nexusclaw_ollama_port": 11436,
        }
        for attr, expected_port in expected.items():
            actual = getattr(self, attr)
            if actual != expected_port:
                raise ValueError(f"{attr} must remain reserved on port {expected_port}")

        if self.cloud_fallback_enabled:
            raise ValueError("cloud fallback must remain disabled in NexusClaw V0")
        if self.background_model_polling_enabled:
            raise ValueError("background model polling must remain disabled in NexusClaw V0")
        if self.per_service_ngrok_tunnels_enabled:
            raise ValueError("per-service ngrok tunnels must remain disabled in NexusClaw V0")
        if self.remote_stdio_enabled:
            raise ValueError("remote stdio must remain disabled in NexusClaw V0")
        if self.all_filesystem_access_enabled:
            raise ValueError("all-filesystem access must remain disabled in NexusClaw V0")
        if self.default_lane != "orchestrator":
            raise ValueError("NexusClaw V0 default lane must be orchestrator")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NexusClawCoordinator:
    """Single-lane NexusClaw V0 coordinator."""

    def __init__(
        self,
        config: NexusClawRuntimeConfig | None = None,
        memory_broker: GovernedMemoryBroker | None = None,
        privilege_control: ProgentPrivilegeControl | None = None,
    ) -> None:
        self.config = config or NexusClawRuntimeConfig()
        self.memory_broker = memory_broker or GovernedMemoryBroker()
        # Empty default policy blocks every call: live execution is
        # fail-closed unless an explicit privilege policy is provisioned.
        self.privilege_control = privilege_control or ProgentPrivilegeControl()
        self._halted = False
        self._halt_reason: str | None = None
        self._last_task: NexusClawTaskEnvelope | None = None
        self._last_result: NexusClawResultEnvelope | None = None

    def propose(self, payload: dict[str, Any] | NexusClawTaskEnvelope) -> NexusClawTaskEnvelope:
        """Validate and remember a proposed NexusClaw task."""

        if self._halted:
            raise RuntimeError(f"NexusClaw is halted: {self._halt_reason}")
        task = payload if isinstance(payload, NexusClawTaskEnvelope) else NexusClawTaskEnvelope.from_dict(payload)
        task.validate()
        self._last_task = task
        return task

    def dispatch_dry_run(
        self,
        payload: dict[str, Any] | NexusClawTaskEnvelope | None = None,
    ) -> NexusClawResultEnvelope:
        """Return a dry-run result envelope without executing external work."""

        if self._halted:
            task_id = self._last_task.task_id if self._last_task else "nexusclaw-halted"
            result = NexusClawResultEnvelope(
                task_id=task_id,
                status=ResultStatus.HALTED,
                executor="nexusclaw.core.v0",
                evidence=[],
                metrics={"dry_run": True, "halted": True},
                vap_record_id=None,
                halt_reason=self._halt_reason or "halted",
            )
            self._last_result = result
            return result

        task = self.propose(payload) if payload is not None else self._require_last_task()
        now = datetime.now(timezone.utc).isoformat()
        memory_context = self.memory_broker.build_context(
            agent_id=task.source,
            lane="orchestration",
            query=task.intent,
            action="read",
            requested_tokens=task.resource_budget.get("max_tokens"),
            include_semantic=task.resource_budget.get("include_semantic_memory") is True,
        )
        result = NexusClawResultEnvelope(
            task_id=task.task_id,
            status=ResultStatus.DRY_RUN,
            executor="nexusclaw.orchestrator.dry_run",
            evidence=list(task.evidence_refs),
            metrics={
                "approved_by": "kaiju_dry_run_gate",
                "resource_lease": "dry_run_only",
                "vap_required": True,
                "created_at": now,
                "ports": dict(PORT_OWNERSHIP),
                "cloud_fallback_enabled": self.config.cloud_fallback_enabled,
                "background_model_polling_enabled": self.config.background_model_polling_enabled,
                "memory_context": {
                    "budget_class": memory_context.plan.budget_class,
                    "memory_query_depth": memory_context.plan.memory_query_depth,
                    "token_budget": memory_context.plan.token_budget,
                    "enabled_paths": list(memory_context.plan.enabled_paths),
                    "denied_paths": list(memory_context.plan.denied_paths),
                    "hot_count": memory_context.metrics.get("hot_count", 0),
                    "track_sections": memory_context.metrics.get("track_sections", 0),
                    "semantic_count": memory_context.metrics.get("semantic_count", 0),
                    "raw_payload_included": False,
                },
            },
            vap_record_id=f"vap-dryrun-{task.task_id}",
            halt_reason=None,
        )
        self._last_result = result
        return result

    def dispatch(
        self,
        payload: dict[str, Any] | NexusClawTaskEnvelope | None = None,
        *,
        live: bool = False,
        executor: Callable[[NexusClawTaskEnvelope], dict[str, Any]] | None = None,
    ) -> NexusClawResultEnvelope:
        """Dispatch a task envelope. Dry-run is the default; live is opt-in."""

        if not live:
            return self.dispatch_dry_run(payload)
        return self.dispatch_live(payload, executor=executor)

    def dispatch_live(
        self,
        payload: dict[str, Any] | NexusClawTaskEnvelope | None = None,
        *,
        executor: Callable[[NexusClawTaskEnvelope], dict[str, Any]] | None = None,
    ) -> NexusClawResultEnvelope:
        """Execute an APPROVED envelope through the governed live path.

        Gates, in order: coordinator halt state, envelope approval state
        (only ``approved`` proceeds; pending/held/rejected refuse), the
        explicit human approval marker for HIGH/CRITICAL risk (HELD
        semantics - never auto-execute), and the Progent privilege check
        (fail-closed: any exception refuses). Execution - successful or
        failed - appends an origin="core" evidence row to the continuity
        ledger with the envelope id and the privilege-check result.
        """

        if self._halted:
            task_id = self._last_task.task_id if self._last_task else "nexusclaw-halted"
            result = NexusClawResultEnvelope(
                task_id=task_id,
                status=ResultStatus.HALTED,
                executor="nexusclaw.core.v0",
                evidence=[],
                metrics={"live": True, "halted": True},
                vap_record_id=None,
                halt_reason=self._halt_reason or "halted",
            )
            self._last_result = result
            return result

        task = self.propose(payload) if payload is not None else self._require_last_task()

        # (a) approval-state gate: only approved envelopes may execute live.
        if task.approval_state is not ApprovalState.APPROVED:
            return self._refuse_live(
                task,
                f"approval_state={task.approval_state.value}: only approved envelopes may execute live",
            )

        # HELD semantics: HIGH/CRITICAL risk additionally requires the
        # explicit human approval marker on the envelope.
        if task.risk_level in _HUMAN_GATED_RISK_LEVELS and not task.human_approved:
            return self._refuse_live(
                task,
                f"{task.risk_level.value}-risk envelope requires an explicit human approval marker - held",
                held_for_human=True,
            )

        # (b) privilege check on the envelope action/target - fail closed.
        privilege_check: dict[str, Any] = {
            "tool": task.intent,
            "lane": task.lane,
            "allowed": False,
        }
        try:
            privilege_check["allowed"] = bool(
                self.privilege_control.check_call(
                    task.intent,
                    {"task_id": task.task_id, "lane": task.lane, "source": task.source},
                )
            )
        except Exception as exc:  # fail-closed: any privilege error refuses
            privilege_check["error"] = str(exc)
        if not privilege_check["allowed"]:
            return self._refuse_live(
                task,
                "privilege check refused envelope action",
                privilege_check=privilege_check,
            )

        # (c) execution.
        execution_error: str | None = None
        outcome: dict[str, Any] = {}
        try:
            if executor is not None:
                outcome = executor(task) or {}
            else:
                outcome = {"detail": "governed no-op execution (no executor provided)"}
        except Exception as exc:
            execution_error = str(exc)
        executed_ok = execution_error is None

        # (d) evidence row in the continuity ledger (origin=core).
        record = ContinuityRunRecord(
            run_id=f"nexusclaw-live-{task.task_id}",
            agent_id="nexusclaw.coordinator.live",
            source_lane=task.lane,
            progress_class=(
                ProgressClass.IMPLEMENTED_DELTA.value if executed_ok else ProgressClass.ADVISORY_ONLY.value
            ),
            blocker=None if executed_ok else f"live execution failed: {execution_error}",
            completed_at=utc_now(),
            verification=VERIFICATION_VERIFIED if executed_ok else VERIFICATION_UNVERIFIED,
            proof={
                "envelope_id": task.task_id,
                "privilege_check": dict(privilege_check),
                "risk_level": task.risk_level.value,
                "human_approved": task.human_approved,
                "executed": executed_ok,
                "execution_error": execution_error,
            },
        )
        ledger_path = append_record(record, origin="core")

        if executed_ok:
            result = NexusClawResultEnvelope(
                task_id=task.task_id,
                status=ResultStatus.COMPLETED,
                executor="nexusclaw.orchestrator.live",
                evidence=[*task.evidence_refs, f"continuity:{ledger_path}"],
                metrics={
                    "live": True,
                    "approved_by": "envelope.approval_state",
                    "privilege_check": dict(privilege_check),
                    "continuity_ledger": str(ledger_path),
                    "execution": outcome,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                vap_record_id=f"vap-live-{task.task_id}",
                halt_reason=None,
            )
        else:
            result = NexusClawResultEnvelope(
                task_id=task.task_id,
                status=ResultStatus.HALTED,
                executor="nexusclaw.orchestrator.live",
                evidence=[f"continuity:{ledger_path}"],
                metrics={
                    "live": True,
                    "privilege_check": dict(privilege_check),
                    "continuity_ledger": str(ledger_path),
                },
                vap_record_id=None,
                halt_reason=f"live execution failed: {execution_error}",
            )
        self._last_result = result
        return result

    def _refuse_live(
        self,
        task: NexusClawTaskEnvelope,
        reason: str,
        *,
        held_for_human: bool = False,
        privilege_check: dict[str, Any] | None = None,
    ) -> NexusClawResultEnvelope:
        """Build, remember, and return a live-path refusal (no execution)."""

        metrics: dict[str, Any] = {
            "live": True,
            "refused": True,
            "refusal_reason": reason,
            "held_for_human": held_for_human,
        }
        if privilege_check is not None:
            metrics["privilege_check"] = dict(privilege_check)
        result = NexusClawResultEnvelope(
            task_id=task.task_id,
            status=ResultStatus.REJECTED,
            executor="nexusclaw.orchestrator.live",
            evidence=[],
            metrics=metrics,
            vap_record_id=None,
            halt_reason=None,
        )
        self._last_result = result
        return result

    def status(self) -> dict[str, Any]:
        return {
            "status": "halted" if self._halted else "ok",
            "version": "core-v0",
            "config": self.config.to_dict(),
            "port_ownership": dict(PORT_OWNERSHIP),
            "last_task": self._last_task.to_dict() if self._last_task else None,
            "last_result": self._last_result.to_dict() if self._last_result else None,
        }

    def halt(self, reason: str) -> NexusClawResultEnvelope:
        if not reason.strip():
            raise ValueError("halt reason must be non-empty")
        self._halted = True
        self._halt_reason = reason.strip()
        task_id = self._last_task.task_id if self._last_task else "nexusclaw-halt"
        result = NexusClawResultEnvelope(
            task_id=task_id,
            status=ResultStatus.HALTED,
            executor="nexusclaw.core.v0",
            evidence=[],
            metrics={"halted": True},
            vap_record_id=None,
            halt_reason=self._halt_reason,
        )
        self._last_result = result
        return result

    @property
    def is_halted(self) -> bool:
        return self._halted

    @property
    def halt_reason(self) -> str | None:
        return self._halt_reason

    def _require_last_task(self) -> NexusClawTaskEnvelope:
        if self._last_task is None:
            raise RuntimeError("no NexusClaw task has been proposed")
        return self._last_task
