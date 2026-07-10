# NEXUS Grok MCP Deep Dive (2026-07-10)

## Why this matters

Grok 4.3 browser “team + sandbox bend” only stays useful if the **connector tools are real, governed, and improved deliberately**. This note maps what exists, how it should be used, and what to build next for A2A.

## Port plane (Grok-facing)

| Port | Role | Not |
|------|------|-----|
| **9224** | Chrome CDP (lane truth) | Playwright fresh profile |
| **7354** | Grok MCP bridge SSE (`tools/browser_ai_mcp/grok_mcp_server_v2.py`) | Brain API |
| **7352** | Brain API only | MCP / dashboard reuse |
| **7355** | ModelRelay Python fallback | Public MCP |

Health (when bridge up):

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:7354/health
```

SSE: `http://127.0.0.1:7354/sse`  
Start: `tools\browser_ai_mcp\start_grok_mcp_v2.ps1`

## Tool inventory (v2.3.0-queue-visible) — 22 tools

### Connectivity
| Tool | Purpose |
|------|---------|
| `ping` | Identity + version + uptime |
| `echo` | Bounded smoke |
| `registry_debug` | Tool list + schema hashes + drift contract |

### Evidence / audit
| Tool | Purpose |
|------|---------|
| `audit_log` | Integrity-hashed audit append |
| `evidence_capture` | Bounded text + SHA256 |
| `query_log` | Browser/source query evidence |
| `http_diagnostic` | **Scoped** public HTTPS GET/HEAD only |
| `comparison_*` | Matrix add/get/export |
| `simulate_probe` | Dry probe pipeline |

### Coordination queue (A2A spine)
| Tool | Purpose |
|------|---------|
| `task_add` | Durable task proposal |
| `task_list` / `task_claim` / `task_complete` / `task_fail` | Queue lifecycle |
| `coordination_status` | Counts + revision |

### Session / messaging
| Tool | Purpose |
|------|---------|
| `session_heartbeat` / `session_status` | Long-run liveness |
| `agent_publish_message` / `agent_retrieve_messages` / `agent_list_topics` | Bounded A2A channels |

## Hardening already in v2 (do not weaken)

1. Strip auth cookies / API key headers from `http_diagnostic`.  
2. Block private / loopback / link-local / metadata IPs.  
3. Host allowlist `GROK_HTTP_ALLOWED_HOSTS`.  
4. Body size caps; no redirect follow (3xx as evidence).  
5. Runtime write fallback to `scratch/browser_ai_mcp_runtime` if `D:\GROSS` unwritable.

## Governed MCP (separate surface)

`nexus_os/mcp/server.py` TrustKernel tools (governance.*, system.health, drift_monitor, memory checkpoint, dry-run slack/notion/telegram).  
This is **not** the same process as 7354 Grok bridge — dashboard/brain may use it; Grok connector should stay on **v2 bridge tools**.

## How Grok browser should use MCP (operator contract)

1. Always `ping` + `registry_debug` first.  
2. `session_heartbeat` at cycle start/end with lane map summary.  
3. Real multi-lane outcomes → `evidence_capture` (snippet + hash) **before** `task_add`.  
4. Cross-lane handoffs → `agent_publish_message` topic `nexus.a2a.handoff` with HandoffCard JSON.  
5. Never invent tools; never claim shell/filesystem/delete.  
6. On failure → `task_fail` or `task_add` failure-analysis, not blind retry storms.

## Gaps / improvements (priority)

| Priority | Gap | Improvement |
|----------|-----|-------------|
| P0 | Ledger not first-class MCP tool | Add `continuity_append` / `continuity_tail` (path allowlisted to NEXUSlogs) |
| P0 | No CDP bounds evidence | Add `cdp_window_probe` (read-only bounds/url sample; no navigate) |
| P1 | task_add too free-form | Schema: risk_level, lane, evidence_refs[], stop_rules[] required |
| P1 | No Drive handoff receipt | `handoff_register` linking Drive path hash + token |
| P2 | Qwen preview success invisible to MCP | `artifact_preview_note` kind for webdev (no chat wait) |
| P2 | Claw daily results ad-hoc | `mimo_claw_daily` structured via evidence_capture template |

## Related files

- `tools/browser_ai_mcp/grok_mcp_server_v2.py`  
- `docs/operations/NEXUS_BROWSER_MCP_EGRESS_HUB_2026-06-21.md`  
- `docs/operations/NEXUS_EXTERNAL_BROWSER_AI_DIRECTOR_2026-06-21.md`  
- Port plane review: `docs/reviews/PORT_PLANE_7350_7360_2026-07-09.md`
