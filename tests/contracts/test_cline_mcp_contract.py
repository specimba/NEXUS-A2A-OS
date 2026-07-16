"""Project-local Cline MCP contract for the governed NEXUS tool surface."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / ".cline" / "mcp.json"


def test_cline_project_mcp_uses_only_the_canonical_governed_sse_bridge() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    servers = config["mcpServers"]

    assert set(servers) == {"nexus-governed-bridge"}
    bridge = servers["nexus-governed-bridge"]
    assert bridge == {
        "type": "sse",
        "url": "http://127.0.0.1:7354/sse",
        "disabled": False,
        "autoApprove": [],
    }
    serialized = json.dumps(config).lower()
    assert "api_key" not in serialized
    assert "authorization" not in serialized
    assert ":7350" not in serialized
