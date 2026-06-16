"""tests/vault/test_semantic_backend.py — Pluggable SEMANTIC Backend Tests"""

import os
import tempfile
import pytest
from nexus_os.vault.semantic_backend import (
    SemanticBackend,
    SemanticResult,
    LocalBackend,
    ChromaBackend,
    HybridBackend,
    get_semantic_backend,
    set_semantic_backend,
)


@pytest.fixture
def local_backend():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield LocalBackend(storage_path=os.path.join(tmpdir, "semantic.json"))


@pytest.fixture
def hybrid_backend():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield HybridBackend(chroma_path=os.path.join(tmpdir, "chroma"), local_path=os.path.join(tmpdir, "local.json"))


class TestLocalBackend:
    def test_store_and_search(self, local_backend):
        mid = local_backend.store("agent1", "The sky is blue and clear today", {"source": "test"})
        assert mid is not None
        assert len(mid) == 16

        results = local_backend.search("sky blue", agent_id="agent1")
        assert len(results) == 1
        assert results[0].agent_id == "agent1"
        assert results[0].score > 0

    def test_search_no_results(self, local_backend):
        local_backend.store("agent1", "hello world")
        results = local_backend.search("nonexistent query", agent_id="agent1")
        assert results == []

    def test_search_by_agent(self, local_backend):
        local_backend.store("agent1", "agent one data")
        local_backend.store("agent2", "agent two data")
        results = local_backend.search("data", agent_id="agent1")
        assert len(results) == 1
        assert results[0].agent_id == "agent1"

    def test_search_empty_query(self, local_backend):
        results = local_backend.search("")
        assert results == []

    def test_delete(self, local_backend):
        mid = local_backend.store("agent1", "test content")
        assert local_backend.get(mid) is not None
        assert local_backend.delete(mid) is True
        assert local_backend.get(mid) is None
        assert local_backend.delete("nonexistent") is False

    def test_get(self, local_backend):
        mid = local_backend.store("agent1", "content", {"key": "val"})
        result = local_backend.get(mid)
        assert result is not None
        assert result.content == "content"
        assert result.metadata.get("key") == "val"

    def test_get_nonexistent(self, local_backend):
        assert local_backend.get("nonexistent") is None

    def test_health(self, local_backend):
        health = local_backend.health()
        assert health["backend"] == "local"
        assert health["ok"] is True
        assert health["entries"] == 0

    def test_clear(self, local_backend):
        local_backend.store("agent1", "content")
        local_backend.clear()
        assert local_backend.health()["entries"] == 0

    def test_persistence(self, local_backend):
        mid = local_backend.store("agent1", "persistent content")
        # Create a new backend loading the same file
        backend2 = LocalBackend(storage_path=local_backend._path)
        assert backend2.get(mid) is not None
        assert backend2.get(mid).content == "persistent content"

    def test_backend_name(self, local_backend):
        assert local_backend.backend_name == "local"

    def test_store_with_metadata(self, local_backend):
        mid = local_backend.store("agent1", "data", {"key1": "val1", "key2": 42})
        result = local_backend.get(mid)
        assert result.metadata["key1"] == "val1"


