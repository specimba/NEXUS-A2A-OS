"""tests/vault/test_memory.py — SuperLocalMemory Tests"""

import pytest

from nexus_os.vault.memory import (
    SuperLocalMemory,
    MemoryChannel,
    get_memory,
)


class TestMemoryBasics:
    """Test basic memory operations."""

    def test_store_and_retrieve(self):
        mem = SuperLocalMemory()
        mem.store(MemoryChannel.EVENT, "task-1", {"type": "started"})
        
        results = mem.retrieve(MemoryChannel.EVENT, "task-1")
        assert len(results) == 1
        assert results[0]["type"] == "started"

    def test_get_channel(self):
        mem = SuperLocalMemory()
        mem.store(MemoryChannel.EVENT, "task-1", "event1")
        mem.store(MemoryChannel.EVENT, "task-2", "event2")
        
        entries = mem.get_channel(MemoryChannel.EVENT)
        assert len(entries) == 2

    def test_get_latest(self):
        mem = SuperLocalMemory()
        for i in range(10):
            mem.store(MemoryChannel.TASK, f"task-{i}", f"result-{i}")
        
        latest = mem.get_latest(MemoryChannel.TASK, 3)
        assert len(latest) == 3


class TestQuery:
    """Test querying."""

    def test_query_by_pattern(self):
        mem = SuperLocalMemory()
        mem.store(MemoryChannel.EVENT, "api-call", "success")
        mem.store(MemoryChannel.EVENT, "db-query", "success")
        mem.store(MemoryChannel.EVENT, "api-error", "fail")
        
        results = mem.query(MemoryChannel.EVENT, pattern="api", limit=10)
        assert len(results) == 2


class TestStats:
    """Test statistics."""

    def test_stats(self):
        mem = SuperLocalMemory()
        mem.store(MemoryChannel.EVENT, "key1", "val1")
        
        stats = mem.get_stats()
        assert "event" in stats
        assert stats["event"] == 1


class TestSingleton:
    """Test singleton."""

    def test_singleton(self):
        mem1 = get_memory()
        mem2 = get_memory()
        assert mem1 is mem2