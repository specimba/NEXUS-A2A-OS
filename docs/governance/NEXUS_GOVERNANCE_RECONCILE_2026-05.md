---
id: NODE-MIG-NEXUS_GOVERNANCE_RECONCILE_2026_05
authority_scope: experimental
origin_sha256: 07124263b0341c0e099fcd8677b5cb9ec44a02c8a1b0707da28de81a3e4124f0
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-410FF1
---
# NEXUS Governance Surface Reconcile Document

**Date:** 2026-06-01  
**Task:** `2026-05-27-governance-consolidation-activation`  
**Lane:** A (Reconcile)

## Scope
This document records the current governance surface and memory fragmentation visible in the tracked repository as of May 2026. It is descriptive only. It does not decide the unification plan.

## Canonical Governance Components

| Component | Current role | File references |
|---|---|---|
| TrustKernel | Canonical trust control plane; maps actions to lanes and consults Vault-backed tracking when available. | `nexus_os/governor/trust_kernel.py` |
| VAPProofChain | Append-only proof-chain recorder for governance-relevant actions. | `nexus_os/governor/proof_chain.py` |
| Vault 5-track store | Structured governance memory over event, trust, capability, failure_pattern, and governance tracks. | `nexus_os/vault/memory_tracks.py`, `nexus_os/vault/manager.py` |
| GovernedMemoryBroker | Read-only trust-bounded context broker across hot, canonical, and semantic memory paths. | `nexus_os/vault/governed_memory_broker.py` |
| Governed MCP bridge | TrustKernel-gated MCP bridge with side-effect tools held by default and governed checkpoint creation. | `nexus_os/mcp/server.py` |
| Guard Plane prefilter | Stateless meta-attack detector that runs before expensive model inference. | `nexus_os/security/meta_attack_detector.py` |
| Activation Lanes | Canonical workflow for Reconcile, Active Diagnosis, and Isolated Candidate. | `docs/governance/ACTIVATION_LANES.md` |
| Research Evidence Compiler | Canonical research evidence pipeline definition. | `research/evidence/README.md` |

## Memory Surface Inventory

| Memory surface | Status | Evidence |
|---|---|---|
| Vault 5-track memory | Active and structured; intended governance memory substrate. | `nexus_os/vault/memory_tracks.py`, `nexus_os/vault/manager.py`, `src/nexus_os/governor/trust_kernel.py` |
| SuperLocalMemory (8-channel) | Active in-process memory implementation with task, context, and custom channels beyond the 5-track schema. | `nexus_os/vault/memory.py` |
| Mem0Adapter | Active persistent semantic memory adapter with local JSON fallback and S-P-E-W style layer mapping. | `nexus_os/vault/memory_adapter.py`, `nexus_os/vault/__init__.py` |
| BrainSync MCP service | External memory/service surface evidenced in archived operational notes, not governed inside the Python control plane. | `docs/archive/handoff/LOCAL_RESOURCE_MONITOR_2026-05-27.md`, `research/intake/2026-05-27-memory-reconciliation.md` |

## File-Backed Findings

1. The repo does not contain a single memory abstraction today. At minimum, Vault 5-track, SuperLocalMemory, and Mem0Adapter coexist in tracked code, while BrainSync is documented as an external service boundary.
2. TrustKernel is the clearest candidate for canonical governance authority because it defines decisions, lane/action policy, and imports Vault tracking through `get_tracker()` when available.
3. VAPProofChain exists as a concrete append-only proof chain, so auditability is implemented as a real module rather than a placeholder.
4. The governed MCP bridge is already wired to TrustKernel concepts and includes `memory.create_checkpoint`, which means governance and memory already intersect at the tool boundary.
5. `GovernedMemoryBroker` is a live read-only retrieval boundary spanning SuperLocalMemory, 5-track, and optional semantic memory, which proves the repo already has a trust-bounded read path even though writes remain fragmented.
6. The research evidence compiler is documented as canonical, but the intake processor is still explicitly a stub. That means research-ingestion intent exists, while full enforcement does not.

## Resolved Factual Position
No unresolved factual disputes were found in the inventory above. The open question is policy, not fact: which memory surface becomes canonical for governance in Lane B.

## Lane B Input

1. Decide whether Vault 5-track is the only governance-authoritative memory layer.
2. Decide whether SuperLocalMemory remains a local cache/context window only.
3. Decide whether Mem0Adapter is part of canonical memory or an auxiliary semantic retrieval layer.
4. Define an explicit adapter and audit boundary for BrainSync before it can influence governed state.
