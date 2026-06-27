"""Tests for bebop_signal.py — TV-distribution hallucination signal (P2.1)."""

import math
import pytest
from nexus_os.monitoring.bebop_signal import (
    BebopSignal,
    assess_bebop,
    build_reference_distribution,
    entropy,
    risk_score_from_bebop,
    tv_distance,
    _normalize,
)


class TestNormalize:
    def test_empty_list(self):
        assert _normalize([]) == []

    def test_single_value(self):
        result = _normalize([5.0])
        assert len(result) == 1
        assert abs(result[0] - 1.0) < 1e-9

    def test_logits_to_probs(self):
        result = _normalize([2.0, 1.0, 0.0])
        assert len(result) == 3
        assert abs(sum(result) - 1.0) < 1e-9
        assert result[0] > result[1] > result[2]

    def test_already_probs_pass_through(self):
        result = _normalize([0.2, 0.3, 0.5])
        assert abs(sum(result) - 1.0) < 1e-9

    def test_all_equal(self):
        result = _normalize([1.0, 1.0, 1.0, 1.0])
        expected = 0.25
        assert all(abs(v - expected) < 1e-9 for v in result)

    def test_negative_logits(self):
        result = _normalize([-1.0, -2.0, -3.0])
        assert abs(sum(result) - 1.0) < 1e-9
        assert result[0] > result[1] > result[2]

    def test_large_positive_explosion_safe(self):
        result = _normalize([1e3, 0.0])
        assert abs(result[0] - 1.0) < 1e-9


class TestTVDistance:
    def test_identical_distributions(self):
        p = [0.25, 0.25, 0.25, 0.25]
        assert tv_distance(p, list(p)) == 0.0

    def test_one_hot_vs_uniform(self):
        p = [1.0, 0.0, 0.0, 0.0]
        q = [0.25, 0.25, 0.25, 0.25]
        result = tv_distance(p, q)
        expected = 0.5 * (0.75 + 0.25 + 0.25 + 0.25)  # 0.75
        assert abs(result - expected) < 1e-9

    def test_empty_input(self):
        assert tv_distance([], [1.0]) == 0.0
        assert tv_distance([1.0], []) == 0.0
        assert tv_distance([], []) == 0.0

    def test_mismatched_lengths(self):
        assert tv_distance([0.5, 0.5], [0.3, 0.3, 0.4]) == 0.0

    def test_bounded_in_01(self):
        p = [0.9, 0.1]
        q = [0.1, 0.9]
        result = tv_distance(p, q)
        assert 0.0 <= result <= 1.0
        assert abs(result - 0.8) < 1e-9

    def test_degenerate_negative_clamped(self):
        p = [-0.5, 1.5]
        q = [0.5, 0.5]
        result = tv_distance(p, q)
        assert 0.0 <= result <= 1.0


class TestBuildReferenceDistribution:
    def test_uniform(self):
        q = build_reference_distribution(10, mode="uniform")
        assert len(q) == 10
        assert all(abs(v - 0.1) < 1e-9 for v in q)

    def test_head(self):
        q = build_reference_distribution(10, mode="head")
        assert len(q) == 10
        assert abs(q[0] - 1.0) < 1e-9
        assert all(v == 0.0 for v in q[1:])

    def test_fluency_is_normalized(self):
        q = build_reference_distribution(100, mode="fluency")
        assert abs(sum(q) - 1.0) < 1e-6

    def test_fluency_is_descending(self):
        q = build_reference_distribution(50, mode="fluency")
        for i in range(len(q) - 1):
            assert q[i] >= q[i + 1], f"at index {i}"

    def test_zero_vocab(self):
        assert build_reference_distribution(0) == []

    def test_default_mode(self):
        q = build_reference_distribution(10)
        assert len(q) == 10
        assert abs(sum(q) - 1.0) < 1e-6


class TestEntropy:
    def test_uniform_max(self):
        h = entropy([0.25, 0.25, 0.25, 0.25])
        expected = 4 * 0.25 * math.log(4)  # ln(4) ≈ 1.386
        assert abs(h - 1.386294361) < 1e-6

    def test_certainty_zero(self):
        h = entropy([1.0, 0.0, 0.0])
        assert abs(h) < 1e-9

    def test_empty_list(self):
        assert entropy([]) == 0.0

    def test_single_value(self):
        assert entropy([1.0]) == 0.0

    def test_non_negative(self):
        import random
        for _ in range(10):
            v = [random.random() for _ in range(10)]
            s = sum(v)
            v = [x / s for x in v]
            assert entropy(v) >= 0.0


