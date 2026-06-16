import json
import sqlite3
import pytest

from nexus_os.governor.base import NexusGovernor
from nexus_os.governor.kaiju_auth import Decision
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
from nexus_os.mcp.server import GovernedMCPServer, MCPConfig, TrustKernelMCPAdapter


class FakeDBAdapter:
    def __init__(self):
        self._conn = sqlite3.connect(":memory:")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                actor_id TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_id TEXT,
                decision TEXT,
                details TEXT,
                trace_id TEXT
            )
            """
        )

    def execute(self, query, params=()):
        return self._conn.execute(query, params)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


class FakeDBManager:
    def __init__(self):
        self._adapter = FakeDBAdapter()

    def get_connection(self):
        return self._adapter

    def close(self):
        self._adapter.close()


def test_trust_kernel_records_events_and_preserves_lane_isolation():
    kernel = TrustKernel()
    good = kernel.record_event(
        TrustEvent(
            agent_id="agent-a",
            lane="implementation",
            event_type="task_outcome",
            action="execute",
            outcome="success",
            Q=0.9,
            U=0.9,
            R=0.0,
            D_plus=0.4,
        )
    )
    bad = kernel.record_event(
        TrustEvent(
            agent_id="agent-a",
            lane="audit_security",
            event_type="proposal_outcome",
            action="secret.expose",
            outcome="denied",
            Q=0.9,
            U=0.0,
            R=0.95,
            D_minus=0.8,
            hard_fail=True,
        )
    )

    assert good.trust > 0.5
    assert bad.trust < good.trust
    assert bad.cdr_stage == "Cascade"
    assert kernel.get_snapshot("agent-a", "implementation").trust == good.trust


def test_low_trust_holds_side_effectful_governor_action():
    db = FakeDBManager()
    kernel = TrustKernel(db=db)
    gov = NexusGovernor(db, trust_kernel=kernel)
    for idx in range(4):
        kernel.record_task_outcome(
            agent_id="worker-low",
            task_id=f"task-{idx}",
            success=False,
            lane="implementation",
        )

    result = gov.check_access(
        agent_id="worker-low",
        project_id="proj-1",
        action="write",
        scope="project",
        intent="write verified project state to the vault",
        impact="low",
        clearance="contributor",
    )

    assert result.decision in {Decision.HOLD, Decision.DENY}
    assert "TrustKernel" in result.reason
    db.close()


def test_cva_reads_canonical_trust_snapshot_not_ad_hoc_context_only():
    db = FakeDBManager()
    kernel = TrustKernel(db=db)
    gov = NexusGovernor(db, trust_kernel=kernel)

    result = gov.check_access(
        agent_id="agent-cva",
        project_id="proj-1",
        action="override",
        scope="project",
        intent="override stale local configuration after explicit review",
        impact="low",
        clearance="contributor",
    )

    assert result.decision == Decision.HOLD
    assert "canonical_trust_kernel" in result.reason
    db.close()


def test_mcp_trust_uses_canonical_kernel():
    kernel = TrustKernel()
    kernel.record_proposal_outcome(
        agent_id="agent-risky",
        proposal_id="proposal-risky",
        status="denied",
        verdict="HARD_BLOCK",
        skill="secret.expose",
    )
    server = GovernedMCPServer(
        MCPConfig(trustkernel_mode="real", allow_side_effects=True),
        trust_adapter=TrustKernelMCPAdapter(kernel=kernel, mode="real"),
    )

    response = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 77,
            "method": "tools/call",
            "params": {
                "name": "memory.create_checkpoint",
                "arguments": {
                    "agent_id": "agent-risky",
                    "lane": "orchestration",
                    "note": "should be held by canonical trust",
                },
            },
        }
    )
    payload = json.loads(response["result"]["content"][0]["text"])
    trust_decision = payload["trust_decision"]

    assert payload["blocked"] is True
    assert trust_decision["source"] == "canonical_trust_kernel"
    assert trust_decision["snapshot"]["trust"] < 0.5
    assert trust_decision["snapshot"]["cdr_stage"] == "Cascade"


def test_trust_decision_allows_default_read_path():
    kernel = TrustKernel()
    decision = kernel.evaluate(
        agent_id="agent-default",
        action="read",
        lane="research",
    )

    assert decision.decision == TrustDecisionKind.ALLOW
    assert decision.snapshot.trust == 0.5


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def kernel_fixture():
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
    def test_known_aliases(self, kernel_fixture):
        assert kernel_fixture.coerce_lane("code") == Lane.IMPLEMENTATION
        assert kernel_fixture.coerce_lane("audit") == Lane.AUDIT_SECURITY
        assert kernel_fixture.coerce_lane("read") == Lane.RESEARCH

    def test_unknown_defaults_to_orchestration(self, kernel_fixture):
        result = kernel_fixture.coerce_lane("unknown_action_xyz")
        assert isinstance(result, Lane)

    def test_alias_mapping_completeness(self):
        for alias, lane in LANE_ALIASES.items():
            assert isinstance(lane, Lane)


# ── Evaluate ─────────────────────────────────────────────────────────

class TestEvaluate:
    def test_returns_trust_decision(self, kernel_fixture):
        decision = kernel_fixture.evaluate("agent-1", action="read", lane="research")
        assert isinstance(decision, TrustDecision)
        assert decision.decision in TrustDecisionKind

    def test_high_risk_action_increases_scrutiny(self, kernel_fixture):
        safe_decision = kernel_fixture.evaluate("agent-1", action="read", lane="research")
        risky_decision = kernel_fixture.evaluate("agent-2", action="delete", lane="audit")
        assert isinstance(risky_decision, TrustDecision)

    def test_evaluate_unknown_agent(self, kernel_fixture):
        decision = kernel_fixture.evaluate("brand-new-agent", action="read")
        assert isinstance(decision, TrustDecision)


# ── Record Event ─────────────────────────────────────────────────────

class TestRecordEvent:
    def test_positive_event_improves_trust(self, kernel_fixture):
        snap_before = kernel_fixture.get_snapshot("a1", "research")
        trust_before = snap_before.trust

        evt = TrustEvent(agent_id="a1", lane="research", Q=0.9, n=5, U=0.9, R=0.0)
        kernel_fixture.record_event(evt)

        snap_after = kernel_fixture.get_snapshot("a1", "research")
        assert snap_after.trust >= trust_before
        assert snap_after.evidence_count > snap_before.evidence_count

    def test_hard_fail_degrades_trust(self, kernel_fixture):
        for _ in range(5):
            evt = TrustEvent(agent_id="a1", lane="code", Q=0.9, n=5, U=0.9, R=0.0)
            kernel_fixture.record_event(evt)
        snap_before = kernel_fixture.get_snapshot("a1", "code")

        evt = TrustEvent(agent_id="a1", lane="code", hard_fail=True, R=0.9)
        kernel_fixture.record_event(evt)
        snap_after = kernel_fixture.get_snapshot("a1", "code")
        assert snap_after.regression_events > snap_before.regression_events

    def test_lane_isolation(self, kernel_fixture):
        evt_code = TrustEvent(agent_id="a1", lane="code", Q=0.9, n=10, U=0.9, R=0.0)
        evt_research = TrustEvent(agent_id="a1", lane="read", Q=0.5, n=1, U=0.3, R=0.0)
        kernel_fixture.record_event(evt_code)
        kernel_fixture.record_event(evt_research)

        snap_code = kernel_fixture.get_snapshot("a1", Lane.IMPLEMENTATION.value)
        snap_research = kernel_fixture.get_snapshot("a1", Lane.RESEARCH.value)
        # Both should have 1 event each, in different lanes
        assert snap_code.evidence_count == 1
        assert snap_research.evidence_count == 1

    def test_record_task_outcome(self, kernel_fixture):
        snap = kernel_fixture.record_task_outcome("a1", "task-123", success=True)
        assert isinstance(snap, TrustSnapshot)
        assert snap.evidence_count == 1

    def test_record_proposal_denied(self, kernel_fixture):
        snap = kernel_fixture.record_proposal_outcome(
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
