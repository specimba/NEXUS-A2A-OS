---
id: NODE-MIG-NEXUS_LOCAL_RESTART_RECOVERY_2026_05_18
authority_scope: experimental
origin_sha256: 3e382425fc14945c5b8ad4e87a2b4d4507b5c4533c0cd5e806f0b678f0968344
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-54DAB0
---
# NEXUS Local Restart Recovery Handoff

Date: 2026-05-18
Host: SPECIMBAPC
Scope: sudden restart, workstation stability, local performance recovery, and safe background cleanup planning.

## Executive Verdict

The latest sudden restart is not proven to be high-load RAM exhaustion. The strongest current evidence points to an abrupt no-dump restart class with hardware/driver/firmware involvement:

- `Kernel-Power` Event 41 at 2026-05-18 02:08:39 local.
- Event 6008 reports the previous shutdown at 2026-05-18 01:07:16 local was unexpected.
- Latest Event 41 payload observed in this session: `BugcheckCode=0`, `SleepInProgress=0`, `PowerButtonTimestamp=0`, `ConnectedStandbyInProgress=false`, `LongPowerButtonPressDetected=false`, `WHEABootErrorCount=0`.
- WHEA entries near the reboot window show corrected PCIe errors on the NVIDIA endpoint and corrected CPU internal parity errors.

Treat this as a stability incident, not just a process hog incident. The older Streamlabs/OBS memory-pressure issue is still real, but it is a separate failure class.

## Evidence Sources Read

