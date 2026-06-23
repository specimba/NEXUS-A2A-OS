# NEXUS OS — Canonical Knowledge Base

**Compiled:** 2026-06-13 | **Branch:** codex/specimba/1805mainSpeci | **HEAD:** Sprints 0-4 Complete (2237+ tests pass)

<!-- CANARY: 7a14b495084935aa0985a638734cf0bb -->
<!-- UPDATED: 2026-06-13 by Sprint 3 Execution -->
---

## PROJECT IDENTITY

Nexus OS is a governed, local-first agent operating system. Python/FastAPI governance is canonical. Next.js dashboard (port 3000) is the UI proxy. Windows = control/authoring plane; Linux/WSL = execution sandbox.

---

## 8-PILLAR ARCHITECTURE

| Pillar | Path | Purpose |
|--------|------|---------|
| Bridge | `nexus_os/bridge/` | JSON-RPC server, SDK, secrets, MCP auth, vault bridge |
| Governor | `nexus_os/governor/` | KAIJU gates, TrustEngine v2.2, VAP proof chain, compliance |
| Vault | `nexus_os/vault/` | 8-channel memory (SENSORY/WORKING/EPISODIC/SEMANTIC/PROCEDURAL/TRUST/TASK/META), encryption |
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

### Phase 2: NEXUS-Bench 5-Track Benchmark Suite (June 10, 2026)
- **BenchmarkRunner** — `nexus_os/benchmark/runner.py`: Orchestrates all 5 tracks, SQLite history persistence, regression detection, JSON/Markdown/HTML report generation
- **Governance Track (GOV)** — KAIJU precision test (F1=1.0), TrustEngine drift test (±5% threshold), constitutional coverage, CDR latency test
- **Security Track (SEC)** — MetaAttackDetector (F1=1.0), MisalignmentDetector (80% detection), IntentClassifier (86% accuracy), zero-width Unicode detection (100%)
- **Operations Track (OPS)** — ModelRelay routing accuracy, provider health (62.5% available), SmartPing state machine, God Mode Proxy latency
- **Research Track (R&D)** — Dataset coverage (281 files, 50% domain coverage), intelligence score accuracy (0% delta), provider coverage (5/15), gap closure (5/22 resolved)
- **Integration Track (INT)** — E2E pipeline latency (p50=212ms), VAP proof chain (100% completeness), memory tracks (75% consistency), dashboard freshness (ModelRelay available), MCP bridge (code exists)
- **Status: ALL 5 TRACKS PASS** — GOV 0.911, SEC 0.905, OPS 0.700, R&D 0.845, INT 0.867
- **Draft plans saved** — Behavioral Audit (`nexus_os/audit/BEHAVIORAL_AUDIT_PLAN.md`), Cybersecurity Testing (`nexus_os/ctf/CYBERSECURITY_TESTING_PLAN.md`)

### Phase 0 Security (May 12-14)
- **Terminal Sanitizer** — `src/nexus_os/security/sanitizer.py` (256 lines): TerminalSanitizer (ANSI/VT escape stripper), AgentPTY (dedicated PTY per agent), VerifiableOutput (SHA-256 integrity)
- **AGENTS.md** — Safety-gated autonomous operation rules v2.0 with Pre-Execution Safety Gates (SAFETY-1 through SAFETY-4)
- **AFK Workflow Style** — `docs/handbook/05_NEXUS_AFK_WORKFLOW_STYLE.md`: 5-phase autonomous loop (SCAN→DIGEST→SYNTHESIZE→PRODUCE→VERIFY)
- **Test suite** — 23 security tests in `tests/security/test_sanitizer.py`

### Phase A Emergency Hardening (June 12, 2026)
- **nexusctl doctor/status restored** — `nexusctl/cli.py`: comprehensive diagnostic with module health checks, timestamped reporting, protected workload awareness. No more `legacy_doctor_entrypoint_not_restored`.
- **pytest cache_dir fix** — `pyproject.toml`: `cache_dir = ".tmp/pytest_cache"` prevents WinError 5 access denied on Windows by using a project-local temp directory (already gitignored).
- **PortRegistry** — `nexus_os/bridge/port_registry.py`: thread-safe, JSON-backed, active socket checks, canonical port validation (`3001`, `7350`, `7352`, `7353`, `7354`, `7355`, `7356`, `7357`, `11434`, `11435`, `11436`), stale registration cleanup, health check reporting. Hard rule: `7352` is Brain API only; ModelRelay uses `7350` primary and `7355` fallback.
- **SQLite DB Guard timeout** — `timeout=30.0` added to all `sqlite3.connect()` calls in `db/manager.py`, `bridge/server.py`, `monitoring/token_guard.py`. Prevents deadlock under concurrent schema setup.

