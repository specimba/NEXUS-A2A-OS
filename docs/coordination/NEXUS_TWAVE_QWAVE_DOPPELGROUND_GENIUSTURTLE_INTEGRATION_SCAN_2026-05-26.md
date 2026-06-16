---
id: NODE-MIG-NEXUS_TWAVE_QWAVE_DOPPELGROUND_GENIUSTURTLE_INTEGRATION_SCAN_2026_05_26
authority_scope: experimental
origin_sha256: 017419762e9a1ae7779aaef90cd8296123a5140fafe5a71135faa97614043245
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-23B85C
---
# NEXUS External Layer Integration Scan - 2026-05-26

## Scope

<!-- CANARY: cd7a9355b1eaee773e8efdc0582746ed -->
Read-only scan for TWAVE, QWAVE, DoppelGround/DoppleGround, and GeniusTurtle assets on the Windows host.

The first blind full `C:\` traversal timed out. The completed scan covered the high-probability project roots:

- `C:\Users\speci.000\Documents`
- `C:\Users\speci.000\Downloads`
- `C:\Users\speci.000\Desktop`
- `C:\Users\speci.000\.codex`
- `C:\Users\speci.000\.agents`
- `C:\tmp`

No files were moved, deleted, staged, or committed.

## Current Canonical Boundary

NEXUS remains the governance and orchestration layer.

| Layer | Current canonical role | Current integration rule |
|---|---|---|
| DoppelGround | Evidence preparation and research-intake layer | USE MODE only; sanitize outputs before handoff; resolve gitleaks before external/public use. |
| TWAVE | Low-VRAM execution / thermodynamic control layer | HOLD for algorithm/runtime redesign; wrapper/API integration only. |
| QWAVE | TWAVE research/evidence workspace | Evidence source only until reviewer gate changes. |
| GeniusTurtle | Operator UI layer | UI/API integration only; no model weights, secrets, or governance internals. |

## High-Signal Folder Inventory

| Area | Path | Evidence |
|---|---|---|
| NEXUS TWAVE current runtime | `C:\Users\speci.000\Documents\NEXUS\nexus_os\twave` | 6 files; latest code timestamp `2026-05-24T09:37:55`; exposes `ChimeraRouterV2`, `QwaveAllocator`, `LandauGinzburgTrackerV2`, EDT/LEAD/EPR/LED/CK-PLUG classes. |
| NEXUS TWAVE src copy | `C:\Users\speci.000\Documents\NEXUS\src\nexus_os\twave` | older parallel copy; layout drift exists, so import precedence must be verified before changes. |
| QWAVE/TWAVE workspace | `C:\Users\speci.000\Documents\QWAVE\twave` | 278 dirs / 687 files; `gitleaks-report.json` is empty; roadmap says v3 contract restored but gate remains HOLD. |
| DoppelGround main | `C:\Users\speci.000\Documents\DoppelGround` | 2076 dirs / 23701 files; `gitleaks-report.json` has 1919 `generic-api-key` findings; this is the largest blocker. |
| DoppelGround freeze | `C:\Users\speci.000\Documents\DoppelGround_m0_freeze_current` | 278 dirs / 2889 files; includes Chimera snapshot and same 1919 gitleaks findings. |
| GeniusTurtle main | `C:\Users\speci.000\Documents\GeniusTurtle` | 922 dirs / 8698 files; `gitleaks-report.json` is empty; latest benchmark/runtime evidence is April 2026. |
| GeniusTurtle newer design | `C:\Users\speci.000\Documents\opusmanSEEKv4\GeniusTurtle\design.md` | latest direct GeniusTurtle planning file, timestamp `2026-05-19T11:25:12`. |
| TWAVE v3 scaffold | `C:\Users\speci.000\Downloads\twave_v3_scaffold_unpacked` | older March v3 research package; useful as research evidence, not gate authority. |
| DoppelGround landing/readme draft | `C:\Users\speci.000\Downloads\DoppelGroundREADMEzohostingLanding.md` | public landing/readme draft, timestamp `2026-05-23T17:17:49`. |

## Latest Planned Version Reading

### TWAVE / QWAVE

Latest usable implementation inside NEXUS is **TWAVE v2.0**:

- `nexus_os/twave/__init__.py` re-exports v2.0 package paths.
- `chimera_router_v2.py` provides tiered routing, model capability flags, temperature policy selection, and ERNIE suggestion hooks.
- `landau_ginzburg_tracker_v2.py` provides EDT, LEAD, EPR, LED, CK-PLUG, and attention-divergence structures.

Latest QWAVE/TWAVE plan is **v3 research evidence under HOLD**, not direct integration approval:

- `QWAVE\twave\ROADMAP.md` says v3 operator contract is restored: `U_k` FP16, `S_k` FP16, quantized `Vt`, sign preconditioning, runtime decode, true packed int3, saved artifacts, and manifest-backed truth-lab runs.
- The `m8` lane is completed, with Qwen 0.5B `chi=32` and `chi=64`, `max_modules=8`.
- `docs\final_verdict_proposals.md` still says `KEEP HOLD`; it explicitly does not approve redesign-prep execution, redesign implementation, new compute, replay, model widening, or fixture widening.
- Immediate next action is artifact/report path re-verification and hold-compatible diagnosis, not redesign.

Integration decision: keep NEXUS on TWAVE v2.0 runtime/wrapper integration now. Treat QWAVE/TWAVE v3 as evidence for a later gated lift package only.

### DoppelGround

Latest current-position doc says DoppelGround is **USE MODE**, not rebuild mode:

- It is a governed research operating surface for messy external inputs.
- It should produce structured evidence, dossiers, repo notes, mission candidates, session summaries, and export packages.
- It is not the swarm OS; NEXUS owns orchestration, routing, trust, execution, and memory.
- A2A/MCP boundaries should stay outside DoppelGround itself.

But the blocker is concrete:

- `DoppelGround\gitleaks-report.json`: 1919 findings, all `generic-api-key`.
- `DoppelGround_m0_freeze_current\gitleaks-report.json`: same count.

Integration decision: do not import raw DoppelGround trees. First create a sanitized evidence-export path into `nexus_knowledge_base/` with hashes, quality labels, and source ranking.

### GeniusTurtle

Latest newer planning file is the `opusmanSEEKv4` design note:

- Operator UI layer for NEXUS OS.
- Terminal-native, keyboard-first, information-dense, real-time.
- Surfaces agent status, trust scores, pipeline state, blocked actions, and governance logs.

Older `Documents\GeniusTurtle` runtime evidence shows GemmaTurtle running via `llama-server.exe` on `127.0.0.1:8080` with a safe desktop E4B Q4 profile. Some benchmark logs show earlier reasoning-only/final-answer capture failures, later corrected in the final-test log.

Integration decision: GeniusTurtle should consume NEXUS APIs only. It should not embed model weights, governance decisions, private research dumps, or TWAVE internals.

## Recommended Integration Sequence

1. Freeze the boundary map in a single integration ledger.
2. Keep TWAVE v2.0 as the active NEXUS runtime surface; add `/twave/*` wrapper smoke tests before any v3 adoption.
3. Treat QWAVE/TWAVE v3 as HOLD evidence; run only re-verification and read-only artifact summaries until the reviewer gate changes.
4. Build DoppelGround sanitized-export intake: source hash, truth layer, confidence, evidence quality, and leak-scan status.
5. Block raw DoppelGround import until the 1919 gitleaks findings are triaged as false positives or removed.
6. Wire GeniusTurtle as a thin operator UI over NEXUS governance/status APIs.
7. Reconcile `01_PROJECT_STATE.md`, `knowledge.md`, and newer handoff reports before calling any version canonical.

## Risk Notes

- `01_PROJECT_STATE.md` still says Guard Plane v1.2.0; a newer untracked handoff report claims v1.4.0 readiness. Treat this as evidence drift until live tests or canonical docs are reconciled.
- NEXUS has both root `nexus_os/` and `src/nexus_os/` layouts. Import precedence matters before modifying TWAVE.
- DoppelGround is useful, but it is currently the dirtiest external layer from a leak-gate perspective.
- QWAVE/TWAVE v3 has promising evidence, but the project docs repeatedly reject direct redesign or kernel/runtime lift right now.

## Actionable Insight

The safest high-value move is not to merge these projects. It is to make NEXUS the governed control plane that can consume them through four narrow contracts: TWAVE wrapper, QWAVE evidence ledger, DoppelGround sanitized evidence export, and GeniusTurtle read-only/operator UI API.
