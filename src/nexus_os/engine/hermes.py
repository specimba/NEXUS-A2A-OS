"""engine/hermes.py — Hermes Task Router with GMR Integration"""
import logging
from dataclasses import dataclass
from typing import List, Dict, Any

from nexus_os.gmr.rotator import GeniusModelRotator, GMRSelection
from nexus_os.gmr.telemetry import TelemetryIngest

logger = logging.getLogger(__name__)

@dataclass
class RoutingDecision:
    selected_model: str
    fallback_models: List[str]
    reason: str
    domain: str

class IntentClassifier:
    """Zero-shot semantic keyword classifier"""
    KEYWORDS = {
        "code": ["code", "debug", "python", "script", "function", "refactor", "implement"],
        "reasoning": ["plan", "analyze", "architecture", "think", "logic", "solve"],
        "research": ["research", "summarize", "find", "paper", "explain", "literature"],
        "fast": ["quick", "ping", "hello", "status", "format"],
        "security": ["audit", "vulnerability", "auth", "security", "exploit", "policy"]
    }
    
    @classmethod
    def classify(cls, text: str) -> str:
        text = text.lower()
        scores = {domain: sum(1 for kw in words if kw in text) for domain, words in cls.KEYWORDS.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "general"

class HermesRouter:
    def __init__(self, token_guard=None):
        self.token_guard = token_guard
        self.classifier = IntentClassifier()
        # Initialize GMR Core
        self.gmr = GeniusModelRotator(telemetry=TelemetryIngest())
        
    def route(self, task_id: str, description: str, context: Dict[str, Any]) -> RoutingDecision:
        # 1. Classify Intent
        domain = self.classifier.classify(description)
        
        # 2. Check Budget
        agent_id = context.get("agent_id", "default")
        budget = self.token_guard.remaining(agent_id) if self.token_guard else 100000
        
        # 3. GMR Selection (Dual-Pool, Budget-Aware)
        selection: GMRSelection = self.gmr.select(task_type=domain, budget_remaining=budget)
        
        logger.info(f"[Hermes] Task {task_id} routed to {selection.primary} (Domain: {domain}, Budget: {budget})")
        
        return RoutingDecision(
            selected_model=selection.primary,
            fallback_models=selection.fallbacks,
            reason=selection.reason,
            domain=domain
        )
