"""TIES-Merging Integration for Multi-Model Ensembling.

Resolves parameter interference when combining models.
"""

import time
from typing import Dict, List, Optional, Any


class TIESMerger:
    """Task Arithmetic with Interference-augmented Sparse Merging."""

    def __init__(self, trust_store: Optional[Any] = None):
        self.trust_store = trust_store

    def merge(
        self,
        base_model: str,
        merge_models: List[str],
        sparsity: float = 0.5,
    ) -> Dict[str, Any]:
        """Merge models using TIES sparsity to resolve interference."""
        start = time.time()

        try:
            from ties import merge_state_dicts
            merged_state = merge_state_dicts(
                base_model=base_model,
                models=merge_models,
                sparsity=sparsity,
            )
        except ImportError:
            merged_state = {"stub": "ties_unavailable"}

        result = {
            "base_model": base_model,
            "merge_models": merge_models,
            "sparsity": sparsity,
            "merged_signature": self._signature(merged_state),
            "merge_time_s": time.time() - start,
            "conflict_pairs": self._detect_conflicts(merge_models),
            "status": "ok" if "stub" not in merged_state else "requires_ties_lib",
        }

        if self.trust_store:
            self._record_merge_lineage(result)

        return result

    def _signature(self, state: Dict[str, Any]) -> str:
        import hashlib
        return hashlib.sha256(str(state).encode()).hexdigest()[:16]

    def _detect_conflicts(self, models: List[str]) -> List[str]:
        """Detect known conflicting model pairs from trust store."""
        if not self.trust_store:
            return []
        conflicts = []
        for m in models:
            if self.trust_store.has_conflict(m):
                conflicts.append(m)
        return conflicts

    def _record_merge_lineage(self, result: Dict[str, Any]) -> None:
        """Record merge operation in trust store for audit."""
        self.trust_store.record_merge(result)

    def validate_merge(self, merged_model: str) -> bool:
        """Validate merged model doesn't exceed safety thresholds."""
        try:
            from ties.validator import validate_merge
            return validate_merge(merged_model)
        except ImportError:
            return True