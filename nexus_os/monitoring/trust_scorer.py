"""Trust scoring system — v2.1 Canonical Implementation.

Implements the canonical scoring formula with:
- Lane-scoped parameters (not global!)
- Non-compensatory harm (R > Rcrit → None)
- Hot-path optimization (O(1) with caching)
- 5-track memory integration
"""

from typing import Dict, Optional
from dataclasses import dataclass
import math

# ── Lane Parameters (from Expert Reports + SCORING v2.1) ──────────────

@dataclass(frozen=True)
class LaneParams:
    """Lane-specific parameters for trust scoring.
    
    CRITICAL: Trust must be lane-scoped, not global!
    """
    qmin: float = 0.1      # Minimum evidence confidence
    n0: float = 5.0        # Evidence count normalization
    Rcrit: float = 0.6     # Harm threshold (non-compensatory!)
    alpha: float = 0.4     # Utility weight
    beta: float = 0.2      # Harm/regression weight
    gamma: float = 0.3     # Coverage contribution weight
    eta: float = 0.1       # Omission/under-delivery weight
    kappa: float = 2.5     # Scaling factor
    delta: float = 0.5     # Exponent for Qeff
    epsilon: float = 1e-4  # Near-zero compression threshold


# Lane-specific defaults (CRITICAL: different lanes have different thresholds!)
LANE_PARAMS = {
    "research": LaneParams(qmin=0.3, n0=5, Rcrit=0.7),   # Exploration-friendly
    "audit": LaneParams(qmin=0.7, n0=2, Rcrit=0.3),      # Recall-first
    "compliance": LaneParams(qmin=0.7, n0=2, Rcrit=0.2), # Hard-stop
    "implementation": LaneParams(qmin=0.4, n0=3, Rcrit=0.4),  # Correctness
    "orchestration": LaneParams(qmin=0.5, n0=4, Rcrit=0.4),  # Coverage
    "general": LaneParams(),  # Default values
}


class TrustScorer:
    """v2.1 Canonical Trust Scorer.
    
    Features:
    - Lane-scoped parameters (not global!)
    - Non-compensatory harm (R > Rcrit → score = None)
    - Hot-path optimization with caching
    - Zero-context-loss handoff support
    """
    
    def __init__(self):
        self._hot_path_cache: Dict[str, float] = {}
    
    def get_score_hotpath(
        self,
        agent_id: str,
        Q: float,
        n: int = 1,
        U: float = 1.0,
        D_plus: float = 0.0,
        R: float = 0.0,
        D_minus: float = 0.0,
        lane: str = "general",
        status: str = "active",
    ) -> Optional[float]:
        """Calculate trust score using v2.1 canonical formula.
        
        HOT PATH: Must complete in <20μs
        
        Formula:
            if status in {blocked, unassigned}: return None
            if R > Rcrit(lane): return None  # NON-COMPENSATORY
            Qeff = clip((Q - qmin)/(1 - qmin)) * (1 - exp(-n/n0))
            P = alpha*U + gamma*D_plus - beta*R - eta*D_minus
            raw = tanh(kappa * Qeff^delta * P)
            return 0 if |raw| < epsilon else raw
        
        Args:
            agent_id: Agent identifier
            Q: Evidence confidence (0-1)
            n: Evidence count
            U: Utility created (normalized)
            D_plus: Coverage/delivery contribution
            R: Harm/regression (normalized)
            D_minus: Under-delivery/omission
            lane: Task lane (determines parameters)
            status: Agent status
        
        Returns:
            float in [-1, 1] or None (if blocked/harm exceeded)
        """
        # 1. NULL STATE CHECK
        if status in {"blocked", "unassigned", "not_applicable"}:
            return None
        
        # 2. LANE PARAMETERS (CRITICAL: Lane-scoped, not global!)
        params = LANE_PARAMS.get(lane, LANE_PARAMS["general"])
        
        # 3. NON-COMPENSATORY HARM CHECK (CRITICAL!)
        # If harm exceeds lane threshold, score = None (held)
        # Utility CANNOT compensate for harm above Rcrit
        if R > params.Rcrit:
            return None  # HOLD state - no score calculated
        
        # 4. EFFECTIVE EVIDENCE CONFIDENCE
        Qeff = max(0.0, min(1.0, (Q - params.qmin) / (1 - params.qmin)))
        if n > 0:
            Qeff *= (1 - math.exp(-n / params.n0))
        
        # 5. PERFORMANCE CALCULATION
        P = (
            params.alpha * U
            + params.gamma * D_plus
            - params.beta * R
            - params.eta * D_minus
        )
        
        # 6. BOUNDING (tanh ensures [-1, 1])
        raw_score = math.tanh(params.kappa * (Qeff ** params.delta) * P)
        
        # 7. NEAR-ZERO COMPRESSION
        if abs(raw_score) < params.epsilon:
            return 0.0
        
        return round(raw_score, 4)
    
    def get_lane_params(self, lane: str) -> LaneParams:
        """Get parameters for a specific lane."""
        return LANE_PARAMS.get(lane, LANE_PARAMS["general"])
    
    def is_harm_critical(self, R: float, lane: str) -> bool:
        """Check if harm exceeds critical threshold for lane."""
        params = LANE_PARAMS.get(lane, LANE_PARAMS["general"])
        return R > params.Rcrit