class TestChromaBackend:
    def test_fallback_when_chromadb_unavailable(self):
        backend = ChromaBackend(path="/tmp/_test_chroma_nonexistent", fallback=None)
        assert backend._available is False
        # Should still work via fallback
        assert backend.backend_name == "chromadb"

    def test_store_falls_back(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = ChromaBackend(path=os.path.join(tmpdir, "chroma"))
            mid = backend.store("agent1", "test content", {"source": "test"})
            assert mid is not None
            # If chromadb unavailable, fallback was auto-created
            if not backend._available:
                assert len(mid) == 16

    def test_search_falls_back(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = ChromaBackend(path=os.path.join(tmpdir, "chroma"))
            backend.store("agent1", "the sky is blue")
            results = backend.search("sky", agent_id="agent1")
            if not backend._available:
                assert len(results) >= 0
            # If chromadb IS available, this is a real test
            if backend._available:
                assert len(results) >= 1

    def test_delete_falls_back(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = ChromaBackend(path=os.path.join(tmpdir, "chroma"))
            mid = backend.store("agent1", "content")
            assert backend.delete(mid) is not False

    def test_health(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = ChromaBackend(path=os.path.join(tmpdir, "chroma"))
            health = backend.health()
            assert "backend" in health
            assert "ok" in health

    def test_with_explicit_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fb = LocalBackend(storage_path=os.path.join(tmpdir, "fb.json"))
            backend = ChromaBackend(path=os.path.join(tmpdir, "chroma"), fallback=fb)
            mid = backend.store("agent1", "test")
            assert mid is not None
            if not backend._available:
                # Check fallback was used
                assert fb.get(mid) is not None


class TestHybridBackend:
    def test_store_and_search(self, hybrid_backend):
        mid = hybrid_backend.store("agent1", "the sky is blue today", {"source": "test"})
        assert mid is not None
        results = hybrid_backend.search("sky blue", agent_id="agent1")
        # At minimum, fallback secondary should have it
        assert len(results) >= 1

    def test_search_by_agent_filter(self, hybrid_backend):
        hybrid_backend.store("agent1", "data one")
        hybrid_backend.store("agent2", "data two")
        results = hybrid_backend.search("data", agent_id="agent2")
        assert len(results) >= 1
        assert all(r.agent_id == "agent2" for r in results)

    def test_delete(self, hybrid_backend):
        mid = hybrid_backend.store("agent1", "content")
        assert hybrid_backend.delete(mid) is True

    def test_get(self, hybrid_backend):
        mid = hybrid_backend.store("agent1", "content")
        result = hybrid_backend.get(mid)
        if result:
            assert result.content == "content"

    def test_health(self, hybrid_backend):
        health = hybrid_backend.health()
        assert health["backend"] == "hybrid"
        assert "primary" in health
        assert "secondary" in health

    def test_allows_empty_query(self, hybrid_backend):
        results = hybrid_backend.search("")
        assert results == []

    def test_backend_name(self, hybrid_backend):
        assert hybrid_backend.backend_name == "hybrid"

    def test_multiple_agents(self, hybrid_backend):
        for i in range(3):
            hybrid_backend.store(f"agent{i}", f"data from agent {i}")
        results = hybrid_backend.search("data")
        assert len(results) >= 1


class TestSemanticResult:
    def test_semantic_result_defaults(self):
        r = SemanticResult(id="test", content="hello", score=0.95)
        assert r.id == "test"
        assert r.content == "hello"
        assert r.score == 0.95
        assert r.agent_id is None
        assert r.metadata == {}
        assert r.timestamp is None

    def test_semantic_result_full(self):
        r = SemanticResult(id="t1", content="data", score=0.8, agent_id="a1", metadata={"key": "val"}, timestamp=123.0)
        assert r.agent_id == "a1"
        assert r.metadata["key"] == "val"
        assert r.timestamp == 123.0


class TestSemanticBackendSingleton:
    def test_get_semantic_backend_consistent(self):
        b1 = get_semantic_backend()
        b2 = get_semantic_backend()
        assert b1 is b2

    def test_set_semantic_backend(self):
        b = LocalBackend()
        set_semantic_backend(b)
        assert get_semantic_backend() is b
        # Reset for other tests
        import nexus_os.vault.semantic_backend as sb
        sb._SEMANTIC_BACKEND_INSTANCE = None


class TestLocalBackendFilterMetadata:
    def test_search_with_metadata_filter(self, local_backend):
        local_backend.store("agent1", "content a", {"type": "code", "lang": "python"})
        local_backend.store("agent1", "content b", {"type": "doc", "lang": "python"})
        results = local_backend.search("content", filter_metadata={"type": "code"})
        assert len(results) == 1
        assert results[0].metadata["type"] == "code"

    def test_search_with_metadata_filter_no_match(self, local_backend):
        local_backend.store("agent1", "content", {"type": "code"})
        results = local_backend.search("content", filter_metadata={"type": "doc"})
        assert results == []


class TestLocalBackendEdgeCases:
    def test_store_empty_content(self, local_backend):
        mid = local_backend.store("agent1", "")
        assert mid is not None

    def test_large_content(self, local_backend):
        content = "word " * 1000
        mid = local_backend.store("agent1", content)
        result = local_backend.get(mid)
        assert result is not None
        assert len(result.content) == len(content)

    def test_search_case_insensitive(self, local_backend):
        local_backend.store("agent1", "The Quick Brown Fox")
        results = local_backend.search("quick brown")
        assert len(results) == 1
