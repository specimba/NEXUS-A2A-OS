# Proposal: report-only desktop/input diagnostic for `nexusctl`

**Status:** proposed; not implemented  
**Incident evidence:** `logs/workstation-diagnostics-2026-07-14_mouse-flicker.json` (ignored local artifact)  
**Scope:** Windows desktop pointer flicker, display instability, GPU/PCIe telemetry, and resource-pressure diagnosis.

## Why this exists

The 2026-07-14 investigation found a live hybrid-GPU workstation with healthy present input devices, but repeated corrected PCIe/WHEA events on the active discrete-GPU path, historical GPU-driver errors, high paging, and concurrent compositor/capture GPU load. Existing NEXUS doctors do not provide a safe, repeatable way to collect or classify that evidence.

This proposal deliberately separates **diagnosis** from **remediation**. It must never silently restart a driver, stop an application, modify a device, change power policy, install a driver, or reboot the host.

## Proposed interface

```text
python -m nexusctl doctor desktop --report-only --json
python -m nexusctl doctor desktop --report-only --json --out logs/workstation-diagnostics/<run-id>.json
```

The implementation belongs only in the active `nexusctl` package, not the legacy `nexus_os.cli.nexusctl` entrypoint.

## Required report contract

```json
{
  "schema_version": "nexus.desktop_diagnostic.v1",
  "status": "ok|degraded|unsupported|unavailable",
  "mode": "read_only",
  "mutations": [],
  "probe_errors": [],
  "evidence": {},
  "hypotheses": [],
  "advisories": []
}
```

The collector may gather only bounded, read-only data:

- present mouse, HID, USB, and Bluetooth status;
- video-controller and display topology data;
- bounded System/Application event metadata for display, GPU driver, DWM, PnP, HID/USB, WHEA, Kernel-Power, and EventLog;
- DWM presence plus RAM, paging, and GPU pressure samples;
- explicit probe failures.

It must not inspect browser profiles, sessions, cookies, history, credentials, private files, or raw event data outside the bounded categories.

## Advisory protocol

The command may emit only approval-bound advice. Each advisory must state risk, rollback, validation, and `approval_required: true`.

1. Classify current attached input devices before treating historical PnP entries as faults.
2. If GPU/PCIe events or compositor pressure exist, recommend a user-visible graphics-stack reset before a reboot.
3. Recommend a controlled A/B test of capture/overlay workloads, never an automatic process stop.
4. Recommend a direct USB-port test only when the symptom tracks the physical mouse.
5. Escalate to vendor-supported graphics/chipset/firmware maintenance only when a repeated event pattern survives the live tests.

## Evidence artifact rules

`--out` is opt-in only. It must:

- accept a new path only under `logs/workstation-diagnostics/`;
- reject traversal, source/docs paths, and existing files;
- write sanitized JSON atomically;
- return its SHA-256;
- create no worklog, canonical-document update, memory entry, proposal promotion, or automatic remediation.

## Acceptance tests

- `tests/nexusctl/test_desktop_doctor_cli.py`
  - schema-versioned JSON, zero default writes, strict read-only probe allowlist;
  - probe denial degrades gracefully;
  - no browser-private-state access or sensitive-path leakage;
  - non-Windows returns `unsupported` without probing;
  - generic doctor memory/version paths are not called.
- `tests/monitoring/test_desktop_diagnostics.py`
  - pure classifier behavior for no findings, GPU-display fault evidence, PnP evidence, and mixed-refresh evidence;
  - hypotheses remain hypotheses rather than asserted root causes.
- `tests/nexusctl/test_cli_console_encoding.py`
  - `python -m nexusctl --help` exits successfully under forced CP1252 output.

## Implementation gates

1. Work on a clean, proposal-linked branch: `nexusctl/cli.py` is already locally modified by unrelated work in the current checkout.
2. Repair the active CLI's CP1252 help-output failure before exposing a new public command.
3. Bypass the unrelated, fragile generic doctor path; do not widen this slice to repair it.
4. Run the focused tests above, then relevant existing CLI/grounding tests.
5. Attach the sanitized incident artifact and review the diff before any promotion to a handbook protocol.

## Maintenance escalation rule

Repeated corrected PCIe/GPU events plus GPU-driver errors are **high priority**, but not automatically an emergency. A controlled vendor-supported update/reboot is appropriate only after fresh pre-change evidence is captured and the approval-bound no-reboot tests do not stabilize the system.
