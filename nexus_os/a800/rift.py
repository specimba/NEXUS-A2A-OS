#!/usr/bin/env python3
"""
RIFT: Reward-Informed Trust-Weighted Fine-Tuning
==================================================
From PAPERS P0 #7 + F4 finding.
Uses trust ledger Beta posterior as reward weight.
Failures are not discarded — they train with partial weight.
"""

import math
from typing import Optional


class RIFTWeightCalculator:
    """Compute per-trust-weighted loss coefficients from trust ledger."""

    def __init__(self, alpha: float = 1.0, beta: float = 1.0, min_weight: float = 0.1):
        self.alpha = alpha
        self.beta = beta
        self.min_weight = min_weight

    def compute_weight(self, trust_score: float, outcome_ok: bool) -> float:
        """
        Compute RIFT weight for a single trace.
        
        High trust + success  → weight ≈ 1.0 (full gradient)
        High trust + failure  → weight ≈ 0.5 (learn from mistakes)
        Low trust + anything  → weight ≈ min_weight (don't fully trust)
        """
        # Update Beta posterior
        a = self.alpha + (1.0 if outcome_ok else 0.0)
        b = self.beta + (0.0 if outcome_ok else 1.0)
        
        # Posterior mean = a / (a + b)
        posterior_mean = a / (a + b)
        
        # Scale to [min_weight, 1.0]
        weight = self.min_weight + (1.0 - self.min_weight) * posterior_mean
        return round(weight, 4)

    def batch_weights(self, traces: list[dict]) -> list[float]:
        """Compute weights for a batch of traces."""
        return [
            self.compute_weight(
                t.get("trust_score", 0.5),
                t.get("outcome_ok", False),
            )
            for t in traces
        ]


def trust_weighted_loss(logits, labels, weights, model):
    """
    Compute trust-weighted cross-entropy loss.
    Failed traces contribute partial gradient instead of being dropped.
    """
    import torch
    import torch.nn.functional as F
    
    # Standard CE per token
    shift_logits = logits[..., :-1, :].contiguous()
    shift_labels = labels[..., 1:].contiguous()
    token_loss = F.cross_entropy(
        shift_logits.view(-1, shift_logits.size(-1)),
        shift_labels.view(-1),
        reduction="none",
    )
    
    # Apply trust weights (per-sequence)
    weights = weights.view(-1, 1).expand_as(token_loss)
    weighted = (token_loss * weights).sum() / weights.sum()
    return weighted
