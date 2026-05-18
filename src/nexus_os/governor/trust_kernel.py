"""Canonical trust control plane for Nexus OS.

This module unifies the existing lane-scoped trust formula, Bayesian
reputation memory, and HARDWALL/CDR-style degradation into one runtime API.
It is intentionally small: callers emit TrustEvent records and read
TrustSnapshot/TrustDecision objects. They should not maintain competing trust
scores.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from nexus_os.governor.trust_engine_v2 import CDRStage
from nexus_os.governor.trust_scoring import (
    AgentStatus,
    FindingState,
    Lane,
    ScoringInput,
    compute_score,
)

logger = logging.getLogger(__name__)


class TrustDecisionKind(Enum):
    ALLOW = "allow"
    HOLD = "hold"
    DENY = "deny"
    QUARANTINE = "quarantine"
    ESCALATE = "escalate"


SIDE_EFFECT_ACTIONS = {"write", "delete", "execute", "override", "deploy", "run"}
HIGH_RISK_ACTIONS = {"delete", "override", "escalate", "root", "wipe", "system.wipe"}

LANE_ALIASES = {
    "general": Lane.ORCHESTRATION,
    "audit": Lane.AUDIT_SECURITY,
    "audit_sec": Lane.AUDIT_SECURITY,
    "security": Lane.AUDIT_SECURITY,
    "code": Lane.IMPLEMENTATION,
    "code_gen": Lane.IMPLEMENTATION,
    "data_ops": Lane.IMPLEMENTATION,
    "realtime": Lane.ORCHESTRATION,
    "autonomous": Lane.ORCHESTRATION,
    "tasks_submit": Lane.IMPLEMENTATION,
    "tasks/submit": Lane.IMPLEMENTATION,
    "tasks_result": Lane.REVIEW,
    "tasks/result": Lane.REVIEW,
    "read": Lane.RESEARCH,
    "write": Lane.IMPLEMENTATION,
    "execute": Lane.IMPLEMENTATION,
    "run": Lane.IMPLEMENTATION,
    "deploy": Lane.IMPLEMENTATION,
    "delete": Lane.AUDIT_SECURITY,
    "override": Lane.AUDIT_SECURITY,
    "escalate": Lane.AUDIT_SECURITY,
    "vault_write": Lane.IMPLEMENTATION,
    "vault/write": Lane.IMPLEMENTATION,
    "vault_read": Lane.RESEARCH,
    "vault/read": Lane.RESEARCH,
}


@dataclass
class TrustEvent:
    """Immutable event input for canonical trust updates."""

    agent_id: str
    lane: str = "general"
    event_type: str = "generic"
    action: str = ""
    outcome: str = "observed"
    Q: float = 0.7
    n: int = 1
    U: float = 0.5
    R: float = 0.0
    D_plus: float = 0.0
    D_minus: float = 0.0
    hard_fail: bool = False
    source: str = "trust_kernel"
    provenance: str = "local"
    metadata: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TrustSnapshot:
    """Current canonical trust state for one agent/lane pair."""

    agent_id: str
    lane: str
    trust: float = 0.5
    alpha: float = 1.0
    beta: float = 1.0
    evidence_count: int = 0
    latest_score: Optional[float] = None
    latest_qeff: float = 0.0
    finding_state: str = FindingState.NONE.value
    cdr_stage: str = CDRStage.NORMAL.value
    cdr_severity: int = 0
    regression_events: int = 0
    authority_band: str = "standard"
    last_event_id: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    risk_flags: Tuple[str, ...] = field(default_factory=tuple)
    source: str = "canonical_trust_kernel"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["risk_flags"] = list(self.risk_flags)
        return data


@dataclass
class TrustDecision:
    """Policy decision returned to Governor/KAIJU callers."""

    decision: TrustDecisionKind
    reason: str
    snapshot: TrustSnapshot
    policy: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "snapshot": self.snapshot.to_dict(),
            "policy": self.policy,
            "source": "canonical_trust_kernel",
        }


class TrustKernel:
    """Canonical event-sourced trust kernel.

    The kernel preserves the existing NEXUS lane formula as the event scorer,
    then maintains a Bayesian posterior as the durable trust state. CDR is kept
    as a degradation state derived from hard failures, regressions, and low
    posterior trust.
    """

    def __init__(self, db: Any = None):
        self.db = db
        self._snapshots: Dict[Tuple[str, str], TrustSnapshot] = {}
        self._storage_available = True
        self._ensure_storage()

    def evaluate(
        self,
        agent_id: str,
        action: str,
        lane: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> TrustDecision:
        ctx = context or {}
        lane_enum = self.coerce_lane(lane or ctx.get("lane") or action)
        snapshot = self.get_snapshot(agent_id, lane_enum.value)
        action_lower = (action or "").lower()
        side_effect = action_lower in SIDE_EFFECT_ACTIONS or ctx.get("side_effect") is True
        high_risk = action_lower in HIGH_RISK_ACTIONS or ctx.get("high_risk") is True

        policy = {
            "lane": lane_enum.value,
            "side_effect": side_effect,
            "high_risk": high_risk,
            "requested_clearance": ctx.get("requested_clearance"),
            "requested_impact": ctx.get("requested_impact"),
            "max_clearance": "reader" if snapshot.authority_band == "restricted" else None,
            "max_impact": "low" if snapshot.authority_band == "restricted" else None,
        }

        if ctx.get("trust_hard_fail") is True:
            return TrustDecision(
                TrustDecisionKind.DENY,
                "TrustKernel DENY: request carried trust_hard_fail",
                snapshot,
                {**policy, "trigger": "context_hard_fail"},
            )

        if snapshot.cdr_stage == CDRStage.COLLAPSE.value:
            return TrustDecision(
                TrustDecisionKind.DENY,
                "TrustKernel DENY: agent is in CDR COLLAPSE",
                snapshot,
                {**policy, "trigger": "cdr_collapse"},
            )

        if snapshot.cdr_stage == CDRStage.CASCADE.value and side_effect:
            return TrustDecision(
                TrustDecisionKind.QUARANTINE,
                "TrustKernel QUARANTINE: CDR CASCADE blocks side-effectful action",
                snapshot,
                {**policy, "trigger": "cdr_cascade"},
            )

        if snapshot.finding_state == FindingState.ESCALATED.value and side_effect:
            return TrustDecision(
                TrustDecisionKind.ESCALATE,
                "TrustKernel ESCALATE: latest trust finding is escalated",
                snapshot,
                {**policy, "trigger": "finding_escalated"},
            )

        if snapshot.trust < 0.20 and side_effect:
            return TrustDecision(
                TrustDecisionKind.DENY,
                f"TrustKernel DENY: trust={snapshot.trust:.2f} below side-effect floor",
                snapshot,
                {**policy, "trigger": "trust_floor"},
            )

        if snapshot.trust < 0.35 and side_effect:
            return TrustDecision(
                TrustDecisionKind.HOLD,
                f"TrustKernel HOLD: trust={snapshot.trust:.2f} requires human review",
                snapshot,
                {**policy, "trigger": "low_trust"},
            )

        if snapshot.authority_band == "restricted" and (side_effect or high_risk):
            return TrustDecision(
                TrustDecisionKind.HOLD,
                "TrustKernel HOLD: restricted authority band cannot run this action",
                snapshot,
                {**policy, "trigger": "authority_band"},
            )

        if high_risk and snapshot.trust < 0.45:
            return TrustDecision(
                TrustDecisionKind.HOLD,
                f"TrustKernel HOLD: high-risk action needs stronger trust ({snapshot.trust:.2f})",
                snapshot,
                {**policy, "trigger": "high_risk_low_trust"},
            )

        return TrustDecision(
            TrustDecisionKind.ALLOW,
            f"TrustKernel ALLOW: trust={snapshot.trust:.2f}, lane={lane_enum.value}",
            snapshot,
            policy,
        )

    def record_event(self, event: TrustEvent) -> TrustSnapshot:
        lane_enum = self.coerce_lane(event.lane)
        previous = self.get_snapshot(event.agent_id, lane_enum.value)
        evidence_n = max(int(event.n or 1), previous.evidence_count + 1)
        scoring_input = ScoringInput(
            status=AgentStatus.ACTIVE,
            lane=lane_enum,
            Q=self._clamp(event.Q),
            n=evidence_n,
            U=self._clamp(event.U),
            R=self._clamp(event.R),
            D_plus=self._clamp(event.D_plus),
            D_minus=self._clamp(event.D_minus),
            hard_fail=event.hard_fail,
        )
        score = compute_score(scoring_input)

        alpha = previous.alpha
        beta = previous.beta
        weight = max(score.Qeff, min(max(event.Q, 0.0), 1.0) * 0.5, 0.10)
        if score.score is not None:
            alpha += weight * max(score.score, 0.0)
            beta += weight * (max(-score.score, 0.0) + (0.5 if event.hard_fail else 0.0))
        elif score.finding_state == FindingState.HELD:
            beta += weight * max(event.R, 0.1)

        trust = alpha / (alpha + beta) if (alpha + beta) else 0.5
        regression = event.hard_fail or (score.score is not None and score.score < 0) or score.finding_state in {
            FindingState.HELD,
            FindingState.ESCALATED,
        }
        regression_events = previous.regression_events + (1 if regression else 0)
        cdr_stage = self._derive_cdr_stage(previous, trust, regression_events, event, score.finding_state)
        authority_band = self._derive_authority_band(trust, cdr_stage, regression_events)
        flags = self._derive_risk_flags(event, score.finding_state, cdr_stage)

        snapshot = TrustSnapshot(
            agent_id=event.agent_id,
            lane=lane_enum.value,
            trust=round(trust, 4),
            alpha=round(alpha, 6),
            beta=round(beta, 6),
            evidence_count=previous.evidence_count + 1,
            latest_score=round(score.score, 6) if score.score is not None else None,
            latest_qeff=round(score.Qeff, 6),
            finding_state=score.finding_state.value,
            cdr_stage=cdr_stage.value,
            cdr_severity=cdr_stage.severity,
            regression_events=regression_events,
            authority_band=authority_band,
            last_event_id=event.event_id,
            last_updated=datetime.now(timezone.utc).isoformat(),
            risk_flags=tuple(flags),
        )

        self._snapshots[(event.agent_id, lane_enum.value)] = snapshot
        self._persist_event(event, score.score, score.Qeff, score.finding_state.value)
        self._persist_snapshot(snapshot)
        return snapshot

    def record_task_outcome(
        self,
        agent_id: str,
        task_id: str,
        success: bool,
        lane: str = "implementation",
        error: Optional[str] = None,
        source: str = "task_executor",
    ) -> TrustSnapshot:
        return self.record_event(
            TrustEvent(
                agent_id=agent_id,
                lane=lane,
                event_type="task_outcome",
                action="execute",
                outcome="success" if success else "failure",
                Q=0.8,
                U=0.7 if success else 0.0,
                R=0.0 if success else 0.75,
                D_plus=0.3 if success else 0.0,
                D_minus=0.0 if success else 0.8,
                hard_fail=False,
                source=source,
                metadata={"task_id": task_id, "error": error},
            )
        )

    def record_proposal_outcome(
        self,
        agent_id: str,
        proposal_id: str,
        status: str,
        verdict: str,
        skill: str,
        lane: str = "orchestration",
        source: str = "governance_mcp",
    ) -> TrustSnapshot:
        denied = status == "denied"
        held = status == "needs_review"
        hard_fail = verdict in {"HARD_BLOCK", "TRUST_DENY"} or skill in {
            "model.delete",
            "secret.expose",
            "fine_tune.auto",
            "system.wipe",
        }
        return self.record_event(
            TrustEvent(
                agent_id=agent_id,
                lane=lane,
                event_type="proposal_outcome",
                action=skill,
                outcome=status,
                Q=0.85 if denied or held else 0.65,
                U=0.25 if status == "approved" else 0.0,
                R=0.95 if hard_fail else (0.65 if denied else (0.4 if held else 0.0)),
                D_plus=0.2 if status == "approved" else 0.0,
                D_minus=0.6 if denied else (0.25 if held else 0.0),
                hard_fail=hard_fail,
                source=source,
                metadata={"proposal_id": proposal_id, "verdict": verdict, "skill": skill},
            )
        )

    def get_snapshot(self, agent_id: str, lane: str = "general") -> TrustSnapshot:
        lane_enum = self.coerce_lane(lane)
        key = (agent_id, lane_enum.value)
        if key in self._snapshots:
            return self._snapshots[key]
        loaded = self._load_snapshot(agent_id, lane_enum.value)
        if loaded is not None:
            self._snapshots[key] = loaded
            return loaded
        snapshot = TrustSnapshot(agent_id=agent_id, lane=lane_enum.value)
        self._snapshots[key] = snapshot
        return snapshot

    @staticmethod
    def coerce_lane(lane: Optional[str]) -> Lane:
        if isinstance(lane, Lane):
            return lane
        raw = (lane or "general").lower().replace("-", "_")
        if raw in LANE_ALIASES:
            return LANE_ALIASES[raw]
        for candidate in Lane:
            if candidate.value == raw:
                return candidate
        return Lane.ORCHESTRATION

    def _derive_cdr_stage(
        self,
        previous: TrustSnapshot,
        trust: float,
        regression_events: int,
        event: TrustEvent,
        finding_state: FindingState,
    ) -> CDRStage:
        previous_stage = CDRStage(previous.cdr_stage)
        if trust < 0.15:
            return CDRStage.COLLAPSE
        if event.hard_fail:
            return CDRStage.CASCADE
        if finding_state == FindingState.ESCALATED:
            return max(previous_stage, CDRStage.OUTPUT_HALLUCINATION, key=lambda s: s.severity)
        if regression_events >= 5:
            return max(previous_stage, CDRStage.MEMORY_CORRUPTION, key=lambda s: s.severity)
        if trust < 0.30:
            return max(previous_stage, CDRStage.DEGRADED_REASONING, key=lambda s: s.severity)
        if trust > 0.55 and previous_stage.severity <= CDRStage.DEGRADED_REASONING.severity:
            return CDRStage.NORMAL
        return previous_stage

    @staticmethod
    def _derive_authority_band(trust: float, cdr_stage: CDRStage, regression_events: int) -> str:
        if trust >= 0.75 and cdr_stage == CDRStage.NORMAL and regression_events == 0:
            return "elevated"
        if trust < 0.40 or cdr_stage.severity >= CDRStage.DEGRADED_REASONING.severity:
            return "restricted"
        return "standard"

    @staticmethod
    def _derive_risk_flags(event: TrustEvent, finding_state: FindingState, cdr_stage: CDRStage) -> list:
        flags = []
        if event.hard_fail:
            flags.append("hard_fail")
        if event.R >= 0.7:
            flags.append("high_regression")
        if finding_state in {FindingState.HELD, FindingState.ESCALATED}:
            flags.append(finding_state.value)
        if cdr_stage != CDRStage.NORMAL:
            flags.append("cdr_" + cdr_stage.name.lower())
        return flags

    def _ensure_storage(self) -> None:
        conn = self._connection()
        if conn is None:
            return
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS trust_events (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    lane TEXT NOT NULL,
                    event_type TEXT,
                    action TEXT,
                    outcome TEXT,
                    score REAL,
                    qeff REAL,
                    finding_state TEXT,
                    hard_fail INTEGER,
                    source TEXT,
                    provenance TEXT,
                    ts TEXT,
                    payload_json TEXT
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS trust_snapshots (
                    agent_id TEXT NOT NULL,
                    lane TEXT NOT NULL,
                    trust REAL NOT NULL,
                    alpha REAL NOT NULL,
                    beta REAL NOT NULL,
                    evidence_count INTEGER NOT NULL,
                    latest_score REAL,
                    latest_qeff REAL,
                    finding_state TEXT,
                    cdr_stage TEXT,
                    cdr_severity INTEGER,
                    regression_events INTEGER,
                    authority_band TEXT,
                    last_event_id TEXT,
                    last_updated TEXT,
                    risk_flags_json TEXT,
                    source TEXT,
                    PRIMARY KEY (agent_id, lane)
                )"""
            )
            self._commit(conn)
        except Exception as exc:
            logger.warning("TrustKernel storage unavailable: %s", exc)
            self._storage_available = False

    def _persist_event(
        self,
        event: TrustEvent,
        score: Optional[float],
        qeff: float,
        finding_state: str,
    ) -> None:
        conn = self._connection()
        if conn is None or not self._storage_available:
            return
        try:
            conn.execute(
                """INSERT OR REPLACE INTO trust_events
                   (id, agent_id, lane, event_type, action, outcome, score, qeff,
                    finding_state, hard_fail, source, provenance, ts, payload_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.event_id,
                    event.agent_id,
                    self.coerce_lane(event.lane).value,
                    event.event_type,
                    event.action,
                    event.outcome,
                    score,
                    qeff,
                    finding_state,
                    1 if event.hard_fail else 0,
                    event.source,
                    event.provenance,
                    event.created_at,
                    json.dumps(event.metadata, sort_keys=True),
                ),
            )
            self._commit(conn)
        except Exception as exc:
            logger.warning("TrustKernel failed to persist event: %s", exc)

    def _persist_snapshot(self, snapshot: TrustSnapshot) -> None:
        conn = self._connection()
        if conn is None or not self._storage_available:
            return
        try:
            conn.execute(
                """INSERT OR REPLACE INTO trust_snapshots
                   (agent_id, lane, trust, alpha, beta, evidence_count,
                    latest_score, latest_qeff, finding_state, cdr_stage,
                    cdr_severity, regression_events, authority_band,
                    last_event_id, last_updated, risk_flags_json, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    snapshot.agent_id,
                    snapshot.lane,
                    snapshot.trust,
                    snapshot.alpha,
                    snapshot.beta,
                    snapshot.evidence_count,
                    snapshot.latest_score,
                    snapshot.latest_qeff,
                    snapshot.finding_state,
                    snapshot.cdr_stage,
                    snapshot.cdr_severity,
                    snapshot.regression_events,
                    snapshot.authority_band,
                    snapshot.last_event_id,
                    snapshot.last_updated,
                    json.dumps(list(snapshot.risk_flags)),
                    snapshot.source,
                ),
            )
            self._commit(conn)
        except Exception as exc:
            logger.warning("TrustKernel failed to persist snapshot: %s", exc)

    def _load_snapshot(self, agent_id: str, lane: str) -> Optional[TrustSnapshot]:
        conn = self._connection()
        if conn is None or not self._storage_available:
            return None
        try:
            row = conn.execute(
                """SELECT agent_id, lane, trust, alpha, beta, evidence_count,
                          latest_score, latest_qeff, finding_state, cdr_stage,
                          cdr_severity, regression_events, authority_band,
                          last_event_id, last_updated, risk_flags_json, source
                   FROM trust_snapshots WHERE agent_id=? AND lane=?""",
                (agent_id, lane),
            ).fetchone()
            if row is None:
                return None
            risk_flags = json.loads(self._row_get(row, "risk_flags_json", 15) or "[]")
            return TrustSnapshot(
                agent_id=self._row_get(row, "agent_id", 0),
                lane=self._row_get(row, "lane", 1),
                trust=float(self._row_get(row, "trust", 2)),
                alpha=float(self._row_get(row, "alpha", 3)),
                beta=float(self._row_get(row, "beta", 4)),
                evidence_count=int(self._row_get(row, "evidence_count", 5)),
                latest_score=self._row_get(row, "latest_score", 6),
                latest_qeff=float(self._row_get(row, "latest_qeff", 7) or 0.0),
                finding_state=self._row_get(row, "finding_state", 8) or FindingState.NONE.value,
                cdr_stage=self._row_get(row, "cdr_stage", 9) or CDRStage.NORMAL.value,
                cdr_severity=int(self._row_get(row, "cdr_severity", 10) or 0),
                regression_events=int(self._row_get(row, "regression_events", 11) or 0),
                authority_band=self._row_get(row, "authority_band", 12) or "standard",
                last_event_id=self._row_get(row, "last_event_id", 13),
                last_updated=self._row_get(row, "last_updated", 14) or datetime.now(timezone.utc).isoformat(),
                risk_flags=tuple(risk_flags),
                source=self._row_get(row, "source", 16) or "canonical_trust_kernel",
            )
        except Exception as exc:
            logger.warning("TrustKernel failed to load snapshot: %s", exc)
            return None

    def _connection(self):
        if self.db is None:
            return None
        if hasattr(self.db, "get_connection"):
            return self.db.get_connection()
        return self.db

    @staticmethod
    def _commit(conn) -> None:
        if hasattr(conn, "commit"):
            conn.commit()

    @staticmethod
    def _row_get(row, key: str, index: int):
        try:
            return row[key]
        except Exception:
            return row[index]

    @staticmethod
    def _clamp(value: float) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0
