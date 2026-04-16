"""tests/engine/test_hermes_gmr.py — Phase 2 Integration Tests"""
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
