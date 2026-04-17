"""tests/vault/test_cache.py — KV Cache Tests"""

import pytest

from nexus_os.vault.cache import (
    KVCache,
    cache_get,
    cache_set,
    get_kv_cache,
)


class TestKVCacheBasics:
    """Test basic cache operations."""

    def test_set_and_get(self):
        cache = KVCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_returns_none(self):
        cache = KVCache()
        assert cache.get("missing") is None

    def test_delete(self):
        cache = KVCache()
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_clear(self):
        cache = KVCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.clear() == 2

    def test_stats(self):
        cache = KVCache()
        cache.set("key1", "value1")
        stats = cache.get_stats()
        assert stats["entries"] == 1
        assert stats["total_hits"] == 0


class TestCacheHitTracking:
    """Test hit count tracking."""

    def test_hit_count_increments(self):
        cache = KVCache()
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key1")
        
        stats = cache.get_stats()
        assert stats["total_hits"] == 2


class TestConvenienceFunctions:
    """Test module-level functions."""

    def test_cache_set_and_get(self):
        cache_set("test-key", "test-value")
        assert cache_get("test-key") == "test-value"
        get_kv_cache().clear()

    def test_singleton(self):
        cache1 = get_kv_cache()
        cache2 = get_kv_cache()
        assert cache1 is cache2