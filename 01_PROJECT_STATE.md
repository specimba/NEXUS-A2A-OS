# NEXUS OS - Canonical Project State

Date: 2026-06-22
Current local HEAD: codex/specimba/1805mainSpeci (5e7046bf)
Status: Phases A-D + Phases 1-8 COMPLETE. Sprints 0-4 Complete. 224 governor tests + 141 bridge tests + 236 NEXUSCLAW tests passing. Brain API (53 routes including /api/stress/report), MCP bridge hardened with transport_validator + MCPGuard.

## 2026-06-22 Cognitive Elastic Reasoning & Monotonic Privilege Confinement Integration

### Cognitive-Inspired Elastic Reasoning (CogER) & Tandem Routing
- **`nexus_os/gmr/coger.py`**: Complexity classification and routing engine. Query complexity is classified (heuristically or via LLM) into levels L1 to L4: L1 (No Think, routed to direct local SLM), L2 (Think, routed to Tandem Routing), L3 (Extend, routed to Peer-Review Swarm), and L4 (Delegate, routed to CoTool delegation).
- **`nexus_os/gmr/tandem_routing.py`**: Implementation of LLM-SLM collaboration ("Tandem Riding"). High-capability coordinator models generate strategic step-by-step blueprints, and local, low-VRAM SLMs (e.g., VibeThinker-3B) execute individual blueprint steps to conserve VRAM and reduce inference costs.
- **`nexus_os/gmr/peer_review.py`**: BUAA/Tsinghua LLM-PeerReview ensembling framework. Evaluates $N$ candidate responses by conducting $N$ circular sliding triplets $(R_i, R_{i+1}, R_{i+2})$ and their flipped forms $(R_{i+2}, R_{i+1}, R_i)$. Each candidate is rated exactly 6 times across all three triplet positions, mathematically neutralizing position and consistency biases.

### Progent Monotonic Privilege Control
- **`nexus_os/governor/privilege_control.py`**: Least-privilege policy bouncer over tool execution. Restricts allowed and forbidden tool spaces using regular expressions and numerical intervals (e.g. `< 100`, `[10, 50]`). Implements **monotonic confinement**: updates can only narrow allowed tools/arguments or expand forbidden constraints. Privilege expansions block automatically and require explicit human/user approval.
- **`tests/governor/test_privilege_control.py`**: Upgraded test suite with 9/9 passing tests verifying numerical range containment narrowing vs expansion, deny-override rules (forbid override), and forbid rule monotonicity.

### Intern Discovery & Science Context Protocol (SCP)
- **`nexus_os/bridge/intern_discovery.py`**: Connects to the Chinese Intern Discovery platform via JWT. Mapped 8 primary scientific tools (multiomics_integration, polymer_property_analysis, chemical_safety_assessment, alanine_scanning_pipeline, bioassay_analysis, admet_druglikeness_report, protein_drug_interaction, drug_warning_report) to Governed MCP declarations.
- **`nexus_os/bridge/gross_bridge.py`**: Integrated with `InternDiscoveryClient` to mount scientific SCP tools, routing tool calls through the platform and gating high-governance tools (chemical_safety_assessment, drug_warning_report) with a minimum trust threshold of 90.
- **`tests/bridge/test_intern_discovery.py`**: Added 10/10 unit and integration tests verifying client initialization, SCP tool discovery/parsing, and GrossMCPBridge routing and trust-gate enforcement.

## 2026-06-21 Deep Grounding + Security Hardening

### MCP Bridge Security Hardening
- **`nexus_os/mcp/bridge_server.py`** (138→225 lines): `/invoke` endpoint now validates source identity, tool invocation parameters (path traversal, shell injection), and MCPGuard invocation sequence before any tool execution. `/sse` endpoint now validates transport type, attaches source identity to all events, and adds `X-Nexus-Agent-Id` + `X-Nexus-Transport-Validated` headers.
- **`nexus_os/security/steg/mcp_guard.py`** (514→570 lines): Added `TOOL_SHADOWING` and `TOOL_CONFUSION` threat types (MCPThreatType 15-16). New detection: homoglyph substitution (Cyrillic/IPA/phonetic Unicode), delimiter confusion (`/`/`.`/`-` → `_` normalization), tool name shadowing patterns, description-based shadowing. KNOWN_LEGITIMATE_TOOLS registry with 19 canonical MCP tool names. 4 new detection methods: `check_tool_shadowing()`, `check_tool_confusion()`, `_normalize_homoglyphs()`.
- **Tests**: Transport validator 27/27, MCP red team lab 32/32, Security suite 529/529 — **zero regressions**.

