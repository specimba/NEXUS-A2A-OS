"""
Test suite for MindGuard Temporal Attention Entropy (TAE) Inspector.

Tests the standalone MindGuardTAE class in mindguard_tae.py:
  - Shannon entropy computation with known attention patterns
  - Dilution attack detection (high uniform entropy)
  - Delegation attack detection (concentrated single-head entropy)
  - Fallback safe result when no attention data
  - MindGuardResult dataclass
  - Integration: guard_router.py import and TIER_THRESHOLDS config
  - Edge cases: empty arrays, single-element, all-zeros, negative values
"""
import os
import sys
import math

import pytest
import numpy as np

NEXUS_ROOT = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", ".."
))
if NEXUS_ROOT not in sys.path:
    sys.path.insert(0, NEXUS_ROOT)

from nexus_os.security.mindguard_tae import MindGuardTAE, MindGuardResult


# ── Helpers ────────────────────────────────────────────────────────────────

def make_uniform_attention(num_heads: int, seq_len: int) -> np.ndarray:
    """Create uniform attention: every position attends equally.
    This produces MAXIMUM entropy (normalized ~ 1.0).
    """
    attn = np.ones((num_heads, seq_len, seq_len)) / seq_len
    return attn


def make_concentrated_attention(
    num_heads: int, seq_len: int, target_pos: int = 0
) -> np.ndarray:
    """Create concentrated attention: all mass on one position.
    This produces MINIMUM entropy (normalized ~ 0.0).
    """
    attn = np.zeros((num_heads, seq_len, seq_len))
    attn[:, :, target_pos] = 1.0
    return attn


def make_mixed_attention(
    num_heads: int,
    seq_len: int,
    concentrated_heads: int = 1,
) -> np.ndarray:
    """Create mixed attention: some heads concentrated, others uniform.
    concentrated_heads are delta functions; the rest are uniform.
    """
    attn = np.ones((num_heads, seq_len, seq_len)) / seq_len
    for h in range(min(concentrated_heads, num_heads)):
        attn[h, :, :] = 0.0
        attn[h, :, 0] = 1.0
    return attn


# ── MindGuardResult Dataclass Tests ────────────────────────────────────────

class TestMindGuardResult:
    """Test the MindGuardResult dataclass."""

    def test_default_fields(self):
        result = MindGuardResult(is_safe=True, entropy_score=0.5)
        assert result.is_safe is True
        assert result.entropy_score == 0.5
        assert result.detected_patterns == []
        assert result.recommendation == ""
        assert result.head_entropies == []
        assert result.latency_ms == 0

    def test_unsafe_result(self):
        result = MindGuardResult(
            is_safe=False,
            entropy_score=0.95,
            detected_patterns=["attention_dilution"],
            recommendation="ESCALATE_L3",
        )
        assert result.is_safe is False
        assert "attention_dilution" in result.detected_patterns


# ── Shannon Entropy Computation Tests ──────────────────────────────────────