### Phase B P1 — CLAW Ecosystem Integration (June 12, 2026)
- **Semia SkillAuditor** — `nexus_os/governor/skill_auditor.py` (320 lines): 4-stage deterministic pipeline (PREPARE → SYNTHESIZE → DETECT → REPORT). 8 default Datalog-style rules: EXEC_UNSAFE_EVAL (CRITICAL), SHELL_UNSAFE_SUBSTITUTION (CRITICAL), NETWORK_ARBITRARY_EGRESS (HIGH), SECRET_UNVALIDATED_READ (HIGH), FILE_ESCAPE_WORKDIR (HIGH), NETWORK_NO_TIMEOUT (MEDIUM), SECRET_LEAK_LOG (MEDIUM), API_DEPRECATED (LOW), DOC_MISSING (INFO). Outputs: JSON, SARIF 2.1.0, Markdown. 36 tests.
- **HeavySkill Parallel Reasoning** — `nexus_os/nexusclaw/brainstorm.py` enhanced: K-trajectory parallel reasoning + deliberation synthesis. Auto-triggers for CRITICAL proposals with <3 participants. Configurable K (default 8), diverse emphasis angles (8 coverage dimensions), confidence-weighted synthesis, cross-validation, error identification. 18 tests.
- **CK-PLUG Confidence Gain** — `nexus_os/governor/token_confidence.py` (110 lines): Token-level confidence gain as optional Q input enhancement. 3 aggregation modes (mean/min/harmonic), `QEnhancer` with configurable blend weight, floor enforcement, logprob conversion. 23 tests.
- **Cross-references**: Paper analysis report (`docs/research/NEXUSCLAW_V1_PAPER_ANALYSIS_2026-06-12.md`), gap analysis (`docs/research/NEXUSCLAW_GAP_ANALYSIS_ANTIGRAV_2026-06-12.md`), Edict investigation (`docs/research/EDICT_DEEP_INVESTIGATION_2026-06-12.md`), CLAW ecosystem report (`docs/research/CLAW_ECOSYSTEM_INVESTIGATION_2026-06-12.md`).

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
| Python pytest (core) | **1,640 collected** | 0 errors, 0 failures, 30 skipped |
| Sprint 3+4 new code | **191/191** | 113 Sprint 3 + 78 Sprint 4 |
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
| 7350 | ModelRelay Node/npm primary | HTTP | `/v1/chat/completions`, provider routing, smart ping |
| 7352 | NEXUS Brain API / Governance | HTTP | FastAPI governance routes + WS; never ModelRelay |
| 7353 | TWAVE wrapper | HTTP | `/twave/*` — wrapper-only, HOLD |
| 7354 | GROSS MCP Bridge | HTTP | ONLINE — 10 tools, SSE transport, read-only |
| 7355 | ModelRelay Python fallback/internal | HTTP | fallback relay, internal health |
| 7356 | HTML Dashboard | HTTP | Quality × Health Matrix |
| 7357 | God Mode Proxy v3 | HTTP | FastAPI, 7 profiles, GLM 5.1 selected |
| 3003 | WebSocket mini-service | Socket.io | Dashboard socket layer |

---

## TRUST-MEMORY-ARCHIVIST INTEGRATION (June 11, 2026)

### Unified Architecture (3-Layer Cognitive Loop)

**Trust** provides the *governance plane* (what is allowed).
**Memory** provides the *data plane* (what is known).
**Archivist** provides the *knowledge plane* (what is learned).

### Key Deliverables

| Component | Files | Status |
|-----------|-------|--------|
| **Trust Anti-Grinding Fix** | `governor/trust_engine_v2.py`, `governor/trust_formulas.py` | Fixed inverted sigmoid, 48 tests pass |
| **Trust Research Paper** | `docs/research/NEXUS_TRUST_FRAMEWORK.md` | 11-element formula, dual-scale (0-1 internal, 0-100 display), anti-grinding theorem |
| **8-Channel Memory** | `vault/memory_channels.py` | SENSORY(0), WORKING(1), EPISODIC(2), SEMANTIC(3), PROCEDURAL(4), TRUST(5), TASK(6), META(7), 42 tests pass |
| **ARCHIVIST Pipeline** | `archivist/import_stage.py`, `compile.py`, `fit.py`, `daemon.py` | 3-stage DoppelGround port, 36 tests pass |
| **Real File Processing** | 1,588 records, 789 wiki-admissible, 8 dossiers | security(65), model(138), benchmark(41), memory(35), trust(32), governance(37), agent(63), multimodal(75) |
| **Integration** | `trust_kernel.py` ↔ `memory_channels.py` | Trust events write to EPISODIC + TRUST channels, governed_memory_broker reads from EPISODIC |

### Test Validation

