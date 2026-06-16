---
id: NODE-MIG-ACTIVATION_LANES
authority_scope: experimental
origin_sha256: 10da7e15de77fd63e3fb276e97fe9a90d3399742553596851e14b8aa302f9c43
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-AC4A73
---
# NEXUS Activation Lanes

**Version:** 1.0  
**Date:** 2026-05-27  
**Purpose:** Reusable governance primitive for moving work out of HOLD states or integrating new capability layers.

## The Three Lanes

### Lane A — Reconcile
**Goal:** Cleanly document the current state and the gap.
<!-- CANARY: a1f355460ba51c9a1216db2ecc0c8613 -->
- Inventory of relevant artifacts with content hashes.
- Clear statement of what is missing or blocked.
- Source of truth references (files, manifests, VAP entries).

**Exit Condition:** A single, agreed "Reconcile Document" exists with no unresolved factual disputes.

**Example Artifacts:** `research/intake/2026-05-27-first-batch-lane-a-reconcile.md`

### Lane B — Active Diagnosis
**Goal:** Run bounded, diagnostic work to understand the problem without committing to production changes.
- Sequential, low-risk experiments.
- Strict stop rules (time, scope, or success criteria).
- Only diagnostic outputs — no claims of production readiness.

**Exit Condition:** One or more well-defined "Diagnosis Questions" with clear success/stop rules and recorded findings.

### Lane C — Isolated Candidate
**Goal:** Build and validate one specific candidate solution in isolation.
- Worktree or dedicated branch.
- Full regression + governance tests.
- Proposal must pass TrustKernel evaluation and VAP recording before promotion.

**Exit Condition:** Candidate improves the target without violating storage, ABI, runtime constraints, or governance invariants. Ready for formal governance approval.

## Usage Rules
- All significant HOLD states or external layer integrations must declare which lane they are in.
- Lane transitions must be recorded (VAP entry + update to relevant task file).
- You cannot skip lanes. Lane A must complete before Lane B begins in earnest.

## Templates
See `tasks/templates/activation-lane.task.md` for the standard task template.

This document is now the canonical reference for the Activation Lanes primitive.