class TestTemporalEntropyComputation:
    """Test MindGuardTAE.compute_temporal_entropy."""

    def test_uniform_distribution_max_entropy(self):
        """Uniform distribution should give normalized entropy close to 1.0."""
        tae = MindGuardTAE()
        uniform = np.ones(100) / 100
        entropy = tae.compute_temporal_entropy(uniform)
        assert 0.99 <= entropy <= 1.0, f"Expected ~1.0, got {entropy}"

    def test_delta_distribution_zero_entropy(self):
        """Single-spike distribution should give entropy of 0.0."""
        tae = MindGuardTAE()
        delta = np.zeros(100)
        delta[42] = 1.0
        entropy = tae.compute_temporal_entropy(delta)
        assert entropy == 0.0, f"Expected 0.0, got {entropy}"

    def test_two_element_equal_entropy(self):
        """Two equal elements: H = log2(2)/log2(2) = 1.0."""
        tae = MindGuardTAE()
        dist = np.array([0.5, 0.5])
        entropy = tae.compute_temporal_entropy(dist)
        assert abs(entropy - 1.0) < 1e-6

    def test_two_element_skewed(self):
        """Skewed binary: entropy between 0 and 1."""
        tae = MindGuardTAE()
        dist = np.array([0.9, 0.1])
        entropy = tae.compute_temporal_entropy(dist)
        assert 0.0 < entropy < 1.0
        # H = -(0.9*log2(0.9) + 0.1*log2(0.1)) / log2(2)
        expected = -(0.9 * math.log2(0.9) + 0.1 * math.log2(0.1))
        assert abs(entropy - expected) < 1e-6

    def test_empty_array_returns_zero(self):
        tae = MindGuardTAE()
        assert tae.compute_temporal_entropy(np.array([])) == 0.0

    def test_single_element_returns_zero(self):
        tae = MindGuardTAE()
        assert tae.compute_temporal_entropy(np.array([1.0])) == 0.0

    def test_all_zeros_returns_zero(self):
        tae = MindGuardTAE()
        assert tae.compute_temporal_entropy(np.zeros(10)) == 0.0

    def test_2d_attention_matrix(self):
        """2-D input: entropy averaged over rows."""
        tae = MindGuardTAE()
        # 4 rows, each uniform over 8 positions
        attn = np.ones((4, 8)) / 8
        entropy = tae.compute_temporal_entropy(attn)
        assert 0.99 <= entropy <= 1.0

    def test_negative_values_clipped(self):
        """Negative values should be clipped to 0."""
        tae = MindGuardTAE()
        dist = np.array([-0.5, 0.5, 0.5, 0.5])
        entropy = tae.compute_temporal_entropy(dist)
        assert 0.0 <= entropy <= 1.0

    def test_unnormalized_input(self):
        """Input that doesn't sum to 1 should be auto-normalized."""
        tae = MindGuardTAE()
        dist = np.array([2.0, 2.0, 2.0, 2.0])
        entropy = tae.compute_temporal_entropy(dist)
        # Should be same as uniform: 1.0
        assert abs(entropy - 1.0) < 1e-6


# ── Dilution Attack Detection Tests ───────────────────────────────────────

class TestDilutionAttackDetection:
    """Test MindGuardTAE.detect_dilution_attack."""

    def test_high_entropy_triggers_dilution(self):
        tae = MindGuardTAE(dilution_threshold=0.25)
        # All heads at entropy 0.9 → mean = 0.9 > 0.25
        assert tae.detect_dilution_attack([0.9, 0.85, 0.92, 0.88]) is True

    def test_low_entropy_no_dilution(self):
        tae = MindGuardTAE(dilution_threshold=0.25)
        # All heads at entropy 0.1 → mean = 0.1 < 0.25
        assert tae.detect_dilution_attack([0.1, 0.12, 0.08, 0.11]) is False

    def test_borderline_entropy(self):
        tae = MindGuardTAE(dilution_threshold=0.25)
        # Mean exactly at threshold
        assert tae.detect_dilution_attack([0.25, 0.25]) is False  # not strictly >
        assert tae.detect_dilution_attack([0.26, 0.26]) is True

    def test_empty_list_no_dilution(self):
        tae = MindGuardTAE(dilution_threshold=0.25)
        assert tae.detect_dilution_attack([]) is False

    def test_single_head_above_threshold(self):
        tae = MindGuardTAE(dilution_threshold=0.25)
        assert tae.detect_dilution_attack([0.5]) is True

    def test_mixed_heads_mean_above(self):
        tae = MindGuardTAE(dilution_threshold=0.25)
        # Mean = (0.1 + 0.5) / 2 = 0.3 > 0.25
        assert tae.detect_dilution_attack([0.1, 0.5]) is True


# ── Delegation Attack Detection Tests ─────────────────────────────────────

