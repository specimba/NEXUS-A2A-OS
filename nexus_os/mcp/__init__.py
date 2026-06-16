"""Governed MCP bridge for NEXUS OS."""

from nexus_os.mcp.server import (
    GovernedMCPServer,
    MCPConfig,
    ToolSpec,
    TrustKernelMCPAdapter,
    create_server,
    handle_request,
)
from nexus_os.mcp.client import (
    GovernedMCPClient,
    MCPConnectionConfig,
    MCPCallResult,
    MCPToolInfo,
    get_client,
)

__all__ = [
    "GovernedMCPServer",
    "MCPConfig",
    "ToolSpec",
    "TrustKernelMCPAdapter",
    "create_server",
    "handle_request",
    "GovernedMCPClient",
    "MCPConnectionConfig",
    "MCPCallResult",
    "MCPToolInfo",
    "get_client",
]
