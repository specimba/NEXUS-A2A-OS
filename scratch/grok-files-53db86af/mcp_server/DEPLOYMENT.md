# NEXUS A2A OS — Governed MCP Server Deployment Guide

## 1. Local Development

<!-- CANARY: b3967e21b572ebcc953907cbed853c24 -->
```bash
cd mcp_server

# Run security tests
python security_tests/test_trustkernel_gating.py
python security_tests/test_telegram_connector.py
python security_tests/test_notion_connector.py

# Start server
python governed_mcp_server.py
```

## 2. Docker (Recommended)

### Build and Run

```bash
docker compose up --build
```

### Environment Variables

| Variable                    | Default              | Description                              |
|----------------------------|----------------------|------------------------------------------|
| `NEXUS_LOG_LEVEL`          | INFO                 | Logging level                            |
| `NEXUS_TRUSTKERNEL_MODE`   | stub                 | `stub` or `real`                         |
| `NEXUS_ENABLE_DRIFT`       | true                 | Enable drift protection simulation       |
| `NEXUS_MCP_NAME`           | nexus-a2a-os-governed-mcp | Server name                     |

## 3. Production Considerations (Future)

- Replace `consult_trustkernel()` stub with real TrustKernel
- Store connector tokens securely (via connector-hub or secrets manager)
- Add persistent logging + audit trail to nexus-memory
- Enable real MCP SDK when network is available
- Add authentication layer in front of MCP server (if exposed)

## 4. Health Check

The server exposes `system.health` tool for basic monitoring.

---

**Status**: Ready for local + Docker development with full governance simulation.
