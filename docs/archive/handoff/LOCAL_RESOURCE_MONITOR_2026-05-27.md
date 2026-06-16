---
id: NODE-MIG-LOCAL_RESOURCE_MONITOR_2026_05_27
authority_scope: experimental
origin_sha256: 2404712c025dcb828f407fb92c6d784f5e857fd93689b7f73df42620ae14df12
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-6A6B74
---
# Local Resource Monitor Findings - 2026-05-27

<!-- CANARY: b314cde37417402e7b6b62d2ece9859b -->
Scope: `codex/specimba/1805mainSpeci @ 9cc32e2`

## Evidence Artifacts

- Monitor run: `logs/resource-monitor/20260527_072820/`
- Samples: `logs/resource-monitor/20260527_072820/samples.csv`
- Process top snapshots: `logs/resource-monitor/20260527_072820/process_top.csv`
- Ollama churn CSV: `logs/resource-monitor/20260527_072820/ollama_churn.csv`
- Windows event export: `logs/resource-monitor/20260527_072820/events_after.jsonl`
- Summary: `logs/resource-monitor/20260527_072820/summary.json`

Run window: `2026-05-27T07:28:20+03:00` to `2026-05-27T07:48:26+03:00`.

## Verdict

The old bad Ollama Desktop retry loop on `127.0.0.1:49152` did not recur during this 20-minute window. The random `ollama.exe` PIDs are active model-runner churn against the stable server on `127.0.0.1:11435`, not the old desktop supervisor failure loop.

That churn is still operationally expensive. The run shows high memory commit pressure, repeated Ollama runner private memory spikes, a heavy OBS/Streamlabs baseline, and short disk queue/write stalls that can plausibly cause audio stutter when streaming or recording.

## Key Measurements

- Samples captured: `137`
- Commit pressure: average `86.38%`, p95 `88.56%`, max `91.92%`
- Disk write: average `13.35 MB/s`, p95 `59.86 MB/s`, max `178.46 MB/s`
- Disk read: average `86.50 MB/s`, p95 `681.54 MB/s`, max `1052.50 MB/s`
- Disk queue: average `0.259`, p95 `0.517`, max `16.472`
- `49152` detections: `0`
- Ollama app log growth: `0`
- Ollama server log growth: `0`
- Startup link: `Ollama.lnk` absent, `Ollama.lnk.disabled` present
- Windows event export showed no new displayed WHEA, `nvlddmkm`, Display, Application Error, or WER evidence in the captured output.

Note: the original monitor script's RAM percent fields from `Win32_OperatingSystem` recorded as `0`. Commit pressure and process private memory are valid. The script has been patched to use `\Memory\Available MBytes` for future runs.

## Process Findings

Largest working set and private memory contributors:

- `obs64`: max working set `2063.5 MB`, max private memory `6206.1 MB`
- `ollama`: max working set `1883.2 MB`, max private memory `6659.8 MB`
- `Memory Compression`: max working set `1542.3 MB`
- `chrome`: max working set `939.0 MB`, max private memory `992.6 MB`
- `language_server`: max working set `927.7 MB`
- `zo`: max working set `762.8 MB`, max private memory `1178.3 MB`
- `vmmemWSL`: max working set `639.0 MB`, max private memory `5600.1 MB`
- `python`: max working set `551.0 MB`, max private memory `1698.6 MB`
- `opencode`: max working set `498.0 MB`, max private memory `1875.2 MB`
- `kilo`: max working set `495.2 MB`, max private memory `4139.0 MB`
- `devin`: max private memory `11766.7 MB`

Largest CPU contributors during the run:

- `ollama`: aggregate CPU delta `934.73`
- `chrome`: aggregate CPU delta `547.20`
- `obs64`: aggregate CPU delta `431.68`
- `Taskmgr`: aggregate CPU delta `422.45`
- `Streamlabs OBS`: aggregate CPU delta `294.73`
- `Antigravity`: aggregate CPU delta `179.09`
- `zo`: aggregate CPU delta `137.81`
- `Spotify`: aggregate CPU delta `134.68`
- `Codex`: aggregate CPU delta `108.22`
- `grok`: aggregate CPU delta `94.90`

## Ollama Churn Interpretation

Stable server:

- `ollama` PID `47060` stayed alive throughout the run on `127.0.0.1:11435`.

Runner churn:

- Short-lived `ollama` runner PIDs appeared repeatedly in `process_top.csv`.
- Many runner samples showed working sets around `624 MB`, `1256 MB`, or `1880 MB`.
- Private memory frequently reached roughly `5 GB` to `6.6 GB`.
- This matches model-runner lifecycle churn while local agents are actively querying models.

This is useful work only when the active agent request needs that model. During OBS/audio work, it is still a resource hog because it creates commit pressure and disk/cache pressure even when CPU and VRAM appear quiet in Task Manager.

