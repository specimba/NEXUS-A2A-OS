# NEXUS OS — Canonical Knowledge Base

**Compiled:** 2026-06-10 | **Branch:** codex/specimba/1805mainSpeci | **HEAD:** Phase 1 Critical Implementation Complete

<!-- CANARY: 7a14b495084935aa0985a638734cf0bb -->
<!-- UPDATED: 2026-06-10 by Phase 1 Critical Implementation -->
---

## PROJECT IDENTITY

Nexus OS is a governed, local-first agent operating system. Python/FastAPI governance is canonical. Next.js dashboard (port 3000) is the UI proxy. Windows = control/authoring plane; Linux/WSL = execution sandbox.

---

## 8-PILLAR ARCHITECTURE

| Pillar | Path | Purpose |
|--------|------|---------|
| Bridge | `nexus_os/bridge/` | JSON-RPC server, SDK, secrets, MCP auth, vault bridge |
| Governor | `nexus_os/governor/` | KAIJU gates, TrustEngine v2.2, VAP proof chain, compliance |
| Vault | `nexus_os/vault/` | 5-track memory (EVENT/TRUST/CAP/FAIL/GOV), encryption |
| Engine | `nexus_os/engine/` | Hermes router, executor, skillsmith, tool discipline |
| GMR | `nexus_os/gmr/` | Model rotation, circuit breaker, telemetry, domain mapping |
| Swarm | `nexus_os/swarm/` | Foreman, worker pool, auction, OpenClaw spawner |
| Monitoring | `nexus_os/monitoring/` | TokenGuard, counters, strategies |
| Observability | `nexus_os/observability/` | Tracing, log compression (Squeez) |

---

## WHAT WE BUILT (Full Inventory)

### Phase 1 Critical: Misalignment Detection + Safety Classifier (June 10, 2026)
- **MisalignmentDetector** — `nexus_os/governor/misalignment_detector.py` (574 lines): 8 concealment patterns (git obfuscation, sandbox escape, jailbreak, steganography, data exfiltration, privilege escalation, covert communication), circuit breaker (score ≥100), CDR auto-escalation (score ≥50), zero-width Unicode detection
- **IntentClassifier** — `nexus_os/governor/intent_classifier.py` (682 lines): 8 safety categories (cybersecurity, biology, distillation, jailbreak, code injection, privacy violation, hate harassment, self-harm), fallback routing to lower-capability models, KAIJU integration, 30-day retention, weekly audit with false positive/negative tracking
- **TrustEngine v2.2 integration** — `detect_misalignment()` auto-triggers CDR CASCADE on CRITICAL events
- **TokenGuard integration** — `check_deception_patterns()` VAP-compliant audit logging
- **Constitution.yaml updates** — 7 misalignment rules + 9 classifier categories with confidence thresholds
- **Leaked intelligence analysis** — Claude Fable 5 system prompt (121KB), Crystalline cognitive memory (5-level ACT-R), ST3GG threat toolkit
- **meta_attack_detector.py fix** — Added `_entropy_check()` call to `scan()` method (was never invoked, causing test failure). Narrative entropy escalation now properly detected.

### Phase 0 Security (May 12-14)
- **Terminal Sanitizer** — `src/nexus_os/security/sanitizer.py` (256 lines): TerminalSanitizer (ANSI/VT escape stripper), AgentPTY (dedicated PTY per agent), VerifiableOutput (SHA-256 integrity)
- **AGENTS.md** — Safety-gated autonomous operation rules v2.0 with Pre-Execution Safety Gates (SAFETY-1 through SAFETY-4)
- **AFK Workflow Style** — `docs/handbook/05_NEXUS_AFK_WORKFLOW_STYLE.md`: 5-phase autonomous loop (SCAN→DIGEST→SYNTHESIZE→PRODUCE→VERIFY)
- **Test suite** — 23 security tests in `tests/security/test_sanitizer.py`

