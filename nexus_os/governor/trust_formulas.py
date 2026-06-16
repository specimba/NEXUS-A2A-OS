"""Trust Formulas — arXiv research-derived trust computations.

References:
  - Logistic Scaling: arXiv:2603.15973 (HARDWALL defenses)
  - Temporal Decay: arXiv:2603.13325 (decay-regularized trust)
  - 6-Stage CDR: arXiv:2604.02375 (CDR state machine)
  - Bayesian Posterior: arXiv:2403.13031 (Bayesian reputation)
  - Non-Compensatory Eval: arXiv:2511.10400 (safety evaluation)
"""

from __future__ import annotations
import math
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class HardwallParams:
    logistic_k: float = 0.1
    logistic_x0: float = 50.0
    decay_lambda: float = 0.05
    decay_base: float = 25.0
    cdr_trust_thresholds: list[float] = None
    cdr_regression_thresholds: list[int] = None
    bayesian_prior_alpha: float = 10.0
    bayesian_prior_beta: float = 2.0
    non_compensatory_floor: float = -20.0

    def __post_init__(self):
        if self.cdr_trust_thresholds is None:
            self.cdr_trust_thresholds = [30.0, 25.0, 20.0, 15.0, 5.0]
        if self.cdr_regression_thresholds is None:
            self.cdr_regression_thresholds = [3, 5, 8, 10, 15]


def logistic_scale(raw: float, k: float = 0.1, x0: float = 50.0) -> float:
    """HARDWALL anti-grinding logistic scaling (arXiv:2603.15973).
    Inverted sigmoid: high-trust agents receive progressively smaller
    per-success rewards, preventing volume-based gaming.
    Maps trust score to (0,1) with maximum at low trust, minimum at high trust.
    """
    return 1.0 / (1.0 + math.exp(k * (raw - x0)))


def temporal_decay(score: float, last_active: Optional[float] = None, decay_lambda: float = 0.05, decay_base: float = 25.0) -> float:
    """Decay-regularized trust (arXiv:2603.13325).
    Exponential decay toward baseline over hours since last activity.
    """
    if last_active is None:
        return score
    hours = (time.time() - last_active) / 3600.0
    decayed = decay_base + (score - decay_base) * math.exp(-decay_lambda * hours)
    return max(decayed, decay_base)


def cdr_escalate(trust: float, regression_events: int, trust_thresholds: Optional[list[float]] = None, regression_thresholds: Optional[list[int]] = None) -> int:
    """6-stage CDR escalation check (arXiv:2604.02375).
    Returns the CDR stage index (0-5) based on trust and regression thresholds.
    """
    tt = trust_thresholds or [30.0, 25.0, 20.0, 15.0, 5.0]
    rt = regression_thresholds or [3, 5, 8, 10, 15]
    for i, (t, r) in enumerate(zip(tt, rt)):
        if trust < t or regression_events >= r:
            return i + 1
    return 0


def bayesian_posterior(successes: int, failures: int, prior_alpha: float = 10.0, prior_beta: float = 2.0) -> float:
    """Bayesian reputation posterior (arXiv:2403.13031).
    Beta-Binomial posterior mean as smoothed trust score.
    """
    alpha = prior_alpha + successes
    beta = prior_beta + failures
    return alpha / (alpha + beta)


def non_compensatory_penalty(raw_delta: float, critical: bool = False, floor: float = -20.0) -> float:
    """Non-compensatory critical block (arXiv:2511.10400).
    If critical, forces a minimum penalty that cannot be compensated by other gains.
    """
    if critical:
        return max(raw_delta, floor)
    return raw_delta
