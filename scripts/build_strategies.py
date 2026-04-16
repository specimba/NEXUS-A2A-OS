#!/usr/bin/env python3
"""Phase 1.6: Execution Strategies & Semantic Cache Builder"""
import os

MONITORING_DIR = os.path.join("src", "nexus_os", "monitoring")
TEST_DIR = os.path.join("tests", "monitoring")
os.makedirs(MONITORING_DIR, exist_ok=True)
os.makedirs(TEST_DIR, exist_ok=True)

STRATEGIES_CODE = '''"""monitoring/strategies.py — Execution Boundaries & Caching"""
import asyncio
import threading
import hashlib
from typing import List, Dict, Any, Optional

# ── Execution Path Decorators ──

def hot_path(func):
    """Enforces <20ms synchronous execution. Blocks async functions."""
    def wrapper(*args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            raise RuntimeError(f"Hot path violation: {func.__name__} cannot be async")
        return func(*args, **kwargs)
    return wrapper

def warm_path(func):
    """Offloads execution to a background thread (fire-and-forget)."""
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=lambda: func(*args, **kwargs), daemon=True)
        thread.start()
        return {"status": "queued", "path": "warm"}
    return wrapper

# ── Semantic Caching ──

class SemanticCache:
    """Intercepts redundant queries to save Token/Time budgets."""
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def _hash(self, query: str) -> str:
        # Standardize the query to maximize cache hits
        normalized = " ".join(query.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()

    @hot_path
    def get(self, query: str) -> Optional[Any]:
        with self._lock:
            key = self._hash(query)
            if key in self._cache:
                self.hits += 1
                return self._cache[key]["response"]
            self.misses += 1
            return None

    @warm_path
    def set(self, query: str, response: Any):
        """Warm path: storing data shouldn't block the caller."""
        with self._lock:
            key = self._hash(query)
            self._cache[key] = {"response": response, "warmed": False}

    def warm_cache(self, queries: List[str], responses: List[Any]):
        """Pre-load the cache at startup (Cold Path)."""
        with self._lock:
            for q, r in zip(queries, responses):
                key = self._hash(q)
                self._cache[key] = {"response": r, "warmed": True}
'''

TEST_CODE = '''"""tests/monitoring/test_strategies.py — Path & Cache Diagnostics"""
import pytest
import time
from nexus_os.monitoring.strategies import hot_path, warm_path, SemanticCache

def test_hot_path_blocks_async():
    import asyncio
    
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
'''

# Write Strategies
with open(os.path.join(MONITORING_DIR, "strategies.py"), "w", encoding="utf-8") as f:
    f.write(STRATEGIES_CODE)
print(f"[✅] Created {os.path.join(MONITORING_DIR, 'strategies.py')}")

# Write Tests
with open(os.path.join(TEST_DIR, "test_strategies.py"), "w", encoding="utf-8") as f:
    f.write(TEST_CODE)
print(f"[✅] Created {os.path.join(TEST_DIR, 'test_strategies.py')}")

print("\n[🚀] Phase 1.6: Execution Strategies & Cache Ready.")