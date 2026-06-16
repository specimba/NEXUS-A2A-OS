---
id: NODE-MIG-STREAMLABS_OBS_HEALTH_INVESTIGATION_2026_05_23
authority_scope: experimental
origin_sha256: 82e934ab199bb9f0e34bde965dded0c7e8534d77070e8d4ac6c3c87f85a88c51
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-8C5985
---
# Streamlabs OBS Health Investigation - 2026-05-23

## Scope

<!-- CANARY: acbac27de9dc87b93fa1d75d1648d866 -->
Local investigation of Streamlabs Desktop / Streamlabs OBS launch hangs, memory spikes, and crash behavior without rebooting the workstation.

## Evidence Summary

- Streamlabs spawned multiple `Streamlabs OBS` child processes during the stuck launch window.
- `crash-handler.log` reports a critical crash in:
  `C:\Program Files\Streamlabs OBS\resources\app.asar.unpacked\node_modules\obs-studio-node\obs.dll`
- Crash handler observed process RAM at about 3.56 GB before failing to save a memory dump.
- Latest OBS backend log ends with:
  `Failed while trying to allocate 1382400 bytes, errno 12`
- The crash stack goes through OBS video frame allocation / source frame copy / ffmpeg unload paths.

## GPU / Driver Evidence

Windows logs show this is not only a Streamlabs UI issue:

- `nvlddmkm` Event ID 153 bursts on 2026-05-22.
- LiveKernelEvent 141 references `nvlddmkm.sys_Ada`.
- DWM crashed on 2026-05-22 with `dwm.exe` / `dwmcore.dll`.
- WHEA-Logger Event ID 17 corrected PCIe hardware errors reference NVIDIA device paths.

Interpretation: Streamlabs is likely triggering an already unstable GPU / DWM / NVIDIA driver path through Electron, CEF browser sources, OBS rendering, and NVENC.

## Scene / Cache Evidence

Active scene collection:

`C:\Users\speci.000\AppData\Roaming\slobs-client\SceneCollections\4c516060-fc41-4fb9-a715-079742e315be.json`

Observed scene size and source profile:

- Scene JSON: 1.44 MB
- Media folder: 911.72 MB
- Browser source mentions: 43
- FFmpeg source mentions: 15
- Local file references: 16
- Empty URL references: 1

Missing local references:

- `C:\Users\speci\AppData\Roaming\slobs-client\Media\33120523-Main logo int.mp4`
- `C:\Users\speci\AppData\Roaming\slobs-client\Media\47161136-Render 1080 yayin basliyor.mp4`
- `D:\Download\stream\widgetfx.html`

The missing `widgetfx.html` source also has `url: ""`, matching Streamlabs log noise:

`ERR_INVALID_URL (-300) loading ''`

Cache footprint:

- `slobs-client\Cache`: 7.33 MB
- `slobs-client\GPUCache`: 10.82 MB
- `slobs-client\DawnCache`: 0.53 MB
- `plugin_config\obs-browser\Cache`: 81.49 MB
- `plugin_config\obs-browser\Code Cache`: 294.15 MB

## Current Config Notes

`global.ini`:

- `BrowserHWAccel=true`
- `fileCaching=true`
- `ProcessPriority=Normal`

`basic.ini`:

- `ForceGPUAsRenderDevice=true`
- Stream encoder: `obs_nvenc_h264_tex`
- Output: 1280x720 30 FPS

`streamEncoder.json`:

- NVENC CBR 2800
- `lookahead=false`
- `adaptive_quantization=true`
- `bf=2`

## Working Diagnosis

The failure is a compound issue:

1. GPU / PCIe / NVIDIA driver instability is present at the OS level.
2. Streamlabs uses Electron / CEF browser acceleration and OBS GPU rendering, which stresses that path.
3. The scene collection contains broken local file references and one empty local browser URL.
4. OBS backend crashes during video frame/source handling, not during a simple login screen only.
5. Streamlabs network / schema / media-backup fetch failures add UI startup stalls.

## Safe Fix Plan

No reboot required for the first pass.