- **Governor tests:** 164/164 pass
- **Vault tests:** 100/100 pass (including new memory_channels + old memory_tracks backward compat)
- **Archivist tests:** 36/36 pass
- **Benchmark tests:** 31/31 pass
- **Security tests:** 75/75 pass
- **Total:** 406/406 tests pass, zero regression

### Canonical Document Clones

- `docs/research/NEXUS_TRUST_FRAMEWORK.md` → `nexus_os/archivist/canonical/NEXUS_TRUST_FRAMEWORK.md`
- All future high-value docs (≥500 words, structured, novel) auto-cloned to `archivist/canonical/`
| 11434 | Local Ollama | HTTP | GPU 8GB VRAM, ~35% utilization |

---

## CURRENT STATE (2026-06-18, Grounded)

Added 2026-06-18: Verified facts from recent recovery work.

- Team roster: OpenCode CLI / Kilo CLI / Mimo CLI / Cline CLI / Hermes, all routed through NEXUS ModelRelay (`7350` Node/npm primary, `7355` Python fallback/internal). `7352` is Brain API only.
- Step 3.7 Flash grounding review artifact added: `docs/research/STEP_3_7_FLASH_GROUNDING_REVIEW_2026-06-18.md`.
- NEXUSCLAW task files present: `docs/research/NEXUSCLAW_DESIGN.md` and `tasks/pending/2026-06-18-nexusclaw-lane-a-design.task.md`; `nexus_os/claw/` tree also present.
- Recovery work completed: root files restored (`CONTRIBUTING.md`, `ONBOARDING.md`, `PUBLIC_SHARE_ALLOWLIST.toml`, `NEXT_MOVEMENTS_PLAN.txt`, `PROJECT_GROUNDING_LEDGER.md`, `CLAUDE.md`); team/role map corrected; security test counts: 7 test files present and 403/403 security tests green per `01_PROJECT_STATE.md`.
- Active blockers: `models/guards/guard_plane_service.py` source path mismatch with the import path in tests; `PUBLIC_SHARE_ALLOWLIST.toml` placeholder still present; `pm2_nexus.json` intentionally skipped per session decision.
- DWM GPU hog evidence: RTX 4070, internal 240 Hz vs external 74 Hz mismatch, 33+ GPU processes, HAGS disabled; source evidence `ARCHIVIST\dwm_gpu_analysis.md`.

---

## NEXUSCLAW v1 — Multi-Agent Orchestration (June 11, 2026)

NEXUSCLAW v1 is our own multi-agent coordination system — NOT a clone of OpenClaw/SwarmClaw/NemoClaw. Inspired by the design space but built uniquely for NEXUS OS governance, trust, and 8-channel memory integration.

### Architecture

