# NEXUS Multi-Lane A2A Doctrine (operator-grounded)

| Field | Value |
|-------|-------|
| **Status** | LIVE 2026-07-10 |
| **CDP** | Authenticated Chrome `:9224` |
| **Observe** | Chrome window is source of truth; terminal optional |
| **Ledger** | `C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl` |

## Observation (operator priority)

- You want the CDP Chrome **visible** so you can intervene randomly.
- Prefer leaving **`.\scripts\keep_visible_daemon.ps1`** running (continuous anti-offscreen).
- `.\scripts\watch_lane_stack.ps1` = one-shot restore + preflight (not a substitute for the daemon).
- Random minimize/offscreen (`-32000` / `-26214`) is blocked when:
  - `VISIBLE_LANES=1` or `NEXUS_KEEP_VISIBLE=1`, or
  - `WINDOW_PROTECT.json` lock exists (daemon writes this).

## Lane roles (do not waste)

| Lane | Role | Wait for chat text? | Notes |
|------|------|---------------------|-------|
| **Qwen WebDev** | Code + **Preview** canvas | **NO** | Success = Code/Preview/Deploy change, not a long chat essay |
| **DeepSeek** | Fast expert review + fast code | Yes (if DOM exposes chat) | Primary speed lane |
| **MiMo Claw** | **Daily 4h paranoid stress / red-team** | Yes | Create Now → agree → Continue Creating; pass here ≈ 95% elsewhere |
| **Zo Computer** | Cloud Ubuntu + NEXUS groundings + self-agents | Yes + **resume summary** after long pause | Creative compute advantage — **not** hide stress |
| **Grok 4.3** | MCP + sandbox bend + synth/coordinator | Yes | Drive/cloud work folder for shared artifacts |
| **Gemini** | Canvas + project + **Google Drive** bridge | Yes / canvas | Shared Drive with GLM = low-cost handoff storage |
| **GLM-5.2 Z.ai** | Next.js sandbox apps | Yes | **Never switch model**; force retry 5.2 only |
| **ChatGPT 5.x** | Custom MCP architecture | Yes | High/Pro friction possible |
| **Meta Muse Spark** | Fast HTML/CSS canvas examples + own FS | Canvas artifacts | Tricky collab; good for throwaway examples |
| **MiniMax Agent** | General + **Coder** + Verifier team | Yes | Producer/verifier cycles for A2A OS work |
| **Mistral Code** | Coder sandbox + GitHub + Drive | Yes | Implementation lane |
| **Intern AI Shanghai** | **GPU A800 / free lab** primary | Notebook + **workbench CDP** | Prefer over GMI for heavy GPU; start via `intern_workbench_cdp.mjs` (not only manual). Persist `/data`. See `INTERN_WORKBENCH_CDP_AUTOMATION_PLAN.md` |
| **GMI Cloud playground** | Secondary GLM/endpoint | Optional | Not primary vs Shanghai |

## Daily routine

1. Start `keep_visible_daemon.ps1` (once per work day).
2. Open/refresh CDP Chrome; confirm you can see tabs.
3. **MiMo Claw:** Create Now → checkbox → Continue Creating → run new red-team / stress case for the day (ledger row).
4. Run A2A specialty work on Grok / Gemini Drive / GLM / DeepSeek / Zo as needed.
5. Qwen WebDev: send task → watch **Preview/Code**, not chat wait.

## Zo resume rule

After long stop / model change / provider refresh: **first message must re-ground** with short summary of where we left off, active paths, open tasks — otherwise Zo sticks on early-thread context.

## Gemini ↔ GLM storage bridge

Grok work folder can bind **Google Drive**. Shared Drive folder + MCP tools = near-zero-API handoff surface between Gemini canvas packaging and GLM sandbox implementation, with Zo as second computer for Ubuntu-side automation.
