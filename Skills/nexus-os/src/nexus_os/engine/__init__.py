"""NEXUS OS — Engine module: Intent routing via Hermes."""
from enum import Enum

class Domain(Enum):
    CODE = "code"
    REASON = "reason"
    RESEARCH = "research"
    FAST = "fast"
    SEC = "sec"

_KEYWORDS = {
    Domain.CODE: ["code", "function", "debug", "api", "python", "write", "class"],
    Domain.REASON: ["think", "analyze", "logic", "reason", "explain"],
    Domain.RESEARCH: ["search", "find", "investigate", "research", "lookup"],
    Domain.FAST: ["quick", "brief", "short", "fast", "simple"],
    Domain.SEC: ["security", "auth", "encrypt", "audit", "safe"],
}

class Hermes:
    def classify(self, text: str) -> Domain:
        text = text.lower()
        scores = {d: sum(1 for kw in kws if kw in text) for d, kws in _KEYWORDS.items()}
        if max(scores.values()) == 0:
            return Domain.REASON
        return max(scores, key=scores.get)

    def route(self, desc: str) -> dict:
        domain = self.classify(desc)
        return {"domain": domain.value, "keywords": _KEYWORDS[domain]}