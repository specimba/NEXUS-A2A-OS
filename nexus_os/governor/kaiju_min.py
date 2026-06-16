"""Minimal KAIJU Auth — Lightweight 4-var gate for relay/GMR calls."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class KaijuDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    HOLD = "hold"


@dataclass
class KaijuResult:
    decision: KaijuDecision
    reason: str = ""
    scope_ok: bool = True
    intent_ok: bool = True
    impact_ok: bool = True
    clearance_ok: bool = True


ALLOWED_INTENTS = {"chat", "model_chat", "query", "read", "infer", "generate", "complete", "embed"}
SENSITIVE_ACTIONS = {"delete", "write", "override", "deploy", "execute", "admin"}
SENSITIVE_SCOPES = {"system", "cross_project"}


def kaiju_check(agent_id: str = "relay", action: str = "model_chat", scope: str = "project", intent: str = "chat", impact: str = "low", clearance: str = "contributor") -> KaijuResult:
    scope_ok = scope not in SENSITIVE_SCOPES or clearance in ("admin", "maintainer")
    intent_ok = intent in ALLOWED_INTENTS or clearance in ("admin", "maintainer")
    impact_ok = impact in ("low", "medium") or clearance in ("admin", "maintainer")
    clearance_ok = clearance in ("contributor", "maintainer", "admin")
    if action in SENSITIVE_ACTIONS and clearance not in ("admin", "maintainer"):
        return KaijuResult(KaijuDecision.DENY, f"Action '{action}' requires admin clearance", scope_ok, intent_ok, impact_ok, clearance_ok)
    if not scope_ok:
        return KaijuResult(KaijuDecision.DENY, f"Scope '{scope}' exceeds clearance '{clearance}'", scope_ok, intent_ok, impact_ok, clearance_ok)
    if not intent_ok:
        return KaijuResult(KaijuDecision.HOLD, f"Intent '{intent}' requires human review", scope_ok, intent_ok, impact_ok, clearance_ok)
    if not impact_ok:
        return KaijuResult(KaijuDecision.HOLD, f"Impact '{impact}' requires human review", scope_ok, intent_ok, impact_ok, clearance_ok)
    return KaijuResult(KaijuDecision.ALLOW, "All checks passed")
