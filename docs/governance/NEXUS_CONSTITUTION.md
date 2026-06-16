---
id: NODE-MIG-NEXUS_CONSTITUTION
authority_scope: experimental
origin_sha256: d8af01ad5d9b9c81139c7e68a2a494bbe31109ce0549037b60dd30a124052af0
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-AFA969
---
# NEXUS Constitution (Draft)

**Version:** 0.5  
**Date:** 2026-06-01

## Core Invariants (Non-Negotiable)

<!-- CANARY: 2acd1760ff1c311f75d2bc715ef1d5e4 -->
1. **Governance Before Execution**  
   No high-risk action (write, delete, execute, deploy, override, escalate) may proceed without passing through TrustKernel evaluation.

2. **Single Source of Truth for Governance State**  
   Trust scores, VAP chains, and governance memory must resolve through the canonical control-plane components (TrustKernel, VAPProofChain, and the Vault 5-track store). External layers may consume or cache state but may not silently override it.

3. **Evidence-Grounded Decisions**  
   All significant changes to governance behavior (new attack categories, lane parameter changes, or memory-schema changes) must be backed by recorded evidence such as a VAP entry, source brief, or test result.

4. **Proposal-Bound + Test-Gated**  
   Work that affects the control plane must be proposal-bound and pass relevant tests before promotion. The three-lane Activation method (Reconcile → Active Diagnosis → Isolated Candidate) is the standard process.

5. **Auditability**  
   Every governance-relevant action must be traceable via VAPProofChain.

## Current Governance Surface (file-backed snapshot as of 2026-06-01)

- **TrustKernel** (`src/nexus_os/governor/trust_kernel.py`) is the canonical trust control plane and imports the Vault tracker when available.
- **VAPProofChain** (`nexus_os/governor/proof_chain.py`) provides append-only proof-chain recording.
- **Vault 5-track store** (`nexus_os/vault/memory_tracks.py`, `nexus_os/vault/manager.py`) is the structured governance memory substrate used by TrustKernel-backed persistence.
- **SuperLocalMemory** (`nexus_os/vault/memory.py`) is an active 8-channel in-process memory implementation.
- **Mem0Adapter** (`nexus_os/vault/memory_adapter.py`, `nexus_os/vault/__init__.py`) is an active persistent semantic memory adapter with local fallback.
- **Governed MCP bridge** (`nexus_os/mcp/server.py`) exposes TrustKernel-gated tools and a governed memory checkpoint tool.
- **Guard Plane prefilter** (`nexus_os/security/meta_attack_detector.py`) is the current stateless attack prefilter.
- **Activation Lanes** (`docs/governance/ACTIVATION_LANES.md`) define the required Reconcile -> Active Diagnosis -> Isolated Candidate workflow.
- **Research Evidence Compiler** (`research/evidence/README.md`) defines the canonical research pipeline.
- **Research Intake Gate** (`research/intake/intake_processor.py`) exists only as a stub and is not yet a full enforcement gate.

## Research Integration Principle
High-value research outputs are intended to flow through the Evidence Compiler before influencing TrustKernel, Guard Plane, or memory. The intake gate remains partially implemented, so enforcement is not yet complete.

## Current State of Memory Systems
Multiple memory systems coexist today:
- The Vault 5-track schema in `nexus_os/vault/memory_tracks.py` and `nexus_os/vault/manager.py`
- `SuperLocalMemory` in `nexus_os/vault/memory.py`
- `Mem0Adapter` in `nexus_os/vault/memory_adapter.py`
- External BrainSync usage evidenced outside the core Python repo surface

Detailed reconciliation document: `docs/governance/NEXUS_GOVERNANCE_RECONCILE_2026-05.md`

Unification remains an active Lane B question, not a settled fact.

## Amendment Process
As previously defined.

## 2026-06-01 Status Snapshot
- TrustKernel, VAPProofChain, Vault 5-track storage, Mem0Adapter, and SuperLocalMemory all exist concurrently in the codebase.
- The governed MCP bridge includes a TrustKernel adapter and a guarded `memory.create_checkpoint` tool.
- Activation Lanes are documented canonically.
- The research evidence pipeline is documented, but the intake gate is still a stub.

See active to-do list for current priorities.

*Living draft.*
