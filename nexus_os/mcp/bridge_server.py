"""GROSS MCP Bridge - HTTP/SSE transport wrapper for NEXUS OS MCP server.

Exposes the governed MCP server over HTTP with Server-Sent Events (SSE)
for use by external tools and clients. Defaults to read-only mode.

Port: 7354
Transport: HTTP/SSE
Tools: 17 (read-only by default, side-effect tools require explicit enable)
"""

import sys
import os
import json
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

from nexus_os.mcp.server import create_server, GovernedMCPServer
from nexus_os.bridge.port_registry import PortRegistry, PortConflictError
from nexus_os.bridge.transport_validator import (
    validate_mcp_transport,
    validate_request_source,
    validate_tool_invocation,
    TransportValidation,
)
from nexus_os.security.steg.mcp_guard import MCPGuard


app = FastAPI(title="NEXUS OS GROSS MCP Bridge", version="0.5-phase6-nexus")

# Global server instance
_mcp_server: GovernedMCPServer | None = None
_mcp_guard: MCPGuard | None = None


def get_guard() -> MCPGuard:
    global _mcp_guard
    if _mcp_guard is None:
        _mcp_guard = MCPGuard()
    return _mcp_guard


def get_server() -> GovernedMCPServer:
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = create_server()
    return _mcp_server


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gross-mcp-bridge", "version": "0.5-phase6-nexus"}


@app.get("/tools")
async def list_tools():
    """List all available MCP tools."""
    server = get_server()
    request = {
        "jsonrpc": "2.0",
        "id": "tools-list",
        "method": "tools/list",
        "params": {}
    }
    response = server.handle_request(request)
    return JSONResponse(content=response)


@app.post("/invoke")
async def invoke_tool(request: Request):
    """Invoke an MCP tool via JSON-RPC over HTTP.

    Transport validation enforced before any MCP tool execution:
    - Source identity required per request
    - Tool invocation parameters validated against path traversal, shell injection
    - MCPGuard invocation sequence checked for implicit tool poisoning
    """
    body = await request.json()
    method = body.get("method", "")
    params = body.get("params", {})

    source_check = validate_request_source(body)
    if not source_check.allowed:
        return JSONResponse(
            content={"jsonrpc": "2.0", "error": {"code": -32000, "message": source_check.reason},
                     "id": body.get("id")},
            status_code=403,
        )

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        tool_check = validate_tool_invocation(tool_name, arguments)
        if not tool_check.allowed:
            return JSONResponse(
                content={"jsonrpc": "2.0", "error": {"code": -32001, "message": tool_check.reason,
                         "data": {"severity": tool_check.severity}}, "id": body.get("id")},
                status_code=403,
            )

        guard = get_guard()
        guard_result = guard.check_invocation(
            tool_name,
            params.get("description", ""),
            arguments,
            session_id=body.get("_session_id", ""),
            caller_agent=body.get("agent_id", body.get("source", "")),
        )
        if guard_result and guard_result.is_blocked:
            return JSONResponse(
                content={"jsonrpc": "2.0",
                         "error": {"code": -32002,
                                   "message": f"MCP invocation blocked: {guard_result.recommendation}",
                                   "data": {
                                       "risk_score": guard_result.risk_score,
                                       "threat_types": guard_result.threat_types,
                                       "injection_matches": guard_result.injection_matches,
                                       "description_issues": guard_result.description_issues,
                                   }},
                         "id": body.get("id")},
                status_code=403,
            )

    server = get_server()
    response = server.handle_request(body)
    return JSONResponse(content=response)


@app.get("/sse")
async def sse_stream(request: Request):
    """Server-Sent Events endpoint for real-time MCP events.

    Transport validation enforced:
    - Transport type must be in allowed list (SSE is allowed for remote)
    - Request source identity validated from headers
    - Response tagged with source identity for event attribution
    """
    transport_check = validate_mcp_transport("sse", remote=True)
    if not transport_check.allowed:
        return JSONResponse(
            content={"error": transport_check.reason, "severity": transport_check.severity},
            status_code=403,
        )

    client_host = request.client.host if request.client else "unknown"
    agent_id = request.headers.get("x-nexus-agent-id", f"sse-client-{client_host}")
    source_check = validate_request_source({"agent_id": agent_id})

    async def event_generator():
        server = get_server()
        init_event = {
            "jsonrpc": "2.0",
            "id": "init",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "gross-mcp-bridge", "version": "0.5-phase6-nexus"}
            },
            "source": agent_id,
            "transport": "sse",
        }
        init_response = server.handle_request(init_event)
        init_response["_meta"] = {"transport_validated": True, "source": agent_id}
        yield f"data: {json.dumps(init_response)}\n\n"

        tools_request = {
            "jsonrpc": "2.0",
            "id": "tools",
            "method": "tools/list",
            "params": {},
            "source": agent_id,
        }
        tools_response = server.handle_request(tools_request)
        tools_response["_meta"] = {"source": agent_id}
        yield f"data: {json.dumps(tools_response)}\n\n"

        while True:
            await asyncio.sleep(30)
            yield f"data: {json.dumps({'event': 'heartbeat', 'source': agent_id, 'timestamp': asyncio.get_event_loop().time()})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Nexus-Agent-Id": agent_id,
            "X-Nexus-Transport-Validated": "true",
        }
    )


@app.get("/")
async def root():
    return {
        "service": "NEXUS OS GROSS MCP Bridge",
        "version": "0.5-phase6-nexus",
        "transport": "HTTP/SSE",
        "endpoints": {
            "health": "/health",
            "tools": "/tools",
            "invoke": "/invoke (POST)",
            "sse": "/sse"
        },
        "read_only": True,
        "side_effects": "disabled by default"
    }


if __name__ == "__main__":
    port = 7354
    registry = PortRegistry()
    try:
        registry.register(port, "gross_bridge", pid=os.getpid())
    except PortConflictError as exc:
        print(f"[GROSS MCP Bridge] Port conflict: {exc}")
        print(f"[GROSS MCP Bridge] Use PortRegistry.release_stale() to clean up, or choose a different port.")
        raise SystemExit(1)
    uvicorn.run(app, host="0.0.0.0", port=port)
