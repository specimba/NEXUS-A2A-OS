"""tests/governor/test_trust_kernel_singleton.py — P2-2: process-wide kernel
singleton + bootstrap priors."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nexus_os.governor.trust_kernel import (
    TrustEvent,
    TrustKernel,
    get_trust_kernel,
    set_trust_kernel,
)


@pytest.fixture(autouse=True)
def isolated_singleton():
    set_trust_kernel(None)
    yield
    set_trust_kernel(None)


class TestSingleton:
    def test_same_instance_returned(self):
        assert get_trust_kernel() is get_trust_kernel()

    def test_set_trust_kernel_injects(self):
        k = TrustKernel(vault_enabled=False)
        set_trust_kernel(k)
        assert get_trust_kernel() is k

    def test_reset_creates_fresh(self):
        first = get_trust_kernel()
        set_trust_kernel(None)
        assert get_trust_kernel() is not first

    def test_env_db_path_used(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NEXUS_TRUST_DB", str(tmp_path / "trust.db"))
        kernel = get_trust_kernel()
        assert kernel.db is not None


class TestBootstrapPrior:
    def _kernel(self):
        return TrustKernel(vault_enabled=False)

    def test_seed_sets_prior_trust(self):
        k = self._kernel()
        snap = k.ensure_bootstrap_prior("agent-x", "general", prior_trust=95.0)
        assert snap.trust == pytest.approx(0.95)
        assert snap.evidence_count == 0

    def test_reseed_allowed_while_no_evidence(self):
        k = self._kernel()
        k.ensure_bootstrap_prior("agent-x", "general", prior_trust=95.0)
        snap = k.ensure_bootstrap_prior("agent-x", "general", prior_trust=40.0)
        assert snap.trust == pytest.approx(0.40)

    def test_evidence_outranks_prior(self):
        k = self._kernel()
        k.ensure_bootstrap_prior("agent-x", "general", prior_trust=50.0)
        after_event = k.record_event(TrustEvent(
            agent_id="agent-x", lane="general", event_type="task",
            outcome="success", Q=0.9,
        ))
        assert after_event.evidence_count == 1
        # A later registration attempt must NOT reset the posterior
        snap = k.ensure_bootstrap_prior("agent-x", "general", prior_trust=99.0)
        assert snap.trust == after_event.trust
        assert snap.evidence_count == 1

    def test_prior_capped(self):
        k = self._kernel()
        snap = k.ensure_bootstrap_prior("agent-x", "general", prior_trust=100.0)
        assert snap.trust <= 0.995

    def test_prior_weight_moderates_early_evidence(self):
        """A prior is pseudo-evidence: a hard failure applies the
        non-compensatory drop from the seeded value but does not zero it."""
        k = self._kernel()
        k.ensure_bootstrap_prior("agent-x", "general", prior_trust=90.0)
        snap = k.record_event(TrustEvent(
            agent_id="agent-x", lane="general", event_type="task",
            outcome="failure", Q=0.1, hard_fail=True,
        ))
        assert 0.3 < snap.trust <= 0.71  # 0.90 - 0.20 non-compensatory floor
