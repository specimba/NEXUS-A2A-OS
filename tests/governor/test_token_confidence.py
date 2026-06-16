"""Tests for CK-PLUG-inspired token confidence gain module."""

import math

import pytest

from nexus_os.governor.token_confidence import TokenConfidenceGain, QEnhancer


class TestTokenConfidenceGain:
    def test_mean_mode_basic(self):
        tcg = TokenConfidenceGain(mode="mean")
        result = tcg.compute([0.9, 0.85, 0.88])
        assert result == pytest.approx((0.9 + 0.85 + 0.88) / 3, rel=1e-6)

    def test_mean_mode_empty(self):
        tcg = TokenConfidenceGain(mode="mean")
        assert tcg.compute([]) == 0.0

    def test_mean_mode_out_of_bounds(self):
        tcg = TokenConfidenceGain(mode="mean")
        assert tcg.compute([1.2, -0.3, 0.5]) == pytest.approx((1.0 + 0.0 + 0.5) / 3, rel=1e-6)

    def test_min_mode(self):
        tcg = TokenConfidenceGain(mode="min")
        assert tcg.compute([0.9, 0.1, 0.8]) == 0.1

    def test_harmonic_mode(self):
        tcg = TokenConfidenceGain(mode="harmonic")
        result = tcg.compute([0.5, 0.5, 0.5])
        assert result == pytest.approx(0.5, rel=1e-6)

    def test_harmonic_mode_penalizes_low(self):
        tcg = TokenConfidenceGain(mode="harmonic")
        result = tcg.compute([0.9, 0.9, 0.1])
        # Harmonic mean should be strongly pulled down by the 0.1
        assert result < 0.3

    def test_harmonic_mode_with_zero(self):
        tcg = TokenConfidenceGain(mode="harmonic")
        result = tcg.compute([0.5, 0.0])
        # Should not crash; epsilon prevents division by zero
        assert result > 0.0

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            TokenConfidenceGain(mode="median")

    def test_from_logprobs(self):
        logprobs = [math.log(0.9), math.log(0.5), math.log(0.1)]
        confidences = TokenConfidenceGain.from_logprobs(logprobs)
        assert len(confidences) == 3
        assert confidences[0] == pytest.approx(0.9, rel=1e-6)
        assert confidences[1] == pytest.approx(0.5, rel=1e-6)
        assert confidences[2] == pytest.approx(0.1, rel=1e-6)

    def test_from_logprobs_very_low(self):
        logprobs = [-200.0, -100.0, -50.0]
        confidences = TokenConfidenceGain.from_logprobs(logprobs)
        assert confidences[0] == 0.0  # exp(-200) underflows to 0 after clipping
        assert confidences[1] == 0.0  # exp(-100) is also 0 after clipping
        assert confidences[2] > 0.0


class TestQEnhancer:
    def test_no_confidences_returns_original(self):
        enhancer = QEnhancer(confidence_weight=0.3)
        assert enhancer.enhance(0.75, None) == 0.75
        assert enhancer.enhance(0.75, []) == 0.75

    def test_basic_enhancement(self):
        enhancer = QEnhancer(confidence_weight=0.3, mode="mean")
        # Original Q=0.5, confidence gain=0.8 -> blended = 0.7*0.5 + 0.3*0.8 = 0.59
        result = enhancer.enhance(0.5, [0.8, 0.8, 0.8])
        assert result == pytest.approx(0.59, rel=1e-6)

    def test_zero_confidence_weight_returns_original(self):
        enhancer = QEnhancer(confidence_weight=0.0)
        result = enhancer.enhance(0.5, [0.9, 0.9, 0.9])
        assert result == 0.5

    def test_full_confidence_weight(self):
        enhancer = QEnhancer(confidence_weight=1.0, mode="mean")
        result = enhancer.enhance(0.2, [0.9, 0.9, 0.9])
        assert result == pytest.approx(0.9, rel=1e-6)

    def test_clipping_upper(self):
        enhancer = QEnhancer(confidence_weight=0.5, mode="mean")
        result = enhancer.enhance(1.0, [1.0, 1.0, 1.0])
        assert result == 1.0

    def test_clipping_lower(self):
        enhancer = QEnhancer(confidence_weight=0.5, mode="mean")
        result = enhancer.enhance(0.0, [0.0, 0.0, 0.0])
        assert result == 0.0

    def test_floor_enforcement(self):
        enhancer = QEnhancer(confidence_weight=0.5, mode="mean", floor=0.3)
        result = enhancer.enhance(0.1, [0.0, 0.0, 0.0])
        assert result == 0.3

    def test_invalid_weight_raises(self):
        with pytest.raises(ValueError):
            QEnhancer(confidence_weight=-0.1)
        with pytest.raises(ValueError):
            QEnhancer(confidence_weight=1.5)

    def test_invalid_floor_raises(self):
        with pytest.raises(ValueError):
            QEnhancer(floor=-0.1)
        with pytest.raises(ValueError):
            QEnhancer(floor=1.5)

    def test_enhance_with_out_of_bounds_Q(self):
        enhancer = QEnhancer(confidence_weight=0.3)
        # Q=1.5 gets clipped to 1.0, then blended with 0.9 at weight 0.3 -> 0.7*1.0 + 0.3*0.9 = 0.97
        assert enhancer.enhance(1.5, [0.9]) == pytest.approx(0.97, rel=1e-6)
        # Q=-0.5 gets clipped to 0.0, then blended with 0.9 at weight 0.3 -> 0.7*0.0 + 0.3*0.9 = 0.27
        assert enhancer.enhance(-0.5, [0.9]) == pytest.approx(0.3 * 0.9, rel=1e-6)

    def test_batch_enhance(self):
        enhancer = QEnhancer(confidence_weight=0.5, mode="mean")
        Qs = [0.5, 0.6, 0.7]
        tcs = [
            [0.8, 0.8],
            None,
            [0.9, 0.9],
        ]
        results = enhancer.batch_enhance(Qs, tcs)
        assert len(results) == 3
        # Q=0.5, tc=0.8 -> 0.5*0.5 + 0.5*0.8 = 0.65
        assert results[0] == pytest.approx(0.65, rel=1e-6)
        # Q=0.6, tc=None -> 0.6
        assert results[1] == 0.6
        # Q=0.7, tc=0.9 -> 0.5*0.7 + 0.5*0.9 = 0.8
        assert results[2] == pytest.approx(0.8, rel=1e-6)

    def test_min_mode_enhancer(self):
        enhancer = QEnhancer(confidence_weight=0.5, mode="min")
        # Min confidence is 0.1, so blended = 0.5*0.5 + 0.5*0.1 = 0.3
        result = enhancer.enhance(0.5, [0.9, 0.1, 0.8])
        assert result == pytest.approx(0.3, rel=1e-6)

    def test_harmonic_mode_enhancer(self):
        enhancer = QEnhancer(confidence_weight=0.5, mode="harmonic")
        result = enhancer.enhance(0.5, [0.9, 0.1, 0.8])
        # Harmonic mean should be strongly penalized by the 0.1
        harmonic = TokenConfidenceGain(mode="harmonic").compute([0.9, 0.1, 0.8])
        expected = 0.5 * 0.5 + 0.5 * harmonic
        assert result == pytest.approx(expected, rel=1e-6)
