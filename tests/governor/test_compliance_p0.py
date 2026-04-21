"""tests/governor/test_compliance_p0.py — P0: Governor Budget & VAP Integration"""

import pytest
from nexus_os.governor.compliance import ComplianceEngine, ComplianceStatus
from nexus_os.monitoring.token_guard import TokenGuard
from nexus_os.governor.proof_chain import ProofChain


@pytest.fixture
def guard():
    # Use 'agent' key because _get_budget_key() maps 'test-agent' -> 'agent'
    return TokenGuard(budgets={"agent": 5000})


@pytest.fixture
def vap():
    return ProofChain()


@pytest.fixture
def engine(guard, vap):
    # Pass our test instances into the Governor (no db needed for this test)
    return ComplianceEngine(db=None, token_guard=guard, vap_chain=vap)


class TestGovernorIntegration:
    def test_budget_allows_and_vap_logs(self, engine, vap):
        """Budget allows request and VAP logs the approval."""
        res = engine.evaluate("test-agent", "read", {"required_tokens": 1000})
        assert res.status == ComplianceStatus.COMPLIANT
        # VAP should have logged the approval
        assert len(vap._entries) > 0

    def test_budget_exhaustion_hard_stops(self, engine, guard, vap):
        """Budget exhaustion results in BLOCKED status."""
        guard.track("test-agent", 5000)  # Exhaust the budget
        res = engine.evaluate("test-agent", "read", {"required_tokens": 1000})
        assert res.status == ComplianceStatus.BLOCKED
        assert len(res.violations) == 1
        assert res.violations[0].rule_id == "TOKEN-BUDGET-001"

    def test_vap_cryptographic_integrity(self, engine, guard, vap):
        """VAP chain maintains cryptographic integrity."""
        # First request passes
        engine.evaluate("agent3", "read", {"required_tokens": 500})
        
        # Exhaust budget
        guard.track("agent3", 5000)
        
        # Second request fails (budget exceeded)
        engine.evaluate("agent3", "read", {"required_tokens": 1000})

        # Verify the SHA-256 chain is unbroken
        assert vap.verify_chain() is True

    def test_unknown_agent_gets_default_budget(self, engine):
        """Unknown agents get default budget and can proceed."""
        res = engine.evaluate("unknown-agent", "read", {"required_tokens": 1000})
        # Should pass because unknown agents get default budget
        assert res.status == ComplianceStatus.COMPLIANT
