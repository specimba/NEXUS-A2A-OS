"""ASTRA Risk Integration for Agent Steerability Assessment.

Provides risk scoring for model evaluation and TrustKernel integration.
"""

import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass


@dataclass
class RiskScore:
    """Risk assessment components."""
    steerability: float
    alignment_resistance: float
    adversarial_robustness: float
    composite: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "steerability": self.steerability,
            "alignment_resistance": self.alignment_resistance,
            "adversarial_robustness": self.adversarial_robustness,
            "composite": self.composite,
        }


class ASTRARiskAssessor:
    """Agentic Steerability and Risk Analysis framework integration."""

    def __init__(self):
        self._steerability_cache: Dict[str, RiskScore] = {}

    def assess(
        self,
        model_name: str,
        prompts: Optional[List[str]] = None,
    ) -> RiskScore:
        """Assess model risk profile using ASTRA framework."""
        if model_name in self._steerability_cache:
            return self._steerability_cache[model_name]

        try:
            from astra import assess_steerability
            result = assess_steerability(model_name, prompts=prompts)
            score = RiskScore(
                steerability=result.get("steerability", 0.5),
                alignment_resistance=result.get("alignment_resistance", 0.5),
                adversarial_robustness=result.get("adversarial_robustness", 0.5),
                composite=self._composite_score(result),
            )
        except ImportError:
            score = RiskScore(
                steerability=0.5,
                alignment_resistance=0.5,
                adversarial_robustness=0.5,
                composite=0.5,
            )

        self._steerability_cache[model_name] = score
        return score

    def _composite_score(self, result: Dict[str, Any]) -> float:
        s = result.get("steerability", 0.5)
        a = result.get("alignment_resistance", 0.5)
        ar = result.get("adversarial_robustness", 0.5)
        return round((s + a + ar) / 3, 3)

    def integrate_with_benchmark(self, benchmark_result: Dict[str, Any]) -> Dict[str, Any]:
        """Add risk scores to benchmark results."""
        model = benchmark_result.get("model_name", "unknown")
        risk = self.assess(model)
        benchmark_result["astra_risk_score"] = risk.to_dict()
        benchmark_result["risk_composite"] = risk.composite
        return benchmark_result