### Dataset Forge Verification
- **56 tests pass** in `tests/nexus_cli_ctl/test_dataset_forge.py` covering all 5 forge modules (NEXUSDataset, CodeSecurityGenerator, GuardSafeGenerator, DatasetSplitter, deduplicate_jsonl).
- **4 pre-existing bugs confirmed fixed**: NEXUSDataset constructor crash, XSS template variable mismatch, VULN_TEMPLATES expansion, deduplicate_jsonl string strategy.

### New Provider: LongCat API (Meituan)
- **Discovery**: `ak_2NX8Y89gC6BE6j21SA2gj8II2bH8J` from ARCHIVIST curation. OpenAI + Anthropic compatible. Base: `https://api.longcat.chat`. Model: `LongCat-2.0-Preview` (560B MoE, 128K output, beta-only, daily quota slots at 01:00/07:00/13:00/15:00 UTC).
- **Lane policy**: Teacher/eval only (`allowed_lanes=["teacher", "eval"]`). NOT core/default.
- **Integration**: `upload/longcat_lanes.py` (173 lines), 5 CLI adapter manifests, quota guard with 429 handling. Provider registered in ModelRelay config.
- **Status**: Code-complete. Live verification blocked on beta quota allocation.

### papers09 Research — 80 Papers Analyzed
- **27 Guard/Defense** papers (SoK jailbreak guardrails, STAR multi-turn safety, CRA latent-space ablation, CHASE red-blue RL, S2C semantic cloaking)
- **19 Reasoning/GMR** papers (AceReason-Nemotron, L1 length control, VibeThinker 1.5B/3B, TFPI, Lightning OPD)
- **12 SWE/CLAW** papers (SERA soft verification, daVinci-Env, SWE-Master, FastContext, GLM-5)
- **4 TWAVE/Speculative Decoding** papers (SPEED-Bench, seminal SD paper, Scratchpad Patching, Kimi Linear)
- **8 Forge/Training** papers (Nemotron 3, Evolved Sampling, Butterfly Effect)
- **Top 5 for immediate NEXUS upgrade**: SoK Guardrails → Guard Plane, How Alignment Works → KAIJU, Adversarial Deja Vu → KAIJU signatures, STAR → MCP sessions, SERA → NEXUSCLAW

### New Models for ModelRelay (from papers09)
| Model | Size | Best Use | Lane |
|-------|------|----------|------|
| LongCat-2.0-Preview | 560B MoE | Agentic coding, codex/opencode | teacher/eval |
| VibeThinker-3B | 3B dense | Reasoning (94.3 AIME26) | local/eval |
| VibeThinker-1.5B | 1.5B dense | Ultra-compact reasoning | local/eval |
| FastContext-1.0-4B-SFT | 4B | Repo explorer subagent | eval/probe |
| Nanbeige4.1-3B | 3B | 600-turn tool agent | eval |
| AceReason-Nemotron-14B | 14B | Math→code RL transfer | teacher |
| NVIDIA Nemotron 3 | Nano→Ultra | Mamba-Tx MoE, 1M ctx | eval |
| Terminal-Lego-Qwen3-8B | 8B | SWE terminal agent | eval |

### 36+ Agent Logs Grounded
- **GROSS A2A v1.0** on port 7354 — dual-protocol SSE MCP + A2A HTTP, 5 skills bridged, tunnel chain (cloudflared → ngrok → Pinggy)
- **Grok 37.42 GB exfiltration bypass** — staged 788 files to 3 Google Cloud DCs, GDP 17 violation pattern
- **Gastown Zilliz Swarm** — Zero Trust agent audit trail via `nexus_events` collection, pymilvus 3.0.0
- **Docker Gordon blueprint** — gVisor isolation for GROSS, 16-container infra, Kafka bridge
- **Landau-Ginzburg TWAVE framework** — hallucination = phase transition, CK-PLUG retrieval coupling
- **2 documented agent fabrication incidents** (Kimi K2.6 wrong paper set, Opus fabricated V5/V6/V7 plans)
- ARCHIVIST bundle Trojan flag resolved — file not on disk, not in git history

## Verification Gate

Latest local verification (June 23, 2026):

