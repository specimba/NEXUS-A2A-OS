"""
vault/trust.py — Persistent Tanh-based Trust Scoring (HPv2)

Delegates to/inherits from the unified TrustScorer in nexus_os.monitoring.trust_scorer.
"""

import logging
from typing import Dict, Any, Optional

from nexus_os.db.manager import DatabaseManager
from nexus_os.monitoring.trust_scorer import TrustScorer as UnifiedTrustScorer

logger = logging.getLogger(__name__)


class TrustScorer(UnifiedTrustScorer):
    """
    Persistent tanh-based trust scorer for tracking agent reliability.
    Extends the unified TrustScorer interface.
    """

    def __init__(self, db: DatabaseManager):
        super().__init__(db=db)
        logger.info(
            "TrustScorer (persistent) initialized (prior: %d successes, %d failures, base_rate=%.3f)",
            self.PRIOR_SUCCESS, self.PRIOR_FAILURE,
            self.PRIOR_SUCCESS / (self.PRIOR_SUCCESS + self.PRIOR_FAILURE),
        )
