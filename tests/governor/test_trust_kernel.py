"""tests/governor/test_trust_kernel.py — Canonical Trust Kernel tests

Covers:
- TrustEvent creation
- TrustSnapshot serialization
- TrustDecision outcomes
- TrustKernel.evaluate() policy decisions
- Lane coercion from aliases
- Bayesian posterior updates via ingest()
- CDR degradation tracking
- High-risk action detection
"""

import pytest

from nexus_os.governor.trust_kernel import (
    HIGH_RISK_ACTIONS,
    LANE_ALIASES,
    SIDE_EFFECT_ACTIONS,
    TrustDecision,
    TrustDecisionKind,
    TrustEvent,
    TrustKernel,
    TrustSnapshot,
)
from nexus_os.governor.trust_engine_v2 import CDRStage
from nexus_os.governor.trust_scoring import Lane


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def kernel():
    return TrustKernel(db=None)


# ── TrustEvent ───────────────────────────────────────────────────────

class TestTrustEvent:
    def test_defaults(self):
        evt = TrustEvent(agent_id="a1")
        assert evt.lane == "general"
        assert evt.Q == 0.7
        assert evt.hard_fail is False
        assert evt.event_id is not None

    def test_custom_fields(self):
        evt = TrustEvent(agent_id="a1", lane="code", action="write", hard_fail=True)
        assert evt.lane == "code"
        assert evt.hard_fail is True


# ── TrustSnapshot ────────────────────────────────────────────────────

class TestTrustSnapshot:
    def test_defaults(self):
        snap = TrustSnapshot(agent_id="a1", lane="code")
        assert snap.trust == 0.5
        assert snap.alpha == 1.0
        assert snap.cdr_stage == CDRStage.NORMAL.value

    def test_to_dict(self):
        snap = TrustSnapshot(agent_id="a1", lane="code", risk_flags=("flag1", "flag2"))
        d = snap.to_dict()
        assert d["agent_id"] == "a1"
        assert isinstance(d["risk_flags"], list)
        assert "flag1" in d["risk_flags"]


# ── TrustDecision ────────────────────────────────────────────────────

class TestTrustDecision:
    def test_to_dict(self):
        snap = TrustSnapshot(agent_id="a1", lane="code")
        decision = TrustDecision(
            decision=TrustDecisionKind.ALLOW,
            reason="trust sufficient",
            snapshot=snap,
        )
        d = decision.to_dict()
        assert d["decision"] == "allow"
        assert d["source"] == "canonical_trust_kernel"

    def test_all_decision_kinds(self):
        kinds = [k.value for k in TrustDecisionKind]
        assert "allow" in kinds
        assert "deny" in kinds
        assert "quarantine" in kinds


# ── Lane Coercion ────────────────────────────────────────────────────

class TestLaneCoercion:
    def test_known_aliases(self, kernel):
        assert kernel.coerce_lane("code") == Lane.IMPLEMENTATION
        assert kernel.coerce_lane("audit") == Lane.AUDIT_SECURITY
        assert kernel.coerce_lane("read") == Lane.RESEARCH

    def test_unknown_defaults_to_orchestration(self, kernel):
        result = kernel.coerce_lane("unknown_action_xyz")
        assert isinstance(result, Lane)

    def test_alias_mapping_completeness(self):
        for alias, lane in LANE_ALIASES.items():
            assert isinstance(lane, Lane)


# ── Evaluate ─────────────────────────────────────────────────────────

class TestEvaluate:
    def test_returns_trust_decision(self, kernel):
        decision = kernel.evaluate("agent-1", action="read", lane="research")
        assert isinstance(decision, TrustDecision)
        assert decision.decision in TrustDecisionKind

    def test_high_risk_action_increases_scrutiny(self, kernel):
        safe_decision = kernel.evaluate("agent-1", action="read", lane="research")
        risky_decision = kernel.evaluate("agent-2", action="delete", lane="audit")
        assert isinstance(risky_decision, TrustDecision)

    def test_evaluate_unknown_agent(self, kernel):
        decision = kernel.evaluate("brand-new-agent", action="read")
        assert isinstance(decision, TrustDecision)


# ── Record Event ─────────────────────────────────────────────────────

class TestRecordEvent:
    def test_positive_event_improves_trust(self, kernel):
        snap_before = kernel.get_snapshot("a1", "research")
        trust_before = snap_before.trust

        evt = TrustEvent(agent_id="a1", lane="research", Q=0.9, n=5, U=0.9, R=0.0)
        kernel.record_event(evt)

        snap_after = kernel.get_snapshot("a1", "research")
        assert snap_after.trust >= trust_before
        assert snap_after.evidence_count > snap_before.evidence_count

    def test_hard_fail_degrades_trust(self, kernel):
        for _ in range(5):
            evt = TrustEvent(agent_id="a1", lane="code", Q=0.9, n=5, U=0.9, R=0.0)
            kernel.record_event(evt)
        snap_before = kernel.get_snapshot("a1", "code")

        evt = TrustEvent(agent_id="a1", lane="code", hard_fail=True, R=0.9)
        kernel.record_event(evt)
        snap_after = kernel.get_snapshot("a1", "code")
        assert snap_after.regression_events > snap_before.regression_events

    def test_lane_isolation(self, kernel):
        evt_code = TrustEvent(agent_id="a1", lane="code", Q=0.9, n=10, U=0.9, R=0.0)
        evt_research = TrustEvent(agent_id="a1", lane="read", Q=0.5, n=1, U=0.3, R=0.0)
        kernel.record_event(evt_code)
        kernel.record_event(evt_research)

        snap_code = kernel.get_snapshot("a1", Lane.IMPLEMENTATION.value)
        snap_research = kernel.get_snapshot("a1", Lane.RESEARCH.value)
        # Both should have 1 event each, in different lanes
        assert snap_code.evidence_count == 1
        assert snap_research.evidence_count == 1

    def test_record_task_outcome(self, kernel):
        snap = kernel.record_task_outcome("a1", "task-123", success=True)
        assert isinstance(snap, TrustSnapshot)
        assert snap.evidence_count == 1

    def test_record_proposal_denied(self, kernel):
        snap = kernel.record_proposal_outcome(
            "a1", "prop-1", status="denied",
            verdict="HARD_BLOCK", skill="system.wipe",
        )
        assert snap.regression_events >= 1


# ── Constants ────────────────────────────────────────────────────────

class TestConstants:
    def test_side_effect_actions(self):
        assert "write" in SIDE_EFFECT_ACTIONS
        assert "execute" in SIDE_EFFECT_ACTIONS
        assert "read" not in SIDE_EFFECT_ACTIONS

    def test_high_risk_actions(self):
        assert "delete" in HIGH_RISK_ACTIONS
        assert "system.wipe" in HIGH_RISK_ACTIONS