The stronger explanation is model swapping or missing per-request keep-alive in one or more agent paths, not the old `49152` retry loop.

## Disk Stall Evidence

Worst queue sample:

- Time: `2026-05-27T07:40:05+03:00`
- Disk queue: `16.472`
- Read: about `17.6 MB/s`
- Write: about `18.9 MB/s`
- Top working-set process: `obs64`

Highest write sample:

- Time: `2026-05-27T07:39:38+03:00`
- Write: `178.46 MB/s`
- Disk queue: `0.221`
- Top working-set process: `obs64`
- Top CPU process: `grok`

Second pressure sample:

- Time: `2026-05-27T07:42:25+03:00`
- Read: about `180.8 MB/s`
- Write: about `155.7 MB/s`
- Disk queue: `1.663`
- Top working-set process: `obs64`
- Top CPU process: `Taskmgr`

The `16.472` queue spike with modest throughput points to latency or contention, not pure bandwidth exhaustion. Likely contributors are pagefile pressure, OBS/Streamlabs write activity, model loading/cache activity, antivirus scanning, or multiple agents doing local I/O at once.

## Optimization Plan

Immediate low-risk actions:

- Keep the Ollama Desktop startup supervisor disabled. The stable server on `11435` is the path to preserve.
- Do not run long compare/safety sweeps, chaos generators, or merge optimizer workloads while OBS/audio is active.
- Keep only one local Ollama-heavy agent lane active during streaming/recording. Queue the others.
- Avoid alternating guard models during live work. Model alternation forces runner swap churn.
- Prefer direct HTTP calls to `http://127.0.0.1:11435`, not shelling through `ollama` CLI paths that may wake desktop behavior.
- Move OBS recordings/cache and Ollama models away from the system/pagefile disk when possible.
- Close or pause high-background-cost UI surfaces during recording: heavy Chrome tabs, Task Manager, Grok, Antigravity, Zo, Spotify, and extra agent dashboards.

Ollama-specific follow-up:

- Audit active scripts for missing `keep_alive` in `/api/generate` and `/api/chat` payloads.
- Enforce a single live local model lane for OBS/audio windows.
- Consider setting Ollama runtime limits only after confirming the current build supports them: `OLLAMA_NUM_PARALLEL=1` and either `OLLAMA_MAX_LOADED_MODELS=1` for minimum memory or `2` if RAM is upgraded and model swapping is worse than keeping both loaded.
- `OLLAMA_KEEP_ALIVE=30m` helps only when the same model is reused. It will not fix churn if agents alternate models and loaded-model limits force eviction.

OBS/Streamlabs follow-up:

- Re-check Streamlabs/OBS browser source count and refresh behavior.
- Keep prior safe-repair style reductions in place: disable unnecessary browser hardware acceleration, file caching, and forced GPU render paths only after backing up current config.
- Keep a clean baseline snapshot after a stable test window.

Next measurement:

- Re-run `scripts/local_resource_monitor.ps1 -DurationMinutes 20 -IntervalSeconds 2` after applying one optimization at a time.
- Compare commit max, disk queue max, disk write p95, and short-lived Ollama PID count against this baseline.

## Grok Network Incident Addendum

Screenshot evidence:

- Screenshot: `C:\Users\speci.000\Downloads\grokNETWORKusage.png`
- Captured process: `grok.exe`
- Captured PID: `1796`
- Captured network rate: `12.2 Mbps`
- Captured working set: `321.2 MB`
- Screenshot timestamp on disk: `2026-05-27 07:40:52+03:00`

Current live state:

- `grok.exe` was not running when re-checked.
- No live TCP endpoints could be recovered for PID `1796` after process exit.

Local Grok state:

- `C:\Users\speci.000\.grok` exists.
- `C:\Users\speci.000\.grok\upload_queue` exists.
- Direct queue children: `1086`
- Direct queue size: `14,149,435,226 bytes`
- Queue last write: `2026-05-27 07:43:16+03:00`
- `C:\Users\speci.000\.grok\logs\unified.jsonl` exists and was last written around the same session window.

Largest queue entries included multiple deduplicated blobs between roughly `168 MB` and `502 MB`. The queue timestamps overlap the Task Manager screenshot and the 20-minute resource-monitor window.

Grok claim assessment:

- Supported: `grok.exe` was using sustained network throughput in the screenshot.
- Supported: BrainSync was present as an MCP server. `C:\Users\speci.000\.grok\logs\mcp\brainsync.stderr.log` shows BrainSync MCP startup.
- Not fully supported: the claim about "many connected MCP servers" is imprecise. `unified.jsonl` reported `mcp_server_count: 2`, not many servers.
- More important than MCP count: the `14.15 GB` upload queue is direct local evidence of a large sync/upload workload that can saturate upstream and starve OBS.

