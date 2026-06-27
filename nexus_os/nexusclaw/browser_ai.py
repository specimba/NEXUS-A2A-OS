"""Browser-AI supervisor to NexusClaw/Hermes/GMR bridge.

This module is intentionally proposal-only. It converts a material browser-AI
supervisor decision into a governed NexusClaw task envelope and can attach
Hermes/GMR/Chimera routing metadata without executing a relay call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from nexus_os.nexusclaw.envelope import NexusClawTaskEnvelope, RiskLevel


_EXECUTABLE_ACTIONS = {"CONTINUE_SENT", "ARTIFACT_CAPTURED"}


@dataclass(frozen=True)
class BrowserAIRoutingPacket:
    """Dry routing artifact for a browser-AI supervisor cycle."""

    task: NexusClawTaskEnvelope | None
    supervisor_action: str
    reason: str
    hermes: dict[str, Any] = field(default_factory=dict)
    chimera: dict[str, Any] = field(default_factory=dict)
    relay_execution_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task.to_dict() if self.task else None,
            "supervisor_action": self.supervisor_action,
            "reason": self.reason,
            "hermes": dict(self.hermes),
            "chimera": dict(self.chimera),
            "relay_execution_allowed": self.relay_execution_allowed,
        }


class BrowserAINexusClawBridge:
    """Proposal bridge from browser-AI supervisor to NexusClaw/Hermes/GMR."""

    def __init__(self, *, hermes_router: Any | None = None, chimera_selector: Any | None = None) -> None:
        self.hermes_router = hermes_router
        self.chimera_selector = chimera_selector

    def task_from_decision(
        self,
        *,
        run_id: str,
        source_id: str,
        observation: Any,
        decision: Any,
    ) -> NexusClawTaskEnvelope | None:
        """Build a governed task only for material browser-AI decisions."""

        action = str(getattr(decision, "action", ""))
        if action not in _EXECUTABLE_ACTIONS:
            return None

        artifact = getattr(observation, "new_artifact_name", None)
        visible_tail = str(getattr(observation, "visible_tail", ""))
        bridge_tools = tuple(getattr(decision, "bridge_tools", ()) or ())
        intent = artifact or visible_tail[:180] or "browser AI material delta"
        capabilities = ["browser_ai_supervisor", "nexusclaw_dry_run", "hermes_gmr_route"]
        if "http_diagnostic" in bridge_tools:
            capabilities.append("mcp_http_diagnostic")
        if "task_add" in bridge_tools:
            capabilities.append("coordination_queue")

        return NexusClawTaskEnvelope(
            task_id=f"BAI-{run_id}",
            source=source_id,
            lane="integration",
            intent=intent,
            risk_level=RiskLevel.MEDIUM,
            required_capabilities=capabilities,
            resource_budget={
                "max_tokens": 1200,
                "max_runtime_s": 600,
                "provider_calls_max": 1,
                "prompt": visible_tail[:4000],
            },
            egress_policy={
                "cloud_fallback": False,
                "remote_stdio": False,
                "all_filesystem_access": False,
                "network_access": "allowlisted_public_https_via_7354_only",
                "data_egress": "bounded_tool_observations_only",
            },
            evidence_refs=[
                f"browser_ai:{source_id}",
                f"supervisor_action:{action}",
                f"bridge_tools:{','.join(bridge_tools) or 'none'}",
            ],
        )

    def route_packet(
        self,
        *,
        run_id: str,
        source_id: str,
        observation: Any,
        decision: Any,
        agent_id: str = "browser-ai-supervisor",
    ) -> BrowserAIRoutingPacket:
        """Return a dry routing packet with optional Hermes/Chimera metadata."""

        task = self.task_from_decision(
            run_id=run_id,
            source_id=source_id,
            observation=observation,
            decision=decision,
        )
        if task is None:
            return BrowserAIRoutingPacket(
                task=None,
                supervisor_action=str(getattr(decision, "action", "")),
                reason=str(getattr(decision, "reason", "not_material")),
            )

        hermes_meta = self._route_hermes(task, agent_id=agent_id)
        chimera_meta = self._route_chimera(task)
        return BrowserAIRoutingPacket(
            task=task,
            supervisor_action=str(getattr(decision, "action", "")),
            reason=str(getattr(decision, "reason", "")),
            hermes=hermes_meta,
            chimera=chimera_meta,
            relay_execution_allowed=False,
        )

    def _route_hermes(self, task: NexusClawTaskEnvelope, *, agent_id: str) -> dict[str, Any]:
        router = self.hermes_router
        if router is None:
            try:
                from nexus_os.engine.hermes import HermesRouter
                from nexus_os.monitoring.token_guard import TokenGuard

                router = HermesRouter(token_guard=TokenGuard(budgets={agent_id: task.resource_budget.get("max_tokens", 1200)}))
            except Exception as exc:
                return {"status": "degraded", "reason": exc.__class__.__name__}
        try:
            routed = router.route(task.task_id, task.intent, {"agent_id": agent_id, "source": task.source})
            return {
                "status": "routed",
                "selected_model": getattr(routed, "selected_model", None),
                "fallback_models": list(getattr(routed, "fallback_models", []) or []),
                "domain": getattr(getattr(routed, "domain", None), "value", getattr(routed, "domain", None)),
                "complexity": getattr(getattr(routed, "complexity", None), "value", getattr(routed, "complexity", None)),
            }
        except Exception as exc:
            return {"status": "degraded", "reason": str(exc)}

    def _route_chimera(self, task: NexusClawTaskEnvelope) -> dict[str, Any]:
        selector = self.chimera_selector
        if selector is None:
            try:
                from nexus_os.twave.chimera_router_v2 import ChimeraRouterV2

                selector = ChimeraRouterV2(has_cloud_access=False)
            except Exception as exc:
                return {"status": "degraded", "reason": exc.__class__.__name__}
        try:
            decision = selector.route(
                task.resource_budget.get("prompt") or task.intent,
                latency_budget_ms=30000,
                quality_target=0.80,
            )
            return {
                "status": "selected",
                "model": getattr(decision, "model", None),
                "temperature": getattr(decision, "temperature", None),
                "temperature_policy": getattr(getattr(decision, "temperature_policy", None), "value", getattr(decision, "temperature_policy", None)),
                "tier": getattr(getattr(decision, "tier", None), "value", getattr(decision, "tier", None)),
            }
        except Exception as exc:
            return {"status": "degraded", "reason": str(exc)}
