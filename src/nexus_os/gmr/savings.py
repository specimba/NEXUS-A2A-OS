"""GMR Token Savings Tracker"""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List


@dataclass
class TokenSavings:
    timestamp: str
    task_type: str
    primary_model: str
    fallback_model: str
    tokens_used: int
    tokens_saved: int
    cost_saved: float
    reason: str


class SavingsTracker:
    """Track and report token savings from model rotation."""

    def __init__(self):
        self.savings: List[TokenSavings] = []
        self.total_tokens_used = 0
        self.total_tokens_saved = 0
        self.total_cost_saved = 0.0

    def record(
        self,
        task_type: str,
        primary: str,
        fallback: str,
        tokens_used: int,
        tokens_saved: int,
        cost_saved: float,
        reason: str,
    ):
        saving = TokenSavings(
            timestamp=datetime.now(timezone.utc).isoformat(),
            task_type=task_type,
            primary_model=primary,
            fallback_model=fallback,
            tokens_used=tokens_used,
            tokens_saved=tokens_saved,
            cost_saved=cost_saved,
            reason=reason,
        )
        self.savings.append(saving)
        self.total_tokens_used += tokens_used
        self.total_tokens_saved += tokens_saved
        self.total_cost_saved += cost_saved

    def get_report(self) -> Dict:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_tokens_used": self.total_tokens_used,
                "total_tokens_saved": self.total_tokens_saved,
                "total_cost_saved": round(self.total_cost_saved, 4),
                "savings_rate": (
                    self.total_tokens_saved / max(self.total_tokens_used, 1)
                ) * 100,
            },
            "recent": [
                {
                    "ts": s.timestamp,
                    "task": s.task_type,
                    "primary": s.primary_model,
                    "saved": s.tokens_saved,
                    "cost_saved": s.cost_saved,
                }
                for s in self.savings[-10:]
            ],
        }

    def save_report(self, path: str):
        """Save report to JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.get_report(), f, indent=2)
