#!/usr/bin/env python3
"""
mindguard_tae.py
MindGuard Temporal Attention Entropy (TAE) Inspector — L2 Enhancement.

Inspects attention patterns from the L1 forward pass to detect hidden
jailbreak prompts via two entropy-based anomalies:

  1. Attention Dilution Attack: abnormally HIGH entropy across attention
     heads indicates the prompt distributes attention uniformly to
     mask a hidden payload among many distractors.

  2. Delegation Attack: abnormally LOW entropy on specific heads
     indicates concentrated attention on injected tool/metadata
     segments, hijacking decision provenance.

Design philosophy:
  - Uses NUMPY ONLY for tensor operations (no torch dependency).
  - Runs on CPU — no VRAM required.
  - Fallback-safe: returns pass-through SAFE when no attention data
    is available (L1 forward pass did not emit attentions).
  - Operates as an OPTIONAL enhancement before the existing L2 text
    guard (MindGuardClient / Llama-Guard-3-1B).  Does NOT replace it.

Reference: arXiv 2508.20412 (Decision Dependence Graphs, TAE analysis)
"""

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import numpy as np

logger = logging.getLogger(__name__)

__all__ = ["MindGuardTAE", "MindGuardResult"]


# ── Result Dataclass ───────────────────────────────────────────────────────

@dataclass
class MindGuardResult:
    """Result of a MindGuard TAE inspection.

    Attributes:
        is_safe: True if no anomalous attention patterns were detected.
        entropy_score: Aggregate Shannon entropy across attention heads
                       (mean of per-head entropies, normalized to [0, 1]).
        detected_patterns: List of detected anomaly labels, e.g.
                           ["attention_dilution", "delegation_head_3"].
        recommendation: Human-readable action recommendation.
        head_entropies: Per-head entropy values (for audit/debug).
        latency_ms: Processing time in milliseconds.
    """
    is_safe: bool
    entropy_score: float
    detected_patterns: List[str] = field(default_factory=list)
    recommendation: str = ""
    head_entropies: List[float] = field(default_factory=list)
    latency_ms: int = 0


# ── TAE Inspector ──────────────────────────────────────────────────────────

