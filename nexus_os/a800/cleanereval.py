#!/usr/bin/env python3
"""
CLEANER + FAPO: Trajectory Purification
=========================================
From PAPERS P0 #8.
CLEANER: purified trajectories, SOTA at 1/3 the steps.
FAPO: ~30-50% of "correct" RLVR rollouts are flawed positives — add process-check judge.
"""

from typing import Any


class CLEANERPurifier:
    """Purify trajectories before training."""

    def __init__(self, strategy: str = "outcome_verified"):
        self.strategy = strategy

    def purge(self, trace: dict) -> bool:
        """Return True if trace should be PURGED (dropped)."""
        # Drop empty or malformed
        if not trace.get("prompt") or not trace.get("output"):
            return True

        # Drop if outcome is missing
        if "outcome_ok" not in trace:
            return True

        # Drop if tool calls all failed
        tool_calls = trace.get("tool_calls", [])
        if tool_calls and all(not t.get("ok") for t in tool_calls):
            return True

        # Drop if trust is too low
        if trace.get("trust_score", 0.5) < 0.3:
            return True

        return False


class FAPOChecker:
    """Flawed-positive process check."""

    def __init__(self, judge_type: str = "programmatic_verdict"):
        self.judge_type = judge_type

    def check(self, trace: dict) -> bool:
        """
        Return True if trace is GENUINE (not a flawed positive).
        ~30-50% of "correct" rollouts are actually flawed.
        """
        # If outcome is wrong, it's not a flawed positive — it's just wrong
        if not trace.get("outcome_ok", False):
            return True

        # Check for suspicious patterns that indicate a flawed positive:
        # - Output matches expected but reasoning is circular
        # - Tool call succeeded but result was ignored
        # - Multiple retries masking a fundamental error

        output = trace.get("output", "")
        reasoning = trace.get("reasoning", "")

        # Circular reasoning detection
        if reasoning and output in reasoning:
            return False  # flawed positive

        # Ignored tool result
        tool_results = [t.get("result") for t in trace.get("tool_calls", []) if t.get("ok")]
        if tool_results and not any(r in output for r in tool_results if r):
            return False  # succeeded but result was ignored

        return True


def purify_trajectories(traces: list[dict], strategy: str = "outcome_verified",
                        min_outcome_score: float = 0.7) -> list[dict]:
    """Convenience: full purification pipeline."""
    purifier = CLEANERPurifier(strategy)
    fapo = FAPOChecker()

    result = []
    for t in traces:
        if not purifier.purge(t) and fapo.check(t):
            result.append(t)
    return result
