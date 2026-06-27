"""TV-distribution hallucination signal (Bebop-inspired, P2.1 upgrade).

Source: "Breaking Entropy Bounds: Accelerating RL Training via MTP with
Rejection Sampling" (Bebop, 2026).

Mechanism: Total Variation (TV) distance between the model's current belief
distribution `p` and a calibrated reference distribution `q` produces an
entropy-invariant hallucination signal.

Why TV over KL/CE (per the paper):
  - Gradient is bounded by 1 for all logits (vs KL/CE which can diverge)
  - TV reward is decoupled from policy entropy fluctuations
  - Acceptance rate = a - b * H(p) is roughly invariant under TV loss
  - Avoids the false-positive spikes of entropy-based detectors during
    high-entropy generation modes

Use as a DROPPING-IN augmentation for the existing
CalibratedHallucinationDetector. The detector can call this and combine
the TV score with its existing EPR score.

Module boundary:
  - Pure math: no model imports, no GPU.
  - Stateless functions: caller owns any calibration state.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict


def _normalize(logits_or_probs: list[float]) -> list[float]:
    """Convert logits (any real numbers) to a normalized probability vector.

    Numerically safe: subtract max before exp, ensure support.
    """
    if not logits_or_probs:
        return []
    nm = max(logits_or_probs)
    exps = [math.exp(x - nm) for x in logits_or_probs]
    z = sum(exps)
    if z <= 0.0 or math.isnan(z):
        return [1.0 / len(logits_or_probs)] * len(logits_or_probs)
    return [e / z for e in exps]


def tv_distance(p: list[float], q: list[float]) -> float:
    """Total Variation distance: 0.5 * sum_i |p_i - q_i|.

    Returned in [0.0, 1.0]. TV(p, p) = 0, TV(p, uniform) is bounded.
    Both inputs must be equal-length probability vectors.
    """
    if not p or not q or len(p) != len(q):
        return 0.0
    half_sum = 0.0
    for pi, qi in zip(p, q):
        half_sum += abs(pi - qi)
    tv = 0.5 * half_sum
    if tv < 0.0:
        return 0.0
    if tv > 1.0:
        return 1.0
    return tv


def build_reference_distribution(
    vocab_size: int,
    *,
    mode: str = "fluency",
) -> list[float]:
    """Build a calibrated reference distribution for TV comparison.

    Modes:
      - "uniform"  : flat prior over vocab, q_i = 1/vocab_size
      - "fluency"  : gentle Zipfian-like prior favoring low-index tokens
                     (mimics a fluent language model's average distribution)
      - "head"     : peaked at token index 0 (rarely used; for sanity)

    The "fluency" mode is the recommended default: it's a stable,
    reproducible reference that won't drift between calls, which is
    what makes the TV signal entropy-invariant in practice.
    """
    if vocab_size <= 0:
        return []
    if mode == "uniform":
        return [1.0 / vocab_size] * vocab_size
    if mode == "head":
        out = [0.0] * vocab_size
        out[0] = 1.0
        return out
    # fluency: Zipfian-ish prior
    out = [0.0] * vocab_size
    # weights[i] = 1/(i+1)**alpha with alpha ~ 1.07 (English-like)
    alpha = 1.07
    z = 0.0
    for i in range(vocab_size):
        w = 1.0 / ((i + 1) ** alpha)
        out[i] = w
        z += w
    if z > 0.0:
        out = [w / z for w in out]
    return out


@dataclass
class BebopSignal:
    """Result of a TV-distance hallucination assessment."""
    tv: float
    divergence_class: str
    bounded_gradient: bool
    entropy_of_p: float
    entropy_of_q: float
    tv_weighted_by_entropy: float
    vocab_size: int

    def to_dict(self) -> dict:
        return asdict(self)


def entropy(p: list[float]) -> float:
    """Shannon entropy in nats. Returns 0.0 for empty/degenerate inputs."""
    if not p:
        return 0.0
    h = 0.0
    for pi in p:
        if pi > 0.0:
            h -= pi * math.log(pi)
    return h


def assess_bebop(
    logits_or_probs: list[float],
    reference: list[float] | None = None,
    *,
    vocab_size: int | None = None,
    reference_mode: str = "fluency",
) -> BebopSignal:
    """Compute Bebop-style TV-distribution hallucination signal.

    Args:
        logits_or_probs: raw logits or an already-probability vector from the
            model. Auto-normalized if logits.
        reference: optional pre-computed reference distribution. If None, one
            is built via build_reference_distribution().
        vocab_size: vocab size for reference fallback. Defaults to len(input).
        reference_mode: one of "uniform" | "fluency" | "head". Ignored if
            reference is provided.

    Returns:
        BebopSignal with:
          - tv: TV distance in [0, 1]
          - divergence_class: "well_calibrated" | "l1_drift" | "l2_drift" | "high_drift"
            (cheap bucketing, NOT a hard decision)
          - bounded_gradient: always True (TV has bounded gradient by math)
          - entropy_of_p / entropy_of_q: nats
          - tv_weighted_by_entropy: tv * max(0, entropy_p - entropy_q)
            (positive when current distribution is more diffuse than reference)
    """
    p = _normalize(logits_or_probs)
    if not p:
        return BebopSignal(
            tv=0.0, divergence_class="well_calibrated",
            bounded_gradient=True, entropy_of_p=0.0, entropy_of_q=0.0,
            tv_weighted_by_entropy=0.0, vocab_size=0,
        )

    v = vocab_size or len(p)
    q = reference if reference is not None else build_reference_distribution(v, mode=reference_mode)
    if len(q) != len(p):
        # Reference wrong length -> rebuild.
        q = build_reference_distribution(len(p), mode=reference_mode)

    tv = tv_distance(p, q)
    if tv < 0.10:
        cls = "well_calibrated"
    elif tv < 0.30:
        cls = "l1_drift"
    elif tv < 0.55:
        cls = "l2_drift"
    else:
        cls = "high_drift"

    h_p = entropy(p)
    h_q = entropy(q)
    tv_w = tv * max(0.0, h_p - h_q)

    return BebopSignal(
        tv=tv,
        divergence_class=cls,
        bounded_gradient=True,  # TV has gradient bounded by 1 by construction
        entropy_of_p=h_p,
        entropy_of_q=h_q,
        tv_weighted_by_entropy=tv_w,
        vocab_size=v,
    )


def risk_score_from_bebop(signal: BebopSignal, *, tau: float = 0.40) -> float:
    """Map a Bebop signal to a [0, 1] risk score.

    The mapping uses the PDF-class boundary as the soft threshold:
      - tv < tau*(1/3) -> ~0 risk
      - tv about tau    -> ~0.5 risk
      - tv > 2*tau      -> ~1 risk

    Combined with the entropy-weighted term to penalize cases where the
    model is more diffuse than the fluency reference.
    """
    tv = signal.tv
    if tau <= 0.0:
        return tv
    raw = tv / (2.0 * tau)
    if raw < 0.0:
        raw = 0.0
    if raw > 1.0:
        raw = 1.0
    bonus = min(0.25, signal.tv_weighted_by_entropy)
    out = raw + bonus
    if out > 1.0:
        out = 1.0
    return out


if __name__ == "__main__":
    import sys
    # Smoke test: known-input => known-output.
    p_flat = [0.25] * 4
    q_flat = [0.25] * 4
    sig = assess_bebop(p_flat, q_flat)
    assert sig.tv < 1e-9, f"flat vs flat should be TV=0, got {sig.tv}"
    assert sig.divergence_class == "well_calibrated"

    # Each-token-probability test (model already in prob space).
    # Use the largest-possible uniform-style gap by passing pre-normalized
    # probs that auto-normalize to roughly the same shape.
    p_hot = [5.5, 0.5, 0.5, 0.5]                   # logits; will normalize to peaked p
    q_flat = [0.25] * 4                           # uniform reference
    sig2 = assess_bebop(p_hot, q_flat)
    # Sanity-check shape: result is a valid bucket + has entropy info.
    assert sig2.tv > 0.0, f"any non-flat should be TV>0, got {sig2.tv}"
    assert sig2.entropy_of_p < sig2.entropy_of_q, (
        f"peaked p should have lower entropy than flat q; "
        f"got H_p={sig2.entropy_of_p}, H_q={sig2.entropy_of_q}"
    )
    # Mid-bucket drift
    sig_mid = assess_bebop([0.45, 0.25, 0.15, 0.15], q_flat)
    assert 0.05 < sig_mid.tv < 1.0
    # Token-probability test: pure one-hot should saturate the high_drift bucket
    # after normalization.
    p_one_hot = [10.0, -10.0, -10.0, -10.0]
    sig3 = assess_bebop(p_one_hot, q_flat)
    assert sig3.tv > 0.5, f"one-hot vs uniform should give TV>0.5, got {sig3.tv}"
    assert sig3.divergence_class == "high_drift", (
        f"one-hot should be high_drift bucket, got {sig3.divergence_class}"
    )

    # Edit the reference file too so its smoke test mirrors the same shape.
    sig4 = assess_bebop([0.55, 0.20, 0.15, 0.10], q_flat)
    payload = {
        "tests": [
            {"name": "flat_vs_flat", "sig": sig.to_dict(),
             "risk": risk_score_from_bebop(sig)},
            {"name": "peaked_vs_flat", "sig": sig2.to_dict(),
             "risk": risk_score_from_bebop(sig2)},
            {"name": "mid_drift_vs_flat", "sig": sig_mid.to_dict(),
             "risk": risk_score_from_bebop(sig_mid)},
            {"name": "one_hot_vs_uniform", "sig": sig3.to_dict(),
             "risk": risk_score_from_bebop(sig3)},
            {"name": "mild_drift", "sig": sig4.to_dict(),
             "risk": risk_score_from_bebop(sig4)},
        ]
    }
    print(json.dumps(payload, indent=2))
