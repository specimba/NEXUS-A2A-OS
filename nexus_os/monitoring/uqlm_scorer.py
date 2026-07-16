"""
monitoring/uqlm_scorer.py — Uncertainty Quantification Scorers for Hallucination Detection

Backed by:
  - arXiv:2507.06196 (UQLM: Python Package for UQ in LLMs)
  - arXiv:2505.20045 (RAUQ: Recurrent Attention-based UQ)
  - arXiv:2509.04492 (Learned Hallucination Detection via Token Entropy)

Integration: Additive to existing calibrated_hallucination_detector.py (461 lines).
The existing detector wraps the LG tracker with EPR + Bebop + TokenHD(dark) +
adaptive thresholds. This module adds 3 new UQ scorers that fuse into the
existing risk computation:

  1. BlackBoxUQScorer  — Multiple sampling + agreement rate
  2. WhiteBoxUQScorer  — Logit entropy (overlaps with EPR → use as CONFIRMATION)
  3. LLMJudgeScorer     — External LLM evaluates hallucination risk

Key design: UQLM white-box (logit entropy) overlaps with EPR (already in LG tracker).
Don't double-count. Use white-box as a CONFIRMATION signal:
  - If EPR and white-box agree → high confidence in risk assessment
  - If EPR and white-box disagree → increase meta-uncertainty

Usage:
    from nexus_os.monitoring.uqlm_scorer import UQLMScorer

    scorer = UQLMScorer()
    scores = scorer.assess(prompt, response, logits=None, model_client=None)
    # scores = {"black_box": 0.3, "white_box": 0.6, "llm_judge": 0.4,
    #           "agreement": 0.8, "meta_uncertainty": 0.1}
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger(__name__)


@dataclass
class UQLMScores:
    """Scores from the three UQLM scorers."""
    black_box: float = 0.0       # Multiple sampling agreement rate (0=high halluc, 1=safe)
    white_box: float = 0.0       # Logit entropy (0=safe, 1=high halluc)
    llm_judge: float = 0.0       # External LLM assessment (0=safe, 1=high halluc)
    agreement: float = 1.0        # How much the scorers agree (1=full agree, 0=disagree)
    meta_uncertainty: float = 0.0  # Uncertainty about the scores themselves
    epr_correlation: Optional[float] = None  # Correlation with existing EPR score

    def to_dict(self) -> dict:
        return {
            "black_box": round(self.black_box, 4),
            "white_box": round(self.white_box, 4),
            "llm_judge": round(self.llm_judge, 4),
            "agreement": round(self.agreement, 4),
            "meta_uncertainty": round(self.meta_uncertainty, 4),
            "epr_correlation": round(self.epr_correlation, 4) if self.epr_correlation else None,
        }


class BlackBoxUQScorer:
    """Black-box UQ via multiple sampling.

    Paper: arXiv:2507.06196 (UQLM)

    Samples N responses from the same model and computes agreement rate.
    Low agreement = high hallucination risk.

    No access to model internals needed — works with any API.
    Cost: N× inference cost (use N=3 for balance).
    """

    def __init__(self, n_samples: int = 3, temperature: float = 0.8):
        self.n_samples = n_samples
        self.temperature = temperature

    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable] = None,
    ) -> float:
        """Score hallucination risk via sampling agreement.

        Returns: 0.0 (safe, high agreement) to 1.0 (high hallucination, low agreement).

        If no generate_fn provided, returns 0.0 (disabled/safe default).
        """
        if generate_fn is None:
            logger.debug("BlackBoxUQScorer: no generate_fn, returning 0.0 (disabled)")
            return 0.0

        try:
            # Sample N responses
            samples = []
            for _ in range(self.n_samples):
                sample = generate_fn(prompt, temperature=self.temperature)
                if sample:
                    samples.append(sample)

            if len(samples) < 2:
                return 0.0

            # Compute pairwise agreement (Jaccard on token sets)
            agreements = []
            for i in range(len(samples)):
                for j in range(i + 1, len(samples)):
                    tokens_i = set(samples[i].lower().split())
                    tokens_j = set(samples[j].lower().split())
                    if tokens_i or tokens_j:
                        jaccard = len(tokens_i & tokens_j) / len(tokens_i | tokens_j)
                        agreements.append(jaccard)

            if not agreements:
                return 0.0

            avg_agreement = sum(agreements) / len(agreements)
            # Low agreement = high hallucination risk
            return 1.0 - avg_agreement

        except Exception as e:
            logger.warning(f"BlackBoxUQScorer error: {e}")
            return 0.0


class WhiteBoxUQScorer:
    """White-box UQ via logit entropy.

    Paper: arXiv:2507.06196 (UQLM), arXiv:2509.04492 (Token Entropy)

    Computes token-level entropy from model logits during generation.
    High entropy = high uncertainty = higher hallucination risk.

    NOTE: This overlaps with EPR (already in LG tracker).
    Use as CONFIRMATION, not independent signal:
    - If EPR and white-box agree → high confidence
    - If they disagree → increase meta-uncertainty
    """

    def __init__(self, top_k: int = 10):
        self.top_k = top_k

    def score(self, logits: Optional[list] = None) -> float:
        """Score hallucination risk from logits.

        Returns: 0.0 (safe, low entropy) to 1.0 (high hallucination, high entropy).

        If no logits provided, returns 0.0 (disabled).
        """
        if logits is None:
            return 0.0

        try:
            import numpy as np

            # Use top-K logits
            top_k = sorted(logits, reverse=True)[:self.top_k]
            if len(top_k) < 2:
                return 0.0

            # Softmax
            max_logit = max(top_k)
            exp_logits = [math.exp(l - max_logit) for l in top_k]
            sum_exp = sum(exp_logits)
            probs = [e / sum_exp for e in exp_logits]

            # Entropy
            entropy = -sum(p * math.log(p + 1e-10) for p in if probs else [0])
            max_entropy = math.log(len(probs))

            # Normalize to [0, 1]
            normalized = entropy / max_entropy if max_entropy > 0 else 0.0

            return float(normalized)

        except Exception as e:
            logger.warning(f"WhiteBoxUQScorer error: {e}")
            return 0.0


class LLMJudgeScorer:
    """LLM-as-judge hallucination assessment.

    Paper: arXiv:2507.06196 (UQLM)

    Uses an external LLM (e.g., existing GuardEnsemble L3 confirmer)
    to evaluate hallucination risk.

    Can use existing NEXUS GuardEnsemble Granite-Guardian-3.2 as the judge.
    """

    def __init__(self, judge_fn: Optional[Callable] = None):
        self.judge_fn = judge_fn

    def score(
        self,
        prompt: str,
        response: str,
    ) -> float:
        """Score hallucination risk via LLM judge.

        Returns: 0.0 (safe) to 1.0 (high hallucination).

        If no judge_fn provided, returns 0.0 (disabled).
        """
        if self.judge_fn is None:
            return 0.0

        try:
            judge_prompt = (
                "Evaluate whether the following response contains hallucinated "
                "or fabricated information. Respond with a risk score from 0.0 "
                "(safe) to 1.0 (highly likely hallucinated).\n\n"
                f"Prompt: {prompt[:500]}\n\n"
                f"Response: {response[:500]}\n\n"
                "Risk score:"
            )
            result = self.judge_fn(judge_prompt)
            # Parse float from response
            if isinstance(result, str):
                result = result.strip()
                try:
                    return max(0.0, min(1.0, float(result)))
                except ValueError:
                    # Look for number in text
                    import re
                    match = re.search(r'[0-9]+\.[0-9]+', result)
                    if match:
                        return max(0.0, min(1.0, float(match.group())))
                    return 0.0
            elif isinstance(result, (int, float)):
                return max(0.0, min(1.0, float(result)))
            return 0.0
        except Exception as e:
            logger.warning(f"LLMJudgeScorer error: {e}")
            return 0.0


class UQLMScorer:
    """Unified UQLM scorer combining all three UQ methods.

    Integrates with existing CalibratedHallucinationDetector fusion pipeline.
    Each scorer is OPTIONAL and defaults to disabled (returns 0.0).

    Fusion formula (added to existing EPR + Bebop + TokenHD):
        risk = w_epr * epr + w_bebop * bebop + w_tokenhd * tokenhd
             + w_bb * black_box + w_wb * white_box + w_judge * llm_judge
        where all weights sum to 1.0

    Key: white_box overlaps with EPR → use as confirmation, not double-counting.
    """

    def __init__(
        self,
        enable_black_box: bool = False,
        enable_white_box: bool = False,
        enable_llm_judge: bool = False,
        black_box_weight: float = 0.15,
        white_box_weight: float = 0.10,
        llm_judge_weight: float = 0.10,
        n_samples: int = 3,
    ):
        self.black_box_scorer = BlackBoxUQScorer(n_samples=n_samples)
        self.white_box_scorer = WhiteBoxUQScorer()
        self.llm_judge_scorer = LLMJudgeScorer()

        self.enable_black_box = enable_black_box
        self.enable_white_box = enable_white_box
        self.enable_llm_judge = enable_llm_judge

        self.black_box_weight = black_box_weight
        self.white_box_weight = white_box_weight
        self.llm_judge_weight = llm_judge_weight

    def assess(
        self,
        prompt: str,
        response: str,
        logits: Optional[list] = None,
        generate_fn: Optional[Callable] = None,
        judge_fn: Optional[Callable] = None,
        epr_score: Optional[float] = None,
    ) -> UQLMScores:
        """Run all enabled UQLM scorers.

        Args:
            prompt: The user prompt
            response: The model response
            logits: Token logits for white-box scoring (optional)
            generate_fn: Function to generate samples for black-box scoring
            judge_fn: Function to call LLM judge
            epr_score: Existing EPR score from LG tracker (for correlation)

        Returns:
            UQLMScores with individual scores + agreement + meta_uncertainty
        """
        bb_score = 0.0
        wb_score = 0.0
        lj_score = 0.0

        if self.enable_black_box:
            bb_score = self.black_box_scorer.score(prompt, response, generate_fn)

        if self.enable_white_box and logits is not None:
            wb_score = self.white_box_scorer.score(logits)

        if self.enable_llm_judge and judge_fn is not None:
            self.llm_judge_scorer.judge_fn = judge_fn
            lj_score = self.llm_judge_scorer.score(prompt, response)

        # Compute agreement (how much scorers agree)
        active_scores = [s for s in [bb_score, wb_score, lj_score] if s > 0]
        if len(active_scores) >= 2:
            avg = sum(active_scores) / len(active_scores)
            variance = sum((s - avg) ** 2 for s in active_scores) / len(active_scores)
            std = math.sqrt(variance)
            agreement = max(0.0, 1.0 - std * 2)  # Low std = high agreement
        else:
            agreement = 1.0  # Only one scorer → no disagreement

        # Meta-uncertainty: if scorers disagree, increase uncertainty
        meta_uncertainty = 1.0 - agreement

        # EPR correlation: check if white-box agrees with EPR
        epr_correlation = None
        if epr_score is not None and wb_score > 0:
            # Simple agreement: |epr - wb| → low difference = high correlation
            diff = abs(epr_score - wb_score)
            epr_correlation = max(0.0, 1.0 - diff * 2)
            # If they disagree, boost meta_uncertainty
            if diff > 0.3:
                meta_uncertainty = min(1.0, meta_uncertainty + 0.2)

        return UQLMScores(
            black_box=bb_score,
            white_box=wb_score,
            llm_judge=lj_score,
            agreement=agreement,
            meta_uncertainty=meta_uncertainty,
            epr_correlation=epr_correlation,
        )

    def get_fusion_weights(self) -> dict:
        """Get weights for fusion into CalibratedHallucinationDetector.

        The existing detector already has:
          risk = epr * (1-bebop_w-tokenhd_w) + bebop * bebop_w + tokenhd * tokenhd_w

        UQLM adds:
          + black_box * bb_weight + white_box * wb_weight + llm_judge * judge_weight

        All weights must sum to 1.0. The caller should normalize.
        """
        return {
            "black_box": self.black_box_weight if self.enable_black_box else 0.0,
            "white_box": self.white_box_weight if self.enable_white_box else 0.0,
            "llm_judge": self.llm_judge_weight if self.enable_llm_judge else 0.0,
        }
