"""vault/semantic_backend.py — Pluggable SEMANTIC Backend

Provides a unified interface for the SEMANTIC memory channel (Channel 3),
supporting multiple backends:

  - ChromaBackend:  ChromaDB (local, optional dependency)
  - LocalBackend:   JSON-file keyword search (always available, same as
                    _LocalMemoryBackend in memory_adapter.py)
  - HybridBackend:  ChromaBackend with LocalBackend fallback

All backends implement the ``SemanticBackend`` ABC.
Wired into ``MemoryChannelManager.append_semantic()`` via ``set_backend()``.

Usage:
    backend = ChromaBackend(path="./chroma_data")
    backend.store("agent_1", "encoded knowledge", {"source": "archivist"})
    results = backend.search("knowledge query", agent_id="agent_1", limit=5)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Result Type ─────────────────────────────────────────────────────────────────


@dataclass
class SemanticResult:
    id: str
    content: str
    score: float
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[float] = None


# ── Abstract Backend ────────────────────────────────────────────────────────────


class SemanticBackend(ABC):
    """Pluggable backend for SEMANTIC channel storage and retrieval."""

    @abstractmethod
    def store(
        self,
        agent_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        ...

    @abstractmethod
    def search(
        self,
        query: str,
        agent_id: Optional[str] = None,
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SemanticResult]:
        ...

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        ...

    @abstractmethod
    def get(self, memory_id: str) -> Optional[SemanticResult]:
        ...

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Return backend health status."""
        ...

    @property
    @abstractmethod
    def backend_name(self) -> str:
        ...


# ── Local Fallback Backend (inline, no external deps) ─────────────────────────


