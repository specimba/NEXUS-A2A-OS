# NEO / HERMES Evidence Matrix

This document reconciles claims from the experimental workspaces (**NEO agent** and **hermes-agent**), main **NEXUS**, downloads (`NEXUSlogs`), and **Archivist** reports into a verified, audit-compliant evidence matrix. All secrets, credentials, and API keys are redacted to preserve repository governance.

---

## 1. Grounded Evidence Matrix

| Claim | Source Path | Status | Evidence | NEXUS Import Value | Risk |
|---|---|---|---|---|---|
| **7352 = ModelRelay** | `Downloads/NEXUSlogs` | **REJECTED** (Stale) | The canonical [port_registry.py](file:///C:/Users/speci.000/Documents/NEXUS/nexus_os/bridge/port_registry.py#L49-L66) explicitly locks port `7352` to `brain_api` (Brain API / Governance only). ModelRelay uses `7350` (primary) and `7355` (fallback). | **None** | **CRITICAL** (Port hijacking/conflict with Brain API) |
| **Blockchain-backed memory** | `Downloads/NEXUSlogs` | **REJECTED** (Fabricated) | No blockchain code, imports, or schemas exist in `nexus_os` or experimental paths. Vault memory uses SQLite [memory_channels.py](file:///C:/Users/speci.000/Documents/NEXUS/nexus_os/vault/memory_channels.py) and ChromaDB [semantic_backend.py](file:///C:/Users/speci.000/Documents/NEXUS/nexus_os/vault/semantic_backend.py). | **None** | **High** (Unnecessary dependency bloat) |
| **Audit all Johns** | `Downloads/NEXUSlogs` | **REJECTED** (Fabricated) | Occurrences of "John" are exclusively found in cached `bigcodebench` datasets and mock test files. No operational logs or security incidents reference a real "John". | **None** | **Low** (Irrelevant audit chasing) |
| **21 working lines** | `Downloads/NEXUSlogs` | **REJECTED** (Suspect) | Mentioned in historical transcripts as an arbitrary metric or code constraint, but lacks any implementation, definition, or verification in the runtime. | **None** | **Low** (Ad-hoc constraint chasing) |
| **Port 7354 GROSS Bridge Conflict** | `Downloads/NEXUSlogs/NEXUSantiGRAVnexlog-05.txt` | **VERIFIED** | Active processes showed `PID 58880` (NEXUS bridge server) had to be killed to clear port `7354` for GROSS bridge. Checked against [port_registry.py](file:///C:/Users/speci.000/Documents/NEXUS/nexus_os/bridge/port_registry.py). | **High** (Centralized port arbitration is now active in PortRegistry) | **Medium** (Service disruption if registry is bypassed) |
| **Next.js Dashboard on Port 3001** | `C:\Users\speci.000\Documents\NEXUS\worklog.md` | **VERIFIED** | Dashboard relocated to `3001` because port `3000` is owned by the WSL2 networking relay (`wsl_relay`). | **High** (Prevents conflict with default WSL2 dev ports) | **Low** (Minor redirection required) |
| **NEO Git Repository Corruption** | `C:\Users\speci.000\Documents\NEO agent\AGENTS.md` | **VERIFIED** | Running git commands in NEO workspace fails with `fatal: bad object HEAD` and missing blobs. | **None** | **High** (Untracked code drift and history loss) |
| **Azure AI Foundry is DEAD** | `C:\Users\speci.000\Documents\NEO agent\AGENTS.md` | **VERIFIED** | Azure AI subscription is blocked. All Azure models and `AZURE_GROK_API_KEY` are dead. NEO's `.env` still contains stale placeholders. | **None** | **High** (API requests fail immediately, VRAM/rate limits wasted) |
| **HERMES SessionDB (FTS5 + WAL)** | `C:\Users\speci.000\Documents\HERMES\hermes-agent\cli.py` | **VERIFIED** | `hermes_state.py` implements a SQLite-based SessionDB with full-text search (FTS5) and NFS/SMB-safe WAL fallback. | **High** (Integrate FTS5 search into NEXUS local search) | **Low** (Stable, well-tested module) |
| **S-P-E-W Memory Hierarchy** | `C:\Users\speci.000\Documents\NEO agent\PROJECT_KNOWLEDGE_BASE.md` | **VERIFIED** (Stale) | S-P-E-W (Session, Project, Experience, Wisdom) is a legacy layout; NEXUS has migrated to the unified 8-channel Memory. | **Low** (Use as conceptual guide only) | **Medium** (Schema drift if merged directly) |
| **MARS Speculative Decoding** | `C:\Users\speci.000\Documents\NEO agent\PROJECT_KNOWLEDGE_BASE.md` | **VERIFIED** (Provisional) | Code exists in NEO agent for multi-token autoregressive speculative decoding, but is not active or integrated into NEXUS main. | **Medium** (Useful for low-VRAM throughput testing) | **High** (Requires deep verification for compilation issues) |
| **GLM-5.2 Serving on RTX 4090** | `C:\Users\speci.000\Documents\NEXUS\docs\research\GLM_5_2_4090_DSA_PORT_INTAKE_2026-06-19.md` | **VERIFIED** | Serves GLM-5.2 FP8 via `renning22/glm-5.2-4090` using custom SM90-to-Ada DSA kernels and `--disable-shared-experts-fusion`. | **High** (Allows Modal/multi-GPU teacher-lane execution) | **High** (Monkeypatching, VRAM constraints) |
| **POST /api/stress/report operational** | `C:\Users\speci.000\Documents\NEXUS\docs\research\CODEX_v4_GROUNDING_REVIEW.md` | **VERIFIED** | Endpoint is active in Brain API (53 routes total) and wired to `sync_memory_context()` (Vault) and `generate_log_entry()` (Archivist). | **High** (Durable writeback path for StressLab data) | **Low** (Operational and unit-tested) |
| **Plaintext Key Exposure** | `C:\Users\speci.000\Downloads\ARCHIVIST\29&(][11!34.txt` | **VERIFIED** | Plaintext provider keys exist in the Archivist file and connectivity report. | **None** | **CRITICAL** (Security leak; requires immediate rotation) |

---

## 2. Invariants & Guardrails

1. **Port Registry Sovereignty:** Port `7352` is strictly locked to Brain API. Under no circumstances should any ModelRelay process bind to it.
2. **Secrets Sandboxing:** No raw key material or tokens (e.g., from `29&(][11!34.txt` or `docs/research/NEXUS_CONNECTIVITY_REPORT.md`) should ever be checked in. The vault must enforce AES-256-GCM encryption on the key file.
3. **Model Selection:** GLM-5.2 is restricted to the teacher/judge lane (SiliconFlow/DeepInfra/Modal). It must never run autonomously without KAIJU and VAP gates.