### Architecture Plans
- **v4 Master Plan** — `NEXUS_OS_V4_MASTER_PLAN.md` (1,182 lines): 15-section architecture plan. Covers sandbox abstraction, cross-agent security (4-layer), governance mesh unification, TWAVE/QWAVE/CHIMERA speculative decoding, 14-bot Slack network, hallucination detection, 12-week roadmap (Phases 0-6). Core insight: Windows=control, Linux=execution, Cloud=burst.
- **Zo/Claw A2A Integration** — `NEXUS_ZO_CLAW_INTEGRATION_PLAN.md` (374 lines): 4-layer protocol stack (Tailscale→MCP→A2A→OpenClaw), 3 OsmanClaw agents, Kafka bridge decision, MCP tool provider design. **Confluent key redacted from git history.**
- **Full Asset Inventory** — `docs/reviews/...md` (417 lines): Complete resource map. **Azure resources marked DEAD (sub blocked).** 3 Horsemen strategy cancelled.

### Dataset Creation Pipeline (Massive)
**6 versions of stress lab datasets** evolving through v1→v6:

| Version | Rows | Size | Source |
|---------|------|------|--------|
| v1 ISC-Bench | 1,164 | Baseline | 84 ISC templates |
| v2 ISC Expander | 10,000 | 10 phases | Combinatorial expansion |
| v3 Multi-source | 484 | 4 benchmarks | AgentHazard+SOS+Gov+Claws |
| v4 Regenerator | 536,530 | ~385 MB | 13 governance × 13 templates × 12 domains |
| v5 Frontier | 181,000 | ~117 MB scored | 7 frontier types, 11 research sources |
| v6 TAMAS | 6,840 | ~4 MB | 7 attack types, 3 topologies, 5 domains |

**Key files:** `benchmarks/regenerate_datasets.py` (v4), `benchmarks/regenerate_frontier_v5.py` (v5), `benchmarks/stres6_tamas_generator.py` (v6), `benchmarks/stres5_final.py`, `benchmarks/stres5_payload_generator.py`

**Eggroll configs:** 7 per-model MultiReward configs in `foundry_datasets/stress_lab/`. 64 sources scored in `state/dataset_quality/`. Gap analysis found dual_use_detection (21.5%) and tool_misuse (20.7%) as weak spots.

**Total dataset volume:** ~1.5+ GB across 85+ JSONL files, 17 parquet files.

### Dashboard (Next.js, 107 TS files, ~16,800 lines)
26 custom components, 19 API endpoints, 8+1 tab panels, Prisma SQLite with 12 models, Socket.io WebSocket mini-service (port 3003). All tabs wired to real API data. Zero lint errors.

### GitHub Integration
- 12 API providers integrated (NVIDIA, SambaNova, SiliconFlow, OpenCode, Groq, OpenRouter, etc.)
- 14 free provider models routed through AI Provider Bridge
- 4 provider call functions (Nvidia, Sambanova, Siliconflow, Opencode)
- Branch `release/v3.1-dashboard` pushed to `github.com/specimba/nexusalpha`

### Trust Engine v2.2
HARDWALL defense: logistic scaling, adaptive decay, non-compensatory CRITICAL, 6-stage CDR (Nominal→Caution→Restricted→High Risk→Critical→Collapsed). Baseline 25.0, max 99.5.

### GMR System Design
Full rotation engine, telemetry ingest, savings tracker, domain mapping with fallback chains. 74 online models across 10 providers. 15 local Ollama models (62.2 GB).

### .pi/ Agent Workspace
Full architecture deep-dive, expert report synthesis, swarm team design, model registry, rotation table, critical integration review. Pi Agent profile with 6 task patterns.

### STRES5.0 Research
10 new dimensions from 28 forked repos: decensored models, payload conversion matrix, synthetic agent traces, orchestration schema, multi-provider stress, PDF injection, dimension-aware rubrics, data darwinism, speculative decoding probe, MCP tool attacks.

### STRES6.0 (TAMAS Integration)
6 attack types × 3 interaction topologies × 5 domains. 12 base scenarios, 6,840 total rows. ERS metric.

