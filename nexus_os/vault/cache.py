"""cache.py — NEXUS KV Cache with Compression

Simple key-value cache with LZ4 compression for memory efficiency.
"""

import gzip
import hashlib
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: float
    accessed_at: float
    hit_count: int = 0
    size_bytes: int = 0
    compressed: bool = False


class KVCache:
    """
    Key-Value Cache with compression.
    
    Features:
    - LZ4 compression for large values
    - Size-based eviction
    - TTL-based expiration
    - Hit tracking
    """
    
    def __init__(
        self,
        max_size_mb: float = 100.0,
        default_ttl_seconds: float = 3600.0,
        compress_threshold_bytes: int = 1024,
    ):
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.default_ttl = default_ttl_seconds
        self.compress_threshold = compress_threshold_bytes
        
        self._cache: Dict[str, CacheEntry] = {}
        self._current_size = 0
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        import pickle
        
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            # Check expiration
            if time.time() - entry.created_at > self.default_ttl:
                del self._cache[key]
                self._current_size -= entry.size_bytes
                return None
            
            # Update access stats
            entry.accessed_at = time.time()
            entry.hit_count += 1
            
            value = entry.value
            # Decompress if needed
            if entry.compressed:
                value = gzip.decompress(value)
            
            # Unpickle
            return pickle.loads(value)
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> bool:
        """Set value in cache with optional compression."""
        if value is None:
            return False
        
        import pickle
        serialized = pickle.dumps(value)
        size = len(serialized)
        
        # Compress if large
        compress = size > self.compress_threshold
        if compress:
            serialized = gzip.compress(serialized)
            size = len(serialized)
        
        # Check size limit
        if size > self.max_size_bytes:
            return False
        
        # Evict if needed
        with self._lock:
            while self._current_size + size > self.max_size_bytes and self._cache:
                self._evict_oldest()
            
            entry = CacheEntry(
                key=key,
                value=serialized,
                created_at=time.time(),
                accessed_at=time.time(),
                size_bytes=size,
                compressed=compress,
            )
            
            old_entry = self._cache.get(key)
            if old_entry:
                self._current_size -= old_entry.size_bytes
            
            self._cache[key] = entry
            self._current_size += size
        
        return True
    
    def _evict_oldest(self):
        """Evict least recently accessed entry."""
        if not self._cache:
            return
        
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].accessed_at
        )
        entry = self._cache.pop(oldest_key)
        self._current_size -= entry.size_bytes
        logger.debug(f"Evicted cache entry: {oldest_key}")
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            entry = self._cache.pop(key, None)
            if entry:
                self._current_size -= entry.size_bytes
                return True
        return False
    
    def clear(self) -> int:
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._current_size = 0
            return count
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        with self._lock:
            total_hits = sum(e.hit_count for e in self._cache.values())
            return {
                "entries": len(self._cache),
                "size_bytes": self._current_size,
                "max_bytes": self.max_size_bytes,
                "total_hits": total_hits,
            }


# ── Singleton ────────────────────────────────────────────────────────────

_cache_instance: Optional[KVCache] = None
_cache_lock = threading.Lock()


def get_kv_cache() -> KVCache:
    """Get or create KVCache singleton."""
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = KVCache()
    return _cache_instance


def cache_get(key: str) -> Optional[Any]:
    """Convenience function for cache get."""
    return get_kv_cache().get(key)


def cache_set(key: str, value: Any, ttl_seconds: Optional[float] = None) -> bool:
    """Convenience function for cache set."""
    return get_kv_cache().set(key, value, ttl_seconds)