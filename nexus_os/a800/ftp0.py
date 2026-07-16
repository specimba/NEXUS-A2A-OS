#!/usr/bin/env python3
"""
FTPO: Final-Token Preference Optimization
==========================================
From PAPERS P0 #9 + F3 finding.
90% slop suppression <1% quality loss — displaces DPO for style objectives.
"""

import json
from pathlib import Path
from typing import Any


class FTPOTrainer:
    """Train with final-token preference pairs."""

    def __init__(self, beta: float = 0.1):
        self.beta = beta

    def prepare_pairs(self, preferred: list[dict], rejected: list[dict]) -> list[dict]:
        """Prepare preference pairs for training."""
        pairs = []
        for pref, rej in zip(preferred, rejected):
            pairs.append({
                "prompt": pref.get("prompt", ""),
                "chosen": pref.get("output", ""),
                "rejected": rej.get("output", ""),
            })
        return pairs


def generate_preference_pairs(traces: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Split traces into preferred/rejected by trust score.
    High-trust → preferred, low-trust → rejected.
    """
    sorted_traces = sorted(traces, key=lambda t: t.get("trust_score", 0.5), reverse=True)
    mid = len(sorted_traces) // 2
    return sorted_traces[:mid], sorted_traces[mid:]
