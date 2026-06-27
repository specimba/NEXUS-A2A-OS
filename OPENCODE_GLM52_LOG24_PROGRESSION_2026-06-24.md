# NEXUS Project State Update — GLM-5.2 OpenCode Log 24 (2026-06-24→25)
**Source:** `/mnt/c/Users/speci.000/Downloads/NEXUSlogs/NEXUSopencodeMAINbackendGLM52log-24.txt`  
**Agent:** OpenCode + GLM-5.2 backend/main lane  
**Scope:** TWAVE monitoring + hallucination detector + auto-revive 7355 + NEO/HERMES wiring blocker  
**Date:** 2026-06-24/25 (derived from log content + ARCHIVIST 12-gap doc)

---

## What Was Actually Done (Verified from Log-24)

### Completed
- `nexus_os/monitoring/bebop_signal.py` — fixed probability-vector math for `assess_bebop(logits_or_probs)`; smoke tests pass (flat vs flat → TV≈0, peaked vs flat → high_drift, extreme vs uniform → TV≈0.75).
- `nexus_os/monitoring/calibrated_hallucination_detector.py` — wiring extended with `bebop_weight` / `bebop_tau` knobs exposed through `nexus_os/cli/nexusctl.py` subcommands.
- `nexus_os/twave/landau_ginzburg_tracker_v2.py` — `get_report(apply_spectral_bounds=True)` opt-in flag added; spectral stability wrapper applied.
- `nexus_os/twave/spectral_stability.py` — new module; smoke test passes: pre-max 12.7 → post-max 1.24 bounded.
- P2.1 + P2.2 declared clean by log author: spectral stability + bebop signal both executable.
- `nexus_os/gmr/circuit_breaker.py` — persistence default bug fixed (in-progress in log; author later marked fix applied and read-only verification pending).
- `scripts/install_nexus_autostart.ps1` — **created but not confirmed installed**; registers Windows Scheduled Task `NexusServiceAutoRevive` (AtLogon + 10 min); durable auto-revive after restart.
- `scripts/revive_relay_ports.ps1` — exists (log references); likely under `C:\NEXUS\scripts\`.

### In Progress / Half-Done
- P2.3 entropy-thresholded draft switching: `DraftStrategySwitcher` design discussed but **not implemented** (log author paused to keep scope bounded).
- `nexusctl.py` CLI flags for `--bebop-weight` / `--bebop-tau` added on one branch; full subcommand wire-up presumably complete.
- CATEGORIZE_TO_FILETYPE — **explicitly flagged NOT wired** by orchestrator (Kilo log-04). This is a real unfinished task.

### Not Started / Avoided By Author
- P0 detector lift: 20–30% → 80%+ (author noted scaffolding exists but actual detector logic still needs raising).
- Dream Cycle (`nexus_os/vault/dream_cycle.py`) — declared P0 in 12-gap plan; no evidence of work in this log.
- P1 self-correction/reflection-retry loop — no evidence of work.
- Full P0/P1 test verification for every new module — only a subset ran.

---

## Hermes–ModelRelay Wiring Blocker (Restated Precisely)

- Hermes relays via `model.base_url`. Current successful path is Windows Node relay on **7350**.
- After PC restart, 7350/7355/7357 died. WSL Hermes could not revive 7355 because WSL can't execute the Windows `.venv` path `C:\Users\speci.000\Documents\NEXUS\.venv\Scripts\python.exe`.
- `.modelrelay_7357.json` was missing at the time; log indicates it was later created (`06/25`).
- The fix is external durable auto-revive (Windows Scheduled Task) + port-only health checks independent of WSL.
- The `CHIMERA_MODELRELAY_IMPLEMENTATION_PLAN.md` remains partially implemented: ChimeraRouter → RoutingDecision → `model_relay_adapter.py` is the contract; `--execute/--relay-url/--fallback-url` CLI wiring is the residual step.

---

## Updated Port Truth (2026-06-25 WSL check)

| Port | Owner | Live Now | Comment |
|------|-------|----------|---------|
| 7350 | Node ModelRelay | OPEN | Primary relay; `/` returns 200 |
| 7352 | Brain API | CLOSED | Governance only — needs `uvicorn`/FastAPI |
| 7355 | Python ModelRelay | CLOSED | Fallback relay; needs Windows .venv |
| 7356 | static dashboard | OPEN | Serving |
| 7357 | god_mode_proxy | OPEN | Up; config now exists |
| 3001 | Next.js dashboard | CLOSED | Not started |

---

## Actionable Next Steps (From Log-24 Close-Out)

1. **Confirm `install_nexus_autostart.ps1` was actually registered** — `Get-ScheduledTask -TaskName NexusServiceAutoRevive | Get-ScheduledTaskInfo`. If not, run the installer elevated.
2. **Repair `revive_relay_ports.ps1`** — eliminate WSL `.venv` reference; use the actual Windows Python or skip 7355 on boot if Node 7350 + 7357 are sufficient.
3. **Verify Hermes routes through 7350 in one session** — `hermes chat -q 'say ping'` and watch relay logs under `/tmp/modelrelay_7350.log` or the Windows equivalent.
4. **Wire CATEGORIZE_TO_FILETYPE** — the orchestrator left this explicitly unfinished; it means downstream Archivist helpers are still using raw extensions.
5. **P0 detector lift** — go from "mocked" to "read real logit stream" for hallucination and MCP gateway tool poisoning.

---

## Risks / Residual Blockers

- Auto-revive script is Not-Confirmed-Run-in-Production — unverified at next boot.
- 7355 Python relay still second-class citizen because of Windows/WSL execution boundary.
- 12-gap P0 items (MCP gateway, dream consolidation, hallucination detection) remain scaffolding-level.
- Hermes config `model.base_url` not yet aligned to 7350 gateway path; without it, Hermes may bypass ModelRelay entirely.
