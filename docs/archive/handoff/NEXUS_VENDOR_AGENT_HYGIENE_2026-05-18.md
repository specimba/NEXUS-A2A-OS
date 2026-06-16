---
id: NODE-MIG-NEXUS_VENDOR_AGENT_HYGIENE_2026_05_18
authority_scope: experimental
origin_sha256: 7ed3257da61d06401877557ccd010fac748b9c04eb811efebec015fbb11c3ce2
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-AC938E
---
# NEXUS Vendor Agent Hygiene Addendum

Date: 2026-05-18
Host: SPECIMBAPC
Scope: Dell, Alienware, Killer, Phone Link, Xbox/Gaming Services, and user autostart hygiene.

## Executive Verdict

The vendor/background layer is not harmless. In the current local snapshot, Dell/Alienware/Killer/Phone/Xbox/Gaming-related processes accounted for about:

- 31 processes.
- 5231.6 MB working set.
- 2476.9 MB private memory.
- 986.6 seconds cumulative CPU time since boot.

This is a valid optimization track. It should be handled separately from the WHEA/restart root-cause track, but it has direct impact on NEXUS long-running local stability.

## Strongest Local Evidence

Largest current targets:

- `ServiceShell.exe` / Dell Client Management Service: about 1594.5 MB working set.
- `SupportAssistAgent.exe`: about 464.8 MB working set.
- `Dell.TechHub.Instrumentation.SubAgent.exe`: about 321.8 MB working set.
- `AlienFXSubAgent.exe`: about 231.2 MB working set and about 154 CPU seconds.
- `AWCC.SCSubAgent.exe`: about 201.6 MB working set.
- `AWPerformance.SCSubAgent.exe`: about 162.8 MB working set.
- `PhoneExperienceHost.exe`: about 161.5 MB working set.
- `Killer.exe`: observed earlier around 147-156 MB working set and about 487 CPU seconds.
- `DellSupportAssistRemedationService.exe`: about 116.7 MB working set.
- `OCControl.Service.exe`: about 98.6 MB working set.

Running automatic services of interest:

- `Dell Digital Delivery Services`
- `Dell SupportAssist Remediation`
- `DellClientManagementService`
- `DellConnectedServiceDelivery`
- `DellTechHub`
- `FusionService`
- `GamingServices`
- `GamingServicesNet`
- `Killer Analytics Service`
- `Killer Network Service`
- `Killer Provider Data Helper Service`
- `SupportAssistAgent`

Running manual services of interest:

- `KNDBWM`
- `PhoneSvc`
- `XblAuthManager`

User-level autostarts observed:

- BitTorrent Web
- Steam
- RiotClient
- Blitz
- TFTAcademy
- Docker Desktop
- Notion
- ERNIE hidden autostart
- Microsoft Edge auto-launch

Machine-level autostarts observed:

- SteelSeriesGG
- Realtek audio background service
- Windows Security tray

## SupportAssist Risk

This machine has:

- Dell SupportAssist Remediation installed version: `5.5.15.1`.
- Dell SupportAssist OS Recovery Plugin for Dell Update installed version: `5.5.16.1`.
- SARemediation plugin/audit files with product version `5.5.16.1`.
- Application log shows Dell SupportAssist OS Recovery Plugin for Dell Update `5.5.16.1` installed successfully at 2026-05-18 00:39:18 local.
- Dell SupportAssist / Remediation components were reconfigured again around 2026-05-18 02:45 after reboot.

Dell's current advisory specifically names Dell/Alienware SupportAssist Remediation `5.5.16.0` as causing blue screen errors and unexpected restarts, while also saying the Remediation service is independent of the primary SupportAssist app. The local installed Remediation service is not exactly `5.5.16.0`, so the advisory does not prove root cause by itself. It does prove this stack is a high-priority suspect and cleanup target because the installed plugin side is `5.5.16.1` and the install happened near the incident window.

## Fan And Thermal Control Reality

AWCC is the official Dell/Alienware path for Dell G16 7630 fan offset, thermal presets, AlienFX lighting, game library, and overlay features.

However, AWCC is not the only possible control path:

- Dell documents `fn + F9` as Game Shift toggle on the G16 7630.
- `alienfx-tools` provides fan, light, and power profile control for Alienware/Dell G-series systems using Alienware ACPI BIOS calls rather than direct embedded-controller writes. It still requires admin rights for fan control.
- `tcc-g15` provides a Dell G15-focused AWCC alternative with thermal mode switching, fan speed visibility, and semi-manual fan speed control. It also requires admin privileges and warns that BIOS can override unsafe fan settings.

Practical conclusion: do not keep the entire AWCC/Dell stack just because fans exist, but also do not remove AWCC/OCControl until an alternative is tested and temperature/fan behavior is verified under load.

## Cut Tiers

### Tier A: Highest-confidence cuts

These are not required for fan control and are either documented bloat, recovery telemetry, gaming overlay, or optional UX:

