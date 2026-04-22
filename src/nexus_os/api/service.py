"""Pure governance API service logic.

This module intentionally avoids FastAPI imports so the decision path can be
tested in environments where the async runtime is unavailable.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from nexus_os.db.manager import DBConfig, DatabaseManager
from nexus_os.governor.base import NexusGovernor
from nexus_os.governor.kaiju_auth import Decision


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def proposal_status_from_decision(decision: Decision) -> str:
    """Map Governor decisions to proposal lifecycle states."""
    if decision == Decision.ALLOW:
        return "approved"
    if decision == Decision.DENY:
        return "rejected"
    if decision == Decision.HOLD:
        return "held"
    return "halted"


class GovernanceAPIState:
    """Stateful proposal registry backed by the canonical NexusGovernor."""

    def __init__(self, db_path: str = "nexus_api.db"):
        self.db = DatabaseManager(
            DBConfig(
                db_path=db_path,
                passphrase="",
                encrypted=False,
                allow_unencrypted=True,
            )
        )
        self.db.setup_schema()
        self.governor = NexusGovernor(self.db)
        self.proposals: Dict[str, Dict[str, Any]] = {}

    def close(self) -> None:
        self.db.close()

    def audit_count(self) -> int:
        try:
            adapter = self.db.get_connection()
            cursor = adapter.execute("SELECT COUNT(*) FROM audit_logs")
            row = adapter.fetchone(cursor)
            return int(row[0]) if row else 0
        except Exception:
            return 0

    def propose_skill(
        self,
        *,
        proposal_id: str,
        model_id: str,
        skill: Optional[Dict[str, Any]],
        rationale: str,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        if proposal_id in self.proposals:
            raise ValueError(f"Proposal already exists: {proposal_id}")

        skill_data = skill or {}
        result = self.governor.check_access(
            agent_id=str(skill_data.get("agent_id") or model_id),
            project_id=str(skill_data.get("project_id") or "nexus-os"),
            action=str(skill_data.get("action") or "execute"),
            scope=str(skill_data.get("scope") or "project"),
            intent=rationale,
            impact=str(skill_data.get("impact") or "low"),
            clearance=str(skill_data.get("clearance") or "contributor"),
            trace_id=proposal_id,
            context={
                "proposal_id": proposal_id,
                "model_id": model_id,
                "skill": skill_data,
                "timestamp": timestamp or utc_now(),
            },
        )
        record = {
            "proposal_id": proposal_id,
            "model_id": model_id,
            "skill": skill_data,
            "rationale": rationale,
            "timestamp": timestamp or utc_now(),
            "status": proposal_status_from_decision(result.decision),
            "decision": result.decision.value,
            "reason": result.reason,
            "trace_id": result.trace_id,
            "review": None,
        }
        self.proposals[proposal_id] = record
        return record

    def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        return self.proposals.get(proposal_id)

    def list_proposals(self) -> Dict[str, Any]:
        return {
            "count": len(self.proposals),
            "proposals": list(self.proposals.values()),
        }

    def review_proposal(
        self,
        *,
        proposal_id: str,
        decision: str,
        reviewer: str = "speci",
        reason: str = "",
    ) -> Optional[Dict[str, Any]]:
        record = self.proposals.get(proposal_id)
        if record is None:
            return None

        if decision == "approve":
            record["status"] = "approved"
            record["decision"] = "allow"
        elif decision == "reject":
            record["status"] = "rejected"
            record["decision"] = "deny"
        elif decision == "hold":
            record["status"] = "held"
            record["decision"] = "hold"
        else:
            raise ValueError("decision must be approve, reject, or hold")

        record["review"] = {
            "reviewer": reviewer,
            "reason": reason,
            "reviewed_at": utc_now(),
        }
        return record

    def dashboard_stats(self) -> Dict[str, Any]:
        counts = Counter(record["status"] for record in self.proposals.values())
        return {
            "status": "operational",
            "service": "nexus-governance-api",
            "proposal_count": len(self.proposals),
            "approved": counts.get("approved", 0),
            "rejected": counts.get("rejected", 0),
            "held": counts.get("held", 0),
            "audit_entries": self.audit_count(),
        }
