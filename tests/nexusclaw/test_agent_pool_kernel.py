"""tests/nexusclaw/test_agent_pool_kernel.py — P2-2: agent_pool reads trust
through the TrustKernel; static seeds are bootstrap priors only."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nexus_os.governor.trust_kernel import TrustKernel
from nexus_os.nexusclaw.agent_pool import (
    AgentPool,
    AgentRecord,
    AgentStatus,
    AgentType,
)


@pytest.fixture
def kernel():
    return TrustKernel(vault_enabled=False)


@pytest.fixture
def pool(kernel):
    from nexus_os.vault.memory_channels import MemoryChannelManager
    return AgentPool(memory_channels=MemoryChannelManager(), trust_kernel=kernel)


def _record(agent_id="agent-a", trust=85.0, lane="research"):
    return AgentRecord(
        agent_id=agent_id,
        name=agent_id,
        agent_type=AgentType.INTERNAL,
        status=AgentStatus.ONLINE,
        trust_score=trust,
        lane=lane,
    )


class TestRegisterSeedsPrior:
    def test_register_seeds_kernel_prior_and_mirrors(self, pool, kernel):
        agent = pool.register(_record(trust=85.0))
        snap = kernel.get_snapshot("agent-a", "research")
        assert snap.trust == pytest.approx(0.85)
        assert agent.trust_score == pytest.approx(85.0)

    def test_discover_internal_agents_seeds_priors(self, pool, kernel):
        pool.discover_internal_agents()
        gov = kernel.get_snapshot("nexus-governor", "governance")
        assert gov.trust == pytest.approx(0.95)
        assert gov.evidence_count == 0  # prior, not evidence


class TestUpdateTrustRoundTrip:
    def test_update_trust_persists_to_kernel(self, pool, kernel):
        """Roadmap gate: round-trip agent_pool.update_trust → kernel."""
        pool.register(_record(trust=50.0))
        agent = pool.update_trust("agent-a", 90.0)
        snap = kernel.get_snapshot("agent-a", "research")
        assert snap.evidence_count == 1
        # Record mirrors the kernel posterior, not the raw target
        assert agent.trust_score == pytest.approx(snap.trust * 100.0, abs=0.01)

    def test_no_second_store_absolute_writes(self, pool, kernel):
        """An absolute score can no longer be assigned: anti-grinding and
        the Beta posterior govern the outcome."""
        pool.register(_record(trust=50.0))
        agent = pool.update_trust("agent-a", 100.0)
        assert agent.trust_score < 100.0  # single event cannot buy max trust

    def test_repeated_negative_observations_lower_trust(self, pool, kernel):
        """Single observations are damped by design (anti-grinding both
        ways); accumulated regressions must move the posterior down."""
        pool.register(_record(trust=80.0))
        before = kernel.get_snapshot("agent-a", "research").trust
        for _ in range(6):
            agent = pool.update_trust("agent-a", 5.0)
        after = kernel.get_snapshot("agent-a", "research").trust
        assert after < before
        assert agent.trust_score == pytest.approx(after * 100.0, abs=0.01)

    def test_kernel_unavailable_falls_back_to_float(self, tmp_path):
        from nexus_os.vault.memory_channels import MemoryChannelManager

        class _BrokenKernel:
            def ensure_bootstrap_prior(self, *a, **k):
                raise RuntimeError("kernel down")

            def record_event(self, *a, **k):
                raise RuntimeError("kernel down")

            def get_snapshot(self, *a, **k):
                raise RuntimeError("kernel down")

        pool = AgentPool(memory_channels=MemoryChannelManager(),
                         trust_kernel=_BrokenKernel())
        pool.register(_record(trust=70.0))
        agent = pool.update_trust("agent-a", 33.0)
        assert agent.trust_score == pytest.approx(33.0)


class TestReadThrough:
    def test_get_reflects_external_kernel_changes(self, pool, kernel):
        """Trust recorded directly in the kernel (e.g. by the governor)
        shows up on the pool record without a pool-side write."""
        from nexus_os.governor.trust_kernel import TrustEvent
        pool.register(_record(trust=80.0))
        for _ in range(5):
            kernel.record_event(TrustEvent(
                agent_id="agent-a", lane="research", event_type="task",
                outcome="failure", Q=0.05, hard_fail=True,
            ))
        agent = pool.get("agent-a")
        snap = kernel.get_snapshot("agent-a", "research")
        assert agent.trust_score == pytest.approx(snap.trust * 100.0, abs=0.01)
        assert agent.trust_score < 80.0

    def test_list_available_filters_on_kernel_trust(self, pool, kernel):
        from nexus_os.governor.trust_kernel import TrustEvent
        pool.register(_record("good-agent", trust=80.0))
        pool.register(_record("bad-agent", trust=80.0))
        for _ in range(6):
            kernel.record_event(TrustEvent(
                agent_id="bad-agent", lane="research", event_type="task",
                outcome="failure", Q=0.02, hard_fail=True,
            ))
        available = pool.list_available(min_trust=60.0)
        ids = {a.agent_id for a in available}
        assert "good-agent" in ids
        assert "bad-agent" not in ids
