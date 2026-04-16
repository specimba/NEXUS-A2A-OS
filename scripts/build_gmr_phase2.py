#!/usr/bin/env python3
"""Phase 2: Hermes ↔ GMR ↔ TokenGuard Integration"""
import os

ENGINE_DIR = os.path.join("src", "nexus_os", "engine")
TEST_DIR = os.path.join("tests", "engine")
os.makedirs(ENGINE_DIR, exist_ok=True)
os.makedirs(TEST_DIR, exist_ok=True)

HERMES_CODE = '''"""engine/hermes.py — Hermes Task Router with GMR Integration"""
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
'''

TEST_CODE = '''"""tests/engine/test_hermes_gmr.py — Phase 2 Integration Tests"""
import pytest
from nexus_os.engine.hermes import HermesRouter
from nexus_os.monitoring.token_guard import TokenGuard

def test_hermes_classification_and_routing():
    guard = TokenGuard(budgets={"test-agent": 150000})
    router = HermesRouter(token_guard=guard)
    
    # Test code routing
    decision = router.route("task-1", "Write a python script to sort a list securely", {"agent_id": "test-agent"})
    assert decision.domain == "code"
    assert decision.selected_model is not None
    assert isinstance(decision.fallback_models, list)
    assert len(decision.fallback_models) > 0

def test_hermes_budget_awareness():
    # Agent with a critically low budget (forces local/cheap fallback in GMR)
    guard = TokenGuard(budgets={"broke-agent": 5000})
    router = HermesRouter(token_guard=guard)
    
    decision = router.route("task-2", "Analyze this complex architecture deeply", {"agent_id": "broke-agent"})
    
    # Should correctly classify as reasoning
    assert decision.domain == "reasoning"
    
    # Because budget < 50000, GMR restricts selection to Tier <= 50 (Local models)
    # Based on our domain_mapping, the local fallback for reasoning is osman-reasoning
    assert decision.selected_model == "osman-reasoning"
'''

# Write Hermes
with open(os.path.join(ENGINE_DIR, "hermes.py"), "w", encoding="utf-8") as f:
    f.write(HERMES_CODE)
print(f"[✅] Upgraded {os.path.join(ENGINE_DIR, 'hermes.py')}")

# Write Tests
with open(os.path.join(TEST_DIR, "test_hermes_gmr.py"), "w", encoding="utf-8") as f:
    f.write(TEST_CODE)
print(f"[✅] Created {os.path.join(TEST_DIR, 'test_hermes_gmr.py')}")

print("\n[🚀] Phase 2 Ready. Hermes is now fully powered by GMR.")