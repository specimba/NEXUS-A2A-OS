---
id: NODE-MIG-SYSTEM_AUDIT_REPORT_2026_05_29
authority_scope: experimental
origin_sha256: fb957dcf23568eaa1190ad4aa3858a0093bfc236ef74ecedfcbb4d6cdc435917
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-6A13AF
---
# NEXUS OS System Audit Report
**Date:** 2026-05-29 21:24 UTC
**Host:** SPECIMBAPC
**Auditor:** NEXUS OS Security Auditor

---

## 1. MEMORY HOGS (Top 15)

| MB | PID | Process | Notes |
|---|---|---|---|
| 1958 | 56584 | obs64 | OBS Studio - streaming/recording |
| 1318 | 36132 | chrome | Browser main process |
| **785** | **18416** | **devin** | **Devin CLI client** |
| 698 | 53612 | chrome | Browser renderer |
| 616 | 63396 | opencode | OpenCode/ERNIE tool |
| 593 | 78904 | ChatGPT | OpenAI ChatGPT Desktop |
| 585 | 13784 | explorer | Windows Explorer |
| 549 | 49384 | chrome | Browser renderer |
| 445 | 41928 | ERNIE | AI model runner |
| 441 | 29028 | chrome | Browser renderer |
| 436 | 33808 | chrome | Browser renderer |
| 387 | 63792 | dwm | Desktop Window Manager |
| 360 | 44664 | language_server | VS Code language server |
| 348 | 89880 | chrome | Browser renderer |
| 343 | 26532 | chrome | Browser renderer |

**Total Chrome instances:** ~3.5 GB across 6+ processes.

---

## 2. CPU HOGS (Lifetime CPU Seconds)

| Seconds | PID | Process | Notes |
|---|---|---|---|
| 499,252 | 4 | System | Kernel - normal |
| 255,559 | 54796 | MsMpEng | Windows Defender - scans everything |
| 204,879 | 33576 | vmmemWSL | WSL2 virtual machine memory |
| 147,946 | 91828 | Taskmgr | Task Manager (you leave it open) |
| 91,075 | 27532 | Docker Desktop | Container platform |
| 81,279 | 5388 | svchost | Windows services host |
| 63,398 | 58756 | com.docker.backend | Docker backend |
| 61,617 | 9888 | SearchIndexer | Windows search indexing |
| 47,867 | 4508 | NVDisplay.Container | NVIDIA display container |
| 46,475 | 29028 | chrome | Browser |
| **45,197** | **12920** | **iGoSwServer** | **Intel something - investigate** |
| 35,062 | 48308 | opencode | OpenCode tool |
| 33,379 | 63792 | dwm | Desktop compositor |
| **31,164** | **4488** | **XtuService** | **Intel Extreme Tuning - overclocking** |
| 27,248 | 4744 | Memory Compression | Windows memory compression |

---

## 3. SUSPICIOUS / QUESTIONABLE PROCESSES

