"""Anti-grinding guarantees of the canonical TrustKernel durable update.

The 2026-07-02 trust-formula forensic audit confirmed the live Beta
posterior in record_event had silently dropped the NEXUS Trust Framework's
inverted-logistic scaling (§3.1), the non-compensatory hard-fail floor
(§1.2), and the 99.5 asymptotic cap. These tests pin the restored laws:
volume alone must not buy high trust, a hard fail must cost >= 20 display
points regardless of accumulated positive mass, and trust never exceeds
0.995.
"""
from __future__ import annotations

import pytest

from nexus_os.governor.trust_formulas import logistic_scale, non_compensatory_penalty
from nexus_os.governor.trust_kernel import (
    NON_COMPENSATORY_DROP,
    TRUST_CAP,
    TrustEvent,
    TrustKernel,
    TrustSnapshot,
)


def _success_event(agent_id: str, q: float = 0.7) -> TrustEvent:
    return TrustEvent(
        agent_id=agent_id,
        lane="implementation",
        event_type="task_outcome",
        action="execute",
        outcome="success",
        Q=q,
        U=0.6,
        R=0.0,
        D_plus=0.2,
    )


def _seed(kernel: TrustKernel, agent_id: str, lane: str, trust: float, mass: float = 20.0):
    """Install a snapshot at a chosen trust level with realistic evidence mass."""
    kernel._snapshots[(agent_id, lane)] = TrustSnapshot(
        agent_id=agent_id,
        lane=lane,
        trust=trust,
        alpha=trust * mass,
        beta=(1.0 - trust) * mass,
        evidence_count=int(mass),
    )


@pytest.fixture
def kernel():
    return TrustKernel(vault_enabled=False)


class TestGrindingResistance:
    def test_trust_never_exceeds_cap_under_volume(self, kernel):
        """300 identical successes must plateau below the 99.5 asymptote."""
        snap = None
        for _ in range(300):
            snap = kernel.record_event(_success_event("grinder"))
        assert snap.trust <= TRUST_CAP

    def test_marginal_gains_shrink_as_trust_rises(self, kernel):
        """Framework §3.1: per-success delta at high trust must be smaller
        than at mid trust — the inverted logistic, not a linear +1."""
        _seed(kernel, "mid", "implementation", trust=0.5)
        _seed(kernel, "high", "implementation", trust=0.9)

        mid_delta = kernel.record_event(_success_event("mid")).trust - 0.5
        high_delta = kernel.record_event(_success_event("high")).trust - 0.9

        assert mid_delta > 0
        assert high_delta < mid_delta

    def test_trivial_task_volume_cannot_reach_high_trust(self, kernel):
        """Low-quality grinding (the §1.1 attack) stays out of the top band."""
        snap = None
        for _ in range(200):
            snap = kernel.record_event(_success_event("trivial-grinder", q=0.45))
        assert snap.trust < 0.95


class TestNonCompensatoryFloor:
    def test_hard_fail_costs_at_least_the_drop(self, kernel):
        _seed(kernel, "veteran", "implementation", trust=0.9, mass=100.0)
        snap = kernel.record_event(
            TrustEvent(
                agent_id="veteran",
                lane="implementation",
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
        assert snap.trust <= 0.9 - NON_COMPENSATORY_DROP + 1e-9

    def test_posterior_mass_rebalanced_after_floor(self, kernel):
        """After a clamp the stored alpha/beta must agree with the enforced
        trust, so the next update evolves from the enforced value."""
        _seed(kernel, "veteran2", "implementation", trust=0.9, mass=100.0)
        snap = kernel.record_event(
            TrustEvent(
                agent_id="veteran2",
                lane="implementation",
                hard_fail=True,
                Q=0.9,
                R=0.95,
            )
        )
        assert snap.alpha / (snap.alpha + snap.beta) == pytest.approx(snap.trust, abs=1e-3)


class TestFormulaHelpers:
    def test_logistic_scale_is_inverted(self):
        assert logistic_scale(10.0) > logistic_scale(50.0) > logistic_scale(90.0)

    def test_non_compensatory_penalty_forces_floor(self):
        """CRITICAL forces delta <= floor; it never softens a worse penalty."""
        assert non_compensatory_penalty(-5.0, critical=True) == -20.0
        assert non_compensatory_penalty(-30.0, critical=True) == -30.0
        assert non_compensatory_penalty(-5.0, critical=False) == -5.0
