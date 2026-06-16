"""token_confidence.py — CK-PLUG-inspired token-level confidence gain for trust formula Q input.

CK-PLUG (Confidence Gain for Plug-in Robustness) proposes using token-level
confidence from LLM inference to produce a confidence gain score that acts as an
additional quality signal. The key insight: tokens with low confidence may
indicate hallucination, uncertainty, or degraded reasoning, while high-confidence
tokens indicate reliable inference.

This module provides:
  - TokenConfidenceGain: computes a normalized confidence gain score from
    raw token-level log-probs or confidence values (0.0-1.0 per token).
  - QEnhancer: blends an existing Q score with the confidence gain score
    using configurable weights (advisory-only, does not override deterministic
    trust formula boundaries).

Usage:
    from nexus_os.governor.token_confidence import QEnhancer, TokenConfidenceGain
    enhancer = QEnhancer(confidence_weight=0.3)
    token_confidences = [0.9, 0.85, 0.12, 0.88, 0.91]  # from LLM logits
    Q_original = 0.75
    Q_enhanced = enhancer.enhance(Q_original, token_confidences)
    # Q_enhanced is a blend: 70% original + 30% confidence gain

The confidence gain is clipped to [0, 1] and the enhanced Q is also clipped
to [0, 1], preserving all trust formula invariants (INV3 boundedness, etc.).

Inspired by:
  - CK-PLUG: Confidence Gain for Plug-in Robustness (arXiv:2501.00314)
  - HeavySkill: Multiple independent reasoning paths (arXiv:2505.03045)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence


class TokenConfidenceGain:
    """Compute a normalized confidence gain score from token-level confidences.

    Three aggregation modes are supported:
      - mean: arithmetic mean of token confidences (default, stable)
      - min: minimum token confidence (strict, catches worst-case uncertainty)
      - harmonic: harmonic mean (penalizes low-confidence tokens strongly)
    """

    def __init__(self, mode: str = "mean") -> None:
        if mode not in ("mean", "min", "harmonic"):
            raise ValueError(f"Invalid mode: {mode}. Use 'mean', 'min', or 'harmonic'.")
        self.mode = mode

    def compute(self, token_confidences: Sequence[float]) -> float:
        """Return confidence gain in [0, 1] from a sequence of token confidences.

        Each token confidence should be in [0, 1] (1.0 = certain, 0.0 = uncertain).
        The result is also in [0, 1].
        """
        if not token_confidences:
            return 0.0

        # Validate and clip input
        valid = [max(0.0, min(1.0, float(c))) for c in token_confidences]

        if self.mode == "mean":
            return sum(valid) / len(valid)
        if self.mode == "min":
            return min(valid)
        if self.mode == "harmonic":
            # Harmonic mean: n / sum(1/x). For x=0, we use epsilon to avoid division by zero.
            eps = 1e-9
            inv_sum = sum(1.0 / (max(eps, v)) for v in valid)
            return len(valid) / inv_sum
        return 0.0

    @staticmethod
    def from_logprobs(logprobs: Sequence[float]) -> List[float]:
        """Convert log-probabilities to confidence values via exp(logprob).

        Assumes logprobs are negative (or zero). The result is clipped to [0, 1].
        """
        confidences = []
        for lp in logprobs:
            # exp(logprob) gives raw probability. For very small logprobs, clip to 0.
            c = math.exp(float(lp)) if float(lp) > -100 else 0.0
            confidences.append(max(0.0, min(1.0, c)))
        return confidences


@dataclass
class QEnhancer:
    """Blend an existing Q (quality) score with token-level confidence gain.

    The enhanced Q is:
        Q_enhanced = (1 - w) * Q_original + w * confidence_gain

    where w = confidence_weight (0.0 to 1.0).

    If no token confidences are provided, returns Q_original unchanged.
    The result is always clipped to [0, 1].

    Advisory-only: This enhancement does not change the trust formula's core
    boundaries (qmin, epsilon, etc.). It merely provides an optional signal
    that can be blended into the Q input before scoring.
    """

    confidence_weight: float = 0.3
    mode: str = "mean"
    # Minimum Q to enforce even if confidence is very low (preserves qmin semantics)
    floor: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_weight <= 1.0:
            raise ValueError("confidence_weight must be in [0, 1]")
        if not 0.0 <= self.floor <= 1.0:
            raise ValueError("floor must be in [0, 1]")

    def enhance(
        self,
        Q_original: float,
        token_confidences: Optional[Sequence[float]] = None,
    ) -> float:
        """Return enhanced Q score.

        If token_confidences is None or empty, returns Q_original unchanged.
        """
        Q_original = max(0.0, min(1.0, float(Q_original)))

        if token_confidences is None or len(token_confidences) == 0:
            return Q_original

        gain = TokenConfidenceGain(mode=self.mode).compute(token_confidences)
        blended = (1.0 - self.confidence_weight) * Q_original + self.confidence_weight * gain
        enhanced = max(self.floor, min(1.0, blended))
        return enhanced

    def batch_enhance(
        self,
        Q_originals: Sequence[float],
        token_confidences_list: Sequence[Optional[Sequence[float]]],
    ) -> List[float]:
        """Enhance multiple Q scores in batch."""
        return [
            self.enhance(q, tc)
            for q, tc in zip(Q_originals, token_confidences_list)
        ]
