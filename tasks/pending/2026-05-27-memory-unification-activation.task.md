<!-- CANARY: 2fedc2e8334bf29168ce10157b08c32a -->
---
id: 2026-05-27-memory-unification-activation
title: [Lane A] Memory Unification - Reconcile
priority: P0
status: pending
created: 2026-05-27
lane: A
scope: memory
---

## Lane
**Current Lane:** A (Reconcile)

## Goal
Document all current memory implementations in the codebase and external services, identify overlaps and gaps, and produce a clear Reconcile document.

## Evidence / Reconcile Document
- `research/intake/2026-05-27-memory-reconciliation.md` (initial draft)
- `nexus_os/vault/memory_tracks.py` (canonical 5-track)
- `nexus_os/vault/memory.py` (8-channel SuperLocalMemory)
- External brainsync (MCP, used by the Grok TUI runtime)
- Evidence Compiler (`research/evidence/`) as the governed ingestion path for research-derived memory

## Required Work
1. Inventory all memory-related code paths and external services.
2. Document how TrustKernel and VAP currently interact (or don't) with each memory system.
3. Produce Reconcile Document (see `2026-05-27-memory-reconciliation.md`).

## Exit Condition
Single agreed Reconcile Document with no unresolved factual disputes about current memory landscape.

## Verification Gate
- Inventory complete with file references
- Clear gap analysis documented
- Linked to NEXUS_CONSTITUTION.md

## Boundaries
- Lane A only. No unification design or implementation yet.
- Do not delete or refactor existing memory code during reconciliation.

## Next Lane
Lane B (Active Diagnosis) - decide canonical model and migration path.
