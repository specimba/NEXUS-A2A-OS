---
id: NODE-MIG-STREAMLABS_OBS_CRASH_FOLLOWUP_2026_05_25
authority_scope: experimental
origin_sha256: 1c3daca63b139fb2a9238ea80746b22565d192d6c3168c76c34660df8e9c496f
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-989CF6
---
# Streamlabs OBS Crash Follow-Up - 2026-05-25

## Scope

<!-- CANARY: 56a8f60baddacaf281784aa7a482a187 -->
Follow-up investigation of the latest Streamlabs OBS crash after the 2026-05-23 safe repair and clean baseline.

This pass was read-only against Streamlabs AppData. No Streamlabs config, scene collection, cache, media, driver, or Windows setting was changed.

## Short Verdict

The latest crash was primarily a low virtual-memory / commit-exhaustion failure path involving Streamlabs OBS backend memory growth, not a fresh NVIDIA driver reset.

The old GPU/driver risk is still real historically, but the current crash has stronger evidence for memory exhaustion:

- Windows Error Reporting logged `obs64.exe` crash at `2026-05-25 21:56:10`.
- Faulting module: `ucrtbase.dll`.
- Exception code: `0xc0000409`.
- WER event name: `BEX64`.
- Streamlabs crash handler watched critical PID `48884` die at `2026-05-25 21:55:42`.
- OBS backend log immediately before the crash reports repeated allocation failures with `errno 12`.
- Windows Resource Exhaustion Detector logged low virtual memory events at the same minute.

## Key Evidence

### 1. Windows Application Crash

Application log, `2026-05-25 21:56:10`:

```text
Faulting application name: obs64.exe
Faulting module name: ucrtbase.dll
Exception code: 0xc0000409
Faulting application path:
C:\Program Files\Streamlabs OBS\resources\app.asar.unpacked\node_modules\obs-studio-node\obs64.exe
```

WER, `2026-05-25 21:56:28`:

```text
Event Name: BEX64
P1: obs64.exe
P4: ucrtbase.dll
P8: c0000409
```

The WER archive directory was not readable from this session even after an escalated read attempt, so the event log is the highest-fidelity available Windows crash evidence.

### 2. Streamlabs Crash Handler

`C:\Users\speci.000\AppData\Roaming\slobs-client\crash-handler.log`:

```text
20260525:215542.979: process.pid: 48884
20260525:215542.979: process.isCritical: 1
20260525:215543.105: Handling crash
20260525:224006.338: Failed to save memory dump. err code = 2147942699
```

The same PID appears in the Windows crash as `0xBEF4`.

### 3. OBS Backend Allocation Failures

Latest OBS backend log:

`C:\Users\speci.000\AppData\Roaming\slobs-client\node-obs\logs\2026-05-24 07-08-50.txt`

Important tail region:

```text
Source ffmpeg_source_3eff9dda-5ea4-4d44-b178-110d38ebb0c6 audio is lagging...
Failed while trying to allocate 1843200 bytes, errno 12
Failed while trying to allocate 1365120 bytes, errno 12
Failed while trying to allocate 1373568 bytes, errno 12
ST: unknown function obs64
```

`errno 12` is the important signal here: OBS could not allocate small buffers. That points to exhausted process/system commit, fragmentation, or a runaway memory path rather than a normal CPU/GPU performance dip.

### 4. Resource Exhaustion Detector

System log, `Microsoft-Windows-Resource-Exhaustion-Detector` event `2004`:

```text
2026-05-25 21:54:16
devin.exe consumed 28.84 GB
Streamlabs OBS.exe consumed 7.60 GB
obs64.exe consumed 6.50 GB

2026-05-25 21:55:41
devin.exe consumed 28.87 GB
obs64.exe consumed 20.89 GB
Streamlabs OBS.exe consumed 7.60 GB

2026-05-25 21:56:13
obs64.exe consumed 29.18 GB
devin.exe consumed 28.88 GB
vmmemWSL consumed 5.62 GB
```

This is the root-cause anchor: `obs64.exe` grew rapidly from about 6.5 GB to about 29.2 GB while the system was already under heavy commit pressure from `devin.exe`.

### 5. Current Host Memory Pressure

After the crash, the host was still close to the commit ceiling:

```text
Committed bytes: about 115.8 GB
Commit limit: about 127.7 GB
Commit usage: about 90.7%
Available memory: about 3.8 GB
```

Top current private-memory consumers included:

```text
devin.exe     about 29.47 GB
vmmemWSL      about 5.24 GB
ollama.exe    about 4.20 GB
ollama.exe    about 4.18 GB
opencode      about 1.79 GB
python        about 1.61 GB
```

Starting Streamlabs in this state is unsafe for local stability.

### 6. GPU/WHEA Delta

The last 24-hour event check found:

```text
Application Streamlabs crash count: 2
Resource exhaustion count: 10
GPU/WHEA count: 0
```

That does not erase the older NVIDIA/WHEA problem, but it means the latest crash should not be attributed first to a fresh `nvlddmkm` reset.

## Streamlabs Config State

The 2026-05-23 safe repair settings are still present:

```text
global.ini:
BrowserHWAccel=false
fileCaching=false

basic.ini:
ForceGPUAsRenderDevice=false

streamEncoder.json:
lookahead=false
adaptive_quantization=false
bf=0
```

However, the runtime OBS log still initialized a horizontal streaming encoder with heavier settings:

