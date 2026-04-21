"""tests/monitoring/test_strategies.py — Path & Cache Diagnostics"""
import pytest
import time
from nexus_os.monitoring.strategies import hot_path, warm_path, SemanticCache

def test_hot_path_blocks_async():
    @hot_path
    async def bad_function():
        pass
        
    with pytest.raises(RuntimeError, match="Hot path violation"):
        bad_function()

def test_warm_path_non_blocking():
    @warm_path
    def slow_function():
        time.sleep(0.5)
        
    start = time.perf_counter()
    res = slow_function()
    duration = time.perf_counter() - start
    
    assert res["status"] == "queued"
    assert duration < 0.1  # Proves the caller wasn't blocked

def test_semantic_cache_hit_ratio():
    cache = SemanticCache()
    
    # Pre-warm the cache
    cache.warm_cache(["What is the capital of France?"], ["Paris"])
    
    # Exact hit
    assert cache.get("What is the capital of France?") == "Paris"
    
    # Normalized hit (extra spaces/caps)
    assert cache.get("  what is the CAPITAL of france?  ") == "Paris"
    
    # Miss
    assert cache.get("What is the capital of Germany?") is None
    
    assert cache.hits == 2
    assert cache.misses == 1

def test_cache_set_is_warm_path():
    cache = SemanticCache()
    res = cache.set("New query", "New response")
    assert res["status"] == "queued"
    
    # Allow background thread a tiny moment to write
    time.sleep(0.05)
    assert cache.get("New query") == "New response"
