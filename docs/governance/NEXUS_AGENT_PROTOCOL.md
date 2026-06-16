---
id: NODE-MIG-NEXUS_AGENT_PROTOCOL
authority_scope: experimental
origin_sha256: df303a874aa001f80fbee5c923c8f11e8db99f003467c7e8bcb8db63c2bc62ed
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-5E56E4
---
# NEXUS Agent Protocol v2

**Version:** 2.0  
**Date:** 2026-05-27  
**Status:** Active (supersedes parts of AGENTS.md for new practices)

<!-- CANARY: 0cdb8ea50ab5fd2aabdfdb47969d2602 -->
This document defines the operating protocol for agents working in the NEXUS OS repository, incorporating the governance advancements developed in 2026.

## Core Principles (Unchanged from v1)

- Actions must be **evidence-grounded**, **proposal-bound** where material, **test-gated**, and **auditable**.
- NEXUS is the governance and orchestration layer.
- Prefer filesystem state, tests, git history, and canonical docs over chat memory.

## New Governance Practices (v2 Additions)

### 1. Activation Lanes (Mandatory for Significant Work)

All work that involves:
- Moving items out of HOLD states
- Integrating external layers or research outputs
- Making changes that affect TrustKernel, Guard Plane, VAP, or memory

**Must** use the three-lane process defined in `docs/governance/ACTIVATION_LANES.md`:

- **Lane A — Reconcile**: Document current state and gaps (hashes, evidence).
- **Lane B — Active Diagnosis**: Bounded diagnostic work only.
- **Lane C — Isolated Candidate**: Build and validate in isolation before promotion.

Lane transitions must be recorded via VAP and linked task files.

### 2. Evidence Compiler & Research Intake Gate

Research outputs (datasets, stress results, reports, model artifacts) are **not** automatically canonical.

They must pass through:
1. The **Evidence Compiler** (`research/evidence/`) following the raw → briefs → drafts → published pipeline.
2. The **Research Intake Gate** (see `research/intake/` and `tasks/pending/2026-05-27-research-governance-closed-loop.task.md`).

Only after registration in `research/evidence_manifest.json` and VAP recording may research influence governance components.

### 3. NEXUS Constitution

The canonical invariants and current components are defined in `docs/governance/NEXUS_CONSTITUTION.md`.

All agents must treat this as the source of truth for governance behavior. Amendments follow the defined process.

### 4. Updated Tooling Expectations

Agents should use and contribute to:
- `nexusctl doctor research` / `governance` / `layer-status` (when available)
- The Evidence Compiler and Intake Gate processes
- Activation Lane task templates

## Continuous Operation (Updated)

In addition to the v1 rules:
- When performing research-related or governance work, log progress to the appropriate intake/reconciliation documents.
- Use the Evidence Compiler for any artifacts that will be used to update Guard Plane, TrustKernel, or memory systems.

## Codex-Specific Note

Codex plugin/tool hygiene remains in `.codex/plugin_hygiene_policy.md`.

---

This v2 protocol focuses on the new governance machinery built in mid-2026. The original AGENTS.md remains the base reference for general rules.