Operational disposition:

- Treat Grok Build in `always-approve` mode as unsafe during OBS/audio work.
- Do not run Grok deep filesystem/reasoning sessions while streaming unless upload/sync is disabled or rate-limited.
- Do not delete `C:\Users\speci.000\.grok\upload_queue` blindly. If cleanup is needed, first rename or backup the directory so data can be restored if Grok expects it.
- If the incident recurs, capture live endpoints immediately with the patched monitor or Resource Monitor before ending `grok.exe`.

## Monitor Script Updates

`scripts/local_resource_monitor.ps1` was patched after this run:

- RAM availability now uses `\Memory\Available MBytes`.
- Total physical RAM now comes from `Win32_ComputerSystem`.
- Ollama churn now uses `Get-Process` instead of `Win32_Process` command-line queries.
- Network total throughput is now sampled.
- TCP endpoint snapshots are now captured for high-interest processes, including `grok`, `ollama`, `python`, `obs`, `Streamlabs`, `chrome`, `Codex`, `Antigravity`, `Zo`, `devin`, `opencode`, and `kilo`.

These changes improve future monitoring accuracy. They do not retroactively change the 20-minute run artifacts.

## 2-Hour GROSS Long-Session Resource Follow-Up

Run:

- Output directory: `logs/resource-monitor/gross-long-session/20260527_163655/`
- Window: `2026-05-27T16:36:55+03:00` to `2026-05-27T18:37:07+03:00`
- Samples: `726`
- High disk queue samples: `5`
- Max disk queue: `8.479`
- Max disk read: `978.45 MB/s`
- Max disk write: `238.76 MB/s`
- Max network total: `93.94 Mbps`
- Ollama unique process starts: `604` by summary, `573` unique PIDs in `ollama_churn.csv`
- RAM percent caveat: `total_ram_mb` was `0` in this run because CIM access to `Win32_ComputerSystem` was denied. `free_ram_mb` and `commit_pct` were valid.
- Commit pressure: max `100%`, average `89.76%`, minimum free RAM `794 MB`, maximum free RAM `7607 MB`

Startup popup attribution:

- At `2026-05-27T16:32:31+03:00`, Windows logged `Application popup: powershell.exe - Application Error` with `0xc0000142`.
- This matches the first monitor launch attempt using legacy `powershell.exe`; that attempt did not produce a usable run directory.
- The completed 2-hour monitor was relaunched later with PowerShell 7 `pwsh.exe` at `2026-05-27T16:36:55+03:00`.
- Disposition: related to monitor startup, not evidence of Grok upload behavior. Treat as process initialization failure under the same high-commit workstation pressure window.

Process attribution:

- `devin`: max private memory `26565.10 MB`, max working set `1320.10 MB`, aggregate CPU delta `758.52`
- `ollama`: max private memory `6321.10 MB`, max working set `1358.60 MB`, aggregate CPU delta `13822.73`
- `obs64`: max private memory `6188.00 MB`, max working set `1979.10 MB`
- `Streamlabs OBS`: max private memory `3569.10 MB`
- `opencode`: max private memory `2203.00 MB`
- `zo`: max private memory `1166.80 MB`

Interpretation:

- The old `127.0.0.1:49152` Ollama desktop retry loop still did not recur (`netstat_49152_count=0` in the top disk-queue samples).
- The random `ollama.exe` PID churn is real and heavy: this run recorded hundreds of unique runner starts over two hours, with port `11435` active.
- Devin is now the top private-memory pressure source observed in the long window. This can contribute to paging/memory compression and audio stutter even if Devin is not the top CPU process.
- The worst disk stall sample at `2026-05-27T16:46:53+03:00` had queue `8.479`, read about `902.30 MB/s`, write about `238.76 MB/s`, top working-set process `Memory Compression`, and top CPU process `ollama`.
- Alloy/windows_exporter emitted repeated `diskdrive` WMI timeout warnings during the final segment, which supports the conclusion that WMI/disk telemetry itself was under pressure.

Operational disposition:

- Treat Devin as a memory-heavy agent lane. During OBS/audio windows, do not combine Devin with Ollama-heavy local sweeps and WSL/Grok stress sessions unless RAM headroom is verified.
- Keep Ollama on `11435`; do not chase the runner PID churn as the old desktop retry bug. Optimize it by reducing model alternation and enforcing a single local model lane during live work.
- For future attribution, keep the GROSS queue monitor and Windows resource monitor running together, but use a lighter TCP sampler. This run's TCP CSV stayed header-only, likely due `Get-NetTCPConnection` access/sampling limits in the hidden monitor context.
- `scripts/local_resource_monitor.ps1` is now patched with a .NET `ComputerInfo` fallback for total/available physical RAM when CIM is denied.
