You are continuing the NEXUS MCP/HTTP sandbox internet workaround task. Read this carefully and do a serious long-run implementation response, not a short plan.

Current verified state from Codex:
- Your previous `mcp_egress_governor.py` and `test_mcp_egress_governor.py` were extracted locally into scratch and passed `py_compile` plus your 6/6 dry-run tests.
- That artifact is useful but incomplete: it only returns `proxy_via_bridge` plans. It does not implement the real bridge execution boundary.
- NEXUS already has concrete local files you must target:
  - `nexus_os/bridge/browser_http_diagnostic.py`
  - `nexus_os/cli/nexusctl.py` command `gross-http`
  - `nexus_os/nexusclaw/tool_bridge.py`
  - GROSS bridge canonical local port: `7354`
  - Brain API canonical port: `7352`, never ModelRelay.

Mission:
Design the next apply-ready stage: real governed MCP/HTTP egress bridge execution for browser-AI sandbox internet workarounds, using the existing NEXUS/GROSS boundary instead of generic placeholder paths.

Hard requirements:
1. Do not output generic `skills/...` placeholder imports.
2. Do not assume direct internet from Grok sandbox. The point is: sandbox asks NEXUS for a governed diagnostic/proxy action through a local bridge, with dry-run default and explicit live mode.
3. Preserve safety: HTTPS only, GET/HEAD only by default, explicit allowlist, no cookies/Auth headers/API keys, private/local targets blocked unless operator-local bridge call is already inside NEXUS.
4. Keep 7352 as Brain API only. Keep 7354 as GROSS bridge. Do not invent conflicting ports.
5. Integrate with current `BrowserHTTPDiagnosticRelay` semantics, not a parallel incompatible system.
6. Include tests that can run without a live bridge by using fake transports.
7. Include one live verification command for operator use only, but keep default tests offline.

Deliverables:
- Patch plan against exact NEXUS files and functions.
- Full proposed Python module or diff content for the smallest useful integration.
- Full pytest file content for offline tests with fake transport.
- Exact local verification commands.
- Failure-mode table: bridge down, host blocked, method blocked, header stripped, live JSON-RPC/A2A error, token budget denied, KAIJU required.
- Clear next-step contract: what Codex should implement first, and what remains advisory.

Target quality:
- 3-5 minute thoughtful run.
- Be specific and code-aware.
- If you see flaws in `browser_http_diagnostic.py` or `tool_bridge.py`, name them and propose exact fixes.
- Do not claim production complete. The expected output is a verified Stage 2 implementation package proposal that Codex can apply and test locally.
