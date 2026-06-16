"""NEXUSCLAW MCP Tool Bridge - mcporter-style integration with governance gates."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger("nexusclaw.tool_bridge")


class ExternalMCPServer(BaseModel):
    """Configuration for an external MCP server to bridge."""

    name: str
    url: str
    headers: Dict[str, str] = {}
    enabled: bool = True
    trust_level: str = "review_required"


@dataclass
class BridgedTool:
    """A tool bridged from an external MCP server."""

    name: str
    server_name: str
    description: str
    input_schema: Dict[str, Any]
    governance_level: str = "medium"
    requires_escalation: bool = True

    def to_mcp(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "governance": {
                "level": self.governance_level,
                "requires_escalation": self.requires_escalation,
                "bridged_from": self.server_name,
            },
        }


@dataclass
class ToolBridgeResult:
    """Result from bridged tool execution."""

    tool: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    dry_run: bool = True
    governance_required: bool = True


class MCPToolBridge:
    """Bridge external MCP servers with NEXUSCLAW governance."""

    def __init__(self):
        self.servers: Dict[str, ExternalMCPServer] = {}
        self.bridged_tools: Dict[str, BridgedTool] = {}
        self._tool_cache: Dict[str, List[BridgedTool]] = {}

    def register_server(self, server: ExternalMCPServer) -> None:
        """Register an external MCP server for bridging."""
        self.servers[server.name] = server
        logger.info(f"Registered MCP server: {server.name} at {server.url}")

    def get_server(self, name: str) -> Optional[ExternalMCPServer]:
        return self.servers.get(name)

    async def fetch_tools(self, server_name: str) -> List[BridgedTool]:
        """Fetch tool list from external MCP server."""
        server = self.get_server(server_name)
        if not server:
            return []

        cached = self._tool_cache.get(server_name)
        if cached:
            return cached

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{server.url}",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/list",
                        "params": {},
                    },
                    headers=server.headers,
                )
                data = response.json()
                tools = data.get("result", {}).get("tools", [])
                bridged = [
                    BridgedTool(
                        name=t.get("name"),
                        server_name=server_name,
                        description=t.get("description", ""),
                        input_schema=t.get("inputSchema", {}),
                    )
                    for t in tools
                ]
                self._tool_cache[server_name] = bridged
                for bt in bridged:
                    self.bridged_tools[bt.name] = bt
                return bridged
        except Exception as e:
            logger.error(f"Failed to fetch tools from {server_name}: {e}")
            return []

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        *,
        dry_run: bool = True,
        trustkernel_approved: bool = False,
    ) -> ToolBridgeResult:
        """Call a bridged tool through governance gate."""
        tool = self.bridged_tools.get(tool_name)
        if not tool:
            return ToolBridgeResult(
                tool=tool_name,
                success=False,
                error="Tool not found in bridged registry",
            )

        server = self.get_server(tool.server_name)
        if not server or not server.enabled:
            return ToolBridgeResult(
                tool=tool_name,
                success=False,
                error="Server not available",
            )

        if tool.requires_escalation and not trustkernel_approved:
            logger.warning(f"Governance hold for tool call: {tool_name}")
            return ToolBridgeResult(
                tool=tool_name,
                success=True,
                dry_run=True,
                governance_required=True,
            )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{server.url}",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {"name": tool_name, "arguments": arguments},
                    },
                    headers=server.headers,
                )
                data = response.json()
                return ToolBridgeResult(
                    tool=tool_name,
                    success=True,
                    result=data.get("result"),
                    dry_run=False,
                    governance_required=False,
                )
        except Exception as e:
            return ToolBridgeResult(
                tool=tool_name,
                success=False,
                error=str(e),
            )


_bridge_instance: Optional[MCPToolBridge] = None


def get_tool_bridge() -> MCPToolBridge:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = MCPToolBridge()
    return _bridge_instance


def load_mcp_bridge_from_env() -> MCPToolBridge:
    """Load MCP bridge configuration from environment."""
    bridge = MCPToolBridge()

    mcp_urls = os.getenv("NEXUS_MCP_BRIDGE_URLS", "")
    mcp_names = os.getenv("NEXUS_MCP_BRIDGE_NAMES", "")

    if mcp_urls and mcp_names:
        url_list = mcp_urls.split(",")
        name_list = mcp_names.split(",")
        for name, url in zip(name_list, url_list):
            bridge.register_server(ExternalMCPServer(name=name.strip(), url=url.strip()))

    return bridge