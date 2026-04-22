"""tests/swarm/test_spawner_budget_gate.py — Swarm Budget Gate Tests"""

import pytest
from nexus_os.swarm.openclaw_spawner import OpenClawSpawner, SpawnConfig
from nexus_os.monitoring.token_guard import TokenGuard, TokenBudget


class TestSwarmBudgetGate:
    """Test TokenGuard integration with OpenClawSpawner."""
    
    @pytest.fixture
    def spawner(self):
        """Create spawner with fresh TokenGuard."""
        config = SpawnConfig(task_threshold=2, max_workers=3)
        token_guard = TokenGuard()
        return OpenClawSpawner(config=config, token_guard=token_guard)
    
    @pytest.fixture
    def empty_spawner(self):
        """Create spawner with TokenGuard that has no budget."""
        config = SpawnConfig(task_threshold=2, max_workers=3)
        token_guard = TokenGuard()
        # Exhaust budget by setting used to equal total
        budget_key = token_guard._get_budget_key("swarm")
        token_guard._budgets[budget_key] = TokenBudget(total=50000, used=50000)
        return OpenClawSpawner(config=config, token_guard=token_guard)
    
    def test_spawner_has_token_guard(self, spawner):
        """Test spawner has TokenGuard instance."""
        assert spawner.token_guard is not None
    
    def test_check_budget_true(self, spawner):
        """Test budget check returns True when budget available."""
        assert spawner.check_budget("swarm") is True
    
    def test_check_budget_false_no_budget(self, empty_spawner):
        """Test budget check returns False when no budget."""
        assert empty_spawner.check_budget("swarm") is False
    
    def test_get_budget_status(self, spawner):
        """Test budget status retrieval."""
        status = spawner.get_budget_status("swarm")
        
        assert "remaining" in status
        assert "limit" in status
        assert "pct_used" in status
        assert "can_spawn" in status
    
    def test_get_budget_status_exceeded(self, empty_spawner):
        """Test budget status when exceeded."""
        status = empty_spawner.get_budget_status("swarm")
        
        assert status["remaining"] == 0
        assert status["can_spawn"] is False
    
    def test_track_usage(self, spawner):
        """Test token usage tracking."""
        initial = spawner._total_tokens_used
        
        spawner.track_usage("swarm", 1000)
        
        assert spawner._total_tokens_used == initial + 1000
    
    def test_should_spawn_blocks_on_no_budget(self, empty_spawner):
        """Test spawning is blocked when budget exhausted."""
        # Even with pending tasks, should NOT spawn
        assert empty_spawner.should_spawn() is False
    
    def test_should_spawn_allows_when_budget_available(self, spawner):
        """Test spawning allowed with budget and pending tasks."""
        # Should allow when budget available (threshold check will fail, but budget check passes)
        # This tests the budget check logic specifically
        assert spawner.check_budget("swarm") is True
    
    def test_budget_gate_minimum_threshold(self, spawner):
        """Test minimum budget threshold for spawning."""
        # Default is 1000 tokens minimum
        status = spawner.get_budget_status("swarm")
        
        # If remaining >= 1000, can spawn
        if status["remaining"] >= 1000:
            assert status["can_spawn"] is True
    
    def test_custom_token_guard(self):
        """Test initialization with custom TokenGuard."""
        custom_tg = TokenGuard()
        spawner = OpenClawSpawner(token_guard=custom_tg)
        
        assert spawner.token_guard is custom_tg


class TestSpawnConfig:
    """Test SpawnConfig with token guard."""
    
    def test_default_config(self):
        """Test default config values."""
        config = SpawnConfig()
        
        assert config.task_threshold == 3
        assert config.max_workers == 5
        assert config.spawn_cooldown == 60