"""NEXUSCLAW Model Intake Integration with Security Gates.

Integrates ModelArena techniques (HQQ/TIES/ASTRA) through governed, dry-run validated envelopes.
No raw model loading - all operations pass through KAIJU/VAP gates.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from nexus_os.nexusclaw.security import (
    validate_model_intake,
    SecurityDecision,
)
from nexus_os.nexusclaw.envelope import NexusClawTaskEnvelope, RiskLevel


@dataclass
class ModelIntakeRequest:
    """Requested model operation with taint tracking."""
    operation: str
    model_name: str
    parameters: Dict[str, Any]
    labels: List[str]
    
    def to_envelope(self, source: str = "modelarena") -> NexusClawTaskEnvelope:
        return NexusClawTaskEnvelope(
            task_id=f"model-intake-{self.model_name}",
            source=source,
            lane="orchestrator",
            intent=f"{self.operation} model {self.model_name}",
            risk_level=RiskLevel.HIGH,
            required_capabilities=["model_access", "vault_read"],
            resource_budget={"max_tokens": 1000},
            egress_policy={},
            evidence_refs=self.labels,
        )


class NexusClawModelArena:
    """Governed model intake via dry-run envelopes."""

    def __init__(self):
        self._cache: Dict[str, SecurityDecision] = {}

    def validate_intake(
        self,
        model_name: str,
        *,
        trust_remote_code: bool = False,
        labels: Optional[List[str]] = None,
        requested_lane: str = "normal",
        intent: str = "",
    ) -> SecurityDecision:
        """Validate model intake through security gates."""
        cache_key = f"{model_name}:{trust_remote_code}:{requested_lane}:{intent}:{hash(tuple(labels or []))}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        decision = validate_model_intake(
            model_name,
            trust_remote_code=trust_remote_code,
            labels=labels or [],
            requested_lane=requested_lane,
            intent=intent,
        )
        self._cache[cache_key] = decision
        return decision

    def hqq_compress_request(
        self,
        model_name: str,
        bits: int = 8,
        group_size: int = 128,
    ) -> ModelIntakeRequest:
        return ModelIntakeRequest(
            operation="hqq_compress",
            model_name=model_name,
            parameters={"bits": bits, "group_size": group_size},
            labels=["hqq", "compression"],
        )

    def ties_merge_request(
        self,
        base_model: str,
        merge_models: List[str],
        sparsity: float = 0.5,
    ) -> ModelIntakeRequest:
        return ModelIntakeRequest(
            operation="ties_merge",
            model_name=base_model,
            parameters={"merge_models": merge_models, "sparsity": sparsity},
            labels=["ties", "merge", "ensemble"],
        )

    def astra_risk_request(
        self,
        model_name: str,
    ) -> ModelIntakeRequest:
        return ModelIntakeRequest(
            operation="astra_risk",
            model_name=model_name,
            parameters={},
            labels=["astra", "risk_assessment"],
        )

    def behavior_control_request(
        self,
        model_name: str,
        *,
        method_class: str = "refusal_vector",
    ) -> ModelIntakeRequest:
        """Create a lab-only request for refusal/filtering behavior analysis."""
        return ModelIntakeRequest(
            operation="behavior_control",
            model_name=model_name,
            parameters={"method_class": method_class},
            labels=["behavior_control", "refusal_analysis"],
        )

    def dry_run_task(self, request: ModelIntakeRequest) -> Dict[str, Any]:
        """Return dry-run result for any model operation."""
        security = self.validate_intake(
            request.model_name,
            labels=request.labels,
            requested_lane="behavior_control" if request.operation == "behavior_control" else "normal",
            intent=request.operation,
        )
        return {
            "operation": request.operation,
            "model": request.model_name,
            "parameters": request.parameters,
            "security_decision": security.to_dict(),
            "route_class": security.route_class,
            "allowed_lanes": list(security.allowed_lanes),
            "dry_run": True,
            "requires_vap": security.severity in ("high", "critical"),
        }


def integrate_with_coordinator(coordinator, model_name: str) -> Dict[str, Any]:
    """Integration point for coordinator dispatch."""
    arena = NexusClawModelArena()
    security = arena.validate_intake(model_name, labels=["benchmark", "evaluation"])
    
    if security.allowed:
        return coordinator.dispatch_dry_run().to_dict()
    
    return {
        "status": "rejected",
        "reason": security.reason,
        "security_severity": security.severity,
        "route_class": security.route_class,
        "blocked_reason": security.blocked_reason,
    }