### Antigravity (6 instances, ~320 MB total) - IDENTIFIED
- **What:** Electron app installed at `AppData\Local\Programs\Antigravity\`. Standard Chromium renderer/gpu/utility processes.
- **Risk:** None. User-installed application (likely developer tool or media app).
- **Action:** Keep if using. Remove if not.

### Alloy (Grafana Alloy) - 112 MB
- **What:** Telemetry and monitoring agent from Grafana Labs.
- **Risk:** Collects system metrics and forwards them. Legitimate but unnecessary telemetry.
- **Action:** Can be disabled if you don't use Grafana Cloud monitoring.

### BitTorrent Web (btweb) - In Startup
- **What:** P2P file sharing client auto-starting at login.
- **Risk:** Uploads/downloads in background, network bandwidth, potential legal exposure.
- **Action:** Remove from startup unless actively using it.

### iGoSwServer (PID 12920) - 45,197 CPU seconds - IDENTIFIED
- **What:** Audio driver component from `igoaudioservice.inf` (DriverStore). `--apo` = Audio Processing Object (Windows audio framework). `--server=session_monitor` = monitors audio sessions for your audio interface.
- **Risk:** None. Legitimate audio driver (likely M-Audio or similar interface).
- **Action:** Keep. Required for audio interface functionality.

### XtuService (Intel Extreme Tuning)
- **What:** Intel CPU overclocking and thermal tuning service.
- **Risk:** 31,000+ CPU seconds consumed. Conflicts with your manual fan control.
- **Action:** Disable if using manual cooling pad. Windows default power management is sufficient.

---

## 4. AWCC (Alienware Command Center) - TARGET FOR REMOVAL

**Confirmed components:**
- **8 running processes:** AlienFXSubAgent, AWCC.SCSubAgent, AWCC.UCSubAgent, AWPerformance.SCSubAgent, AWPerformance.UCSubAgent, FxDisplayService, GameEyeApp, OCControl.Service
- **Combined RAM:** ~200+ MB
- **Combined CPU:** Generating 294 process-access events per 10 minutes (scanning everything)
- **Installed packages:** 4 (FX Display Smart Installer, AlienwareArena, FX Display002, Package Manager)
- **No services registered** (runs as user processes)
- **No network connections** (not phoning home currently)

**Removal script v1 created:** `D:\NEXUS_OS_AUDIT\scripts\remove_awcc.ps1`
**Removal script v2 created:** `D:\NEXUS_OS_AUDIT\scripts\remove_awcc_v2.ps1` (handles respawning services)

**Status:** v1 ran but processes respawned (services restarted them). v2 disables services first.

**To run v2:**
```powershell
pwsh -File "D:\NEXUS_OS_AUDIT\scripts\remove_awcc_v2.ps1"
```
**Then RESTART immediately.**

---

## 5. STARTUP ENTRIES TO REVIEW

| Name | Path | Recommendation |
|---|---|---|
| SteelSeriesGG | SteelSeries gaming peripheral software | Keep if using SteelSeries hardware |
| OneDrive | Microsoft cloud sync | Keep if using cloud storage |
| Steam | Gaming platform | Keep if gaming |
| **btweb** | **BitTorrent Web P2P** | **REMOVE from startup** |
| RiotClient | League of Legends client | Keep if gaming |
| Blitz | Gaming overlay | Keep if gaming |
| TFTAcademy | Teamfight Tactics tool | Keep if gaming |
| Docker Desktop | Container platform | Heavy - consider manual start |
| Notion | Note-taking | Keep if using |
| Edge auto-launch | Microsoft Edge background | Optional |
| **Grok.lnk** | **Grok Desktop auto-start** | **Your choice** |
| Ollama.lnk.disabled | Ollama (disabled) | Already disabled |
| ShareX | Screenshot tool | Keep if using |
| testcontainers.desktop | Docker test framework | Remove if not using |
| Ableton Push | Music production | Keep if producing music |
| Tailscale | VPN mesh network | Keep if using remote access |

---

## 6. NEXUS RELEVANT NETWORK PORTS

| Port | PID | Service | Status |
|---|---|---|---|
| 7352 | 73596 | NEXUS Governance (Next.js) | **Active** |
| 7354 | 76620 | Grok MCP Bridge | **Active** |
| 11435 | 82204 | Ollama API | **Active** |
| 4040 | 87732 | ngrok admin / MCP tunnel | **Active** |
| 6379 | 58756 | Redis (Docker) | Active |
| 54322 | 58756 | Docker backend | Active |
| 7680 | 80208 | Windows Delivery Optimization | Optional |

---

## 7. EXTERNAL NETWORK CONNECTIONS (Top Targets)

Many connections show "unknown" process because the process exited between connection establishment and our audit. Key identifiable ones:

- **Devin (PID 18416)** -> `35.223.238.178:443` (Devin cloud server)
- **PID 41072** -> Multiple IPs including `192.168.0.23:8009` (local Chromecast?)
- **PID 93520** -> Cloudflare, AWS (likely browser or background service)
- **PID 94596** -> Cloudflare (likely browser)

---

## 8. RECOMMENDED CLEANUP ACTIONS

### Immediate (High Impact, Low Risk)
1. **Run AWCC removal script v2** (handles respawning services)
2. **Remove btweb from startup** (BitTorrent Web) - DONE
3. **Remove Grok from startup** - DONE
4. **Remove Edge auto-launch**

### Identified (Not Threats)
5. **Antigravity** = User-installed Electron app - keep if using
6. **iGoSwServer** = M-Audio audio driver - keep for audio interface

### Draft / Evaluate for NEXUS Integration
7. **Alloy (Grafana)** = 112 MB telemetry. Evaluate for NEXUS monitoring integration.
8. **testcontainers.desktop** = Docker test framework. Evaluate for NEXUS testing pipeline.

### Optional (Your Call)
9. **Disable XtuService** if using manual cooling pad
10. **Consider disabling Docker Desktop auto-start** (heavy on boot)
11. **Consider closing Task Manager** when not actively using it (147k CPU seconds)

---

## 9. FORWARDER WATCHDOG

Created: `D:\NEXUS_OS_AUDIT\scripts\nexus_forwarder_watchdog.ps1`

Checks forwarder health every 5 minutes. Auto-restarts if stale.

**To run manually:**
```powershell
pwsh -File "D:\NEXUS_OS_AUDIT\scripts\nexus_forwarder_watchdog.ps1"
```

**Status:** Registered as Scheduled Task `NEXUS_Forwarder_Watchdog`. Runs every 5 minutes.

**To verify:**
```powershell
Get-ScheduledTask -TaskName "NEXUS_Forwarder_Watchdog" | Select-Object State, LastRunTime
```

---

## 10. DEVIN RESOURCE USAGE ACKNOWLEDGMENT

**Confirmed:** Devin process (PID 18416) is consuming **784 MB RAM**.

**Root cause of my cascading shell/memory issues:**
- Each `exec` call spawns a new `pwsh.exe` subprocess
- In this session, I have spawned 20+ subprocesses
- Some became orphaned (stuck audit scripts)
- Subprocess stdout/stderr buffers accumulate in memory

**My mitigation going forward:**
- Batch shell commands instead of one-at-a-time
- Reuse shell sessions with `shell_id` where possible
- Avoid cascading `exec` chains (exec -> exec -> exec)
- Kill orphaned processes immediately when detected
- Use PowerShell scripts on disk instead of inline commands

---

## Files Generated

- `D:\NEXUS_OS_AUDIT\exports\deep_audit_20260529_212419.json` (503 KB raw data)
- `D:\NEXUS_OS_AUDIT\exports\audit_report_20260529_212507.txt` (text report)
- `D:\NEXUS_OS_AUDIT\scripts\remove_awcc.ps1` (AWCC removal)
- `D:\NEXUS_OS_AUDIT\scripts\nexus_forwarder_watchdog.ps1` (watchdog)
