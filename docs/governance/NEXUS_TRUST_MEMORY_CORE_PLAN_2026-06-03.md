---
id: NODE-MIG-NEXUS_TRUST_MEMORY_CORE_PLAN_2026_06_03
authority_scope: experimental
origin_sha256: 5a3e2e87464d836d5d59f074be5a4abe34cc120bbd79abe92c6feaad092a7484
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-1926E3
---
# NEXUS Trust-Memory Core Plan

## Correction

NEXUS trust is not a linear 0-100 reputation score. The canonical runtime path is:

1. `nexus_os.governor.trust_scoring.compute_score`
2. `nexus_os.governor.trust_kernel.TrustKernel`
3. `nexus_os.governor.trust_kernel.TrustResourceBudget`
4. `nexus_os.vault.governed_memory_broker.GovernedMemoryBroker`

Trust updates use lane-scoped evidence with Q, n, U, R, D_plus, D_minus, Qeff, tanh scoring, held/escalated finding states, posterior uncertainty, evidence maturity, CDR stage, regression pressure, novelty pressure, risk flags, and authority band. Resource budgets are discrete operating envelopes, not percentages.

## Memory Shape

The active memory stack is layered:

- Hot path: `SuperLocalMemory` 8-channel cache for cheap local context.
- Warm canonical path: `MemoryTracker` 5-track EVENT/TRUST/CAPABILITY/FAILURE_PATTERN/GOVERNANCE records.
- Cold semantic path: injected `Mem0Adapter` or compatible S-P-E-W semantic memory.
- Cloud cold path: disabled by default and not implemented without KAIJU/VAP approval.

No component should broad-poll models or infer against all memories in the background. Retrieval is demand-driven by a task query and constrained by the TrustKernel memory depth.

## Enforcement Added

`GovernedMemoryBroker` now builds read-only context packs from the active TrustKernel budget:

- Cold-start/constrained agents get shallow hot and canonical reads only.
- Elevated agents can use semantic recall only when a semantic memory provider is explicitly injected.
- Review-only, quarantined, and locked states block semantic recall.
- Locked agents receive no memory context.
- Cloud cold recall remains denied by default.

NexusClaw dry-run dispatch now routes task intent through this broker and records only compact memory-context metrics in the result envelope. Raw memory payloads are not copied into VAP/result metrics.

## Next Integration Targets

1. Make FunctionGemma/tool routing attach broker metrics before proposing side-effect tools.
2. Add VAP records for memory context pack decisions, not full raw memory payloads.
3. Keep Mem0 local-first unless an operator-approved KAIJU/VAP cloud path exists.
4. Extend red/blue/purple tests to include memory poisoning, semantic recall overreach, tool-call escalation, and proof-chain fabrication.
