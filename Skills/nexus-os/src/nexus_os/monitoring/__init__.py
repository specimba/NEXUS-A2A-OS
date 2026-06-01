"""NEXUS OS — Monitoring module: Token budget tracking + TALE reasoning.

TALE (Token-Budget-Aware LLM Reasoning, ArXiv 2603.08425):
- Dynamically estimates token budget per problem based on reasoning complexity.
- Guides model within budget. Achieves 68.6% token reduction with <5% accuracy drop.
"""
from typing import Dict, Optional

class TALEEstimator:
    """Estimates per-query token budget based on task complexity heuristics."""

    def __init__(self):
        self._base_budget = 2048
        self._complexity_markers = {
            "code": 1.4,
            "reason": 1.6,
            "research": 1.8,
            "fast": 0.7,
            "sec": 1.5,
        }

    def estimate(self, domain: str, prompt: str, context_chars: int = 0) -> int:
        """Estimate budget for a prompt. Returns tokens (rounded)."""
        base = self._base_budget
        multiplier = self._complexity_markers.get(domain, 1.0)
        length_factor = min(len(prompt) / 200.0, 2.0)
        context_factor = min(context_chars / 4000.0, 1.5)
        budget = int(base * multiplier * (1 + (length_factor - 1) * 0.3 + (context_factor - 1) * 0.2))
        return min(budget, 128000)

    def reserve(self, agent: str, domain: str, prompt: str, context_chars: int = 0) -> int:
        """Reserve budget for a task. Returns allocated token budget."""
        return self.estimate(domain, prompt, context_chars)

    def reclaim(self, agent: str, used: int) -> int:
        """Called after task completion. Returns reclaimed tokens (for logging)."""
        return used


class TokenGuard:
    def __init__(self, budgets: Dict[str, int]):
        self.budgets = budgets
        self.used: Dict[str, int] = {k: 0 for k in budgets}

    def track(self, agent: str, tokens: int):
        if agent in self.used:
            self.used[agent] += tokens

    def check(self, agent: str, need: int) -> bool:
        if agent not in self.budgets:
            return True
        return (self.used.get(agent, 0) + need) <= self.budgets[agent]

    def check_and_reserve(self, agent: str, domain: str, prompt: str, context_chars: int = 0) -> dict:
        """TokenGuard + TALE integration: check budget + reserve TALE-estimated budget."""
        tale = TALEEstimator()
        tale_budget = tale.reserve(agent, domain, prompt, context_chars)
        within_global = self.check(agent, tale_budget)
        return {
            "allowed": within_global,
            "tale_budget": tale_budget,
            "agent": agent,
            "domain": domain,
        }


class TokenMovement:
    def __init__(self, agent: str, prompt: int, completion: int, model: str):
        self.agent = agent
        self.prompt_tokens = prompt
        self.completion_tokens = completion
        self.model = model
        self.total = prompt + completion


class SessionBudget:
    def __init__(self, total: int):
        self.total = total
        self.used = 0

    def deduct(self, amount: int):
        self.used += amount

    def remaining(self) -> int:
        return max(0, self.total - self.used)


class TokenTracker:
    _instance: Optional["TokenTracker"] = None

    @classmethod
    def get_instance(cls) -> "TokenTracker":
        if cls._instance is None:
            cls._instance = TokenTracker()
        return cls._instance

    def __init__(self):
        self.budget: Optional[SessionBudget] = None
        self.movements: list = []

    def start_session(self, total_tokens: int):
        self.budget = SessionBudget(total_tokens)
        self.movements = []

    def record_api_call(self, agent: str, prompt: int, completion: int, model: str):
        m = TokenMovement(agent, prompt, completion, model)
        self.movements.append(m)
        if self.budget:
            self.budget.deduct(m.total)

    def get_current_usage(self) -> dict:
        if not self.budget:
            return {"used": 0, "remaining": 0, "total": 0}
        return {
            "used": self.budget.used,
            "remaining": self.budget.remaining(),
            "total": self.budget.total,
        }


def start_tracking(total_tokens: int):
    TokenTracker.get_instance().start_session(total_tokens)


def track_api_call(agent: str, prompt: int, completion: int, model: str):
    TokenTracker.get_instance().record_api_call(agent, prompt, completion, model)


def get_usage() -> dict:
    return TokenTracker.get_instance().get_current_usage()


def end_tracking():
    TokenTracker._instance = None
