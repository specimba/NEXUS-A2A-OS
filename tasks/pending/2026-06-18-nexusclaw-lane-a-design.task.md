---
id: 2026-06-18-nexusclaw-lane-a-design
title: NEXUSCLAW Lane A — design doc + task artifact
priority: P1
status: done
created: 2026-06-18
lane: A
scope: research-integration
---

## Lane
**Current Lane:** A
**Previous Lane:** (none)

## Goal
Consolidate the switch from NemoClaw to NEXUSCLAW into a single native design doc (NEXUSCLAW_DESIGN.md) and its backing task artifact, capturing the 12-collision resolution, reuse list, native module tree, TrustKernel ID assignments, and effort estimates.

## Evidence / Reconcile Document
- `docs/research/NEXUSCLAW_DESIGN.md`
- `NEXUS-CLAW-01.txt` L138-218 (source evidence)
- Live tree `nexus_os/claw/` verified 2026-06-18

## Required Work
1. Draft NEXUSCLAW_DESIGN.md covering replacement rationale, architecture, module contracts, TrustKernel IDs, port/path reconciliation, and effort estimates.
2. Write this task artifact bound to the completed work for governance tracking.

## Exit Condition
NEXUSCLAW_DESIGN.md exists at docs/research/, 12-collision table is complete, reuse list documented, native modules mapped to nexus_os/claw/ tree, TrustKernel IDs assigned, and Lane A/B/C effort estimates documented.

## Verification Gate
- `docs/research/NEXUSCLAW_DESIGN.md` exists and spans full 165 lines.
- 12-collision table resolves all NemoClaw collisions.
- Reuse list documented (OpenClaw, OpenShell, Hermes).
- Native modules mapped to nexus_os/claw/ tree.
- TrustKernel IDs assigned (claw-orch-001, claw-rev-002, claw-res-003).
- Lane A/B/C effort estimates documented (2300 LoC, ~3 days).

## Boundaries
- Lane A deliverables are docs-only: no code changes.
- Do not implement sandbox.py, agent.py, or any runner code in this lane.
- Respect existing "not allowed yet" lists from the Visible Layers Blueprint.

## Next Lane
Lane B — Active Diagnosis: sandbox.py prototype + minimal agent.py; prove Landlock + seccomp + netns in WSL2 with 1 test agent.
