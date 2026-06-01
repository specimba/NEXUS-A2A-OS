import sqlite3

from nexus_os.governor.base import NexusGovernor
from nexus_os.governor.kaiju_auth import Decision
from nexus_os.governor.trust_kernel import (
    TrustDecisionKind,
    TrustEvent,
    TrustKernel,
)
from nexus_os.mcp.server import NexusGovernanceMCP


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


def test_mcp_trust_uses_canonical_kernel(tmp_path):
    db_path = tmp_path / "governance.db"
    engine = NexusGovernanceMCP(db_path=str(db_path))

    proposal = engine.propose_skill(
        "secret.expose",
        {},
        "agent-risky",
        provenance="pytest",
    )
    trust = engine.get_trust("agent-risky", "orchestration")

    assert proposal["status"] == "denied"
    assert trust["source"] == "canonical_trust_kernel"
    assert trust["trust_snapshot"]["trust"] < 0.5
    assert trust["trust_snapshot"]["cdr_stage"] == "Cascade"
    engine.close()


def test_trust_decision_allows_default_read_path():
    kernel = TrustKernel()
    decision = kernel.evaluate(
        agent_id="agent-default",
        action="read",
        lane="research",
    )

    assert decision.decision == TrustDecisionKind.ALLOW
    assert decision.snapshot.trust == 0.5
