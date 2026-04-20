"""NEXUS OS — Governor module: Auth, trust scoring, action gating."""
from enum import Enum
from typing import Optional

class Scope(Enum):
    SELF = "self"
    PROJECT = "project"
    CROSS = "cross"
    SYSTEM = "system"

class Impact(Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"
    CRIT = "crit"

class Decision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    HOLD = "hold"

_SUSPICIOUS = ["delete all", "rm -rf", "exfiltrate", "backdoor", "sudo rm"]

_LANES = {
    "research": (0.3, 5),
    "review": (0.5, 3),
    "audit": (0.7, 2),
    "impl": (0.6, 4),
}

class Kaiju:
    def auth(self, request: dict) -> Decision:
        action = request.get("action", "")
        if any(bad in action.lower() for bad in _SUSPICIOUS):
            return Decision.DENY
        return Decision.ALLOW

class TrustScorer:
    def score(self, lane: str, quality: float, usage: int, risk: float) -> float:
        base_rate, max_use = _LANES.get(lane, (0.5, 3))
        return min(1.0, base_rate * (quality / 100) * (1 - risk) * (1 - usage / (max_use * 10)))

class Governor:
    def __init__(self):
        self.kaiju = Kaiju()
        self.trust = TrustScorer()

    def check(self, action: str, agent: Optional[str] = None) -> dict:
        decision = self.kaiju.auth({"action": action})
        return {
            "allowed": decision == Decision.ALLOW,
            "decision": decision.value,
            "reason": "suspicious pattern" if decision == Decision.DENY else "ok",
        }