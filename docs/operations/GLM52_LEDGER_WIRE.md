# GLM-5.2 control plane — ledger + MCP wire

**Canonical continuity ledger (Windows host):**
```
C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl
```

## Env for the Next.js ops mirror (local or exported sandbox)

Create `.env.local` next to the control-plane `package.json`:

```env
NEXUS_LEDGER_PATH=C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl
NEXUS_MCP_HEALTH_URL=http://127.0.0.1:7358/health
NEXUS_MCP_SSE_URL=http://127.0.0.1:7358/sse
NEXUS_CDP_PORT=9224
```

### Port notes (2026-07-10 GO)

| Port | Role | Status |
|------|------|--------|
| **7354** | Legacy Grok MCP (elevated PID stuck at **22 tools / 2.3.0**) | Stale — needs Admin taskkill of owning python |
| **7358** | **P0 bridge** `2.4.0-p0-continuity` **25 tools** | LIVE — use this until 7354 recycled |
| **9224** | Chrome CDP multi-lane | LIVE (17 pages; GLM + Qwen present) |

When the elevated 7354 process is killed, restart with:
```powershell
.\tools\browser_ai_mcp\start_grok_mcp_v2.ps1
```
Expect health: `version=2.4.0-p0-continuity`, `mcp_tool_count=25`.

## Prove ledger path from MCP tools

```text
continuity_append  → append JSON object
continuity_tail    → last N rows
cdp_window_probe   → CDP sample (no navigate)
```

Direct import smoke (2026-07-10) wrote:
`kind=p0_smoke` with `line_hash=f98da3c84c33a99f` into the canonical JSONL.

## Chat.z.ai sandbox

If the app only runs inside z.ai Preview (not a local checkout), set the same env in the sandbox secrets panel **or** keep sample ledger + STUB MCP health (already coded). Host ledger path is only readable when the runtime can see the Windows filesystem.
