"""Validation helpers for NEXUS Grok browser-control telemetry.

The browser extension is a convenience controller, not a trust boundary.
Events accepted here are advisory telemetry only; verifier acceptance still
belongs to NEXUS outbox checks and operator review.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ALLOWED_STATUS = {"unknown", "generating", "settling", "idle"}
ALLOWED_ACTIONS = {
    "none",
    "observe_only",
    "continue_drafted",
    "continue_draft_failed",
    "auto_continue_sent",
    "auto_continue_failed",
}
MAX_PREVIEW_CHARS = 500


@dataclass(frozen=True)
class GrokControlDecision:
    accepted: bool
    reason: str
    normalized: dict[str, Any] | None = None
    recommendation: str = "observe"

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "reason": self.reason,
            "normalized": self.normalized,
            "recommendation": self.recommendation,
            "acceptance_scope": "telemetry_only_not_task_acceptance",
        }


def validate_grok_control_event(payload: dict[str, Any]) -> GrokControlDecision:
    if not isinstance(payload, dict):
        return GrokControlDecision(False, "payload_must_be_object")
    if payload.get("kind") != "grok_control_state":
        return GrokControlDecision(False, "kind_must_be_grok_control_state")

    status = str(payload.get("status", "unknown"))
    if status not in ALLOWED_STATUS:
        return GrokControlDecision(False, f"invalid_status:{status}")

    action = str(payload.get("action_taken", "none"))
    if action not in ALLOWED_ACTIONS:
        return GrokControlDecision(False, f"invalid_action:{action}")

    response_chars = _safe_int(payload.get("response_chars"), default=0, minimum=0, maximum=1_000_000)
    continue_count = _safe_int(payload.get("continue_count"), default=0, minimum=0, maximum=100)
    preview = str(payload.get("preview", ""))[:MAX_PREVIEW_CHARS]
    surface_sweep = bool(payload.get("surface_sweep_suspected", False))

    normalized = {
        "kind": "grok_control_state",
        "generated_at": str(payload.get("generated_at", ""))[:64],
        "tab_id": payload.get("tab_id"),
        "url": str(payload.get("url", ""))[:2048],
        "status": status,
        "response_chars": response_chars,
        "continue_count": continue_count,
        "surface_sweep_suspected": surface_sweep,
        "action_taken": action,
        "preview": preview,
    }
    return GrokControlDecision(
        True,
        "accepted_as_telemetry",
        normalized=normalized,
        recommendation=_recommend(status=status, action=action, surface_sweep=surface_sweep),
    )


def _recommend(*, status: str, action: str, surface_sweep: bool) -> str:
    if status == "generating":
        return "wait"
    if surface_sweep and action in {"observe_only", "none"}:
        return "draft_continue_or_assign_concrete_artifact"
    if action == "auto_continue_sent":
        return "wait_for_next_completion"
    if action.endswith("failed"):
        return "operator_review_composer_selector"
    return "observe"


def _safe_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))
