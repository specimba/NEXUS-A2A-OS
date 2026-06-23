# Browser AI MCP Bridge Tools

This folder contains the NEXUS-owned hardened clone of the D:\GROSS Grok MCP bridge.

## Files

- `grok_mcp_server_v2.py` - hardened FastMCP SSE/A2A bridge clone for Grok/GPT custom MCP connectors.
- `start_grok_mcp_v2.ps1` - safe launcher that refuses to overwrite an active 7354 owner.

## Start Local Only

```powershell
.\tools\browser_ai_mcp\start_grok_mcp_v2.ps1
```

## Start With ngrok

```powershell
.\tools\browser_ai_mcp\start_grok_mcp_v2.ps1 -StartNgrok
```

Use the printed `https://.../sse` URL in Grok/GPT custom connector UI.

## Policy Controls

```powershell
$env:GROK_HTTP_ALLOWED_HOSTS = "huggingface.co,github.com,raw.githubusercontent.com,modelcontextprotocol.io,arxiv.org"
$env:GROK_HTTP_MAX_BODY_BYTES = "1048576"
$env:GROK_HTTP_SAFE_PREVIEW_LIMIT = "1024"
```

Hard rules stay in code: HTTPS only, GET/HEAD only, sensitive headers stripped, private targets blocked, redirects not followed, response bodies capped.

## Runtime Storage

By default the cloned bridge preserves `D:\GROSS` as the primary audit/evidence/coordination store, but it now falls back to repo-local runtime storage if primary writes fail:

```powershell
$env:GROK_FALLBACK_RUNTIME_DIR = "scratch/browser_ai_mcp_runtime"
```

The `/health` response exposes `runtime_write_policy` and `directories.fallback_runtime`. This is intentional: Grok/GPT connector calls should not fail just because the original GROSS evidence path is locked or unavailable from the NEXUS clone.

## Verified Preflight

```powershell
python -m pytest tests\tools\test_grok_mcp_server_v2_static.py tests\bridge\test_browser_http_diagnostic.py -q --tb=short
python -m nexus_os.cli.nexusctl gross-http https://huggingface.co --method HEAD --audit-id browser-mcp-preflight --operator codex --live
```