- `C:\Users\speci.000\Downloads\codexCUTTEDoptimizationwork-01.txt`
- Windows System and Application event logs.
- `powercfg` active-plan inspection.
- Process, startup, and service inventory.
- NVIDIA device mapping through signed driver inventory.
- Prior local resource reports under `C:\tmp\nexus-resource-guard\`.
- Official Microsoft Event 41 and bugcheck/WHEA documentation.
- Official NVIDIA and Dell support pages checked during the session.

## External References Checked

- Microsoft Event ID 41 troubleshooting: https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/event-id-41-restart
- Microsoft Bug Check 0xA reference: https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0xa--irql-not-less-or-equal
- Microsoft WHEA introduction: https://learn.microsoft.com/en-us/windows-hardware/drivers/whea/introduction-to-the-windows-hardware-error-architecture
- Microsoft WHEA hardware errors and error sources: https://learn.microsoft.com/en-us/windows-hardware/drivers/whea/hardware-errors-and-error-sources
- NVIDIA official driver search result for 596.49: https://www.nvidia.com/Download/processFind.aspx?ctk=0&dtcid=1&lang=en-us&lid=1&osid=135&pfid=985&psid=120&qnfslb=00
- Dell G15 5530 and G16 7630 BIOS 1.31.0: https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=x1t9x

## Repair Applied

Applied one bounded, reversible power-policy repair:

- Active plan: `My Custom Plan 1`
- Setting changed: PCI Express Link State Power Management / ASPM
- Previous observed values: AC `Moderate power savings`, DC `Maximum power savings`
- New verified values: AC `Off`, DC `Off`
- Command class used: `powercfg`

Reason: WHEA Event 17 repeatedly reports PCIe Advanced Error Reporting on the NVIDIA endpoint. Disabling PCIe link-state power saving is a targeted stability move that does not kill any user workload.

No browser tabs, OBS/Streamlabs, devin, Docker, active Codex agents, AWCC fan controls, or thermal-management services were killed.

## Crash Timeline

### 2026-05-18 incident

- 01:07:16 local: previous shutdown time later reported as unexpected.
- 01:52:51 and 01:56:30 local: WHEA Event 19, Processor Core, Corrected Machine Check, Internal parity error, APIC ID 41.
- 02:08:34 local: OS boot.
- 02:08:39 local: Kernel-Power Event 41.
- 02:08:58 local: Event 6008 unexpected shutdown record.
- 02:08:59 local: three WHEA Event 17 PCIe corrected errors on `PCI\VEN_10DE&DEV_2860&SUBSYS_0BF91028&REV_A1`.

Interpretation: latest restart looks like hard hang, hard reset, firmware reset, power path interruption, or driver/firmware failure without a Windows bugcheck. It does not resemble a normal BSOD because no bugcheck code was written.

### 2026-05-04 incident

- Kernel-Power Event 41 with `BugcheckCode=10` / `0xA`.
- `ConnectedStandbyInProgress=true`.
- WER indicated bugcheck `0x0000000a`.
- Minidump exists at `C:\Windows\Minidump\050426-23750-01.dmp`.

Interpretation: this is a different class from the 2026-05-18 no-dump restart. It likely involves a driver/IRQL path during or around Modern Standby. Direct dump analysis was blocked by access control in this session.

### Prior Streamlabs/OBS issue from uploaded optimization bundle

The uploaded prior work showed Streamlabs/OBS crashes around memory and scene pressure:

- `obs-ffmpeg`, `video_frame_init`, and allocation failures.
- System commit around 95 percent in prior report.
- Heavy scene collection: many browser sources, window captures, media files, URLs, and missing references.

Interpretation: still important for streaming stability, but do not collapse it into the latest Event 41 root cause.

## WHEA Findings

Last 21 days WHEA count from this session:

- Event 17: 283
- Event 19: 22
- Event 2: 1

Most important recent payloads:

- Event 17: `PCI Express Legacy Endpoint`, `Advanced Error Reporting (PCI Express)`, primary device `PCI\VEN_10DE&DEV_2860&SUBSYS_0BF91028&REV_A1`.
- Event 19: `Processor Core`, `Corrected Machine Check`, `Internal parity error`, APIC IDs 40 and 41.

Device mapping:

- `PCI\VEN_10DE&DEV_2860&SUBSYS_0BF91028&REV_A1` maps to NVIDIA GeForce RTX 4070 Laptop GPU.
- Observed NVIDIA display driver branch: `596.49` / `32.0.15.9649`.
- Observed machine: Dell G16 7630.
- Observed BIOS: `1.31.0`.

## Current Post-Reboot Pressure

The machine was not in the same memory-pressure state as the prior May 10 report. Current top user-space groups were moderate:

- Chrome around 5 GB working set.
- ERNIE around 1.4 GB.
- Notion, zo, Codex, and Slack around 0.8-1.1 GB each.
- Dell SupportAssist, Dell TechHub subagents, AlienFX, AWCC, and Killer services were visible but not the largest memory owners.
- No current `vmmemWSL` spike was observed in this fresh state.

This means cleanup is still useful for long-running NEXUS health, but it is not enough by itself to explain the latest abrupt restart.

## Hogger Cleanup Tiers

Tier 0 protected by default:

- Browsers and browser tabs.
- OBS/Streamlabs.
- devin.
- Docker.
- Active Codex, ERNIE, zo, and agent shells unless a mission owner explicitly releases them.
- AWCC, AlienFX, Intel DTT, and fan/thermal controls until fan behavior is verified.

Tier 1 safe review candidates:

- BitTorrent Web.
- Blitz.
- TFTAcademy.
- RiotClient.
- Steam.
- SteelSeriesGG.
- Microsoft Edge auto-launch.
- Phone Link.
- Xbox and GamingServices if unused.

Tier 2 Dell/vendor bloat candidates:

- Dell SupportAssist Agent.
- Dell SupportAssist Remediation.
- Dell Digital Delivery.
- Dell Connected Service Delivery.
- Killer Analytics Service.
- Killer Provider Data Helper Service.

Do not remove AWCC/fan/thermal components as part of a generic cleanup. Separate cooling control from Dell update and telemetry services.

Tier 3 NEXUS workload controls:

- ERNIE hidden autostart.
- Duplicate MCP/node workers.
- zo/Notion/Slack background sessions.
- Old opencode/Kiro/agent leftovers if they reappear.

Only trim Tier 3 after confirming no active mission depends on the process.

## Blocked Checks

- Direct `cdb` analysis of `C:\Windows\Minidump\050426-23750-01.dmp` was blocked with `Access is denied`.
- Copying the dump to `C:\tmp` was also blocked with `Access is denied`.
- `powercfg /requests` previously required administrator privileges in this host context.
- `Get-PhysicalDisk` and `Get-Volume` failed because the Storage PowerShell module could not load `Microsoft.Windows.Storage.Core`.
- WMI disk/pagefile queries were access-denied in this session.
- Writing a generated report under `C:\tmp\nexus-resource-guard\` was denied, so this repo handoff is the durable report for CLI agents.

## Task List For CLI Agents

1. Evidence Agent
   - Export System/Application event slices for 2026-05-18 00:30-02:15 local.
   - Export full XML for all WHEA Event 17, 19, and 2 entries in the last 21 days.
   - Acceptance evidence: saved `.evtx` or text exports plus a count table.

2. Dump Agent
   - Run WinDbg/CDB as a real administrator against `C:\Windows\Minidump\050426-23750-01.dmp`.
   - Do not take ownership of the dump directory unless explicitly approved.
   - Acceptance evidence: `!analyze -v` summary, probable module, stack excerpt, and symbol path used.

3. Driver/Firmware Agent
   - Compare installed Dell G16 7630 BIOS, chipset, Intel ME, Intel DTT, NVIDIA platform, and NVIDIA display driver versions against Dell support.
   - Prefer Dell/OEM laptop packages for stability unless a newer NVIDIA Studio/Game Ready driver has a specific fix.
   - Acceptance evidence: installed version table, latest vendor version table, and rollback/update recommendation.

4. WHEA Stability Agent
   - Monitor whether WHEA Event 17/19 continue after ASPM was set to Off.
   - If Event 17 continues on the NVIDIA endpoint, test NVIDIA driver rollback or clean install path.
   - If Event 19 continues on APIC 40/41, run Dell preboot diagnostics and Windows Memory Diagnostic; consider CPU/memory/power delivery escalation.
   - Acceptance evidence: WHEA delta after repair and diagnostic result files/screenshots.

5. Cleanup Agent
   - Propose a reversible startup cleanup for Tier 1 only.
   - Do not kill protected workloads.
   - Acceptance evidence: before/after startup list and rollback commands.

6. Dell Bloat Agent
   - Inventory Dell SupportAssist, Dell Digital Delivery, Dell Connected Service Delivery, and Killer analytics services.
   - Propose stop/disable/uninstall choices with blast radius.
   - Keep AWCC/fan/thermal stack intact until verified.
   - Acceptance evidence: service table, risk labels, and rollback commands.

7. OBS Agent
   - Duplicate current Streamlabs scene collection before edits.
   - Remove missing media/browser sources.
   - Enable close-inactive behavior where available.
   - Create a stable 720p30 NVENC profile for long sessions.
   - Acceptance evidence: scene collection backup path, source count before/after, and test stream/recording result.

8. Capture Agent
   - Verify crash-dump/pagefile settings with administrator rights.
   - Consider setting `AutoReboot=0` only if the operator accepts that future BSODs may stop on the error screen instead of auto-restarting.
   - Acceptance evidence: CrashControl values and a documented operator decision.

## Next Recommended Action

Do not start with mass process killing. First watch whether new WHEA errors appear after the ASPM-off change. If they do, prioritize driver/firmware and hardware diagnostics before bloat cleanup.

Bloat cleanup should still happen, but as a separate controlled pass with browser/OBS/devin/Docker protection.

## Nexus Diagnostic Workflow Update

This incident also exposed a Nexus workflow gap: `AGENTS.md` points agents to `docs/handbook/03_NEXUSCTL_GUIDE.md`, but that guide was absent and the current `nexusctl` package entrypoint is already tracked as broken in `tasks/pending/2026-05-18-006-nexusctl-packaging-cycle-check.task.md`.

Follow-up artifacts now exist:

- `docs/handbook/03_NEXUSCTL_GUIDE.md` defines the honest doctor/emergency workflow while CLI packaging is under repair.
- `tasks/pending/2026-05-18-009-diagnostic-doctor-workflow-reconciliation.task.md` tracks reconciliation of doctor, status, cycle-check, handoff, and workstation emergency checks.

Until `nexusctl` is verified from repo root, agents should use direct evidence checks and must not report synthetic doctor counts.