```
┌─────────────────────────────────────────────┐
│         NEXUSCLAW Orchestrator              │
├─────────────────────────────────────────────┤
│  AgentPool → TaskRouter → MessageBus       │
│  BrainstormEngine → Coordinator → Runner    │
│  WorklogSystem → MemoryChannelManager      │
└─────────────────────────────────────────────┘
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| **AgentPool** | `nexus_os/nexusclaw/agent_pool.py` | Registry of all agents (internal + external). Trust-gated registration, capability indexing, lane-based discovery. Auto-discovers 5 internal NEXUS OS agents. |
| **TaskRouter** | `nexus_os/nexusclaw/task_router.py` | Intelligent task matching: capability-based, trust-threshold-aware, load-balanced, success-rate-weighted. 4 strategies: DIRECT, BROADCAST, BRAINSTORM, REDUNDANT. |
| **MessageBus** | `nexus_os/nexusclaw/message_bus.py` | Inter-agent messaging (direct, broadcast, thread reply, system, external). Trust-gated delivery, thread lifecycle, external connector bridge. |
| **BrainstormEngine** | `nexus_os/nexusclaw/brainstorm.py` | Structured multi-agent deliberation: PROPOSE → DISCUSS → VOTE → RESOLVE. Trust-weighted voting, consensus computation, evidence-grounded proposals. 3 modes: OPEN, STRUCTURED, RED_TEAM. |
| **Orchestrator** | `nexus_os/nexusclaw/orchestrator.py` | Central coordination: agent lifecycle, task dispatch, message routing, brainstorm management, runner control, full stats integration. |

### Key Design Decisions

- **Trust-gated everything**: Agents must meet trust thresholds for their lane. High-risk tasks require trust ≥70. Critical tasks require trust ≥90. Humans have trust=100.
- **Capability-based routing**: Tasks declare `required_capabilities`. Router matches agents by capability, lane, trust, availability, success rate, and load.
- **Evidence-grounded proposals**: Brainstorm proposals must include evidence references. High/critical risk proposals require evidence.
- **Human-in-the-loop**: HIGH/CRITICAL risk tasks flag `requires_human_oversight`. Human agents registered with `trust_score=100`.
- **Diverse selection**: BRAINSTORM/REDUNDANT strategies prefer diverse agent types (different lanes, different types) for richer deliberation.
- **All auditable**: Every action logged to worklog triple-sink (EPISODIC + TASK + META memory channels).

### External Agent Support (Designed For)

| Agent | Lane | Capabilities | Trust |
|-------|------|-------------|-------|
| Grok | research | code_search, deep_research | 75 |
| ChatGPT 5.5 | research | text_analysis, wide_range | 80 |
| Notion Opus 4.7 | research | long_form, deep_thinking | 85 |
| Slack Bridge | external | message_dispatch, notification | 50 |
| Human Admin | governance | human_oversight, approval | 100 |

### Test Validation

- **NEXUSCLAW v1 tests:** 192/192 pass (Sprints 0-2)
- **Existing nexusclaw tests:** 97/97 pass
- **Sprint 3 new tests:** 113/113 pass (registry + chromadb + mcp bridge)
- **Sprint 4 new tests:** 78/78 pass (heavyskill relay + deliberation synth + config sync)
- **Circuit breaker tests:** 8/8 pass (indentation fix)
- **Full suite (core):** 1,640/1,640 pass, 0 regressions

## Sprint 3 — P2 Ecosystem (2026-06-13, COMPLETED)

### 1. Model Provider Registry (`nexus_os/models/registry.py`)
Centralized model/provider/domain registry. `ModelRegistry` class seeds from `.pi/models_registry.json` (6 domains, 45+ providers, fallback chains). Selection API: `select_model(domain, prefer_local, min_tier, max_cost)`. Search API: `search_models(query, provider, min_tier, max_cost, status)`. Registration API: `register_provider()`, `register_model()`, `register_domain()`. Singleton via `get_registry()`. 45 tests.

### 2. ChromaDB SEMANTIC Backend (`nexus_os/vault/semantic_backend.py`)
Pluggable `SemanticBackend` ABC with 3 implementations:
- `LocalBackend` — JSON-file keyword search (always available)
- `ChromaBackend` — ChromaDB vector search (soft import, falls back to LocalBackend)
- `HybridBackend` — dual-write, ChromaDB-primary with LocalBackend fallback
- `get_semantic_backend()` / `set_semantic_backend()` global access. Exported from vault `__init__.py`. 24 tests.

### 3. GROSS MCP Governance Bridge (`nexus_os/mcp/client.py` + `nexus_os/bridge/gross_bridge.py`)
`GovernedMCPClient` — JSON-RPC 2.0 client for MCP bridges (port 7354). Trust gate: governance tools blocked when trust < 90. Auto-connect, retry with backoff, SSE support. `GrossMCPBridge` wraps client with Governor/AgentPool registration as `external_mcp` agent. 44 tests.

## Sprint 4 — P3 Polish (2026-06-13, COMPLETED)

### 1. HeavySkill Real API via ModelRelay (`nexus_os/nexusclaw/heavyskill_relay.py`)
`ModelRelayHeavySkill` adapter calls `POST /v1/chat/completions` on ModelRelay for trajectory generation, scoring, and synthesis with 8 emphasis angles. Falls back to mock (`generate_mock_trajectory`, `score_mock`, `synthesize_mock`) when ModelRelay unreachable. `TrajectoryScore` and `SynthesisOutput` dataclasses. Singleton via `get_heavy_relay()`. 22 tests.

### 2. Structured Deliberation Synthesis (`nexus_os/nexusclaw/deliberation_synthesis.py`)
`DeliberationSynthesizer` with 5-verdict enum (APPROVE/APPROVE_WITH_CONCERNS/NEEDS_REVISION/REJECT/INCONCLUSIVE), `StructuredDeliberation` result dataclass, `TrajectoryEvaluation` per-trajectory scoring, `SynthesisConfig` thresholds. ModelRelay mode for LLM synthesis ↔ heuristic fallback (confidence-weighted voting). Risk escalation for CRITICAL/HIGH proposals. Bug fix: `_synthesize_ heuristic` → `_synthesize_heuristic`. 18 tests.

### 3. ConfigSyncEngine (`nexus_os/config/sync_engine.py`)
Hierarchical config registry: `ConfigSyncEngine` with `EnvSource` (NEXUS_* vars), `JsonSource` (file load/save), `DataclassSource` (@dataclass fields). Priority ordering (default < env < file < cli), `ConfigEntry`/`ConfigDiff`/`SyncReport`, load/save/sync/diff/export. `discover_ad_hoc_env_vars()` maps 23 known env vars. Singleton via `get_engine()`. Exported from `nexus_os/config/__init__.py`. 38 tests.

### Verification
- **All Sprint 4 tests:** 78/78 pass
- **Core suite:** 1,640 passed, 30 skipped, 0 failures (regression-free)
- **Circuit breaker + deliberation fix:** 2 pre-existing bugs caught and fixed
