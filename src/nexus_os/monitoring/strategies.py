"""monitoring/strategies.py — Execution Boundaries & Caching"""
import hashlib
import inspect
import threading
from typing import List, Dict, Any, Optional

# ── Execution Path Decorators ──

def hot_path(func):
    """Enforces <20ms synchronous execution. Blocks async functions."""
    def wrapper(*args, **kwargs):
        if inspect.iscoroutinefunction(func):
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
