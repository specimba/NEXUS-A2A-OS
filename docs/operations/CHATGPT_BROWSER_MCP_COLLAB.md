# ChatGPT browser + GPT-audit-tools MCP

ChatGPT **Apps** connector (dev mode) points at the same bridge as Grok lane MCP:

- **SSE URL:** `NEXUS_GPT_AUDIT_MCP_SSE_URL` (default in ledger: `https://sharply-unethical-various.ngrok-free.dev/sse`)
- **Server:** `tools/browser_ai_mcp/grok_mcp_server_v2.py` (GROSS egress / coordination tools)

## New GPT-5.x conversation (browser)

```powershell
$env:NEXUS_CHATGPT_CHAT_URL = "https://chatgpt.com/"
$env:NEXUS_CHATGPT_NEW_CHAT = "1"
.\scripts\grok_zo_cdp_lane.ps1 -Action Restore
.\tools\browser_ai_supervisor\send_chatgpt_cdp.ps1 -PromptFile tools\browser_ai_supervisor\prompts\chatgpt\hermes_collab_mcp_new_chat_v1.md
```

In ChatGPT UI: confirm **GPT-audit-tools** connected (Allow all for dev). Ask GPT to run `ping` and `agent_publish_message` to topic `nexus-browser-collab`.

## CDP tab discipline

- Lane start uses `about:blank` + `open_collab_tabs_if_missing.ps1` — **no extra Grok tab** if `grok.com` already open.
- Passkey / forced Grok URL: `start_grok_cdp_9224.ps1 -ForceOpenGrokUrl`

## Tags

`[CHATGPT-PLAN]` ↔ Hermes `[HERMES-EXEC]` ↔ Grok `[GROK-PLAN]` ↔ Zo `[ZO-PLAN]`