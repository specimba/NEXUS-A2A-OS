"""NEXUS OS — Monitoring module: Token budget tracking and enforcement."""
from typing import Dict, Optional

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