class MindGuardTAE:
    """Temporal Attention Entropy inspector for the L2 guard cascade.

    Examines attention maps (numpy arrays or lists convertible to numpy)
    to detect dilution and delegation attacks via Shannon entropy analysis.

    Args:
        dilution_threshold: Mean head entropy ABOVE this triggers dilution
                            anomaly.  Default 0.25 (normalized).
        delegation_threshold: Per-head entropy BELOW this triggers delegation
                              anomaly.  Default 0.15 (normalized).
        min_suspicious_heads: Minimum number of low-entropy heads required
                              to flag a delegation attack.  Default 1.
    """

    def __init__(
        self,
        dilution_threshold: float = 0.25,
        delegation_threshold: float = 0.15,
        min_suspicious_heads: int = 1,
    ):
        if dilution_threshold <= 0 or dilution_threshold >= 1:
            raise ValueError(
                f"dilution_threshold must be in (0, 1), got {dilution_threshold}"
            )
        if delegation_threshold <= 0 or delegation_threshold >= 1:
            raise ValueError(
                f"delegation_threshold must be in (0, 1), got {delegation_threshold}"
            )
        self.dilution_threshold = dilution_threshold
        self.delegation_threshold = delegation_threshold
        self.min_suspicious_heads = max(1, min_suspicious_heads)

    # ── Public API ─────────────────────────────────────────────────────

    def inspect_attention(
        self,
        attention_maps: Optional[List[Any]] = None,
        residual_stream: Optional[np.ndarray] = None,
    ) -> MindGuardResult:
        """Run TAE inspection on attention data from an L1 forward pass.

        Args:
            attention_maps: List of attention weight arrays.  Each element
                can be a numpy array of shape (..., num_heads, seq, seq)
                or any object with a `.numpy()` method (torch tensor).
                If None or empty, returns fallback safe result.
            residual_stream: Optional residual stream activations (unused
                in current version, reserved for future residual-entropy
                analysis).  Shape: (layers, hidden_dim) or similar.

        Returns:
            MindGuardResult with safety verdict, entropy score, and
            detected anomaly patterns.
        """
        t0 = time.perf_counter()

        # Fallback: no attention data available
        if not attention_maps:
            result = self._fallback_safe_result()
            result.latency_ms = int((time.perf_counter() - t0) * 1000)
            return result

        # Convert attention maps to numpy
        np_maps = self._to_numpy_maps(attention_maps)
        if not np_maps:
            result = self._fallback_safe_result()
            result.latency_ms = int((time.perf_counter() - t0) * 1000)
            return result

        # Compute per-head entropy across all layers
        head_entropies = []
        for attn in np_maps:
            layer_entropies = self._compute_head_entropies(attn)
            head_entropies.extend(layer_entropies)

        if not head_entropies:
            result = self._fallback_safe_result()
            result.latency_ms = int((time.perf_counter() - t0) * 1000)
            return result

        # Aggregate entropy score (mean, normalized)
        entropy_score = float(np.mean(head_entropies))

        # Run anomaly detectors
        detected_patterns: List[str] = []

        if self.detect_dilution_attack(head_entropies):
            detected_patterns.append("attention_dilution")

        delegation_heads = self.detect_delegation_attack(head_entropies)
        if delegation_heads:
            for head_idx in delegation_heads:
                detected_patterns.append(
                    f"delegation_head_{head_idx}"
                )

        # Build result
        is_safe = len(detected_patterns) == 0
        recommendation = self._build_recommendation(
            is_safe, detected_patterns, entropy_score
        )

        result = MindGuardResult(
            is_safe=is_safe,
            entropy_score=round(entropy_score, 6),
            detected_patterns=detected_patterns,
            recommendation=recommendation,
            head_entropies=[round(h, 6) for h in head_entropies],
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
        return result

    def compute_temporal_entropy(self, attention: np.ndarray) -> float:
        """Compute Shannon entropy of a single attention distribution.

        Args:
            attention: 1-D or 2-D numpy array of attention weights.
                       If 2-D, entropy is computed over the last axis
                       and then averaged.

        Returns:
            Normalized Shannon entropy in [0, 1].  Returns 0.0 for
            degenerate inputs (all zeros, single element, etc.).
        """
        attention = np.asarray(attention, dtype=np.float64)

        if attention.size == 0:
            return 0.0

        if attention.ndim == 1:
            return self._shannon_entropy_1d(attention)

        if attention.ndim == 2:
            entropies = [
                self._shannon_entropy_1d(attention[i])
                for i in range(attention.shape[0])
            ]
            return float(np.mean(entropies)) if entropies else 0.0

        # For higher-dim, flatten to 2-D (heads × seq)
        flat = attention.reshape(-1, attention.shape[-1])
        entropies = [
            self._shannon_entropy_1d(flat[i])
            for i in range(flat.shape[0])
        ]
        return float(np.mean(entropies)) if entropies else 0.0

    def detect_dilution_attack(self, entropy_scores: List[float]) -> bool:
        """Check if mean entropy exceeds the dilution threshold.

        A dilution attack distributes attention uniformly across many
        tokens, producing abnormally high entropy across most heads.

        Args:
            entropy_scores: List of per-head normalized entropy values.

        Returns:
            True if the mean entropy exceeds dilution_threshold.
        """
        if not entropy_scores:
            return False
        mean_entropy = float(np.mean(entropy_scores))
        return mean_entropy > self.dilution_threshold

    def detect_delegation_attack(
        self, entropy_scores: List[float]
    ) -> List[int]:
        """Find heads with entropy below the delegation threshold.

        A delegation attack concentrates attention on specific injected
        segments (tool metadata, hidden instructions), causing one or
        more heads to have abnormally low entropy.

        Args:
            entropy_scores: List of per-head normalized entropy values.

        Returns:
            List of head indices with entropy below delegation_threshold.
            Empty list if fewer than min_suspicious_heads are found.
        """
        if not entropy_scores:
            return []
        suspicious = [
            i for i, e in enumerate(entropy_scores)
            if e < self.delegation_threshold
        ]
        if len(suspicious) >= self.min_suspicious_heads:
            return suspicious
        return []

    # ── Private helpers ────────────────────────────────────────────────

    def _fallback_safe_result(self) -> MindGuardResult:
        """Return a pass-through safe result when no attention data is
        available.  This ensures the cascade continues to L2 text guard
        without blocking.
        """
        return MindGuardResult(
            is_safe=True,
            entropy_score=0.0,
            detected_patterns=[],
            recommendation="pass_through: no attention data available, deferring to L2 text guard",
            head_entropies=[],
            latency_ms=0,
        )

    def _shannon_entropy_1d(self, dist: np.ndarray) -> float:
        """Compute normalized Shannon entropy of a 1-D distribution.

        Returns value in [0, 1] where 0 = perfectly concentrated
        (delta function) and 1 = perfectly uniform.
        """
        dist = np.asarray(dist, dtype=np.float64).ravel()
        # Ensure non-negative
        dist = np.maximum(dist, 0.0)

        total = dist.sum()
        if total <= 0:
            return 0.0

        # Normalize to probability distribution
        p = dist / total

        # Filter out zeros to avoid log(0)
        p = p[p > 0]
        if len(p) <= 1:
            return 0.0

        # Shannon entropy: H = -sum(p * log2(p))
        entropy = -np.sum(p * np.log2(p))

        # Normalize by max possible entropy: log2(N)
        max_entropy = np.log2(len(dist))
        if max_entropy <= 0:
            return 0.0

        return float(np.clip(entropy / max_entropy, 0.0, 1.0))

    def _to_numpy_maps(self, attention_maps: List[Any]) -> List[np.ndarray]:
        """Convert a list of attention tensors to numpy arrays.

        Handles:
        - Already numpy arrays
        - Objects with .numpy() method (torch tensors)
        - Objects with .detach().cpu().numpy() chain (GPU torch tensors)
        - Nested lists
        """
        result = []
        for attn in attention_maps:
            if attn is None:
                continue
            try:
                if isinstance(attn, np.ndarray):
                    result.append(attn.astype(np.float64))
                elif hasattr(attn, "detach"):
                    # Torch tensor (possibly on GPU)
                    arr = attn.detach().cpu().numpy().astype(np.float64)
                    result.append(arr)
                elif hasattr(attn, "numpy"):
                    result.append(attn.numpy().astype(np.float64))
                else:
                    # Try direct conversion (list of lists, etc.)
                    result.append(np.asarray(attn, dtype=np.float64))
            except Exception as e:
                logger.warning(
                    "MindGuardTAE: failed to convert attention map: %s", e
                )
                continue
        return result

    def _compute_head_entropies(self, attn: np.ndarray) -> List[float]:
        """Compute per-head normalized entropy from an attention array.

        Handles shapes:
        - (num_heads, seq_len, seq_len)  — single layer
        - (batch, num_heads, seq_len, seq_len) — batched
        - (seq_len, seq_len) — single head
        """
        if attn.ndim == 2:
            # Single head: (seq, seq)
            return [self.compute_temporal_entropy(attn)]

        if attn.ndim == 3:
            # (num_heads, seq, seq)
            return [
                self.compute_temporal_entropy(attn[h])
                for h in range(attn.shape[0])
            ]

        if attn.ndim == 4:
            # (batch, num_heads, seq, seq) — use first batch element
            return [
                self.compute_temporal_entropy(attn[0, h])
                for h in range(attn.shape[1])
            ]

        # Unexpected shape — compute entropy on flattened last two dims
        logger.warning(
            "MindGuardTAE: unexpected attention shape %s, flattening",
            attn.shape,
        )
        return [self.compute_temporal_entropy(attn.reshape(-1, attn.shape[-1]))]

    def _build_recommendation(
        self,
        is_safe: bool,
        patterns: List[str],
        entropy_score: float,
    ) -> str:
        """Build a human-readable recommendation string."""
        if is_safe:
            return f"safe: entropy={entropy_score:.4f} within normal range"

        parts = []
        has_dilution = any("dilution" in p for p in patterns)
        has_delegation = any("delegation" in p for p in patterns)

        if has_dilution:
            parts.append(
                f"attention_dilution detected (mean_entropy={entropy_score:.4f} "
                f"> threshold={self.dilution_threshold})"
            )
        if has_delegation:
            n_heads = sum(1 for p in patterns if "delegation" in p)
            parts.append(
                f"delegation_attack detected on {n_heads} head(s) "
                f"(entropy < threshold={self.delegation_threshold})"
            )

        return "ESCALATE_L3: " + "; ".join(parts)
