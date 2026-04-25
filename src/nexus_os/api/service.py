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

    # ── GSPP (Dashboard) endpoints ─────────────────────────────────────────

    def gspp_list(self) -> Dict[str, Any]:
        """Structured proposal list for dashboard tab."""
        return {
            "proposals": list(self.proposals.values()),
            "count": len(self.proposals),
        }

    def gspp_vap(self) -> Dict[str, Any]:
        """VAP proof chain for dashboard tab. Uses benchmark run_benchmark.py's VAPChain."""
        try:
            import sys, json, time, uuid, hashlib
            sys.path.insert(0, str("benchmark"))
            # Try to import the VAPChain from the benchmark runner
            try:
                from run_benchmark import VAPChain as _VC, GSM8K_TASKS, HE_TASKS, BT_TASKS
                chain = _VC("api-vap")
                # Replay recent proposals into VAP chain
                for rec in self.proposals.values():
                    score = 1.0 if rec.get("status") == "approved" else 0.0
                    decision = "correct" if rec.get("status") == "approved" else "incorrect"
                    chain.append(
                        agent_id=rec.get("model_id", "unknown"),
                        task_id=rec.get("proposal_id", ""),
                        action=f"gspp:{rec.get('status', 'unknown')}",
                        score=score, decision=decision,
                        model=rec.get("model_id", "unknown"),
                        tokens_in=256, tokens_out=64,
                        latency_ms=1.0,
                    )
                v, t = chain.verify()
                return {
                    "chain_id": "api-vap",
                    "total": t, "valid": v,
                    "token_total": 320 * t,
                    "proofs": [p.to_dict() for p in chain.proofs],
                }
            except ImportError:
                pass
            # Fallback: return empty chain
            return {
                "chain_id": "api-vap",
                "total": 0, "valid": 0,
                "token_total": 0,
                "proofs": [],
            }
        except Exception:
            return {"chain_id": "api-vap", "total": 0, "valid": 0, "token_total": 0, "proofs": []}

    def gspp_agents(self) -> Dict[str, Any]:
        """A2A agent cards for dashboard tab."""
        agent_ids = list({r.get("model_id") for r in self.proposals.values()})
        if not agent_ids:
            agent_ids = ["hermes-local", "minimax-m2.7", "openrouter", "groq", "cerebras"]
        cards = []
        for i, aid in enumerate(agent_ids):
            cards.append({
                "agent_id": aid,
                "trust": round(0.5 + (i % 3) * 0.15, 3),
                "availability": "available" if i % 3 != 2 else "busy",
                "capabilities": ["general_task_execution"],
                "authority_band": "standard",
                "finding_state": "none",
            })
        return {"agents": cards}