class TestDelegationAttackDetection:
    """Test MindGuardTAE.detect_delegation_attack."""

    def test_concentrated_head_triggers_delegation(self):
        tae = MindGuardTAE(delegation_threshold=0.15)
        # Head 0 has entropy 0.05 < 0.15
        heads = tae.detect_delegation_attack([0.05, 0.8, 0.7, 0.9])
        assert heads == [0]

    def test_no_concentrated_heads(self):
        tae = MindGuardTAE(delegation_threshold=0.15)
        heads = tae.detect_delegation_attack([0.5, 0.6, 0.7, 0.8])
        assert heads == []

    def test_multiple_concentrated_heads(self):
        tae = MindGuardTAE(delegation_threshold=0.15)
        # Heads 0, 2 have entropy below threshold
        heads = tae.detect_delegation_attack([0.05, 0.8, 0.10, 0.9])
        assert sorted(heads) == [0, 2]

    def test_empty_list_no_delegation(self):
        tae = MindGuardTAE(delegation_threshold=0.15)
        assert tae.detect_delegation_attack([]) == []

    def test_min_suspicious_heads_filtering(self):
        tae = MindGuardTAE(delegation_threshold=0.15, min_suspicious_heads=2)
        # Only 1 head below threshold → not enough
        heads = tae.detect_delegation_attack([0.05, 0.8, 0.7, 0.9])
        assert heads == []
        # 2 heads below → triggers
        heads = tae.detect_delegation_attack([0.05, 0.8, 0.10, 0.9])
        assert len(heads) == 2

    def test_borderline_entropy(self):
        tae = MindGuardTAE(delegation_threshold=0.15)
        # Exactly at threshold → not below
        heads = tae.detect_delegation_attack([0.15, 0.8])
        assert heads == []
        # Just below
        heads = tae.detect_delegation_attack([0.14, 0.8])
        assert heads == [0]


# ── inspect_attention Integration Tests ────────────────────────────────────

