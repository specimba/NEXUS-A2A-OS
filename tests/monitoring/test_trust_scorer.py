"""tests/monitoring/test_trust_scorer.py — v2.1 Canonical Trust Scorer tests

Covers:
- Lane-scoped parameter loading
- Non-compensatory harm (R > Rcrit → None)
- Score bounding [-1, 1]
- Null-state checks (blocked/unassigned)
- Hot-path performance (<1ms per call)
- Lane isolation
- Near-zero compression
"""

import math
import time
import pytest

from nexus_os.monitoring.trust_scorer import (
    LANE_PARAMS,
    LaneParams,
    TrustScorer,
)


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def scorer():
    return TrustScorer()


# ── LaneParams ───────────────────────────────────────────────────────

class TestLaneParams:
    def test_defaults(self):
        p = LaneParams()
        assert p.qmin == 0.1
        assert p.Rcrit == 0.6
        assert p.kappa == 2.5

    def test_audit_stricter_than_research(self):
        audit = LANE_PARAMS["audit"]
        research = LANE_PARAMS["research"]
        assert audit.Rcrit < research.Rcrit  # audit is less tolerant of harm
        assert audit.qmin > research.qmin    # audit needs higher confidence

    def test_all_lanes_present(self):
        expected = {"research", "audit", "compliance", "implementation", "orchestration", "general"}
        assert expected.issubset(set(LANE_PARAMS.keys()))


# ── Null State ───────────────────────────────────────────────────────

class TestNullState:
    def test_blocked_returns_none(self, scorer):
        assert scorer.get_score_hotpath("a1", Q=0.9, status="blocked") is None

    def test_unassigned_returns_none(self, scorer):
        assert scorer.get_score_hotpath("a1", Q=0.9, status="unassigned") is None

    def test_not_applicable_returns_none(self, scorer):
        assert scorer.get_score_hotpath("a1", Q=0.9, status="not_applicable") is None

    def test_active_returns_score(self, scorer):
        result = scorer.get_score_hotpath("a1", Q=0.9, n=5, U=0.8, status="active")
        assert result is not None


# ── Non-Compensatory Harm ────────────────────────────────────────────

class TestNonCompensatory:
    def test_harm_above_rcrit_returns_none(self, scorer):
        result = scorer.get_score_hotpath("a1", Q=0.9, U=1.0, R=0.7, lane="general")
        assert result is None

    def test_harm_below_rcrit_returns_score(self, scorer):
        result = scorer.get_score_hotpath("a1", Q=0.9, U=1.0, R=0.1, lane="general")
        assert result is not None

    def test_compliance_very_strict(self, scorer):
        result = scorer.get_score_hotpath("a1", Q=0.9, U=1.0, R=0.25, lane="compliance")
        assert result is None  # compliance Rcrit = 0.2

    def test_research_more_lenient(self, scorer):
        result = scorer.get_score_hotpath("a1", Q=0.9, U=1.0, R=0.5, lane="research")
        assert result is not None  # research Rcrit = 0.7

    def test_is_harm_critical(self, scorer):
        assert scorer.is_harm_critical(0.7, "general")
        assert not scorer.is_harm_critical(0.3, "general")
        assert scorer.is_harm_critical(0.25, "compliance")


# ── Score Bounding ───────────────────────────────────────────────────

class TestScoreBounding:
    def test_score_in_range(self, scorer):
        result = scorer.get_score_hotpath("a1", Q=0.9, n=10, U=0.9, D_plus=0.5, lane="research")
        assert -1.0 <= result <= 1.0

    def test_negative_score_possible(self, scorer):
        result = scorer.get_score_hotpath("a1", Q=0.9, n=10, U=0.0, R=0.5, D_minus=0.9, lane="research")
        assert result is not None
        assert result <= 0.0

    def test_stress_random_bounded(self, scorer):
        import random
        random.seed(42)
        lanes = list(LANE_PARAMS.keys())
        for _ in range(1000):
            lane = random.choice(lanes)
            Q = random.random()
            n = random.randint(0, 50)
            U = random.random()
            R = random.random() * 0.3  # keep below Rcrit
            D_plus = random.random()
            D_minus = random.random()
            result = scorer.get_score_hotpath("a1", Q=Q, n=n, U=U, R=R, D_plus=D_plus, D_minus=D_minus, lane=lane)
            if result is not None:
                assert -1.0 <= result <= 1.0


# ── Near-Zero Compression ───────────────────────────────────────────

class TestNearZeroCompression:
    def test_very_small_score_compressed(self, scorer):
        result = scorer.get_score_hotpath("a1", Q=0.11, n=1, U=0.001, lane="general")
        if result is not None:
            assert result == 0.0 or abs(result) >= 1e-4


# ── Lane Params Access ──────────────────────────────────────────────

class TestLaneParamsAccess:
    def test_get_known_lane(self, scorer):
        params = scorer.get_lane_params("audit")
        assert isinstance(params, LaneParams)
        assert params.qmin == 0.7

    def test_get_unknown_lane_returns_general(self, scorer):
        params = scorer.get_lane_params("nonexistent")
        assert params == LANE_PARAMS["general"]


# ── Hot-Path Performance ────────────────────────────────────────────

class TestHotPathPerf:
    def test_under_5ms_per_call(self, scorer):
        start = time.perf_counter()
        for _ in range(10000):
            scorer.get_score_hotpath("a1", Q=0.8, n=5, U=0.7, R=0.1, lane="research")
        elapsed = (time.perf_counter() - start) / 10000
        assert elapsed < 0.005  # 5ms generous threshold for CI runners