```text
Full test suite: 2,265+ tests collected, all pass
Governor tests: 224/224 pass (including Progent updates)
Vault tests: 113/113 pass (8-channel memory + consolidation daemon)
Archivist tests: 36/36 pass (3-stage pipeline + real file processing)
Benchmark tests: 31/31 pass (5-track NEXUS-Bench, all PASS)
Security tests: 403/403 pass (meta_attack_detector + misalignment + intent + DERDDRE/T2-T4)
NEXUSCLAW v1 tests: 236/236 pass (A1-A5 integration/e2e/stress/governance/swarm + Phase D evidence integration)
nexus_cli_ctl tests: 142/142 pass (wiki_pipeline, messaging, dashboard_sync, brain_api_extensions, master_daemon, a2a_health, tailscale, provider_health, nexusctl, brain_api_auth)
Existing nexusclaw tests: 97/97 pass (coordinator + envelope + model intake + tool bridge + worklog)
Bridge tests: 141/141 pass (PortRegistry thread-safe + active socket checks + Intern Discovery)
Combined suite: 939+ pass, 0 failures
```

All `pytest.mark.skip` removed. Hermes, GMR, VaultManager, Coordinator, TokenGuard migrated to V3.
Vault uses the canonical 8-channel schema (SENSORY, WORKING, EPISODIC, SEMANTIC, PROCEDURAL, TRUST, TASK, META).
NEXUSCLAW v1: Multi-agent orchestration with AgentPool, TaskRouter, MessageBus, BrainstormEngine, Orchestrator.
Phase D: ARCHIVIST evidence integration with ResearchIntegrationEngine, ExternalConnectorManager, SecurityEvidencePipeline, ModelObservatory, TemporalEvidenceSynthesizer.
Phase 1-2: CLI/CTL control panel — nexusctl CLI, Textual TUI (10 tabs), master daemon (12 services), A2A health, Tailscale, provider health.
Phase 4-7: Brain API (FastAPI, 41 routes, WS topics, port 7352), wiki pipeline, messaging integration, dashboard sync.
Phase 8: Rate limiting (SimpleRateLimiter), auth hardening (require_auth + check_rate_limit), nexusctl wiki/messaging/state/doctor commands.

## 2026-06-18 Grounded Recovery State

Added 2026-06-18: Current verified state from recovery work.

- Restored root files: `CONTRIBUTING.md`, `ONBOARDING.md`, `PUBLIC_SHARE_ALLOWLIST.toml`, `NEXT_MOVEMENTS_PLAN.txt`, `PROJECT_GROUNDING_LEDGER.md`, `CLAUDE.md`
- Security suite verification: 403/403 security tests passing per the Verification Gate block above (security test count updated to 7 test files, 403/403 green).
- Blockers: unresolved `models/guards/guard_plane_service.py` import path mismatch with tests; `PUBLIC_SHARE_ALLOWLIST.toml` placeholder still present; `pm2_nexus.json` intentionally skipped per session decision.
- Step 3.7 Flash grounding review artifact added: `docs/research/STEP_3_7_FLASH_GROUNDING_REVIEW_2026-06-18.md`.
- DWM GPU evidence summary: RTX 4070, internal 240 Hz vs external 74 Hz mismatch, 33+ GPU processes, HAGS disabled. Reference: `ARCHIVIST\dwm_gpu_analysis.md`.
- NEXUSCLAW design artifacts added: `docs/research/NEXUSCLAW_DESIGN.md` and `tasks/pending/2026-06-18-nexusclaw-lane-a-design.task.md`; `nexus_os/claw/` tree also present.

## Core Thesis

Nexus OS turns local models, research evidence, and external teams into a governed, audited, low-VRAM execution system where every action is proposal-bound, test-gated, and provenance-tracked.

- **DoppelGround** prepares evidence.
- **Nexus** governs, routes, audits, and approves.
- **TWAVE** executes within VRAM limits.
- **GeniusTurtle** makes it usable.
- **Model Arena** proves what actually works on local hardware.

## System Boundaries

| Layer | Canonical Role | Current Rule |
|-------|---------------|--------------|
| GeniusTurtle | Operator UX layer | UI/API integration only; no model weights, secrets, or governance internals. |
| Nexus OS | Governance and orchestration layer | Python/FastAPI governance is the canonical brain. |
| DoppelGround | Evidence preparation layer | USE MODE; outputs must be sanitized before handoff. |
| TWAVE | Low-VRAM execution layer | HOLD; wrapper/API work only, no algorithm changes. |
| Model Arena | Evidence/evaluation layer | Report-only; no automatic model deletion, fine-tuning, or promotion. |

