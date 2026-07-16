#!/usr/bin/env python3
"""
SERA: Soft-Verified Repo-Native SFT
=====================================
From PAPERS P0 #6 + F3 finding.
26x cheaper than RL, SFT-only, matches Devstral-Small-2.
No unit-test infra needed — uses programmatic verdict from guard pipeline.
"""

from typing import Any


class SERAVerifier:
    """Soft verification for repo-native SFT traces."""

    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold

    def verify(self, trace: dict) -> bool:
        """
        Soft-verify a training trace.
        Returns True if the trace passes verification.
        """
        # Check outcome
        outcome_ok = trace.get("outcome_ok", False)
        if not outcome_ok:
            return False

        # Check verdict from guard pipeline
        verdict = trace.get("verdict", "")
        if verdict in ("UNSAFE", "BLOCKED", "REFUSED"):
            return False

        # Check trust score
        trust = trace.get("trust_score", 0.0)
        if trust < self.threshold:
            return False

        # Check tool-call success
        tool_calls = trace.get("tool_calls", [])
        if tool_calls:
            success_rate = sum(1 for t in tool_calls if t.get("ok")) / len(tool_calls)
            if success_rate < self.threshold:
                return False

        return True

    def verify_batch(self, traces: list[dict]) -> tuple[list[dict], list[dict]]:
        """Verify a batch, returning (passed, failed)."""
        passed, failed = [], []
        for t in traces:
            (passed if self.verify(t) else failed).append(t)
        return passed, failed


def soft_verify_batch(traces: list[dict], threshold: float = 0.8) -> list[dict]:
    """Convenience: filter traces by soft verification."""
    verifier = SERAVerifier(threshold)
    passed, _ = verifier.verify_batch(traces)
    return passed
