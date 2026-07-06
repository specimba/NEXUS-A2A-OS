# Lane response intelligence — observe before nudge; cumulative timing per agent × task class.

## Problem (fixed)

Blind `continue` nudges at ~10s **interrupt** Grok while `Thought for …` / `Thinking` is still active. Zo/ChatGPT need the same discipline.

## Loop (per send)

1. **Probe baseline** — `tailText` length before send.
2. **Send once** — CDP compose + Enter.
3. **Poll** every 4s (`lane_response_wait.mjs`):
   - **generating** if signals: `grok_thought_for`, `thinking_text`, `stop_generating`, `zo_thinking`, `chatgpt_stop_generating`, …
   - **ready** when idle + tail grew ≥40 chars + stable 2 polls.
4. **Probe excerpt** — read answer; only then optional nudge (nudge class uses shorter budget).
5. **Record** → `NEXUSlogs/lane_timing/events.jsonl`.

## Adaptive timeouts

```powershell
.\.venv\Scripts\python.exe -m nexus_os.nexusclaw.lane_timing_cli suggest-wait grok smoke
.\.venv\Scripts\python.exe -m nexus_os.nexusclaw.lane_timing_cli median zo handoff
```

Rolling median × 1.35 caps `MaxWaitSec` when enough history exists; else defaults in `lane_timing.py`.

## Task classes

`smoke` | `handoff` | `nudge` | `coding` | `deep_search` | `audit` | `paper_review` | `general`

## Future roster (IDs reserved)

`meta_muse_spark`, `glm_5_2`, `kimi_2_6`, `apodex_deep`, `alphaxiv_browser` — same telemetry schema; router picks agent by class + median latency.

## Commands

```powershell
.\tools\browser_ai_supervisor\wait_lane_response.ps1 -Required grok.com -AgentId grok -TaskClass handoff -BaselineTailLen 12000
.\scripts\grok_zo_cdp_lane.ps1 -Action CollabPlaytest   # no early nudge; waits each lane
```

## Policy

- **Never** nudge while `phase=generating`.
- **Nudges** only after `RESPONSE_READY` or explicit `TIMEOUT` + operator OK.
- Grok: multi-nudge **after** response, not during.