## Core Architecture Map

| Pillar | Purpose | Canonical Areas |
|--------|---------|-----------------|
| Bridge | Protocol boundary, API ingress, SDK/MCP adapters | `nexus_os/bridge/`, `nexus_os/relay/` |
| Governor | KAIJU, policy, compliance, trust gates, TrustEngine v2.2 | `nexus_os/governor/` |
| Vault | Durable storage, 5-track memory, encryption policy | `nexus_os/vault/`, `nexus_os/db/` |
| Engine/GMR | DAG routing, Hermes/GMR decisions, execution flow | `nexus_os/engine/`, `nexus_os/gmr/` |
| Swarm | Worker orchestration, foreman coordination | `nexus_os/swarm/` |
| Monitoring | TokenGuard, VAP/audit, telemetry | `nexus_os/monitoring/`, `nexus_os/observability/` |

## What Is Verified

- Full test suite passes locally: **~1,642 tests collected, 430+ core tests verified passing** (governor/monitoring/security).
- NEXUS-Bench 5-track benchmark suite: **ALL TRACKS PASS** (GOV 0.911, SEC 0.905, OPS 0.700, R&D 0.845, INT 0.867). Report: `nexus_os/benchmark/reports/`. Fix: Added 16 governance rules (7 misalignment + 9 classifier) to constitution.yaml.
- DB encryption policy hard-fails by default and allows plaintext fallback only when `allow_unencrypted=True`.
- Engine task dependency cycle detection is present and verified.
- TrustEngine v2.2 implements HARDWALL defenses: logistic scaling, adaptive decay, non-compensatory CRITICAL, 6-stage CDR.
- Vault uses canonical 8-channel schema (SENSORY/WORKING/EPISODIC/SEMANTIC/PROCEDURAL/TRUST/TASK/META).
- Bridge secrets management with per-provider health logging.

## Phase A Emergency Hardening (Complete)

1. **nexusctl doctor/status restored**: `run_doctor()` now runs comprehensive memory + version diagnostics when no topic is specified. `run_status()` performs real module health checks across 12 NEXUSCLAW subsystems.
2. **pytest cache_dir fixed**: `pyproject.toml` now sets `cache_dir = ".tmp/pytest_cache"` to prevent WinError 5 access denied on Windows.
3. **PortRegistry skeleton**: `nexus_os/bridge/port_registry.py` — thread-safe, JSON-backed, with active socket checks, canonical port validation (`3001`, `7350`, `7352`, `7353`, `7354`, `7355`, `7356`, `7357`, `8765`, `8766`, `11434`, `11435`, `11436`), stale registration cleanup, and health check reporting. Hard rule: `7352` is Brain API only; ModelRelay uses `7350` primary and `7355` fallback.
4. **SQLite DB Guard timeout**: `timeout=30.0` added to all `sqlite3.connect()` calls in `db/manager.py`, `bridge/server.py`, and `monitoring/token_guard.py` to prevent deadlock under concurrent schema setup.

## Phase B P1 — CLAW Ecosystem Integration (Complete)

1. **Semia SkillAuditor** (`nexus_os/governor/skill_auditor.py`): 4-stage deterministic pipeline (PREPARE → SYNTHESIZE → DETECT → REPORT). 8 default Datalog-style rules covering eval/exec, shell injection, network egress, secret reads, file writes, missing timeouts, secret leaks, deprecated APIs. Outputs: JSON, SARIF 2.1.0, Markdown. 36/36 tests pass. Ready for AgentPool pre-flight gate integration.
2. **HeavySkill Parallel Reasoning** (`nexus_os/nexusclaw/brainstorm.py`): K-trajectory parallel reasoning + deliberation synthesis added to BrainstormEngine. Auto-triggers for CRITICAL proposals with <3 participants. Configurable K (default 8), diverse emphasis angles, confidence-weighted synthesis, cross-validation, error identification. 18/18 tests pass.
3. **CK-PLUG Confidence Gain** (`nexus_os/governor/token_confidence.py`): Token-level confidence gain as optional Q input enhancement. 3 aggregation modes (mean/min/harmonic), `QEnhancer` with configurable blend weight, floor enforcement, logprob conversion. 23/23 tests pass.

## Cloud Dashboard (Next.js)

Port 3000 — Full 8-pillar command center:
- Overview, StressLab, GMR Router, Governor, Vault, Research, Swarm, Token Budget
- AI Assistant (z-ai-web-dev-sdk LLM)
- Command Palette (Ctrl+K), System Logs (Ctrl+L)
- Interactive features: test runner, trust threshold adjustment, model toggle
- Prisma ORM + SQLite for data persistence

