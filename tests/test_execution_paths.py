"""tests/test_execution_paths.py — Hot/Warm/Cold Execution Path Tests"""

import pytest
import time
from nexus_os.execution_paths import (
    ExecutionPath, PathRouter, PathConfig,
    PATH_LATENCY_SLA, get_router, hot_path, warm_path, cold_path
)


class TestExecutionPath:
    """Test ExecutionPath enum."""
    
    def test_path_values(self):
        """Test path enum values."""
        assert ExecutionPath.HOT.value == "hot"
        assert ExecutionPath.WARM.value == "warm"
        assert ExecutionPath.COLD.value == "cold"
    
    def test_all_paths_defined(self):
        """Test all 3 paths are defined."""
        paths = list(ExecutionPath)
        assert len(paths) == 3


class TestPathLatencySla:
    """Test path SLA definitions."""
    
    def test_hot_sla(self):
        """Test HOT path SLA."""
        assert PATH_LATENCY_SLA[ExecutionPath.HOT] == 0.020  # 20μs
    
    def test_warm_sla(self):
        """Test WARM path SLA."""
        assert PATH_LATENCY_SLA[ExecutionPath.WARM] == 50.0  # 50ms
    
    def test_cold_sla(self):
        """Test COLD path SLA."""
        assert PATH_LATENCY_SLA[ExecutionPath.COLD] == 1000.0  # 1000ms


class TestPathConfig:
    """Test PathConfig dataclass."""
    
    def test_hot_config(self):
        """Test HOT path config."""
        config = PathConfig(ExecutionPath.HOT)
        assert config.path == ExecutionPath.HOT
        assert config.timeout_ms == 0.020
    
    def test_warm_config(self):
        """Test WARM path config."""
        config = PathConfig(ExecutionPath.WARM)
        assert config.path == ExecutionPath.WARM
        assert config.timeout_ms == 50.0
    
    def test_custom_timeout(self):
        """Test custom timeout."""
        config = PathConfig(ExecutionPath.WARM, timeout_ms=100.0)
        assert config.timeout_ms == 100.0


class TestPathRouter:
    """Test PathRouter class."""
    
    @pytest.fixture
    def router(self):
        return PathRouter()
    
    def test_route_check_budget(self, router):
        """Test auto-route for check budget."""
        path = router.route("check_budget")
        assert path == ExecutionPath.HOT
    
    def test_route_get_trust(self, router):
        """Test auto-route for get trust."""
        path = router.route("get_trust")
        assert path == ExecutionPath.HOT
    
    def test_route_circuit_breaker(self, router):
        """Test auto-route for circuit breaker."""
        path = router.route("circuit_breaker_check")
        assert path == ExecutionPath.HOT
    
    def test_route_append_event(self, router):
        """Test auto-route for append event."""
        path = router.route("append_event")
        assert path == ExecutionPath.WARM
    
    def test_route_update_capability(self, router):
        """Test auto-route for update capability."""
        path = router.route("update_capability")
        assert path == ExecutionPath.WARM
    
    def test_route_write_db(self, router):
        """Test auto-route for write db."""
        path = router.route("write_db")
        assert path == ExecutionPath.COLD
    
    def test_route_persist(self, router):
        """Test auto-route for persist."""
        path = router.route("persist_state")
        assert path == ExecutionPath.COLD
    
    def test_route_batch(self, router):
        """Test auto-route for batch."""
        path = router.route("batch_process")
        assert path == ExecutionPath.COLD
    
    def test_execute_hot(self, router):
        """Test HOT path execution."""
        result = router.execute_hot(lambda: 42)
        assert result == 42
    
    def test_execute_hot_with_args(self, router):
        """Test HOT path with arguments."""
        def add(a, b):
            return a + b
        
        result = router.execute_hot(lambda: add(2, 3))
        assert result == 5
    
    def test_execute_warm(self, router):
        """Test WARM path execution."""
        def compute():
            return 42
        
        future = router.execute_warm(compute)
        # Future should return result
        assert future.result(timeout=1.0) == 42
    
    def test_execute_cold(self, router):
        """Test COLD path execution."""
        def compute():
            return 42
        
        future = router.execute_cold(compute)
        assert future.result(timeout=1.0) == 42
    
    def test_queue_warm(self, router):
        """Test queuing WARM operations."""
        router.queue_warm("batch-1", lambda: 1)
        router.queue_warm("batch-1", lambda: 2)
        
        stats = router.get_stats()
        assert stats["warm_queued"] == 2
    
    def test_flush_warm(self, router):
        """Test flushing WARM queue."""
        router.queue_warm("flush-test", lambda: 1)
        router.queue_warm("flush-test", lambda: 2)
        
        count = router.flush_warm("flush-test")
        assert count == 2
        
        # Should be empty after flush
        stats = router.get_stats()
        assert stats["warm_queued"] == 0
    
    def test_queue_cold(self, router):
        """Test queuing COLD operations."""
        router.queue_cold("batch-1", lambda: 1)
        
        stats = router.get_stats()
        assert stats["cold_queued"] == 1
    
    def test_flush_cold(self, router):
        """Test flushing COLD queue."""
        router.queue_cold("flush-test", lambda: 1)
        router.queue_cold("flush-test", lambda: 2)
        
        count = router.flush_cold("flush-test")
        assert count == 2
    
    def test_get_stats(self, router):
        """Test statistics gathering."""
        router.queue_warm("q1", lambda: 1)
        router.queue_cold("q1", lambda: 1)
        
        stats = router.get_stats()
        assert "warm_queued" in stats
        assert "cold_queued" in stats


class TestDecorators:
    """Test path decorators."""
    
    @pytest.fixture(autouse=True)
    def cleanup(self):
        yield
        # Clean up after tests
    
    def test_hot_decorator(self):
        """Test @hot_path decorator."""
        @hot_path
        def hot_func():
            return 42
        
        # Should execute (decorator wraps but doesn't change result)
        result = hot_func()
        assert result == 42
    
    def test_warm_decorator(self):
        """Test @warm_path decorator."""
        @warm_path
        def warm_func():
            return 42
        
        result = warm_func()
        assert result is not None
    
    def test_cold_decorator(self):
        """Test @cold_path decorator."""
        @cold_path
        def cold_func():
            return 42
        
        result = cold_func()
        assert result is not None


class TestGetRouter:
    """Test singleton router."""
    
    def test_singleton(self):
        """Test get_router returns same instance."""
        r1 = get_router()
        r2 = get_router()
        assert r1 is r2


class TestRouterIntegration:
    """Integration tests for routing."""
    
    @pytest.fixture
    def router(self):
        return PathRouter()
    
    def test_mixed_operations(self, router):
        """Test routing mixed operations."""
        # Each should route to correct path
        assert router.route("check_budget") == ExecutionPath.HOT
        assert router.route("append_event") == ExecutionPath.WARM
        assert router.route("write_memory") == ExecutionPath.COLD
    
    def test_path_selection_by_keyword(self, router):
        """Test path selection from various keywords."""
        # HOT
        assert router.route("check") == ExecutionPath.HOT
        assert router.route("get") == ExecutionPath.HOT
        assert router.route("lookup") == ExecutionPath.HOT
        
        # WARM  
        assert router.route("append") == ExecutionPath.WARM
        assert router.route("update") == ExecutionPath.WARM
        
        # COLD
        assert router.route("save") == ExecutionPath.COLD
        assert router.route("persist") == ExecutionPath.COLD
        assert router.route("reconcile") == ExecutionPath.COLD