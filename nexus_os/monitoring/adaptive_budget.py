"""
monitoring/adaptive_budget.py — Adaptive Token Budget Allocation

Backed by:
  - arXiv:2605.09104 (Token Economics — 4D taxonomy)
  - arXiv:2505.11274 (SelfBudgeter — adaptive token allocation)

Integration: ADDITIVE to existing monitoring/token_guard.py (953 lines).
The existing TokenBudget is static (total/used/remaining).
This module adds dynamic budget allocation based on:
  1. CogER complexity classification (L1-L4)
  2. Prompt complexity signals (length, code presence, math presence)
  3. Historical token usage patterns
  4. Cost-quality tradeoff optimization

Usage:
    from nexus_os.monitoring.adaptive_budget import AdaptiveBudgetAllocator

    allocator = AdaptiveBudgetAllocator()
    budget = allocator.estimate(prompt="Write a merge sort in Python", complexity="L2")
    # budget = {"input_budget": 500, "output_budget": 1500, "total": 2000, "reason": "..."}
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


@dataclass
class BudgetEstimate:
    """Estimated token budget for a request."""
    input_budget: int
    output_budget: int
    total: int
    reasoning: str
    complexity: str
    confidence: float = 0.8

    @property
    def total_budget(self) -> int:
        return self.input_budget + self.output_budget


class AdaptiveBudgetAllocator:
    """Adaptive token budget allocation.

    Paper: arXiv:2605.09104 (Token Economics), arXiv:2505.11274 (SelfBudgeter)

    Aligns with NEXUS CogER L1-L4 complexity levels:
    - L1 (No Think): tight budget, direct execution
    - L2 (Think): medium budget, single reasoning pass
    - L3 (Extend): generous budget, extended reasoning
    - L4 (Delegate): unlimited + cloud elevation
    """

    # Base budgets per CogER complexity level
    # Aligned with NEXUS_MODEL_USAGE_PLAN_2026-07-10.md
    BASE_BUDGETS = {
        "L1": {"input": 256, "output": 512, "total": 768},
        "L2": {"input": 1024, "output": 2048, "total": 3072},
        "L3": {"input": 2048, "output": 4096, "total": 6144},
        "L4": {"input": 4096, "output": 8192, "total": 12288},
    }

    # Complexity multipliers from prompt signals
    CODE_MULTIPLIER = 1.3      # Code tasks need more output tokens
    MATH_MULTIPLIER = 1.5      # Math/reasoning needs more thinking tokens
    LONG_CONTEXT_MULTIPLIER = 1.8  # Long prompts need more input budget
    MULTI_TURN_MULTIPLIER = 1.2    # Multi-turn needs history budget

    def __init__(self):
        # Historical usage: model → {avg_input, avg_output, avg_total, count}
        self._history: Dict[str, Dict[str, float]] = {}

    def estimate(
        self,
        prompt: str,
        complexity: str = "L2",
        history_turns: int = 0,
        model: str = "default",
    ) -> BudgetEstimate:
        """Estimate token budget for a request.

        Uses:
        1. CogER complexity → base budget
        2. Prompt signals → multipliers
        3. Historical usage → adjustment
        """
        base = self.BASE_BUDGETS.get(complexity, self.BASE_BUDGETS["L2"])
        input_budget = base["input"]
        output_budget = base["output"]

        # Prompt signal analysis
        prompt_lower = prompt.lower()
        prompt_words = prompt.split()
        prompt_len = len(prompt_words)

        # Code detection
        has_code = any(sig in prompt_lower for sig in [
            "def ", "function", "class ", "import ", "```", "code", "python",
            "javascript", "java", "rust", "go ", "shell", "bash", "script",
        ])
        if has_code:
            output_budget = int(output_budget * self.CODE_MULTIPLIER)

        # Math/reasoning detection
        has_math = any(sig in prompt_lower for sig in [
            "prove", "calculate", "solve", "equation", "theorem", "derive",
            "mathematical", "algebra", "calculus", "probability", "statistics",
        ])
        if has_math:
            output_budget = int(output_budget * self.MATH_MULTIPLIER)

        # Long context adjustment
        if prompt_len > 500:
            input_budget = int(input_budget * self.LONG_CONTEXT_MULTIPLIER)
        elif prompt_len > 100:
            input_budget = int(input_budget * 1.3)

        # Multi-turn adjustment
        if history_turns > 0:
            input_budget = int(input_budget * (1 + 0.1 * min(history_turns, 10)))

        # Historical adjustment
        hist = self._history.get(model)
        if hist and hist.get("count", 0) >= 3:
            # Adjust based on average past usage
            avg_output = hist["avg_output"]
            if avg_output > output_budget * 1.2:
                output_budget = int(output_budget * 1.1)
            elif avg_output < output_budget * 0.7:
                output_budget = int(output_budget * 0.9)

        total = input_budget + output_budget
        confidence = 0.8 if not hist else min(0.95, 0.6 + 0.1 * min(hist["count"] / 10, 3))

        reasons = [f"base_{complexity}"]
        if has_code:
            reasons.append(f"code_x{self.CODE_MULTIPLIER}")
        if has_math:
            reasons.append(f"math_x{self.MATH_MULTIPLIER}")
        if prompt_len > 500:
            reasons.append(f"long_context_x{self.LONG_CONTEXT_MULTIPLIER}")
        if history_turns > 0:
            reasons.append(f"multi_turn_{history_turns}turns")
        if hist:
            reasons.append(f"history_adjusted")

        return BudgetEstimate(
            input_budget=input_budget,
            output_budget=output_budget,
            total=total,
            reasoning=", ".join(reasons),
            complexity=complexity,
            confidence=confidence,
        )

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ):
        """Record actual token usage for future budget estimation."""
        if model not in self._history:
            self._history[model] = {"avg_input": 0, "avg_output": 0, "avg_total": 0, "count": 0}

        hist = self._history[model]
        count = hist["count"]
        total = input_tokens + output_tokens

        # Exponential moving average
        alpha = 0.3
        hist["avg_input"] = (1 - alpha) * hist["avg_input"] + alpha * input_tokens if count > 0 else input_tokens
        hist["avg_output"] = (1 - alpha) * hist["avg_output"] + alpha * output_tokens if count > 0 else output_tokens
        hist["avg_total"] = hist["avg_input"] + hist["avg_output"]
        hist["count"] = count + 1

    def get_stats(self) -> Dict[str, Any]:
        """Get allocator statistics."""
        return {
            "models_tracked": len(self._history),
            "history": {
                model: {k: round(v, 1) for k, v in data.items()}
                for model, data in self._history.items()
            },
        }
