# NEXUS A2A OS — Governed MCP Server (Phase 6)

<!-- CANARY: 9238c5edf9bde874de6519800d83a29c -->
This directory contains the **governed MCP server** implementation for NEXUS A2A OS.

## Current Status (v0.2)

- Enhanced MCP skeleton with logging + config
- TrustKernel gate enforced on all high-risk tools
- Security tests for Categories 1, 2, and 3
- Docker + docker-compose ready

## Quick Start

```bash
# Run security tests
python security_tests/test_trustkernel_gating.py
python security_tests/test_connector_scope.py
python security_tests/test_memory_drift_protection.py

# Run the server
python governed_mcp_server.py
```

## Docker

```bash
docker compose up --build
```

## Important Notes

- `consult_trustkernel()` is currently a **stub**. Replace with real TrustKernel for production.
- Only low-risk tools are fully functional in skeleton mode.
- High-risk actions (sending messages, memory mutations) are intentionally blocked until governance approval.

## Next Steps

- Integrate real `mcp` Python SDK
- Add more connector tools after full security test suite passes
- Connect to actual `governance-orchestrator` and `nexus-memory`