1. Close Streamlabs only, not the workstation.
2. Back up Streamlabs config and recent logs into `backups/streamlabs-obs-*`.
3. Disable Streamlabs browser hardware acceleration and forced GPU render-device mode.
4. Reduce NVENC extras by disabling adaptive quantization and B-frames.
5. Rename caches instead of deleting them.
6. Reopen Streamlabs and test with the same scene.
7. If still unstable, create a duplicate lightweight scene collection and remove or disable the three missing sources.

## Follow-Up Sample After UI Opened

At 2026-05-23 15:28 local time, Streamlabs was open and visible.

Process sample:

- Largest Streamlabs child process: about 349.8 MB working set / 396.3 MB private memory.
- Aggregate process set was not at the earlier crash-handler peak.
- GPU sample: RTX 4070 Laptop GPU, driver 596.49, 63 C, 16% utilization, 3756 MiB / 8188 MiB VRAM used, P0.

No new `nvlddmkm`, WHEA, Display, DWM, Application Error, or Windows Error Reporting event was observed in the 15-minute window around the follow-up sample.

However, the app is still not fully clean:

- `crash-handler.log` registered a critical process around 15:25:58 and requested a memory dump.
- `app.log` still shows `TypeError: Failed to fetch` in login/schema loading paths.
- `app.log` still shows repeated media-backup download failures.

Interpretation: the visible UI is open, but the Streamlabs backend remains fragile. Do not treat this as fixed until it survives a scene switch and short recording test without new crash-handler entries.

## Repair Applied

At 2026-05-23 15:35 local time, `scripts/streamlabs_safe_repair.ps1 -Apply -ResetCaches` completed successfully after Streamlabs exited.

Backup root:

`C:\Users\speci.000\Documents\NEXUS\backups\streamlabs-obs-20260523-153525`

Applied changes:

- `global.ini`: `BrowserHWAccel=false`
- `global.ini`: `fileCaching=false`
- `basic.ini`: `ForceGPUAsRenderDevice=false`
- `streamEncoder.json`: `lookahead=false`
- `streamEncoder.json`: `adaptive_quantization=false`
- `streamEncoder.json`: `bf=0`
- Renamed Streamlabs root cache directories with `.bak-20260523-153525`
- Renamed obs-browser cache directories with `.bak-20260523-153525`

No scene collection or media asset was deleted.

Next validation:

1. Start Streamlabs.
2. Wait for the UI to settle.
3. Verify it creates fresh cache directories.
4. Run a 60-second local recording test.
5. Check `crash-handler.log`, latest `node-obs\logs\*.txt`, and recent Windows Application/System events.

## Clean Baseline Saved

At 2026-05-23 15:45 local time, after operator scene changes and a successful 5-minute local recording test, the current Streamlabs config was saved as a NEXUS clean baseline:

`C:\Users\speci.000\Documents\NEXUS\backups\streamlabs-clean-base\20260523-1545-streamlabs-clean-base`

Included:

- `basic.ini`
- `global.ini`
- `streamEncoder.json`
- `recordEncoder.json`
- active scene collection JSON
- scene collection `manifest.json`
- `BASELINE_METADATA.json`

Excluded:

- `Media\` folder, because it is about 911.72 MB and already remains in the Streamlabs profile.
- Raw app/crash logs, because they can contain account-adjacent local state.

Live-go validation sample:

- GPU: RTX 4070 Laptop GPU, driver 596.49, 59 C, 18% utilization, 3995 MiB / 8188 MiB VRAM used, P0.
- No recent System `nvlddmkm`, WHEA, or Display events in the final pre-live window.
- No recent Application Error / Windows Error Reporting event in the final pre-live window.
- Latest OBS recording evidence: `10620` total frames output, `3` lagged frames, recording output stopped cleanly.

Residual warnings:

- Browser sources still log third-party widget warnings from Streamlabs/Twitch/aggr.trade/SayItLive sources.
- `crash-handler.log` still registered a critical child process at startup around 15:36:57, but the recording test completed successfully afterward.
- Treat this as the current stable operational baseline, not proof that Streamlabs vendor internals are clean.

## Guardrails

- Do not delete scene collections.
- Do not delete media assets.
- Do not rotate GPU drivers mid-evaluation unless operator approves downtime.
- Do not reboot unless the local training/evaluation queue is released.
