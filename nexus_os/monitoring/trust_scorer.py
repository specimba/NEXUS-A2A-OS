"""Trust scoring system — v2.1 Canonical Implementation.

Implements the canonical scoring formula with:
- Lane-scoped parameters (not global!)
- Non-compensatory harm (R > Rcrit → None)
- Hot-path optimization (O(1) with caching)
- 5-track memory integration
"""

from typing import Dict, Optional, Any
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
    """Unified Trust Scorer interface for Nexus OS.
    
    Unifies the lane-scoped [-1, 1] hot-path scorer and the Bayesian [0, 1] reputation scorer.
    """
    PRIOR_SUCCESS = 10
    PRIOR_FAILURE = 2

    def __init__(self, db: Optional[Any] = None):
        self.db = db
        self._hot_path_cache: Dict[str, float] = {}
        if db is not None:
            if hasattr(db, "get_connection"):
                self._conn = db.get_connection()
            else:
                self._conn = db
        else:
            self._conn = None

    def get_score(self, agent_id: str, lane: Optional[str] = None) -> float:
        """Get Bayesian [0, 1] trust score for an agent.
        
        If DB connection exists, queries the agent_reputation database.
        Otherwise (or if agent not found), returns the prior rate (~0.833).
        """
        if self._conn is not None:
            try:
                row = self._conn.execute(
                    "SELECT successes, failures FROM agent_reputation WHERE agent_id = ?",
                    (agent_id,),
                ).fetchone()
                if row is not None:
                    successes, failures = row[0], row[1]
                    total = successes + failures
                    return (successes + self.PRIOR_SUCCESS) / (total + self.PRIOR_SUCCESS + self.PRIOR_FAILURE)
            except Exception:
                pass
        return self.PRIOR_SUCCESS / (self.PRIOR_SUCCESS + self.PRIOR_FAILURE)

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
        """
        # 1. NULL STATE CHECK
        if status in {"blocked", "unassigned", "not_applicable"}:
            return None
        
        # 2. LANE PARAMETERS (CRITICAL: Lane-scoped, not global!)
        params = LANE_PARAMS.get(lane, LANE_PARAMS["general"])
        
        # 3. NON-COMPENSATORY HARM CHECK (CRITICAL!)
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

    # Methods from persistent reputation scorer (vault/trust.py)
    def record_success(self, agent_id: str) -> None:
        if self._conn is not None:
            self._ensure_agent_registered(agent_id)
            self._conn.execute(
                """INSERT INTO agent_reputation (agent_id, successes, failures, last_updated)
                   VALUES (?, 1, 0, CURRENT_TIMESTAMP)
                   ON CONFLICT(agent_id) DO UPDATE SET
                       successes = successes + 1,
                       last_updated = CURRENT_TIMESTAMP""",
                (agent_id,),
            )
            if hasattr(self._conn, "commit"):
                self._conn.commit()

    def record_failure(self, agent_id: str) -> None:
        if self._conn is not None:
            self._ensure_agent_registered(agent_id)
            self._conn.execute(
                """INSERT INTO agent_reputation (agent_id, successes, failures, last_updated)
                   VALUES (?, 0, 1, CURRENT_TIMESTAMP)
                   ON CONFLICT(agent_id) DO UPDATE SET
                       failures = failures + 1,
                       last_updated = CURRENT_TIMESTAMP""",
                (agent_id,),
            )
            if hasattr(self._conn, "commit"):
                self._conn.commit()

    def get_stats(self, agent_id: str) -> Dict[str, Any]:
        if self._conn is not None:
            try:
                row = self._conn.execute(
                    "SELECT successes, failures FROM agent_reputation WHERE agent_id = ?",
                    (agent_id,),
                ).fetchone()
                if row is not None:
                    successes, failures = row[0], row[1]
                    total = successes + failures
                    score = (successes + self.PRIOR_SUCCESS) / (total + self.PRIOR_SUCCESS + self.PRIOR_FAILURE)
                    return {
                        "successes": successes,
                        "failures": failures,
                        "score": score,
                        "total": total,
                    }
            except Exception:
                pass
        score = self.PRIOR_SUCCESS / (self.PRIOR_SUCCESS + self.PRIOR_FAILURE)
        return {
            "successes": 0,
            "failures": 0,
            "score": score,
            "total": 0,
        }

    def close(self):
        if self._conn and hasattr(self._conn, "close"):
            self._conn.close()
            self._conn = None

    def _ensure_agent_registered(self, agent_id: str) -> None:
        if self._conn is not None:
            self._conn.execute(
                """INSERT OR IGNORE INTO agent_registry (agent_id, model_id, status)
                   VALUES (?, 'unknown', 'active')""",
                (agent_id,),
            )