- `Dell SupportAssist Remediation`
- Dell SupportAssist OS Recovery Plugin for Dell Update
- `SupportAssistAgent`
- `Dell Digital Delivery Services`
- `DellConnectedServiceDelivery`
- `Killer Analytics Service`
- `Killer Provider Data Helper Service`
- `PhoneSvc` and Phone Link app if unused
- `XblAuthManager`, Xbox app, `GamingServices`, and `GamingServicesNet` if Xbox/Game Pass is unused
- BitTorrent Web autostart
- Blitz autostart
- TFTAcademy autostart
- RiotClient autostart
- Steam autostart
- SteelSeriesGG autostart if not actively needed for device profiles
- Microsoft Edge auto-launch and Startup Boost/background behavior

### Tier B: Cut after network and Dell-update rollback plan

- `Killer Network Service`
- `KNDBWM`
- Intel Killer Control Center app
- `DellClientManagementService` / `ServiceShell.exe`
- `DellTechHub`

Intel's own troubleshooting article says stopping Intel Killer Network Service can improve responsiveness when Killer Control Center causes high CPU. Network driver functionality should be tested after stopping Killer services, and the rollback path must be documented.

`ServiceShell.exe` is currently the largest single target. It is tied to Dell update/client management, not the fan-control path. It should be made manual or removed after confirming an alternate driver/firmware update workflow.

### Tier C: Preserve until fan alternative is proven

- `AWPerformance.*`
- `OCControl.Service.exe`
- AWCC performance subsystem
- `FusionService`
- Intel Dynamic Tuning / platform thermal drivers and services

These are closer to performance presets, thermal modes, power modes, or platform tuning. Replace them only after `alienfx-tools`, `tcc-g15`, BIOS/Game Shift, or another route is validated on this hardware.

### Tier D: Optional after lighting/profile decision

- `AlienFXSubAgent.exe`
- AWCC FX subsystem
- AlienwareArena
- AWCC overlay and game library components

This tier can be removed or disabled if keyboard lighting/profile features are not needed, or if OpenRGB/AlienFX tools cover the needed lighting behavior.

## Recommended Execution Order

1. Create a restore point or at least export the relevant service startup state.
2. Stop and disable only Tier A non-thermal services and autostarts.
3. Reboot.
4. Measure memory, CPU, WHEA deltas, and fan behavior.
5. Stop Killer services as a separate test, then verify network latency, throughput, and stability.
6. Test `fn + F9` Game Shift, AWCC custom thermal offset, and one lightweight fan-control alternative.
7. Only then decide whether to remove AWCC performance/OCControl components.

## References Checked

- Dell SupportAssist Remediation blue screen/restart advisory: https://www.dell.com/support/kbdoc/en-ng/000464214/dell-supportassist-remediation-and-alienware-supportassist-remediation-version-5-5-16-0-causes-blue-screen-errors-and-restarts?lang=en
- Intel Killer Control Center slow performance guidance: https://www.intel.com/content/www/us/en/support/articles/000058995/ethernet-products/intel-killer-ethernet-products.html
- Dell AWCC fan speed offset article for Dell G16 7630: https://www.dell.com/support/kbdoc/en-us/000221917/fan-speed-offset-configuration-on-performance-page-in-alienware-command-center
- Dell AWCC 6.x guide: https://www.dell.com/support/manuals/en-us/alienware-command-center/awcc_ug_6.x/introduction
- Dell G16 7630 keyboard shortcuts / Game Shift: https://www.dell.com/support/manuals/en-us/g-series-16-7630-laptop/dell-g16-7630-owners-manual/keyboard-shortcuts
- AlienFX Tools: https://github.com/T-Troll/alienfx-tools
- TCC-G15: https://github.com/AlexIII/tcc-g15
- Microsoft Windows performance guidance for startup/background apps: https://support.microsoft.com/en-us/windows/tips-to-improve-pc-performance-in-windows-b3b3ef5b-5953-fb6a-2528-4bbed82fba96
- Microsoft Edge auto-start guidance: https://support.microsoft.com/en-us/microsoft-edge/stop-microsoft-edge-from-starting-automatically-c341c879-799a-dccd-d6be-bc51ecdd5804

## Not Executed Yet

No services were stopped or disabled in this addendum pass. This file is a cut plan and evidence ledger for the next controlled execution pass.

## Nexus Diagnostic Workflow Update

Vendor-agent cleanup should be represented in Nexus diagnostics as a report-only track, separate from crash root-cause work. The workflow is now captured in `docs/handbook/03_NEXUSCTL_GUIDE.md`, with follow-up tracked by `tasks/pending/2026-05-18-009-diagnostic-doctor-workflow-reconciliation.task.md`.

Important boundary: do not let a future `doctor` command stop, disable, uninstall, or kill Dell/Alienware/Killer/Phone/Xbox/Gaming components automatically. It should report candidates, risk labels, protected thermal components, and rollback requirements.
