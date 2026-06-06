"""tests/gmr/test_trust_adapter.py — TrustAwareGMR and TrustContext tests"""
import pytest

from nexus_os.gmr.trust_adapter import TrustAwareGMR, TrustContext


class TestTrustContext:
    def test_defaults(self):
        ctx = TrustContext(agent_id="a1", lane="standard")
        assert ctx.agent_id == "a1"
        assert ctx.lane == "standard"
        assert ctx.minimum_score == 0.0

    def test_custom_minimum_score(self):
        ctx = TrustContext(agent_id="a1", lane="premium", minimum_score=0.7)
        assert ctx.minimum_score == 0.7


class TestTrustAwareGMR:
    def test_smoothed_score_no_data(self):
        adapter = TrustAwareGMR(base_gmr=None)
        score = adapter.get_smoothed_score(0, 0)
        # (10 + 0) / (10 + 0 + 2 + 0) = 10/12
        assert abs(score - 10 / 12) < 1e-9

    def test_smoothed_score_all_successes(self):
        adapter = TrustAwareGMR(base_gmr=None)
        score = adapter.get_smoothed_score(100, 0)
        # (10 + 100) / (10 + 100 + 2 + 0) = 110/112
        assert abs(score - 110 / 112) < 1e-9

    def test_smoothed_score_all_failures(self):
        adapter = TrustAwareGMR(base_gmr=None)
        score = adapter.get_smoothed_score(0, 100)
        # (10 + 0) / (10 + 0 + 2 + 100) = 10/112
        assert abs(score - 10 / 112) < 1e-9

    def test_smoothed_score_prevents_overconfidence(self):
        adapter = TrustAwareGMR(base_gmr=None)
        score_small = adapter.get_smoothed_score(1, 0)
        # Even 1 success should not push to 1.0 due to prior
        assert score_small < 1.0

    def test_smoothed_score_monotonically_increases_with_success(self):
        adapter = TrustAwareGMR(base_gmr=None)
        scores = [adapter.get_smoothed_score(s, 0) for s in range(0, 50)]
        for i in range(1, len(scores)):
            assert scores[i] > scores[i - 1]

    def test_smoothed_score_equal_mix(self):
        adapter = TrustAwareGMR(base_gmr=None)
        score = adapter.get_smoothed_score(50, 50)
        # (10+50)/(10+50+2+50) = 60/112
        assert abs(score - 60 / 112) < 1e-9

    def test_gmr_attribute_stored(self):
        sentinel = object()
        adapter = TrustAwareGMR(base_gmr=sentinel)
        assert adapter.gmr is sentinel