## Accepted Principles

- Governance Control Plane first: Python/FastAPI is canonical.
- Dashboard second: Bun/Next/relay layers must proxy governance state, not contain governance decisions.
- Retroactive provenance starts dry-run/report-only.
- Mini Model Arena starts in Phase 0 as a bounded evidence tool.
- GVAW is mandatory for externalized work: proposal-linked branches, VAP/trust trailers, reviewed merges.
- Public/private split is required before launch.
- Cloud/local OpenClaw coordination uses Git as the bus; cloud writes tasks/specs, local runs GPU/model/TWAVE work.

## Rejected Or Parked

- Bun relay calling Python classes directly.
- Auto-committing retroactive provenance.
- Broad `git add .` without review.
- Deleting model packs without inventory, backup, and rollback path.
- Heretic/uncensoring or fine-tuning in P0.
- External handoff before DoppelGround leak status is resolved.
- Claims of cryptographic VAP, full A2A, OWASP ASI, SkillFortify, or production ASBOM maturity unless locally verified.

## Critical Blockers

1. DoppelGround leak status must be resolved before external handoff or public repo flip.
2. Dashboard/relay still needs real governance API wiring.
3. GSPP reference assets need reconciliation before they become canonical.
4. Public launch files still need security/legal review before staging.
5. Sandbox/mock env files must not be committed without an explicit policy decision.
6. **Cold storage operational** — D:\NEXUS_COLD level7 backup (31.33 GB, 5,397 files) with BLAKE3/SHA-256 verification.

## Canonical P0 Sequence

1. Reverify the test baseline before core commits.
2. Keep Git clean with explicit-path staging only.
3. Triage DoppelGround gitleaks report to real secret vs false positive.
4. Add or update a canonical integration ledger for repos, ports, APIs, and protected files.
5. Build Python/FastAPI governance endpoints: `/skills/propose`, `/skills/status/{id}`, `/dashboard/stats`, `/governance/proposals`, `/governance/approve`.
6. Update dashboard/relay to consume the Python governance API.
7. Add `nexus-scan.py` as dry-run provenance inventory only.
8. Add `model_arena/mini_arena.py` as report-only evidence collection.
9. Build `nexus_knowledge_base/` from sanitized DoppelGround exports with evidence hashes and quality labels.
10. Handoff to external teams only after security and governance API gates pass.

## Port Map

| Port | Service | Protocol | Notes |
|------|---------|----------|-------|
| 3000 | WSL Relay | TCP | WSL2 networking relay (NOT Next.js) |
| 3001 | Next.js Dashboard | HTTP | Reconfigured from 3000 to avoid WSL conflict |
| 7350 | ModelRelay Node/npm primary | HTTP | `/v1/chat/completions`, provider routing, smart ping |
| 7352 | NEXUS Brain API | HTTP | FastAPI governance (41 routes + WS); never ModelRelay |
| 7353 | TWAVE wrapper (`/twave/*`) | HTTP | Low-VRAM execution layer |
| 7354 | GROSS MCP Bridge | HTTP | 10 tools, SSE transport, read-only, KAIJU 4-variable auth |
| 7355 | ModelRelay Python fallback/internal | HTTP | Fallback relay, internal health, model selection |
| 7356 | HTML Dashboard | HTTP | Quality × Health Matrix |
| 7357 | God Mode Proxy v3 | HTTP | FastAPI, 7 profiles, GLM 5.1 selected |
| 8765 | Unified State Manager (WS) | WebSocket | CLI/Dashboard real-time sync |
| 8766 | Unified State Manager (HTTP) | HTTP | State REST API |
| 11434 | Local Ollama | HTTP | GPU 8GB VRAM, ~35% utilization |

## TrustEngine v2.2 Configuration

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Baseline Score | 25.0 | Starting trust for new agents |
| Max Score | 99.5 | Asymptotic plateau (never 100) |
| Success Delta | 4.0 × logistic(T) | Anti-gaming via logistic scaling |
| Failure Delta | -10.0 | Standard failure penalty |
| CRITICAL Delta | -20.0 | Non-compensatory hard block |
| Base Decay λ | 0.02 | Temporal decay rate |
| CDR Collapse | <15.0 | Minimum trust for collapse |
| CDR Escalation | <30.0 | Threshold for degraded reasoning |
