"""nexus_os/nexusclaw/external_connectors.py - External API Integrations (Phase D2).

Integrates ARCHIVIST research on MCP adapters for:
- HuggingFace Hub (model registry, datasets)
- GitHub (code operations, issues)
- Reddit (research discussions)
- X/Twitter (real-time discourse)

All connectors are trust-gated via GovernedMCPClient.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from nexus_os.mcp.client import GovernedMCPClient, MCPConnectionConfig


@dataclass
class ExternalDataSource:
    """External data source configuration with trust requirements."""
    source_id: str
    name: str
    connector_type: str  # huggingface, github, reddit, twitter
    trust_threshold: float
    capabilities: List[str]
    blake3_hash: str = ""


class ExternalConnectorManager:
    """Manages multiple external data source connections."""

    SOURCES = {
        "huggingface": ExternalDataSource(
            source_id="hf",
            name="HuggingFace Hub",
            connector_type="huggingface",
            trust_threshold=75.0,
            capabilities=["model_search", "dataset_fetch", "paper_read"],
        ),
        "github": ExternalDataSource(
            source_id="gh",
            name="GitHub API",
            connector_type="github",
            trust_threshold=80.0,
            capabilities=["repo_read", "issue_query", "pr_fetch"],
        ),
        "reddit": ExternalDataSource(
            source_id="rd",
            name="Reddit Research",
            connector_type="reddit",
            trust_threshold=65.0,
            capabilities=["discussion_search", "paper_hunt"],
        ),
        "x": ExternalDataSource(
            source_id="x",
            name="X/Twitter Discourse",
            connector_type="twitter",
            trust_threshold=70.0,
            capabilities=["trending", "signal_detect"],
        ),
    }

    def __init__(self):
        self._clients: Dict[str, GovernedMCPClient] = {}

    def get_client(self, source_id: str) -> Optional[GovernedMCPClient]:
        """Get or create a trust-gated client for a source."""
        if source_id in self._clients:
            return self._clients[source_id]

        source = self.SOURCES.get(source_id)
        if not source:
            return None

        config = MCPConnectionConfig(
            bridge_url=f"http://127.0.0.1:7354/{source_id}",
            trust_threshold=source.trust_threshold,
        )
        client = GovernedMCPClient(config)
        self._clients[source_id] = client
        return client

    def fetch_research_context(
        self,
        query: str,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Fetch research context from multiple sources."""
        sources = sources or ["huggingface", "reddit", "github"]
        results = {}

        for src in sources:
            client = self.get_client(src)
            if client:
                try:
                    # Connect and fetch
                    if client.connect():
                        tools = client.list_tools()
                        results[src] = {
                            "tools_available": [t.name for t in tools],
                            "status": "connected",
                        }
                except Exception as e:
                    results[src] = {"status": "error", "error": str(e)}

        return {
            "query": query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": results,
            "blake3": self._blake3(json.dumps(results).encode("utf-8")),
        }

    def _blake3(self, data: bytes) -> str:
        try:
            import blake3
            return blake3.blake3(data).hexdigest()
        except ImportError:
            return hashlib.sha256(data).hexdigest()


# Singleton accessor
_manager: Optional[ExternalConnectorManager] = None


def get_external_connectors() -> ExternalConnectorManager:
    global _manager
    if _manager is None:
        _manager = ExternalConnectorManager()
    return _manager