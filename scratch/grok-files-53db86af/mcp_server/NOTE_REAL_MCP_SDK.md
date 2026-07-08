# Real MCP SDK Integration Path

## Current State
<!-- CANARY: 76b78a730e7e0a5340c478cd7c8ab3b0 -->
We are using a **custom stdio JSON-RPC implementation** that follows the MCP protocol shape. This allows us to develop governed tools immediately without external dependencies.

## How to Migrate to Official MCP SDK (when internet available)

1. Install the package:
   ```bash
   pip install mcp
   ```

2. Refactor `governed_mcp_server.py`:
   - Use `from mcp.server import Server`
   - Use `@server.call_tool()` decorators instead of manual dispatch
   - Keep the **exact same** `consult_trustkernel()` gate before any tool logic

3. Recommended structure after migration:
   ```python
   from mcp.server import Server
   from mcp.server.stdio import stdio_server

   server = Server("nexus-a2a-os-governed")

   @server.call_tool()
   async def telegram_send_message(...):
       # TrustKernel gate here (same as now)
       ...
   ```

## Why We Did It This Way
- No internet in current environment
- We can still validate governance, TrustKernel integration, and security tests
- The current implementation is **protocol-compatible** enough to be swapped later with minimal changes

## Recommendation
Keep developing governed tools and security tests using the current skeleton.
Migrate to official `mcp` package in a future session when network access is available.

This approach follows NEXUS A2A OS principles: **governance and security first**, implementation details second.
