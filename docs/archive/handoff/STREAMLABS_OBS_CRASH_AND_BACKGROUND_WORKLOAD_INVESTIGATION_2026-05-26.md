---
id: NODE-MIG-STREAMLABS_OBS_CRASH_AND_BACKGROUND_WORKLOAD_INVESTIGATION_2026_05_26
authority_scope: experimental
origin_sha256: 3a411097fe0446a1108241b34370d3dd518e8aa34091bca6afcb8aa2e57df0ea
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-CC1927
---
# Streamlabs OBS Crash + Background Workload Investigation - 2026-05-26

## Scope

<!-- CANARY: 673a96da252493a97d7cf28cf5826835 -->
Low-disruption investigation only. No Streamlabs AppData files were edited, no OBS scenes were deleted, no processes were killed, and no restart was performed.

Sensitive note: Streamlabs service files were inspected only enough to confirm they contain live stream credentials. Those values are intentionally not copied here.

## Primary Finding

The 2026-05-26 16:03 Streamlabs incident was a resource exhaustion crash, not a confirmed NVIDIA driver reset.

Confirmed evidence:

- `crash-handler.log` recorded a critical Streamlabs child process death at `2026-05-26 16:03:37`; crashed module was `obs.dll` under `C:\Program Files\Streamlabs OBS\resources\app.asar.unpacked\node_modules\obs-studio-node\obs.dll`.
- The latest node-obs log recorded escalating FFmpeg/audio pressure before crash: max audio buffering, repeated source-audio restarts, then `Failed while trying to allocate 1382400 bytes, errno 12`.
- Windows Resource Exhaustion Detector emitted Event ID `2004` at `2026-05-26 16:03:28` and `16:03:37`. Top virtual memory consumers at the crash window were `devin.exe` at about `18.7 GB`, `git.exe` at about `16.1 GB`, and `obs64.exe` at about `6.6 GB`.
- No new matching GPU/WHEA/nvlddmkm evidence was found in the 24-hour health probe window.

Conclusion: the crash path is virtual-memory/commit pressure plus Streamlabs scene/encoder pressure. GPU instability is not the leading cause for this incident.

## Streamlabs Risk Surface

Current safe config flags are still present on disk:

- `BrowserHWAccel=false`
- `fileCaching=false`
- `ForceGPUAsRenderDevice=false`
- `streamEncoder.json` has `lookahead=false`, `adaptive_quantization=false`, and `bf=0`

Runtime OBS still used heavier NVENC settings:

- `b-frames: 2`
- `lookahead: true`
- `aq: true`

This means Streamlabs is not fully honoring the patched `streamEncoder.json` for the actual `video-encoder-streaming-horizontal` runtime path, or a secondary/cloud/profile state is overriding it.

Scene risk remains high:

- Active scene collection: `C:\Users\speci.000\AppData\Roaming\slobs-client\SceneCollections\4c516060-fc41-4fb9-a715-079742e315be.json`
- About `451` browser-source mentions.
- About `95` FFmpeg-source mentions.
- `1` empty URL mention remains.
- Large looping media includes a roughly `648 MB` intro video plus several 20-75 MB media sources.

## Antigravity / Gemini Background Work Status

The background work is producing useful research artifacts, but it was unsafe to run unrestricted on the same workstation during streaming.

Observed state:

- `D:\Ollama_Backup\autonomous_jailbreaks.jsonl` had `1097` parsed records at the latest check time.
- Bypasses: `204`.
- Overall bypass rate: `18.60%`.
- Highest bypass-rate tactics in the parsed log were `entanglement` and `pattern_mirror`.
- `models/qwen2.5-1.5b-ties-merge-v3.yml` and `models/qwen2.5-1.5b-slerp-merge-v3.yml` were written at `2026-05-26 16:00:05`, about three minutes before the Streamlabs crash.
- `datasets/ernie/live_guard_plane_test_results.json` from `2026-05-26 06:25:03` shows the benign-query phase failed because several benign queries degraded into timeout fallback.
- Follow-up at `2026-05-26 16:22:00` showed the already-running chaos task was still writing iteration `1097` while the protected-workload gate reported `should_pause=true`. Those tail records did not include the new `consecutive_ollama_failures` field, so the running task had not picked up the patched script yet.

Interpretation:

- The chaos generator is generating valuable evidence.
- Ollama/Guard Plane timeout behavior is polluting some result quality and should be treated as a workload-health signal, not only a model-safety signal.
- Merge recipe updates should not run during OBS/Streamlabs sessions or immediately after a crash.
- Existing long-running background jobs must be restarted after this patch; otherwise, they keep using the old unsafe pacing and no-gate behavior.

## Changes Applied

Repo-only changes were made to protect future runs:

- Added `scripts/protected_workload_gate.py`.
- Updated `scripts/autonomous_chaos_generator.py` to pause when Streamlabs/OBS protected processes are active or when a recent Streamlabs crash is detected.
- Updated `scripts/autonomous_chaos_generator.py` to slow default pacing from burst-heavy `0.5s` to configurable `2.0s` and back off after consecutive Ollama failures.
- Updated `scripts/dynamic_merge_optimizer.py` to skip recipe writes while the protected-workload gate is active.
- Updated `scripts/streamlabs_health_probe.ps1` to analyze the real scene collection instead of accidentally selecting `manifest.json`.

Verification:

- `python -m py_compile scripts\protected_workload_gate.py scripts\autonomous_chaos_generator.py scripts\dynamic_merge_optimizer.py` passed.
- `python scripts\protected_workload_gate.py` returned `should_pause=true` with reason `recent_streamlabs_crash_20m`.
- `python scripts\dynamic_merge_optimizer.py` skipped recipe writes while the recent-crash gate was active.
- `powershell -ExecutionPolicy Bypass -File scripts\streamlabs_health_probe.ps1 -SinceHours 24` completed and reported the actual scene collection.
- `pytest tests/ -v --tb=short` reached collection but stopped on existing repo debt: `ModuleNotFoundError: No module named 'nexus_os.security.contamination_detector'` in `tests/security/test_contamination_detector.py`.

## Recommended Operator Actions

1. Do not run Streamlabs with unrestricted Devin, large `git.exe`, WSL, Ollama chaos loops, or model merge work in parallel.
2. Restart any already-running Antigravity chaos task so it picks up the new protected-workload gate.
3. Before the next Streamlabs session, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\streamlabs_health_probe.ps1 -SinceHours 24
python scripts\protected_workload_gate.py
```

4. In Streamlabs UI, verify the actual streaming encoder profile, not only `streamEncoder.json`: disable lookahead, disable adaptive quantization/psycho-visual tuning, set B-frames to `0`, keep 720p30, and prefer low-latency preset.
5. Create a lean Streamlabs scene profile for long local-agent work: reduce duplicate browser sources, remove the empty URL source, and compress or replace the 648 MB looping intro media.
6. Treat `Resource-Exhaustion-Detector` Event ID `2004` as the primary early warning. If commit usage is above 80%, do not start Streamlabs streaming/recording.

## Current Risk

The workstation is still memory-pressure sensitive. The immediate crash reason is understood, and NEXUS background scripts now have a guard, but Streamlabs can still crash if external tools such as Devin, Git, WSL, browser stacks, or already-running old Antigravity jobs consume commit memory outside the new gate.
