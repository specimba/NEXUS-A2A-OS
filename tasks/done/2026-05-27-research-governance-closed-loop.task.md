<!-- CANARY: e530224066ddff482609d7a33b0320f5 -->
---
id: 2026-05-27-research-governance-closed-loop
title: Research-to-Governance Closed Loop - Phase 0 Intake Gate + First VAP Records
priority: P0
status: done
created: 2026-05-27
scope: research-integration governance
---

## Goal

Establish the first real closed feedback loop between NEXUS research outputs and the canonical governance engine (TrustKernel, VAPProofChain, Guard Plane, 5-track memory). Research must stop being a one-way evidence generator and become the primary, governed driver for improving the control plane.

## Evidence From May 2026 Analysis

- `datasets/ernie/ADVERSARIAL_CORPUS_v2.md` (2026-05-26): 50+ queries explicitly tested against live Guard Plane (MetaAttackDetector v4, entropy profiler, semantic drift). 100% detection reported on multiple INJECAGENT families and reasoning-model attacks. Research is already mapping directly to our components but not feeding back.
- `benchmarks/mixed content/PHASE6_FINAL_HANDOFF.md`: Explicitly states "Ready for Real TrustKernel Integration" with stub/real adapters and "Governance before execution" principle — yet still in foundation/stub state.
- `research/papers01/RED-BLUE-PURPLE/README.md`: Labeled as "Enterprise-grade AI agent security research for NEXUS OS TrustKernel".
- Multiple stress_lab releases (Frontier v5, TAMAS v6, tool taxonomy) and ERNIE swarm reports (v4–v12) contain high-value findings that have never produced VAP entries or TrustKernel parameter deltas.
- Visible Layers Blueprint (2026-05-26) defines the exact three-lane activation method and ReviewGround pipeline that should govern research graduation — currently aspirational for research artifacts.
- Current `resources_state.json` and session data show heavy research file reads with no corresponding governance artifacts created.

## Required Work

1. Create lightweight Research Intake Gate (script + task template) that every new major research output must pass.
2. Process the first batch of high-value artifacts:
   - ERNIE Adversarial Corpus v2 + associated checkpoints
   - Nexus Frontier v5 stress sets and scoring results
   - Latest merged guard artifacts (Special-Virus, Neo_T-Virus, Bouncer combinations)
   - Key ERNIE swarm findings (root cause, failure modes, cross-validation)
3. For each item in the batch produce:
   - Content hash + source brief (ReviewGround style)
   - Mapping to affected NEXUS component (Guard Plane category, TrustKernel lane param, VAP action type)
   - Draft VAPRecord(s) or proposed TrustKernel / meta_attack_detector change
4. Record the intake decisions themselves via VAPProofChain.
5. Update one live component (either add 2–3 new attack categories to MetaAttackDetector or produce a concrete delta proposal for trust_scoring.py lane params) with full test + VAP trail.
6. Deliver the first version of `research/evidence_manifest.json` (or extend existing stress_lab manifests) that future corpora must update.

## Verification Gate

- At least 10 major research outputs from the batch have VAP entries or linked governance proposals.
- One concrete improvement to Guard Plane or TrustKernel code has been made with passing tests and VAP provenance.
- `nexusctl doctor research` (or equivalent manual check) reports the intake status cleanly.
- The new task file follows the exact canonical template (Evidence → Required Work → Verification Gate → Boundaries).
- No secrets or raw unredacted research dumps are introduced into canonical docs.

## Boundaries

- Do not rewrite or move the entire research corpus in Phase 0 — only create the intake process and process the first high-signal batch.
- Do not claim full integration of all ERNIE/Frontier work; this is the intake foundation only.
- All changes must be proposal-bound and recorded (use VAP + this task file).
- Respect existing "not allowed yet" lists from the Visible Layers Blueprint for any model/runtime changes.

## Activation Lanes

This task is the entry point for the three-lane method on research outputs:

- Lane A (Reconcile): Cleanly document the current research → governance gap with hashes and evidence.
- Lane B (Active Diagnosis): Run the intake on the first batch and measure what actually surfaces.
- Lane C (Isolated Candidate): The first live Guard Plane / TrustKernel improvement that graduates from this process.

## Next After This Task

- Formalize the reusable Activation Lanes templates (docs/governance/ACTIVATION_LANES.md)
- Build the full Evidence Compiler directory structure under research/evidence/
- Extend nexusctl doctor with research and governance subcommands
