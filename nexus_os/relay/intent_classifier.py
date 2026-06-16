"""Relay IntentClassifier — Heuristic prompt-based intent detection for routing."""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum


class RoutingIntent(Enum):
    SWE = "swe"
    MATH = "math"
    CODE = "code"
    QUALITY = "quality"
    REASONING = "reasoning"
    SPEED = "speed"
    COST = "cost"
    GENERAL = "general"


KEYWORD_MAP: dict[RoutingIntent, set[str]] = {
    RoutingIntent.SWE: {"refactor", "architecture", "design pattern", "code review", "pull request", "ci/cd", "testing", "deployment", "software engineering", "best practice", "clean code", "technical debt", "unit test"},
    RoutingIntent.MATH: {"calculate", "equation", "formula", "derivative", "integral", "algebra", "geometry", "theorem", "proof", "statistical", "probability", "matrix", "vector", "sum", "compute"},
    RoutingIntent.CODE: {"function", "implement", "bug", "fix", "code", "program", "script", "algorithm", "syntax", "compile", "class", "method", "api", "endpoint", "query", "loop", "variable"},
    RoutingIntent.QUALITY: {"polish", "improve", "optimize", "refine", "clean", "style", "consistent", "readable", "maintainable", "documentation", "comment", "lint", "format"},
    RoutingIntent.REASONING: {"reason", "explain", "analyze", "compare", "contrast", "evaluate", "assess", "why", "how", "strategy", "plan", "think", "logic", "argument", "deduce"},
    RoutingIntent.SPEED: {"quick", "fast", "rapid", "urgent", "asap", "short", "summarize", "brief", "immediate", "instant", "simple"},
    RoutingIntent.COST: {"cheap", "free", "low cost", "budget", "affordable", "economic", "inexpensive", "cost-effective", "minimal"},
}


@dataclass
class IntentResult:
    intent: RoutingIntent
    confidence: float
    keywords_found: list[str] = field(default_factory=list)
    all_scores: dict[str, float] = field(default_factory=dict)


class PromptIntentClassifier:
    def classify(self, prompt: str) -> IntentResult:
        prompt_lower = prompt.lower()
        scores = {}
        for intent, keywords in KEYWORD_MAP.items():
            score = 0.0
            found = []
            for kw in keywords:
                if kw in prompt_lower:
                    score += 1.0
                    found.append(kw)
            if score > 0:
                scores[intent.value] = score
        best_intent = RoutingIntent.GENERAL
        best_score = 0.0
        if scores:
            best_key = max(scores, key=scores.get)
            best_intent = RoutingIntent(best_key)
            best_score = scores[best_key]
        confidence = min(best_score / 3.0, 1.0) if best_score > 0 else 0.0
        return IntentResult(
            intent=best_intent,
            confidence=confidence,
            keywords_found=[kw for intent_kws in KEYWORD_MAP.values() for kw in intent_kws if kw in prompt_lower][:10],
            all_scores=scores,
        )