### STRES6.1 (Tool Taxonomy Expansion — NEW 2026-05-15)
Closes the TAMAS tools gap: **240 tools across 12 categories** (vs TAMAS's 211). 7 attack types, 720 base scenarios, 7,200 total rows (3.68 MB). Generator at `benchmarks/stres6_tool_taxonomy.py`. Attack templates per tool category matched to vulnerability profiles.

---

## TESTS

| Suite | Count | Status |
|-------|-------|--------|
| Python pytest | **~1,642 collected** | 0 errors (fixed 2026-06-10) |
| Security tests | 63 | All passing (meta_attack_detector) |
| Governor tests | 430+ | All passing |
| Dashboard lint | 0 errors | Clean |

---

## GIT HISTORY CLEANUP (2026-05-15)
- **Confluent key** `7OUV257I7PW3AQ4C` scrubbed from `clean/security-phase-0` history via git-filter-repo
- **.env** (with API keys) removed from `clean/security-phase-0` history
- **AZURE_GROK_API_KEY** never committed (only existed locally) — quarantined to `.brv/azure_archive/`
- Full backup: `.brv/git_history_backup/nexus_full_2026-05-15.bundle` (312 MB)
- Other branches (master, main, etc.) have unrelated history and still contain old keys — add to cleanup if needed

---

## WHAT'S DEAD / QUARANTINED

| Asset | Status | Archive Location |
|-------|--------|-----------------|
| Azure subscription | DEAD | `.brv/azure_archive/` |
| Azure AI Gateway (nexus-os-gateway.azure-api.net) | DEAD | same |
| Azure Foundry (rg-OSMANclaw2) | DEAD | same |
| 13 Azure models (Claude Opus 4.7, DeepSeek R1, etc.) | DEAD | same |
| AZURE_GROK_API_KEY | DEAD | same |
| 3 Horsemen Foundry strategy | CANCELLED | same |
| `register_foundry_datasets.py` | DEPRECATED | Header updated |
| `custom_evaluators.py` | DEPRECATED | Header updated |
| v4 plans directory (stale build artifact) | IGNORED | Untracked, .pyc only |
| `docs/usefulthings-01/` (160 stale .pyc files) | ARCHIVED | `.brv/archive_static/docs-usefulthings-01/` |
| `download/` QA screenshots (34 PNG, 3.7 MB) | ARCHIVED | `.brv/archive_static/download/` |
| `session-ses_1e41.md` (590 KB session log) | ARCHIVED | `.brv/archive_static/` |
| `NEXUS.zip` + `NEXUS.zip.tmp` + `docs.zip` | ARCHIVED | `.brv/archive_static/` |
| `Modelfile` (Ollama local config) | ARCHIVED | `.brv/archive_static/` |

---

## WHAT'S PRESERVED (NEXUS-internal "Foundry" — NOT Azure)
- Prisma `FoundryAgent` model — local joker lane agents
- `src/app/api/foundry/route.ts` — uses ZAI SDK, not Azure
- Swarm/Foundry UI components — purely internal concept

---

## COLD STORAGE POLICY (June 10, 2026)

**Rationale:** NEXUS contains proprietary model weights, adversarial datasets, red-team research, and encrypted credentials. These are valuable intellectual property that must remain air-gapped from public repos.

**Rule:** These directories are `.gitignore` excluded and backed up to `D:\NEXUS_COLD`:
- `datasets/` (1.07 GB, 1,298 files)
- `models/` (27.17 GB, 3,236 files)
- `research/` (1.33 GB, 449 files)
- `benchmarks/` (2.78 GB, 281 files)
- `logs/` (minimal, 53 files)
- `upload/` (0.04 GB, 71 files)
- `vault/` (minimal, 9 files)

**Total:** ~31.33 GB across 5,397 files

**Backup Tool:** `scripts/cold_storage_backup.py` — Full copy with BLAKE3/SHA-256 verification, manifest generation, pruning (keep last 3).

**Latest Backup:** `D:\NEXUS_COLD\level7_backup_20260610\NEXUS` — Verified 5,397/5,397 files.

---

## CRITICAL BLOCKERS

1. **Azure sub blocked** — All cloud model routing, Foundry pipelines dead. Need alternative inference strategy.
2. ~~**2 test import errors**~~ ✅ **FIXED 2026-05-15** — ~1,642/430+ verified passing
3. **Dashboard needs real Python governance API** — Still using mock/proxy layer on port 3000
4. ~~**DoppelGround gitleaks**~~ ✅ **RESOLVED 2026-06-10** — False positive from months ago, NOT a current blocker
5. **Key still in old branches** — master, main branches not scrubbed
6. **AsyncBridgeExecutor is a stub** — `executor.py:115`, production executor not wired
7. **CVAVerifier is a stub** — `governor/base.py:329`, CVA always passes
8. **43 repair scripts in scripts/** — evidence of ongoing breakage cycles
9. **Cold storage operational** — D:\NEXUS_COLD level7 backup created (31.33 GB, 5,397 files)

---

## WHERE WE LEFT OFF

The **last active work** (from `session-ses_1e41.md`, 6,186 lines) was:
- **STRES6.0 TAMAS integration** — Successfully generated 6,840 rows across 3 topologies, 7 attack types
- **Session mid-conversation** — User was asking about TAMAS's "211 tools" and acknowledging "we are only behind at tools"

The **largest completed work items before that:**
1. v4 stress lab dataset regeneration (536K rows)
2. v5 frontier dataset generation (181K rows)  
3. 12 API provider integration
4. Dashboard 8+1 tab completion
5. Phase 0 security module
6. Full dashboard QA (34 screenshots, archived to `.brv/archive_static/download/`)

---

## GUARD MODEL RESEARCH (From ARCHIVIST + NEXUSlogs, June 10)

**VRAM Budget Scenarios for 8GB GPU:**

| Scenario | Models | Total VRAM | Notes |
|----------|--------|-----------|-------|
| Minimal (1.5GB) | GLiGuard-300M + Llama-PG2 | 0.8 GB | Fast reject + injection detect |
| Standard (2GB) | GLiGuard-300M + Llama-PG2 + ShieldGemma 2B | 2.3 GB | Generalist safety classifier added |
| Stretch (4GB) | GLiGuard-300M + ShieldGemma 2B + Euler-Guardian 3B | 4.4 GB | Agent security analysis + mitigation mapping |

**Key Guard Models (with one-sentence USP):**

| Model | Size | VRAM | One-Sentence Advantage |
|-------|------|------|--------------------------|
| Llama-Prompt-Guard-2 | 86M | ~0.2 GB | DeBERTa-v2-based injection/jailbreak detector — smallest viable guard, cached locally |
| Arch-Guard | 300M | ~0.6 GB | Highest jailbreak TPR (88.87%) with near-zero FPR (0.30%) — jailbreak specialist |
| GLiGuard-300M | 300M | ~0.6 GB | 23-90x smaller than LlamaGuard with 87.7 F1 — multi-task prompt harmfulness in one pass |
| RoBERTa-Jailbreak | ~125M | ~0.3 GB | Lightweight jailbreak-specific detector built on RoBERTa |
| BERT-tiny Injection | 15M | ~0.1 GB | Ultra-light 2-layer BERT for prompt injection — 40ms GPU inference |
| ShieldGemma 2B | 2B | ~1.5 GB | Google's fine-tuned Gemma 2 with 4 safety policy categories — strongest generalist small guard |
| GLiNER2-Large | ~1B | ~1.2 GB | Generalist NER that extracts credentials/commands/paths from tool args without task-specific training |
| Euler-Guardian | ~3B | ~2.5 GB | Agent security analysis model that maps attack graphs to specific mitigation strategies |
| Zen-Guard-Gen | ~1B | ~1.5 GB | General-purpose guardrail system with generative explanation of why prompts are flagged |
| Prototype-Virus-1B | 1B | ~1.5 GB | Merged RP model — best at detecting role-play/impersonation attacks that slip past standard guards |

**Anchored Base (FunctionGemma + BashGemma):**
- FunctionGemma 270M (~0.75 GB with BashGemma) = control plane function calling
- BashGemma 270M = tool-calling SLM
- Total: ~0.75 GB, leaving 3.25-7.25 GB for guard models depending on scenario

## PORT MAP

| Port | Service | Protocol | Status |
|------|---------|----------|--------|
| 3000 | WSL Relay | TCP | ONLINE (NOT Next.js) |
| 3001 | Next.js Dashboard | HTTP | CONFIGURED (reconfigured from 3000) |
| 7352 | ModelRelay / Nexus API | HTTP | ONLINE — 99 UP, Arena-calibrated scores |
| 7353 | TWAVE wrapper | HTTP | `/twave/*` — wrapper-only, HOLD |
| 7354 | GROSS MCP Bridge | HTTP | ONLINE — 10 tools, SSE transport, read-only |
| 7356 | HTML Dashboard | HTTP | Quality × Health Matrix |
| 7357 | God Mode Proxy v3 | HTTP | FastAPI, 7 profiles, GLM 5.1 selected |
| 3003 | WebSocket mini-service | Socket.io | Dashboard socket layer |
| 11434 | Local Ollama | HTTP | GPU 8GB VRAM, ~35% utilization |
