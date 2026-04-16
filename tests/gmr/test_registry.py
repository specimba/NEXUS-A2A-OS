"""tests/gmr/test_registry.py — GMR Model Registry Tests"""

import pytest
import time
from nexus_os.gmr.registry import ModelRegistry, ModelInfo


class TestModelRegistry:
    """Test ModelRegistry functionality."""
    
    def test_registry_init(self):
        """Test registry initialization."""
        registry = ModelRegistry()
        assert registry._refresh_interval == 300
        assert registry._local_endpoint == "http://localhost:7352"
    
    def test_default_budgets(self):
        """Test default budget categories."""
        registry = ModelRegistry()
        assert registry.get_budget_for_category("agent") == 100000
        assert registry.get_budget_for_category("skill") == 50000
        assert registry.get_budget_for_category("swarm") == 200000
        assert registry.get_budget_for_category("research") == 150000
    
    def test_unknown_category_budget(self):
        """Test unknown category gets default budget."""
        registry = ModelRegistry()
        assert registry.get_budget_for_category("unknown") == 100000
    
    def test_tier_inference(self):
        """Test tier inference from model names."""
        registry = ModelRegistry()
        
        assert registry._infer_tier("gpt-4-turbo") == 90
        assert registry._infer_tier("claude-3-opus") == 90
        assert registry._infer_tier("llama3:70b") == 70
        assert registry._infer_tier("qwen2.5:14b") == 70
        assert registry._infer_tier("osman-coder") == 40
        assert registry._infer_tier("phi-3-mini") == 40
        assert registry._infer_tier("unknown-model") == 50
    
    def test_model_info_creation(self):
        """Test ModelInfo dataclass."""
        info = ModelInfo(
            name="test-model",
            provider="ollama",
            max_context=8192,
            tier=70
        )
        assert info.name == "test-model"
        assert info.provider == "ollama"
        assert info.max_context == 8192
        assert info.tier == 70
    
    def test_list_models_empty(self):
        """Test listing models when registry is empty."""
        registry = ModelRegistry()
        models = registry.list_models()
        assert len(models) == 0
    
    def test_list_models_filter_by_provider(self):
        """Test filtering models by provider."""
        registry = ModelRegistry()
        registry._models["m1"] = ModelInfo("m1", "ollama", 4096, 50)
        registry._models["m2"] = ModelInfo("m2", "openai", 8192, 90)
        
        ollama_models = registry.list_models(provider="ollama")
        assert len(ollama_models) == 1
        assert ollama_models[0].name == "m1"
    
    def test_list_models_filter_by_tier(self):
        """Test filtering models by minimum tier."""
        registry = ModelRegistry()
        # Use keyword args to correctly set tier
        registry._models = {
            "m1": ModelInfo(name="m1", provider="ollama", max_context=4096, tier=40),
            "m2": ModelInfo(name="m2", provider="ollama", max_context=8192, tier=70),
            "m3": ModelInfo(name="m3", provider="ollama", max_context=16384, tier=90),
        }
        
        high_tier = registry.list_models(min_tier=70)
        assert len(high_tier) == 2
    
    def test_is_available_default(self):
        """Test default availability check."""
        registry = ModelRegistry()
        assert registry.is_available("unknown-model") is False
    
    def test_start_stop(self):
        """Test registry start/stop."""
        registry = ModelRegistry()
        registry.start()
        time.sleep(0.5)
        assert registry._refresh_thread is not None
        assert registry._refresh_thread.is_alive()
        
        registry.stop()
        time.sleep(0.5)
        assert not registry._refresh_thread.is_alive()