class TestAssessBebop:
    def test_flat_vs_flat_is_well_calibrated(self):
        p = [0.25] * 4
        q = [0.25] * 4
        sig = assess_bebop(p, q)
        assert sig.tv < 1e-9
        assert sig.divergence_class == "well_calibrated"
        assert sig.bounded_gradient is True
        assert sig.vocab_size == 4

    def test_peaked_vs_flat_positive_tv(self):
        """Logits that produce peaked distribution yield positive TV vs uniform."""
        sig = assess_bebop([5.0, 0.0, 0.0, 0.0], [0.25] * 4)
        assert sig.tv > 0.0

    def test_one_hot_vs_uniform(self):
        sig = assess_bebop([10.0, -10.0, -10.0, -10.0], [0.25] * 4)
        assert sig.tv > 0.5
        assert sig.divergence_class == "high_drift"

    def test_empty_input(self):
        sig = assess_bebop([])
        assert sig.tv == 0.0
        assert sig.divergence_class == "well_calibrated"
        assert sig.vocab_size == 0

    def test_auto_reference_built(self):
        sig = assess_bebop([0.5, 0.3, 0.2], reference_mode="uniform")
        assert sig.vocab_size == 3
        assert sig.tv >= 0.0

    def test_reference_length_mismatch(self):
        sig = assess_bebop([0.5, 0.5], reference=[0.25] * 4)
        assert sig.vocab_size == 2

    def test_reference_provided(self):
        ref = [0.5, 0.5]
        sig = assess_bebop([0.6, 0.4], reference=ref)
        assert sig.vocab_size == 2


class TestBebopDivergenceBuckets:
    @pytest.mark.parametrize("logits,expected_class", [
        ([-1.31, -1.31, -1.47, -1.47], "well_calibrated"),  # TV≈0.04
        ([-0.916, -1.204, -1.897, -1.897], "l1_drift"),     # TV≈0.20
        ([-0.357, -1.897, -2.303, -2.996], "l2_drift"),     # TV≈0.45
        ([-0.105, -3.219, -3.507, -3.507], "high_drift"),   # TV≈0.65
    ])
    def test_bucket_boundaries(self, logits, expected_class):
        sig = assess_bebop(logits, [0.25] * 4)
        assert sig.divergence_class == expected_class


class TestRiskScoreFromBebop:
    def test_well_calibrated_low_risk(self):
        sig = assess_bebop([0.25] * 4, [0.25] * 4)
        risk = risk_score_from_bebop(sig)
        assert risk >= 0.0
        assert risk <= 1.0

    def test_high_drift_high_risk(self):
        sig = assess_bebop([10.0, -10.0, -10.0, -10.0], [0.25] * 4)
        risk = risk_score_from_bebop(sig)
        assert risk > 0.5

    def test_risk_bounded(self):
        for probs in [[0.25] * 4, [0.5, 0.5], [1.0, 0.0],
                      [0.4, 0.3, 0.2, 0.1]]:
            sig = assess_bebop(probs, [1.0 / len(probs)] * len(probs))
            risk = risk_score_from_bebop(sig)
            assert 0.0 <= risk <= 1.0, f"risk {risk} out of bounds for {probs}"

    def test_zero_tau_returns_tv(self):
        sig = assess_bebop([10.0, -10.0], [0.5, 0.5])
        risk = risk_score_from_bebop(sig, tau=0.0)
        assert abs(risk - sig.tv) < 1e-9

    def test_custom_tau(self):
        sig = assess_bebop([0.6, 0.4], [0.5, 0.5])
        risk_low = risk_score_from_bebop(sig, tau=0.5)
        risk_high = risk_score_from_bebop(sig, tau=0.1)
        assert risk_high >= risk_low


class TestBebopSignalDataclass:
    def test_to_dict(self):
        sig = BebopSignal(tv=0.5, divergence_class="l2_drift", bounded_gradient=True,
                          entropy_of_p=0.5, entropy_of_q=0.3, tv_weighted_by_entropy=0.1,
                          vocab_size=4)
        d = sig.to_dict()
        assert d["tv"] == 0.5
        assert d["divergence_class"] == "l2_drift"
        assert d["bounded_gradient"] is True

    def test_roundtrip(self):
        sig = assess_bebop([0.5, 0.3, 0.2], [1.0 / 3] * 3)
        d = sig.to_dict()
        assert d["tv"] == sig.tv
        assert d["vocab_size"] == 3
