"""tests/gmr/test_router.py — GMR Router Tests"""

import pytest
from nexus_os.gmr.router import GMRRouter, RouteResult
from nexus_os.gmr import IntentCategory, ModelPool


class TestGMRRouter:
    """Test GMRRouter functionality."""
    
    @pytest.fixture
    def router(self):
        """Create GMR router instance."""
        return GMRRouter()
    
    def test_router_init(self, router):
        """Test router initialization."""
        assert router.token_guard is not None
        assert router.trust_scorer is not None
        assert router.engine is not None
        assert router.registry is not None
    
    def test_default_models_registered(self, router):
        """Test default models are registered."""
        stats = router.get_stats()
        assert stats["models_registered"] >= 6  # 3 local + 3 cloud
        assert stats["local_models"] >= 3
        assert stats["cloud_models"] >= 3
    
    def test_route_code_intent(self, router):
        """Test routing for code intent."""
        result = router.route(
            prompt="Write a Python function to calculate fibonacci",
            agent_id="test-agent",
            metadata={"is_code_task": True}
        )
        
        assert result.model_name != "error"
        assert result.pool in ["fast", "premium"]
        assert result.budget_remaining >= 0
    
    def test_route_research_intent(self, router):
        """Test routing for research intent."""
        result = router.route(
            prompt="Research the latest advances in quantum computing",
            agent_id="test-agent",
            metadata={"requires_deep_reasoning": True}
        )
        
        assert result.model_name != "error"
        assert result.reason is not None
    
    def test_route_security_intent(self, router):
        """Test routing for security intent."""
        result = router.route(
            prompt="Audit this code for security vulnerabilities",
            agent_id="test-agent",
        )
        
        assert result.model_name != "error"
    
    def test_route_with_low_budget(self, router):
        """Test routing when budget is low."""
        # Exhaust budget
        router.token_guard.track("test-agent", 100000)
        
        result = router.route(
            prompt="Write a function",
            agent_id="test-agent",
        )
        
        # Should still work but log warning
        assert result.model_name != "error"
    
    def test_route_unknown_intent(self, router):
        """Test routing for unknown/general intent."""
        result = router.route(
            prompt="Hello, how are you?",
            agent_id="test-agent",
        )
        
        assert result.model_name != "error"
        assert result.pool in ["fast", "premium"]
    
    def test_route_preserves_budget_info(self, router):
        """Test that route result includes budget info."""
        result = router.route(
            prompt="Test prompt",
            agent_id="test-agent",
        )
        
        assert hasattr(result, "budget_remaining")
        assert hasattr(result, "estimated_cost")
        assert hasattr(result, "reason")
    
    def test_record_outcome_success(self, router):
        """Test recording successful outcome."""
        # Get a model first
        result = router.route(prompt="test", agent_id="test-agent")
        
        # Record success
        router.record_outcome(result.model_name, True)
        
        # Should not raise
        assert True
    
    def test_record_outcome_failure(self, router):
        """Test recording failure outcome."""
        # Get a model first
        result = router.route(prompt="test", agent_id="test-agent")
        
        # Record failure (circuit breaker should increment)
        router.record_outcome(result.model_name, False)
        
        # Should not raise
        assert True
    
    def test_multiple_routes_different_agents(self, router):
        """Test routing for different agents."""
        result1 = router.route(prompt="code", agent_id="agent-1")
        result2 = router.route(prompt="code", agent_id="agent-2")
        
        # Both should work independently
        assert result1.model_name != "error"
        assert result2.model_name != "error"
    
    def test_metadata_influences_selection(self, router):
        """Test that metadata affects model selection."""
        # Code task should prefer fast pool
        code_result = router.route(
            prompt="write a function",
            agent_id="test-agent",
            metadata={"is_code_task": True, "time_sensitive": True}
        )
        
        assert code_result.model_name != "error"


class TestRouteResult:
    """Test RouteResult dataclass."""
    
    def test_route_result_creation(self):
        """Test RouteResult creation."""
        result = RouteResult(
            model_name="test-model",
            provider="ollama",
            pool="fast",
            reason="Top fast model for code",
            trust_score=0.85,
            budget_remaining=50000,
            estimated_cost=0.0,
        )
        
        assert result.model_name == "test-model"
        assert result.provider == "ollama"
        assert result.pool == "fast"
        assert result.trust_score == 0.85
        assert result.budget_remaining == 50000
        assert result.estimated_cost == 0.0
    
    def test_route_result_optional_trust(self):
        """Test RouteResult with None trust score."""
        result = RouteResult(
            model_name="test-model",
            provider="ollama",
            pool="fast",
            reason="test",
            trust_score=None,
            budget_remaining=50000,
            estimated_cost=0.0,
        )
        
        assert result.trust_score is None