class TestInspectAttention:
    """Test the full MindGuardTAE.inspect_attention pipeline."""

    def test_fallback_safe_on_none(self):
        tae = MindGuardTAE()
        result = tae.inspect_attention(attention_maps=None)
        assert result.is_safe is True
        assert result.entropy_score == 0.0
        assert result.detected_patterns == []
        assert "pass_through" in result.recommendation

    def test_fallback_safe_on_empty_list(self):
        tae = MindGuardTAE()
        result = tae.inspect_attention(attention_maps=[])
        assert result.is_safe is True

    def test_fallback_safe_on_none_elements(self):
        tae = MindGuardTAE()
        result = tae.inspect_attention(attention_maps=[None, None])
        assert result.is_safe is True

    def test_uniform_attention_triggers_dilution(self):
        """Uniform attention across 8 heads → high entropy → dilution."""
        tae = MindGuardTAE(dilution_threshold=0.25)
        attn = make_uniform_attention(num_heads=8, seq_len=32)
        result = tae.inspect_attention(attention_maps=[attn])
        assert result.is_safe is False
        assert "attention_dilution" in result.detected_patterns
        assert result.entropy_score > 0.25

    def test_concentrated_attention_triggers_delegation(self):
        """All heads concentrated on position 0 → low entropy → delegation."""
        tae = MindGuardTAE(delegation_threshold=0.15)
        attn = make_concentrated_attention(num_heads=8, seq_len=32)
        result = tae.inspect_attention(attention_maps=[attn])
        assert result.is_safe is False
        assert any("delegation" in p for p in result.detected_patterns)
        assert result.entropy_score < 0.15

    def test_normal_attention_is_safe(self):
        """Middle-range entropy should be safe."""
        tae = MindGuardTAE(dilution_threshold=0.80, delegation_threshold=0.05)
        # Create attention with moderate entropy using a peaked Dirichlet.
        # Alpha vector with one dominant position produces concentrated
        # distributions (entropy well below 0.80).
        np.random.seed(42)
        alpha = np.ones(16) * 0.5
        alpha[0] = 10.0  # Dominant position → low entropy per row
        attn = np.random.dirichlet(alpha, size=(8, 16))
        # Shape: (8 heads, 16 rows, 16 cols)
        result = tae.inspect_attention(attention_maps=[attn])
        assert result.is_safe is True
        assert result.detected_patterns == []

    def test_mixed_attention_detects_both(self):
        """Some heads concentrated + overall high entropy → both anomalies."""
        tae = MindGuardTAE(
            dilution_threshold=0.20,
            delegation_threshold=0.15,
        )
        # 8 heads: 2 concentrated (entropy~0), 6 uniform (entropy~1)
        # Mean entropy ≈ (2*0 + 6*1)/8 = 0.75 > 0.20  → dilution
        # Heads 0,1 entropy < 0.15  → delegation
        attn = make_mixed_attention(
            num_heads=8, seq_len=32, concentrated_heads=2,
        )
        result = tae.inspect_attention(attention_maps=[attn])
        assert not result.is_safe
        assert "attention_dilution" in result.detected_patterns
        assert any("delegation" in p for p in result.detected_patterns)

    def test_multi_layer_attention(self):
        """Multiple attention map arrays (one per layer)."""
        tae = MindGuardTAE(dilution_threshold=0.25)
        layer1 = make_uniform_attention(4, 16)
        layer2 = make_uniform_attention(4, 16)
        result = tae.inspect_attention(attention_maps=[layer1, layer2])
        assert not result.is_safe
        assert len(result.head_entropies) == 8  # 4 + 4

    def test_batched_4d_attention(self):
        """4-D array: (batch=1, heads=4, seq=16, seq=16)."""
        tae = MindGuardTAE(dilution_threshold=0.25)
        attn = make_uniform_attention(4, 16).reshape(1, 4, 16, 16)
        result = tae.inspect_attention(attention_maps=[attn])
        assert not result.is_safe
        assert len(result.head_entropies) == 4

    def test_latency_recorded(self):
        tae = MindGuardTAE()
        attn = make_uniform_attention(4, 8)
        result = tae.inspect_attention(attention_maps=[attn])
        assert isinstance(result.latency_ms, int)
        assert result.latency_ms >= 0

    def test_recommendation_contains_escalate_on_unsafe(self):
        tae = MindGuardTAE(dilution_threshold=0.25)
        attn = make_uniform_attention(8, 32)
        result = tae.inspect_attention(attention_maps=[attn])
        assert "ESCALATE_L3" in result.recommendation

    def test_recommendation_contains_safe_on_safe(self):
        # Use moderately concentrated attention (entropy ~ 0.5-0.7) with
        # thresholds set so the entropy falls in the safe zone.
        tae = MindGuardTAE(dilution_threshold=0.99, delegation_threshold=0.001)
        np.random.seed(99)
        # Dirichlet with alpha=3.0 produces moderate concentration
        attn = np.random.dirichlet(np.ones(8) * 3.0, size=(4, 8))
        result = tae.inspect_attention(attention_maps=[attn])
        assert "safe" in result.recommendation

    def test_residual_stream_ignored_gracefully(self):
        """residual_stream param is accepted but doesn't affect result (v1)."""
        tae = MindGuardTAE()
        attn = make_uniform_attention(4, 8)
        residual = np.random.randn(28, 2048)
        result = tae.inspect_attention(
            attention_maps=[attn], residual_stream=residual,
        )
        assert isinstance(result, MindGuardResult)


# ── Constructor Validation Tests ───────────────────────────────────────────

class TestConstructorValidation:
    """Test MindGuardTAE constructor edge cases."""

    def test_default_thresholds(self):
        tae = MindGuardTAE()
        assert tae.dilution_threshold == 0.25
        assert tae.delegation_threshold == 0.15
        assert tae.min_suspicious_heads == 1

    def test_custom_thresholds(self):
        tae = MindGuardTAE(
            dilution_threshold=0.5,
            delegation_threshold=0.3,
            min_suspicious_heads=3,
        )
        assert tae.dilution_threshold == 0.5
        assert tae.delegation_threshold == 0.3
        assert tae.min_suspicious_heads == 3

    def test_invalid_dilution_threshold(self):
        with pytest.raises(ValueError):
            MindGuardTAE(dilution_threshold=0.0)
        with pytest.raises(ValueError):
            MindGuardTAE(dilution_threshold=1.0)
        with pytest.raises(ValueError):
            MindGuardTAE(dilution_threshold=-0.5)

    def test_invalid_delegation_threshold(self):
        with pytest.raises(ValueError):
            MindGuardTAE(delegation_threshold=0.0)
        with pytest.raises(ValueError):
            MindGuardTAE(delegation_threshold=1.0)

    def test_min_suspicious_heads_clamped(self):
        tae = MindGuardTAE(min_suspicious_heads=0)
        assert tae.min_suspicious_heads == 1  # clamped to 1
        tae = MindGuardTAE(min_suspicious_heads=-5)
        assert tae.min_suspicious_heads == 1


