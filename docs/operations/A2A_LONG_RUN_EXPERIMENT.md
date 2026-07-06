# A2A long-run browser experiments (zero API cost)

## Start (observe-only while you work Grok/GPT/Zo — **no auto messages**)

```powershell
.\scripts\grok_zo_cdp_lane.ps1 -Action CoordinateLiveCollab
```

Stops any ping runner, sets collab lock, snapshots tails, starts 120min **probe-only** telemetry.

## Stop background runner

```powershell
.\scripts\grok_zo_cdp_lane.ps1 -Action StopA2AExperiment
```

## Lab pings (never Grok/GPT/Zo — disposable lanes only when lock allows)

```powershell
.\scripts\grok_zo_cdp_lane.ps1 -Action A2AExperimentLab
```

## Legacy (do not use during live collab)

`A2AExperiment` now aliases **CoordinateLiveCollab** (observe-only).

## Observe only (120 min, no sends — safest while lanes are busy)

```powershell
.\scripts\grok_zo_cdp_lane.ps1 -Action A2AExperimentObserve
```

## Monitor

```powershell
Get-ChildItem C:\Users\speci.000\Downloads\NEXUSlogs\a2a_experiment\runner_*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | % { Get-Content $_.FullName -Tail 15 -Wait }
```

Session artifacts: `Downloads\NEXUSlogs\a2a_experiment\a2a_<timestamp>\`
- `events.jsonl` — every probe, wait, stabilize
- `FINAL_REPORT.md` — medians + reachability (written at end)
- `lane_timing` merges into `Downloads\NEXUSlogs\lane_timing\events.jsonl`

## Cycle design

- Every 12–15 min: align lanes → probe all priority≤2 agents → optional ping + intelligent wait
- Stabilize Chrome every 4th cycle (not every cycle — less window thrash)
- Skips ping when probe shows `generating`
- GLM pings skipped (manual downgrade-cancel policy)