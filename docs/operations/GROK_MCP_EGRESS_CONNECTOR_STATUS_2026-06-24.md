# Grok MCP Egress Connector Status - 2026-06-24

## Verified State

- Local bridge `http://127.0.0.1:7354/health` is live as `nexus-grok-bridge-v2`, version `2.2.0-nexus-hardened`, with 22 tools.
- Public ngrok tunnel is live at `https://sharply-unethical-various.ngrok-free.dev`.
- Public `/health`, `/.well-known/agent.json`, and `/sse` return `200`; `/sse` returns `text/event-stream` with a session endpoint.
- Local director + bridge tests pass: `33 passed` for Grok MCP server static checks, MCP egress governor, browser HTTP diagnostic relay, and external browser-AI director.
- Grok-side verification artifact `GrokMcpEgressIntegrationReport_v2` honestly reports `BLOCKED_TOOL_NOT_VISIBLE`: current visible Grok tools do not include `ping`, `registry_debug`, `http_diagnostic`, or `task_add`.

## Current Blocker

The blocker is not local NEXUS code and not the public tunnel. The blocker is Grok custom connector visibility/activation inside the authenticated Grok UI.

Expected Grok connector setup:

- Name: `nexus-grok-bridge-v2`
- Server URL: `https://sharply-unethical-various.ngrok-free.dev/sse`
- Required visible tools after reconnect: `ping`, `registry_debug`, `http_diagnostic`, `task_add`

If Grok still shows only generic Zapier/Canva/Linear/Vercel tools, the director must return:

- `BLOCKED_SETUP`
- blocker: `grok_connector_tools_missing`
- provider calls: `0`

## Director Rule

Do not call InternAI, LongCat, Codex, or another provider when Grok reports `BLOCKED_TOOL_NOT_VISIBLE` for the NEXUS connector tools. This is a setup failure, not a reasoning task.

Required next verification after connector reconnect:

1. Ask Grok for `GrokMcpEgressIntegrationReport_v2`.
2. It must call `ping` or equivalent health first.
3. It must call `registry_debug` or equivalent tool list second.
4. It must call `http_diagnostic` with `HEAD https://huggingface.co`.
5. It may create one dry-run `task_add` proposal only if a real local blocker remains.

## Local Commands

```powershell
python -m pytest tests\tools\test_grok_mcp_server_v2_static.py tests\mcp\test_egress_governor.py tests\bridge\test_browser_http_diagnostic.py tests\tools\test_external_browser_ai_director.py tests\tools\test_external_browser_ai_director_cli.py -q --tb=short
```

```powershell
node tools\browser_ai_supervisor\grok_cdp_context_probe.mjs --port 9224 --required Grok --outFile scratch\browser_ai_mcp_runtime\grok_mcp_after_ngrok_probe_20260624.json --maxChars 9000 --maxCodeChars 1500
```