```text
video-encoder-streaming-horizontal
preset: p5
tuning: hq
profile: high
b-frames: 2
lookahead: true (8 frames)
aq: true
```

Interpretation: Streamlabs is likely using a separate dual-output/horizontal encoder profile, cloud profile, or internal runtime setting not fully controlled by the simple `streamEncoder.json` file.

This means the earlier repair reduced risk but did not fully neutralize every Streamlabs encoder path.

## Scene Risk

Active scene collection:

```text
C:\Users\speci.000\AppData\Roaming\slobs-client\SceneCollections\4c516060-fc41-4fb9-a715-079742e315be.json
```

Current scene profile:

```text
Scene JSON size: about 1.48 MB
Browser sources: 43
FFmpeg sources: 13
Empty URL references: 1
```

The latest OBS warnings point strongly at:

```text
ffmpeg_source_3eff9dda-5ea4-4d44-b178-110d38ebb0c6
name: grokAIvideo2
file: C:\Users\speci.000\Downloads\grokIMAGINEtestv1\grokStylings\grokIMANGINEpart5\grok-video-7fd2ff11-6853-4e51-8165-ca9ce00bca2d (3).mp4
size: about 15.2 MB
caching: true
```

Related high-risk source:

```text
ffmpeg_source_9872a3a9-b0a4-4bda-8139-d3635b9afd74
name: grokAIvideo1
file: C:\Users\speci.000\Downloads\grokIMAGINEtestv1\grokStylings\grokIMANGINEpart5\grok-video-daab09c8-92c0-4563-b7e8-5d3963db4382 (9).mp4
size: about 13.2 MB
caching: true
hw_decode: true
```

The empty local browser source remains:

```text
name: FX
type: browser_source
local_file: D:\Download\stream\widgetfx.html
url: empty
```

This still matches the repeated Streamlabs `ERR_INVALID_URL (-300) loading ''` noise.

## Root-Cause Model

The best current model is:

1. The host was already under high commit pressure from long-running local agent/model workloads, especially `devin.exe`.
2. Streamlabs/OBS started or kept a complex scene with many browser and FFmpeg sources.
3. At least one looping Grok MP4 source accumulated audio buffering and restart churn.
4. OBS backend `obs64.exe` grew rapidly in virtual memory, from about 6.5 GB to about 29.2 GB.
5. Windows reported low virtual memory.
6. OBS began failing small allocations with `errno 12`.
7. `obs64.exe` fail-fast crashed through `ucrtbase.dll` with `0xc0000409`.

## Fix Strategy

### Immediate Safe Rule

Do not start Streamlabs while host commit usage is above 80 percent or while any single non-Streamlabs agent process is holding more than 20 GB private memory.

For the current machine, the blocker is `devin.exe` holding about 29 GB private memory after the crash.

### Low-Disruption Before Next Streamlabs Run

1. Stop or restart the high-memory agent process first, preferably `devin.exe`, before opening Streamlabs.
2. Reduce WSL/Docker/Ollama memory pressure if active local models are not needed for the stream window.
3. Run the new read-only probe:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\streamlabs_health_probe.ps1
```

4. Open Streamlabs only when the probe shows acceptable commit headroom.

### Streamlabs Scene Fixes

These should be done inside the Streamlabs UI first, not by JSON surgery:

1. Duplicate the current scene collection.
2. In the duplicate, disable `grokAIvideo1` and `grokAIvideo2`.
3. Disable or repair the `FX` browser source with the empty URL / missing local file.
4. If the duplicate is stable, re-add Grok video sources one at a time.
5. For Grok video loops, disable media-source caching and hardware decode where the UI exposes those options.
6. Prefer short, pre-transcoded local MP4 assets in the Streamlabs Media folder instead of `Downloads\...` working paths.

### Encoder Fixes

The simple `streamEncoder.json` is already safe, but the runtime log still used heavier horizontal encoder settings. The next pass should find the real source of:

```text
video-encoder-streaming-horizontal
lookahead: true
aq: true
b-frames: 2
```

Until that is found, avoid dual-output/horizontal streaming mode for live sessions if possible, or manually verify in Streamlabs settings that lookahead/AQ/B-frames are disabled for every output lane.

### Host Stability Fixes

If Streamlabs must run alongside agents/models:

1. Increase Windows pagefile/commit limit only as a secondary mitigation. It can reduce crash frequency but will not fix a runaway OBS memory path.
2. Keep NVIDIA driver work parked unless new `nvlddmkm`, Display, LiveKernelEvent, or WHEA events return near crash time.
3. Keep the 2026-05-23 safe config baseline as rollback.
4. Add a pre-live checklist: commit headroom, no runaway agent, no fresh WHEA/nvlddmkm, scene duplicate verified, 5-minute recording test.

## Current Do / Do Not

Do:

- Treat the latest crash as memory/commit exhaustion first.
- Keep Streamlabs closed until `devin.exe` and other large workloads are controlled.
- Use a duplicate scene for Grok video experiments.
- Run a 5-minute recording test after any scene/encoder change.

Do not:

- Reboot or reinstall drivers as the first response to this specific crash.
- Delete scene collections or media assets.
- Edit the active scene JSON directly before making a duplicate/backup.
- Assume `streamEncoder.json` controls every runtime encoder lane.
- Start a live session while commit usage is already near 90 percent.

