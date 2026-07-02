# Hermes + Grok 4.3 browser CDP — dual-lane architecture

**Status 2026-07-02:** Operator ran `pip install -e ".[mcp]"`, bridge PID live, **`nexusctl grok-lane doctor` — all links UP.**

**Grok project (NEXUS knowledge team):** set once via env (not hardcoded in new code paths):

```powershell
$env:NEXUS_GROK_PROJECT_CHAT_URL = "https://grok.com/project/99253cca-2469-4454-8593-0f173b7f640f?chat=4d8d8598-9da7-4639-918e-4ceb6a8812ba"
$env:NEXUS_GROK_CDP_PORT = "9224"
```

## Roles (no token burn on planner)

| Lane | Where | Job | Cost |
|------|--------|-----|------|
| **Planner / advisory** | Grok in Chrome (CDP :9224) | Long-horizon NEXUS strategy, architecture, risk review | Browser subscription — **not** Hermes API credits |
| **Executor** | Hermes CLI (this session) | Files, tests, relay, patches, local probes | `model.base_url` → **7350** (128 models) or `auto-fastest` |

Hermes does **not** replace Grok in the browser. It **consumes** Grok output when the supervisor detects a material delta and optionally routes a dry-run task envelope (`nexus_os/nexusclaw/browser_ai.py`).

## Chain (verified by `nexusctl grok-lane doctor`)

```
Chrome CDP :9224  →  Grok MCP :7354  →  Node relay :7350  →  Python relay :7355
                              ↓
                    external_browser_ai_director (policy, memory-gated)
                              ↓
                    BrowserAINexusClawBridge → HermesRouter metadata (dry-run)
```

## Operator bring-up (Windows admin terminal)

```powershell
cd C:\Users\speci.000\Documents\NEXUS

# 1) Grok tab (dedicated profile, your chat URL)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_grok_cdp_9224.ps1
# Re-login: add -ShowWindow

# 2) MCP bridge (uses .venv\Scripts\python.exe)
powershell -NoProfile -ExecutionPolicy Bypass -File tools\browser_ai_mcp\start_grok_mcp_v2.ps1

# 3) Probe full lane
.\.venv\Scripts\python.exe -m nexusctl grok-lane doctor
```

## Hermes wiring (executor)

```bash
hermes config set model.base_url http://127.0.0.1:7350/v1
hermes config set model.default auto-fastest
```

Keep **grok-composer-2.5-fast + xai-oauth** only if you want OAuth identity for *this* chat UI; completions still route through 7350 when `base_url` is set.

## How to use Grok as “expert team” in practice

1. Work in the **Grok project chat** (browser) for plans, checklists, and cross-doc synthesis.
2. When Hermes needs that context, paste the **latest Grok artifact** into this session (or let the hourly supervisor automation append to `~/.nexus/browser_ai_supervisor_memory.jsonl`).
3. Hermes executes locally: pytest, patches, `nexusctl`, relay health — and reports evidence back.
4. **Do not** point Hermes `browse_page` at grok.com for bulk scraping; use CDP supervisor + 7354 governed tools instead (`network_access: allowlisted_public_https_via_7354_only` in bridge egress policy).

## Governance

- GROSS / 7354: read-only evidence by default; no credential exfil (see GROSS leak lab docs).
- Director: max **3** paid provider calls/hour per source; **0** calls on `NOOP_UNCHANGED`.
- Bridge start script now uses repo **venv Python** (fixes “7354_down” when system python lacked deps).

## 7354 blocker (if health fails)

Venv may lack the `mcp` package. From repo root (Windows):

```powershell
.\.venv\Scripts\python.exe -m ensurepip
.\.venv\Scripts\python.exe -m pip install -e ".[mcp]"
powershell -NoProfile -ExecutionPolicy Bypass -File tools\browser_ai_mcp\start_grok_mcp_v2.ps1
```

## Files touched (2026-06-30)

- `nexus_os/nexusclaw/grok_lane_env.py` — env defaults
- `tools/browser_ai_supervisor/external_browser_ai_director.py` — dynamic URL/port
- `src/app/api/nexusclaw/status/route.ts` — dashboard profile env
- `scripts/start_grok_cdp_9224.ps1` — opens full chat URL
- `tools/browser_ai_mcp/start_grok_mcp_v2.ps1` — venv python