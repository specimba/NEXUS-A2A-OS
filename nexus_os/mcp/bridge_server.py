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


app = FastAPI(title="NEXUS OS GROSS MCP Bridge", version="0.5-phase6-nexus")

# Global server instance
_mcp_server: GovernedMCPServer | None = None


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
    """Invoke an MCP tool via JSON-RPC over HTTP."""
    server = get_server()
    body = await request.json()
    response = server.handle_request(body)
    return JSONResponse(content=response)


@app.get("/sse")
async def sse_stream():
    """Server-Sent Events endpoint for real-time MCP events."""
    async def event_generator():
        server = get_server()
        # Send initialization event
        init_event = {
            "jsonrpc": "2.0",
            "id": "init",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "gross-mcp-bridge", "version": "0.5"}
            }
        }
        init_response = server.handle_request(init_event)
        yield f"data: {json.dumps(init_response)}\n\n"
        
        # Send tools list
        tools_request = {
            "jsonrpc": "2.0",
            "id": "tools",
            "method": "tools/list",
            "params": {}
        }
        tools_response = server.handle_request(tools_request)
        yield f"data: {json.dumps(tools_response)}\n\n"
        
        # Keep connection alive with heartbeat
        while True:
            await asyncio.sleep(30)
            yield f"data: {json.dumps({'event': 'heartbeat', 'timestamp': asyncio.get_event_loop().time()})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
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
