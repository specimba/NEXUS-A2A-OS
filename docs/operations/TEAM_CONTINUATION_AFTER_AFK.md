# NEXUS browser team — continue from AFK (2026-07-02)

## What the 2h A2A run achieved (session `a2a_2026-07-02T12-28-37`)
- **8 cycles** (~10 min each), **120 min** wall clock — completed successfully.
- **Lane URLs held** on canonical sessions (Grok, Zo, GPT-5.5 `6a4600ec…`, Qwen×2, Apodex, MiMo, Gemini, etc.).
- **22 probes** saw `generating=true` (Grok/Zo often in Thought) — correct to skip blind ping.
- **Grok in-tab evidence**: `[GROK-PING] ok + 4`, `ok + 12` from earlier cycles.
- **ChatGPT pings**: failed wait JSON parse inside `send_*` (fixed: `-NoWait` + better JSON line pick).
- **Median wait table empty** — waits did not record `RESPONSE_READY` JSON; v3 experiment fixes that.

## Chrome twitch diagnosis (your AFK observation)
Every **4th cycle** (~40 min) `STABILIZE` ran **WIN32_RESTORE + CDP maximize** while you had the window **minimized** → fight → “twitch” every ~10 min when combined with tab navigate focus.

**Fix landed:**
- Background jobs: **`align_browser_lanes` only** (no restore).
- **`restore_chrome_cdp_window`**: does nothing unless **`-ForceShow`** (manual recovery).
- **`RecoverChrome`**: kill lane profile → reset prefs → visible start → **one** `-ForceShow`.

## Team roster (unchanged)
Registry: `nexus_os/nexusclaw/browser_lane_registry.json` (17 lanes).

**A2A chain:** Grok `[GROK-PLAN]` → ChatGPT `[CHATGPT-PLAN]` + MCP → Zo `[ZO-PLAN]` long execute.

**GLM:** cancel downgrade, retry 5–10s. **No auto-ping GLM.**

## Recovery now (minimized / won’t maximize)

```powershell
cd C:\Users\speci.000\Documents\NEXUS
.\scripts\grok_zo_cdp_lane.ps1 -Action RecoverChrome
.\scripts\grok_zo_cdp_lane.ps1 -Action ListTabs
```

## Next long run (v3 — no twitch, working waits)

```powershell
.\scripts\grok_zo_cdp_lane.ps1 -Action A2AExperiment
```

Reports: `Downloads\NEXUSlogs\a2a_experiment\a2a_<ts>\FINAL_REPORT.md`

Prior combined: `Downloads\NEXUSlogs\a2a_experiment\A2A_COMBINED_FINDINGS_v1.md`