"""NexusClaw Core V0 coordinator.

The coordinator is deliberately thin. It validates a task envelope, routes it
through dry-run governance metadata, and returns a result envelope. It does not
start autonomous loops, probe every model, or call cloud fallbacks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from nexus_os.nexusclaw.envelope import (
    NexusClawResultEnvelope,
    NexusClawTaskEnvelope,
    ResultStatus,
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
    ) -> None:
        self.config = config or NexusClawRuntimeConfig()
        self.memory_broker = memory_broker or GovernedMemoryBroker()
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
