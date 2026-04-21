"""gmr/trust_adapter.py — Trust integration for GMR"""
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class TrustContext:
    agent_id: str
    lane: str
    minimum_score: float = 0.0

class TrustAwareGMR:
    """Wraps GMR with AlphaXiv Bayesian trust smoothing."""
    def __init__(self, base_gmr):
        self.gmr = base_gmr
        self.prior_success = 10
        self.prior_failure = 2

    def get_smoothed_score(self, successes: int, failures: int) -> float:
        """Bayesian smoothing prevents small-sample overconfidence."""
        return (self.prior_success + successes) / (self.prior_success + successes + self.prior_failure + failures)
