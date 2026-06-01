"""gmr/trust_adapter.py — Trust integration for GMR"""
from dataclasses import dataclass
from typing import Dict, Any, Optional

from nexus_os.governor.trust_kernel import TrustKernel

@dataclass
class TrustContext:
    agent_id: str
    lane: str
    minimum_score: float = 0.0

class TrustAwareGMR:
    """Wraps GMR with canonical TrustKernel reads plus legacy smoothing."""
    def __init__(self, base_gmr, trust_kernel: Optional[TrustKernel] = None):
        self.gmr = base_gmr
        self.trust_kernel = trust_kernel or TrustKernel()
        self.prior_success = 10
        self.prior_failure = 2

    def get_smoothed_score(self, successes: int, failures: int) -> float:
        """Bayesian smoothing prevents small-sample overconfidence."""
        return (self.prior_success + successes) / (self.prior_success + successes + self.prior_failure + failures)

    def get_trust_snapshot(self, context: TrustContext) -> Dict[str, Any]:
        """Return the canonical trust snapshot used by routing decisions."""
        return self.trust_kernel.get_snapshot(context.agent_id, context.lane).to_dict()

    def is_allowed(self, context: TrustContext, action: str = "execute") -> bool:
        """Check whether GMR can route a side-effectful action for this agent."""
        decision = self.trust_kernel.evaluate(context.agent_id, action, context.lane)
        return decision.decision.value == "allow" and decision.snapshot.trust >= context.minimum_score