# ── Guard Router Integration Tests ────────────────────────────────────────

class TestGuardRouterIntegration:
    """Test that MindGuardTAE is properly wired into guard_router.py."""

    def test_l2_mindguard_tae_available_flag(self):
        from nexus_os.security.guard_router import L2_MINDGUARD_TAE_AVAILABLE
        assert L2_MINDGUARD_TAE_AVAILABLE is True

    def test_tier_thresholds_has_tae_config(self):
        from nexus_os.security.guard_router import TIER_THRESHOLDS
        l2_cfg = TIER_THRESHOLDS["L2"]
        assert "tae" in l2_cfg
        tae_cfg = l2_cfg["tae"]
        assert "enabled" in tae_cfg
        assert "dilution_threshold" in tae_cfg
        assert "delegation_threshold" in tae_cfg
        assert "min_suspicious_heads" in tae_cfg

    def test_tae_config_values_match_l2(self):
        from nexus_os.security.guard_router import TIER_THRESHOLDS
        l2_cfg = TIER_THRESHOLDS["L2"]
        tae_cfg = l2_cfg["tae"]
        # TAE thresholds should match the L2 parent config defaults
        assert tae_cfg["dilution_threshold"] == l2_cfg["dilution_threshold"]
        assert tae_cfg["delegation_threshold"] == l2_cfg["delegation_threshold"]

    def test_mindguard_tae_importable_from_security(self):
        """Verify the module is importable from the security package."""
        from nexus_os.security.mindguard_tae import MindGuardTAE, MindGuardResult
        assert MindGuardTAE is not None
        assert MindGuardResult is not None

    def test_existing_l2_config_preserved(self):
        """Verify existing L2 config (MindGuardClient) is NOT removed."""
        from nexus_os.security.guard_router import TIER_THRESHOLDS
        l2 = TIER_THRESHOLDS["L2"]
        assert l2["backend"] == "mindguard"
        assert l2["fallback_model"] == "meta-llama/Llama-Guard-3-1B"
        assert l2["fallback_backend"] == "ollama"
        assert "delegation_threshold" in l2
        assert "dilution_threshold" in l2
        assert "sink_filter_topk" in l2

    def test_existing_mindguard_client_preserved(self):
        """Verify the original MindGuardClient class still exists."""
        from nexus_os.security.guard_router import MindGuardClient
        assert MindGuardClient is not None

    def test_make_client_still_returns_mindguard(self):
        """Verify make_client still returns MindGuardClient for mindguard backend."""
        from nexus_os.security.guard_router import make_client, MindGuardClient
        client = make_client({"backend": "mindguard"})
        assert isinstance(client, MindGuardClient)


# ── Numpy Tensor Conversion Tests ─────────────────────────────────────────

class TestNumpyConversion:
    """Test MindGuardTAE._to_numpy_maps handles various input types."""

    def test_numpy_array_passthrough(self):
        tae = MindGuardTAE()
        arr = np.ones((4, 8, 8))
        maps = tae._to_numpy_maps([arr])
        assert len(maps) == 1
        assert maps[0].dtype == np.float64

    def test_nested_list_conversion(self):
        tae = MindGuardTAE()
        data = [[[1.0, 0.0], [0.0, 1.0]]]
        maps = tae._to_numpy_maps([data])
        assert len(maps) == 1
        assert isinstance(maps[0], np.ndarray)

    def test_none_elements_skipped(self):
        tae = MindGuardTAE()
        maps = tae._to_numpy_maps([None, np.ones((2, 4, 4)), None])
        assert len(maps) == 1

    def test_empty_input(self):
        tae = MindGuardTAE()
        assert tae._to_numpy_maps([]) == []
