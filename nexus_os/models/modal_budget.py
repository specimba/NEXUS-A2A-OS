"""Modal budget and run-safety contracts for NEXUS model experiments.

The default policy is deliberately conservative: one bounded experiment,
scale-to-zero, no background model polling, and explicit artifact evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DEFAULT_PILOT_BUDGET_USD = 40.0


@dataclass(frozen=True)
class ModalRunContract:
    """Operator-approved Modal run constraints."""

    max_spend_usd: float = DEFAULT_PILOT_BUDGET_USD
    min_containers: int = 0
    background_polling: bool = False
    broad_model_health_checks: bool = False
    volume_cleanup_required: bool = True
    per_run_cost_summary_required: bool = True
    artifact_manifest_required: bool = True
    allowed_operations: tuple[str, ...] = ("eval_only", "fine_tune", "distill", "probe")
    notes: list[str] = field(default_factory=list)

    def validate(self) -> dict[str, Any]:
        errors: list[str] = []
        if self.max_spend_usd > DEFAULT_PILOT_BUDGET_USD:
            errors.append(f"max_spend_usd must be <= {DEFAULT_PILOT_BUDGET_USD}")
        if self.max_spend_usd <= 0:
            errors.append("max_spend_usd must be positive")
        if self.min_containers != 0:
            errors.append("min_containers must be 0 to avoid surprise always-on spend")
        if self.background_polling:
            errors.append("background_polling must be disabled")
        if self.broad_model_health_checks:
            errors.append("broad_model_health_checks must be disabled")
        if not self.volume_cleanup_required:
            errors.append("volume_cleanup_required must be true")
        if not self.per_run_cost_summary_required:
            errors.append("per_run_cost_summary_required must be true")
        if not self.artifact_manifest_required:
            errors.append("artifact_manifest_required must be true")
        return {
            "passed": not errors,
            "max_spend_usd": self.max_spend_usd,
            "errors": errors,
        }


def validate_modal_run_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate a Modal run config dict against the NEXUS pilot contract."""
    allowed = set(ModalRunContract().allowed_operations)
    operation = config.get("operation")
    errors: list[str] = []
    if operation not in allowed:
        errors.append(f"operation must be one of {sorted(allowed)}")

    contract = ModalRunContract(
        max_spend_usd=float(config.get("max_spend_usd", DEFAULT_PILOT_BUDGET_USD)),
        min_containers=int(config.get("min_containers", 0)),
        background_polling=bool(config.get("background_polling", False)),
        broad_model_health_checks=bool(config.get("broad_model_health_checks", False)),
        volume_cleanup_required=bool(config.get("volume_cleanup_required", True)),
        per_run_cost_summary_required=bool(config.get("per_run_cost_summary_required", True)),
        artifact_manifest_required=bool(config.get("artifact_manifest_required", True)),
    )
    report = contract.validate()
    errors.extend(report["errors"])
    report["operation"] = operation
    report["passed"] = not errors
    report["errors"] = errors
    return report