class LocalBackend(SemanticBackend):
    """JSON-file keyword search backend — always available, no external deps.

    Mirrors ``_LocalMemoryBackend`` from memory_adapter.py but implements
    the ``SemanticBackend`` ABC for drop-in compatibility.
    """

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self._path = storage_path or os.path.expanduser("~/.nexus_os/semantic_local.json")
        self._entries: Dict[str, Dict[str, Any]] = {}
        self._load()

    # ── Persistence ───────────────────────────────────────────────

    def _load(self) -> None:
        try:
            if os.path.exists(self._path):
                with open(self._path, "r", encoding="utf-8") as f:
                    self._entries = json.load(f)
                logger.debug("LocalBackend: loaded %d entries from %s", len(self._entries), self._path)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("LocalBackend: failed to load %s: %s. Starting empty.", self._path, e)
            self._entries = {}

    def _save(self) -> None:
        try:
            parent = os.path.dirname(self._path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.warning("LocalBackend: failed to save %s: %s", self._path, e)

    # ── SemanticBackend ───────────────────────────────────────────

    @property
    def backend_name(self) -> str:
        return "local"

    def store(
        self,
        agent_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        memory_id = uuid.uuid4().hex[:16]
        now = time.time()
        self._entries[memory_id] = {
            "id": memory_id,
            "content": content,
            "agent_id": agent_id,
            "metadata": metadata or {},
            "created_at": now,
        }
        self._save()
        return memory_id

    def search(
        self,
        query: str,
        agent_id: Optional[str] = None,
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SemanticResult]:
        if not query or not query.strip():
            return []

        query_words = set(re.findall(r"\w+", query.lower()))
        if not query_words:
            return []

        scored: List[tuple[float, Dict[str, Any]]] = []
        for eid, entry in self._entries.items():
            # Agent filter
            if agent_id and entry.get("agent_id") != agent_id:
                continue
            # Metadata filter
            if filter_metadata:
                meta = entry.get("metadata", {})
                if not all(meta.get(k) == v for k, v in filter_metadata.items()):
                    continue

            content_words = set(re.findall(r"\w+", entry.get("content", "").lower()))
            matches = len(query_words & content_words)
            if matches > 0:
                score = matches / len(query_words)
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, entry in scored[:limit]:
            results.append(SemanticResult(
                id=entry["id"],
                content=entry["content"],
                score=round(score, 4),
                agent_id=entry.get("agent_id"),
                metadata=entry.get("metadata", {}),
                timestamp=entry.get("created_at"),
            ))
        return results

    def delete(self, memory_id: str) -> bool:
        if memory_id in self._entries:
            del self._entries[memory_id]
            self._save()
            return True
        return False

    def get(self, memory_id: str) -> Optional[SemanticResult]:
        entry = self._entries.get(memory_id)
        if entry is None:
            return None
        return SemanticResult(
            id=entry["id"],
            content=entry["content"],
            score=1.0,
            agent_id=entry.get("agent_id"),
            metadata=entry.get("metadata", {}),
            timestamp=entry.get("created_at"),
        )

    def health(self) -> Dict[str, Any]:
        return {
            "backend": "local",
            "entries": len(self._entries),
            "path": self._path,
            "ok": True,
        }

    def clear(self) -> None:
        self._entries.clear()
        self._save()


# ── ChromaDB Backend (requires chromadb) ───────────────────────────────────────


class ChromaBackend(SemanticBackend):
    """ChromaDB-based vector semantic backend.

    Uses ChromaDB's built-in ``all-MiniLM-L6-v2`` sentence transformer for
    embeddings (downloaded on first use). Falls back to ``LocalBackend``
    if chromadb is not installed.

    Requires: pip install chromadb
    """

    def __init__(
        self,
        path: str = "./chroma_semantic",
        collection_name: str = "nexus_semantic",
        fallback: Optional[SemanticBackend] = None,
    ) -> None:
        self._path = path
        self._collection_name = collection_name
        self._client: Any = None
        self._collection: Any = None
        self._available = False
        self._fallback = fallback or LocalBackend()
        self._init_error: Optional[str] = None
        self._init_chromadb()

    @property
    def backend_name(self) -> str:
        return "chromadb"

    def _init_chromadb(self) -> None:
        try:
            import chromadb
            from chromadb.config import Settings

            self._client = chromadb.PersistentClient(
                path=self._path,
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._available = True
            logger.info(
                "ChromaBackend initialized: path=%s collection=%s",
                self._path, self._collection_name,
            )
        except ImportError:
            self._available = False
            self._init_error = "chromadb not installed"
            logger.warning("ChromaBackend unavailable: %s. Using fallback.", self._init_error)
        except Exception as e:
            self._available = False
            self._init_error = str(e)
            logger.warning("ChromaBackend init failed: %s. Using fallback.", e)

    def store(
        self,
        agent_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not self._available:
            return self._fallback.store(agent_id, content, metadata)

        memory_id = uuid.uuid4().hex[:16]
        meta = {
            "agent_id": agent_id,
            **(metadata or {}),
        }
        try:
            self._collection.add(
                documents=[content],
                metadatas=[meta],
                ids=[memory_id],
            )
            return memory_id
        except Exception as e:
            logger.warning("ChromaBackend store failed: %s. Falling back.", e)
            return self._fallback.store(agent_id, content, metadata)

    def search(
        self,
        query: str,
        agent_id: Optional[str] = None,
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SemanticResult]:
        if not self._available:
            return self._fallback.search(query, agent_id, limit, filter_metadata)

        try:
            where: Optional[Dict[str, Any]] = None
            if agent_id:
                where = {"agent_id": agent_id}
            if filter_metadata:
                where = {**(where or {}), **filter_metadata}

            results = self._collection.query(
                query_texts=[query],
                n_results=limit,
                where=where,
            )

            return self._map_chroma_results(results)
        except Exception as e:
            logger.warning("ChromaBackend search failed: %s. Falling back.", e)
            return self._fallback.search(query, agent_id, limit, filter_metadata)

    @staticmethod
    def _map_chroma_results(results: Any) -> List[SemanticResult]:
        mapped: List[SemanticResult] = []
        if not results or not results.get("ids"):
            return mapped

        ids_list = results.get("ids", [[]])[0]
        distances_list = results.get("distances", [[]])[0] if results.get("distances") else []
        documents_list = results.get("documents", [[]])[0] if results.get("documents") else []
        metadatas_list = results.get("metadatas", [[]])[0] if results.get("metadatas") else []

        for i, doc_id in enumerate(ids_list):
            content = documents_list[i] if i < len(documents_list) else ""
            distance = distances_list[i] if i < len(distances_list) else 0.0
            meta = metadatas_list[i] if i < len(metadatas_list) else {}
            # Chroma returns L2 distance; convert to a similarity score.
            # Audit fix (P2-6): the old `if distance else 0.0` gave an
            # EXACT match (distance 0) the worst score instead of the
            # best — perfect hits ranked last.
            score = 1.0 / (1.0 + max(float(distance or 0.0), 0.0))

            mapped.append(SemanticResult(
                id=doc_id,
                content=content,
                score=round(score, 4),
                agent_id=meta.get("agent_id"),
                metadata=meta,
            ))
        return mapped

    def delete(self, memory_id: str) -> bool:
        if not self._available:
            return self._fallback.delete(memory_id)
        try:
            self._collection.delete(ids=[memory_id])
            return True
        except Exception as e:
            logger.warning("ChromaBackend delete failed: %s", e)
            return False

    def get(self, memory_id: str) -> Optional[SemanticResult]:
        # ChromaDB doesn't have a native get-by-id; use fallback
        return self._fallback.get(memory_id)

    def health(self) -> Dict[str, Any]:
        base = {
            "backend": "chromadb",
            "available": self._available,
            "path": self._path,
            "collection": self._collection_name,
            "init_error": self._init_error,
        }
        if self._available:
            try:
                count = self._collection.count()
                base["count"] = count
                base["ok"] = True
            except Exception as e:
                base["count"] = -1
                base["ok"] = False
                base["error"] = str(e)
        else:
            base["ok"] = self._fallback.health().get("ok", False)
            base["fallback_entries"] = self._fallback.health().get("entries", 0)
        return base


# ── Hybrid Backend (ChromaDB + Local fallback chain) ───────────────────────────


class HybridBackend(SemanticBackend):
    """Hybrid backend: ChromaDB primary, LocalBackend secondary.

    Writes to both, reads from ChromaDB first, falls back to LocalBackend.
    """

    def __init__(
        self,
        chroma_path: str = "./chroma_semantic",
        local_path: Optional[str] = None,
    ) -> None:
        self._primary = ChromaBackend(path=chroma_path, fallback=LocalBackend(local_path))
        self._secondary = LocalBackend(local_path)

    @property
    def backend_name(self) -> str:
        return "hybrid"

    def store(self, agent_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        mid = self._primary.store(agent_id, content, metadata)
        self._secondary.store(agent_id, content, metadata)
        return mid

    def search(self, query: str, agent_id: Optional[str] = None, limit: int = 10, filter_metadata: Optional[Dict[str, Any]] = None) -> List[SemanticResult]:
        primary_results = self._primary.search(query, agent_id, limit, filter_metadata)
        if primary_results:
            return primary_results
        return self._secondary.search(query, agent_id, limit, filter_metadata)

    def delete(self, memory_id: str) -> bool:
        p = self._primary.delete(memory_id)
        s = self._secondary.delete(memory_id)
        return p or s

    def get(self, memory_id: str) -> Optional[SemanticResult]:
        result = self._primary.get(memory_id)
        if result:
            return result
        return self._secondary.get(memory_id)

    def health(self) -> Dict[str, Any]:
        primary_health = self._primary.health()
        secondary_health = self._secondary.health()
        return {
            "backend": "hybrid",
            "primary": primary_health,
            "secondary": secondary_health,
            "ok": primary_health.get("ok", False) or secondary_health.get("ok", False),
        }


# ── Registry for backends ──────────────────────────────────────────────────────


_SEMANTIC_BACKEND_INSTANCE: Optional[SemanticBackend] = None


def get_semantic_backend() -> SemanticBackend:
    """Get the global SEMANTIC backend instance (HybridBackend by default)."""
    global _SEMANTIC_BACKEND_INSTANCE
    if _SEMANTIC_BACKEND_INSTANCE is None:
        _SEMANTIC_BACKEND_INSTANCE = HybridBackend()
    return _SEMANTIC_BACKEND_INSTANCE


def set_semantic_backend(backend: SemanticBackend) -> None:
    """Set the global SEMANTIC backend instance."""
    global _SEMANTIC_BACKEND_INSTANCE
    logger.info("Setting SEMANTIC backend: %s", backend.backend_name)
    _SEMANTIC_BACKEND_INSTANCE = backend
