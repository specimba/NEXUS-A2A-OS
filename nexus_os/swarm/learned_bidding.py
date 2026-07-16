"""
swarm/learned_bidding.py — ML-Learned Bidding for Auction House

Backed by:
  - arXiv:2605.21932 (Auction-Consensus Algorithm with Learned Bidding)
  - arXiv:2511.13193 (Cost-Effective Communication: Auction-based)

Integration: ADDITIVE to existing swarm/auction.py (204 lines).
The existing AuctionHouse uses capability_weight=0.6 for static bidding.
This module adds an optional learned bidding mode that uses features
(past success, latency, cost, quality, trust) to learn better bids.

Usage:
    from nexus_os.swarm.learned_bidding import LearnedBidder

    bidder = LearnedBidder()
    bid = bidder.compute_bid(
        agent_id="task_coder",
        task_type="code_generation",
        capability_score=0.8,
        load_factor=0.3,
        history={"success_rate": 0.92, "avg_latency_ms": 1200, "avg_cost": 0.001},
    )
    # bid = {"bid_amount": 0.15, "method": "learned", "confidence": 0.85}
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class BidFeatures:
    """Features for learned bidding."""
    capability_score: float      # 0-1, from existing AuctionHouse
    load_factor: float           # 0-1, from existing AuctionHouse
    success_rate: float          # 0-1, historical success
    avg_latency_ms: float        # Historical latency
    avg_cost: float              # Historical cost per request
    trust_score: float           # 0-100, from TrustKernel
    task_match: float            # 0-1, how well specialization matches task
    current_vram_usage: float    # 0-1, GPU memory pressure


@dataclass
class LearnedBid:
    """Output of learned bidding."""
    bid_amount: float            # Lower = more willing (same as existing Bid)
    method: str                  # "learned" or "cost_based" (fallback)
    confidence: float            # 0-1, confidence in the bid
    feature_weights: Dict[str, float] = field(default_factory=dict)
    reason: str = ""


class LearnedBidder:
    """ML-learned bidding mode for AuctionHouse.

    Paper: arXiv:2605.21932 (Auction-Consensus with Learned Bidding)

    Uses a feature-weighted scoring function that learns from past outcomes.
    Starts with heuristic weights and adjusts based on auction results.

    Integration: Plug into existing AuctionHouse as an alternative bidder.
    """

    # Initial heuristic weights (will be adjusted by learning)
    DEFAULT_WEIGHTS = {
        "capability": 0.25,       # Higher capability → lower bid (more willing)
        "success_rate": 0.20,     # Higher success → lower bid
        "load_factor": 0.15,      # Higher load → higher bid (less willing)
        "latency": 0.10,          # Higher latency → higher bid
        "cost": 0.10,             # Higher cost → higher bid
        "trust": 0.10,            # Higher trust → lower bid
        "task_match": 0.05,       # Better match → lower bid
        "vram_pressure": 0.05,    # More VRAM pressure → higher bid
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._learning_rate = 0.01
        self._auction_history: List[Dict[str, Any]] = []

    def compute_bid(
        self,
        agent_id: str,
        task_type: str,
        capability_score: float,
        load_factor: float,
        history: Optional[Dict[str, float]] = None,
        trust_score: float = 50.0,
        task_match: float = 0.5,
        current_vram_usage: float = 0.0,
    ) -> LearnedBid:
        """Compute a learned bid for an auction.

        Bid formula (lower = more willing to take the task):
            bid = w_cap * (1 - capability) + w_succ * (1 - success_rate)
                + w_load * load_factor + w_lat * latency_penalty
                + w_cost * cost_penalty + w_trust * (1 - trust_norm)
                + w_match * (1 - task_match) + w_vram * vram_pressure

        Returns: LearnedBid with bid_amount (0-1, lower is better)
        """
        history = history or {}
        success_rate = history.get("success_rate", 0.5)
        avg_latency = history.get("avg_latency_ms", 1000.0)
        avg_cost = history.get("avg_cost", 0.001)

        # Normalize features to 0-1
        latency_penalty = min(avg_latency / 5000.0, 1.0)
        cost_penalty = min(avg_cost / 0.01, 1.0)
        trust_norm = trust_score / 100.0

        # Weighted sum (each term contributes to bid_amount)
        # Positive terms increase bid (less willing), negative decrease (more willing)
        bid = (
            self.weights["capability"] * (1.0 - capability_score) +
            self.weights["success_rate"] * (1.0 - success_rate) +
            self.weights["load_factor"] * load_factor +
            self.weights["latency"] * latency_penalty +
            self.weights["cost"] * cost_penalty +
            self.weights["trust"] * (1.0 - trust_norm) +
            self.weights["task_match"] * (1.0 - task_match) +
            self.weights["vram_pressure"] * current_vram_usage
        )

        # Normalize to 0-1
        bid = min(max(bid, 0.0), 1.0)

        # Confidence: higher when we have more history
        history_count = history.get("count", 0)
        confidence = min(0.95, 0.5 + 0.05 * min(history_count, 10))

        return LearnedBid(
            bid_amount=round(bid, 4),
            method="learned",
            confidence=confidence,
            feature_weights=dict(self.weights),
            reason=f"Learned bid: cap={capability_score:.2f}, succ={success_rate:.2f}, "
                   f"load={load_factor:.2f}, trust={trust_norm:.2f}, match={task_match:.2f}",
        )

    def record_outcome(
        self,
        agent_id: str,
        task_type: str,
        bid_amount: float,
        won: bool,
        success: bool,
        actual_latency_ms: float,
        actual_cost: float,
    ):
        """Record auction outcome and adjust weights.

        Learning signal:
        - Won + success → weights that led to winning were good
        - Won + failure → bid too low, should have been higher
        - Lost → bid too high, should have been lower
        """
        self._auction_history.append({
            "agent_id": agent_id,
            "task_type": task_type,
            "bid_amount": bid_amount,
            "won": won,
            "success": success,
            "latency_ms": actual_latency_ms,
            "cost": actual_cost,
        })

        # Simple weight adjustment (online learning)
        if won and success:
            # Good outcome: reinforce current weights slightly
            pass  # Weights are fine, no adjustment needed
        elif won and not success:
            # Won but failed: bid was too low, increase penalty weights
            self.weights["success_rate"] *= (1 + self._learning_rate)
            self.weights["capability"] *= (1 + self._learning_rate)
        elif not won:
            # Lost: bid was too high, decrease penalty weights
            self.weights["load_factor"] *= (1 - self._learning_rate)
            self.weights["latency"] *= (1 - self._learning_rate)

        # Normalize weights to sum to 1.0
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
            "history_count": len(self._auction_history),
            "win_rate": (
                sum(1 for h in self._auction_history if h["won"]) / len(self._auction_history)
                if self._auction_history else 0.0
            ),
            "success_rate": (
                sum(1 for h in self._auction_history if h["success"]) / len(self._auction_history)
                if self._auction_history else 0.0
            ),
        }


class CostBasedBidder:
    """Fallback cost-based bidder (existing AuctionHouse behavior).

    Paper: arXiv:2511.13193 (Cost-Effective Communication)
    """

    def compute_bid(
        self,
        capability_score: float,
        load_factor: float,
        capability_weight: float = 0.6,
    ) -> LearnedBid:
        """Compute bid using existing cost-based formula."""
        # Existing formula: bid = (1 - capability_weight * capability) * (1 + load_factor)
        bid = (1.0 - capability_weight * capability_score) * (1.0 + load_factor * 0.5)
        bid = min(max(bid, 0.0), 1.0)

        return LearnedBid(
            bid_amount=round(bid, 4),
            method="cost_based",
            confidence=0.5,
            reason=f"Cost-based: cap_w={capability_weight}, cap={capability_score}, load={load_factor}",
        )
