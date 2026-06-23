# NEO / HERMES Import Plan

This document maps out the import plan for aligning the experimental workspaces (**NEO agent** and **hermes-agent**) with the canonical **NEXUS** architecture.

---

## 1. Safe Ideas (Approved for Import)

- **Centralized ModelRelay Integration:** Configure both agents to route inference through `http://localhost:7350/v1` instead of using direct provider API calls. This enables centralized telemetry, unified model selection, and automated circuit breaking.
- **Inter-Agent Discovery Card (A2A v1.0):** Implement a standardized agent card at `/.well-known/agent.json` mapping out agent metadata, lanes, trust thresholds, and capabilities.
- **HERMES SessionDB Search (FTS5):** Port the SQLite FTS5 search logic from HERMES `hermes_state.py` into the Archivist local search indexer for fast full-text querying.
- **NEO Environment Sanitization:** Remove dead Azure Foundry endpoints and credentials from NEO's `.env`, ensuring it only queries active providers via ModelRelay.
- **Git Tree Repair:** Execute history repair and reflog recovery on the corrupted NEO workspace.

---

## 2. Risky Ideas (Deferred / Under Observation)

- **Speculative Decoding (MARS):** Porting the Multi-token Autoregressive Speculative decoding logic is risky due to high compilation complexity and GPU cache synchronization overhead. Keep quarantined in the `chimera` research lane.
- **Symlinking `src/nexus_os` in NEO:** While replacing NEO's diverged core with a junction link to NEXUS main fixes import errors, it may break ad-hoc NEO-specific assumptions. Must be verified in a separate test branch first.
- **Local GLM-5.2 Serving (RTX 4090 DSA):** Attempting to self-host GLM-5.2 FP8 via custom sparse-attention kernels is highly risky due to SM-architecture gates and VRAM footprint. Restrict to vendor API endpoints (SiliconFlow/DeepInfra) or Modal serverless jobs.

---

## 3. Rejected Claims

- **Blockchain-backed Memory:** Rejected. Vault memory must remain local, encrypted via AES-256-GCM, and vector-indexed (ChromaDB), without distributed ledger bloat.
- **7352 = ModelRelay:** Rejected. Re-routing ModelRelay to port `7352` violates the PortRegistry rules and breaks Brain API governance.
- **Audit all Johns / 21 Working Lines:** Rejected. These are red herrings and mock test residues with no runtime or security logic.

---

## 4. Next Bounded Implementation Tasks

1. **Task 1: NEO Key Sanitization & Env Sync**
   - Delete all `AZURE_*` and `Azure` variables from NEO Agent `.env`.
   - Replace active provider keys with `dummy-key` placeholders, routing all calls to `7350`.
2. **Task 2: Expose agent.json Card**
   - Create a static discovery JSON file in `nexus_os/api/static/agent.json` describing NEXUS capabilities and trust lanes.
3. **Task 3: NEO Git fsck Repair**
   - Run `git fsck --full` in the NEO workspace, identify missing blobs, and reconstruct git tree from reflog or main-candidate clone.
