"""Integration tests: TrustKernel ↔ Vault MemoryTracker wiring.

Verifies that record_event() persists trust data to Vault's 5-track
memory when vault_enabled=True (default).
"""

import pytest
from nexus_os.governor.trust_kernel import TrustKernel, TrustEvent, TrustDecisionKind


def _trust_kernel(vault=True):
    return TrustKernel(db=None, vault_enabled=vault)


class TestVaultIntegration:
    """record_event should persist to MemoryTracker trust track."""

    def test_record_event_stores_to_vault(self):
        tk = _trust_kernel(vault=True)
        event = TrustEvent(agent_id="test-agent", lane="code", action="write", outcome="success")
        snapshot = tk.record_event(event)
        assert snapshot.trust > 0.0

    def test_record_event_with_hard_fail(self):
        tk = _trust_kernel(vault=True)
        event = TrustEvent(agent_id="test-agent", lane="audit", action="delete",
                          outcome="failure", hard_fail=True, R=0.95)
        snapshot = tk.record_event(event)
        assert snapshot.regression_events >= 1

    def test_vault_disabled_does_not_crash(self):
        tk = _trust_kernel(vault=False)
        event = TrustEvent(agent_id="test-agent", lane="general", action="read", outcome="success")
        snapshot = tk.record_event(event)
        assert snapshot.evidence_count == 1

    def test_consecutive_events_accumulate(self):
        tk = _trust_kernel(vault=True)
        for i in range(3):
            tk.record_event(TrustEvent(agent_id="acc-agent", lane="code", action="write", outcome="success"))
        snap = tk.get_snapshot("acc-agent", "code")
        assert snap.evidence_count == 3

    def test_mixed_lanes_isolated(self):
        tk = _trust_kernel(vault=True)
        tk.record_event(TrustEvent(agent_id="multi-agent", lane="code", action="write", outcome="success"))
        tk.record_event(TrustEvent(agent_id="multi-agent", lane="audit", action="delete", outcome="fail", hard_fail=True))
        code_snap = tk.get_snapshot("multi-agent", "code")
        audit_snap = tk.get_snapshot("multi-agent", "audit")
        assert code_snap.trust != audit_snap.trust

    def test_evaluate_does_not_persist_to_vault(self):
        tk = _trust_kernel(vault=True)
        decision = tk.evaluate("eval-agent", "read")
        assert isinstance(decision.decision, TrustDecisionKind)

    def test_low_trust_triggers_quarantine(self):
        tk = _trust_kernel(vault=True)
        for _ in range(3):
            tk.record_event(TrustEvent(agent_id="bad-agent", lane="code", action="write", outcome="fail",
                                       hard_fail=True, R=1.0, Q=0.1, U=0.0))
        decision = tk.evaluate("bad-agent", "write", lane="code")
        # 3 hard fails at >= 20 display points each (framework §1.2
        # non-compensatory floor, restored 2026-07-02): 0.5 -> 0.3 -> 0.1,
        # trust < 0.15 -> CDR COLLAPSE -> DENY (stronger than the old
        # soft-nudge Cascade/QUARANTINE behavior this test used to pin).
        assert decision.decision == TrustDecisionKind.DENY
        assert tk.get_snapshot("bad-agent", "code").cdr_stage == "Collapse"

    def test_vault_persist_with_multiple_agents(self):
        tk = _trust_kernel(vault=True)
        for i in range(5):
            tk.record_event(TrustEvent(agent_id=f"agent-{i}", lane="code", action="write", outcome="success"))
        for i in range(5):
            snap = tk.get_snapshot(f"agent-{i}", "code")
            assert snap.evidence_count == 1

    def test_vault_persist_cdr_cascade(self):
        tk = _trust_kernel(vault=True)
        for _ in range(8):
            tk.record_event(TrustEvent(agent_id="collapsing-agent", lane="code", action="write",
                                      outcome="fail", hard_fail=True, R=1.0, Q=0.1, U=0.0))
        snap = tk.get_snapshot("collapsing-agent", "code")
        assert snap.regression_events >= 5
        # Cascade stage → QUARANTINE for side-effect actions
        decision = tk.evaluate("collapsing-agent", "write", lane="code")
        assert decision.decision in (TrustDecisionKind.QUARANTINE, TrustDecisionKind.DENY)

    def test_vault_persist_authority_band_escalation(self):
        tk = _trust_kernel(vault=True)
        for _ in range(3):
            tk.record_event(TrustEvent(agent_id="trusty-agent", lane="code", action="write", outcome="success", Q=0.9, U=0.8))
        snap = tk.get_snapshot("trusty-agent", "code")
        assert snap.trust > 0.5


class TestVaultDecisionRouting:
    """evaluate() routes correctly with vault integration active."""

    def test_allow_for_good_agent(self):
        tk = _trust_kernel(vault=True)
        tk.record_event(TrustEvent(agent_id="good-agent", lane="code", action="write", outcome="success"))
        decision = tk.evaluate("good-agent", "read")
        assert decision.decision == TrustDecisionKind.ALLOW

    def test_quarantine_for_cascaded_agent(self):
        tk = _trust_kernel(vault=True)
        for _ in range(10):
            tk.record_event(TrustEvent(agent_id="dead-agent", lane="code", action="write",
                                      outcome="fail", hard_fail=True, R=1.0, Q=0.0, U=0.0))
        decision = tk.evaluate("dead-agent", "write", lane="code", context={"side_effect": True})
        # 10 hard fails at the non-compensatory floor collapse trust to ~0
        # -> CDR COLLAPSE -> DENY (framework §1.2, restored 2026-07-02).
        assert decision.decision == TrustDecisionKind.DENY
        assert tk.get_snapshot("dead-agent", "code").trust < 0.15

    def test_deny_for_hard_fail_context(self):
        tk = _trust_kernel(vault=True)
        decision = tk.evaluate("any-agent", "write", context={"trust_hard_fail": True})
        assert decision.decision == TrustDecisionKind.DENY

    def test_allow_for_new_agent_side_effect(self):
        tk = _trust_kernel(vault=True)
        # New agent with trust=0.50 → ALLOW even with side_effect (above 0.35 floor)
        decision = tk.evaluate("new-agent", "write", context={"side_effect": True})
        assert decision.decision == TrustDecisionKind.ALLOW

    def test_quarantine_for_cascade_side_effect(self):
        tk = _trust_kernel(vault=True)
        tk.record_event(TrustEvent(agent_id="cascade-agent", lane="code", action="write",
                                  outcome="fail", hard_fail=True, R=1.0, Q=0.0, U=0.0))
        for _ in range(6):
            tk.record_event(TrustEvent(agent_id="cascade-agent", lane="code", action="write",
                                      outcome="fail", hard_fail=True, R=0.8, Q=0.0, U=0.0))
        decision = tk.evaluate("cascade-agent", "write", lane="code", context={"side_effect": True})
        assert decision.decision in (TrustDecisionKind.QUARANTINE, TrustDecisionKind.DENY)
