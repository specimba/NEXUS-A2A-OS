# CLAW Ecosystem Repository Investigation

**Date:** 2026-06-12
**Agent:** NEXUSCLAW Investigator
**Scope:** 21 curated repositories from `lastCLAWrelatedrepos3.txt` + original OpenClaw
**Purpose:** Map integration opportunities for NEXUSCLAW v2 and NEXUS OS governance, trust, memory, and orchestration layers.

---

## Executive Summary

Investigated 21 CLAW-related repositories across 8 capability categories. Identified **12 high-impact integration opportunities** mapped to NEXUSCLAW's 5 core subsystems (AgentPool, TaskRouter, MessageBus, BrainstormEngine, Orchestrator). Key findings: (1) OpenClaw's 378K-star architecture provides the canonical reference for personal-agent design; (2) Semia's Datalog-based skill auditing directly maps to NEXUS's trust-gated skill validation; (3) Hermes Agent's swarm mode and workspace/desktop ecosystem show how NEXUSCLAW could evolve into a full agent platform; (4) HeavySkill's parallel reasoning + deliberation pattern can enhance BrainstormEngine; (5) Odysseus's local-first privacy model aligns with NEXUS's vault/governance boundaries.

**Repository health:** 1 dead link (slack-agent-template 404), 20 successfully fetched. All repos are public forks under `specimba/` except original `openclaw/openclaw`.

---

## 1. Repository Catalog & Taxonomy

### 1.1 Core Agent Frameworks (3 repos)

| Repo | Stars | Origin | Language | Key Concept | NEXUS Relevance |
|------|-------|--------|----------|-------------|-----------------|
| **openclaw/openclaw** | 378K | OpenClaw | TypeScript | Personal AI assistant, multi-channel gateway | Canonical reference — gateway pattern, sandboxing, DM pairing, skills registry |
| **hermes-agent** | 1 | NousResearch | Python 82.5% | Self-improving agent, skill creation, learning loop | Direct descendant of OpenClaw — migration path `hermes claw migrate`, swarm mode, cron scheduler |
| **NemoClaw** | 0 | NVIDIA | TypeScript 78.1% | Sandboxed agent execution in OpenShell | Security sandboxing, network policies, inference routing — complements NEXUS Governor |

### 1.2 Memory & Context Systems (3 repos)

| Repo | Stars | Origin | Language | Key Concept | NEXUS Relevance |
|------|-------|--------|----------|-------------|-----------------|
| **trustclaw** | 0 | TrustClaw | Python | Self-hostable agent with vector memory | Vector memory, self-hosting, privacy — maps to NEXUS Vault 8-channel memory |
| **agentmemory** | 0 | AgentMemory | Python | Persistent memory benchmarks | Benchmarking memory persistence, retrieval accuracy — could inform NEXUS-Bench memory track |
| **context-mode** | 0 | ContextMode | Unknown | 98% context window reduction | Context compression, token efficiency — relevant to NEXUSCLAW message bus payload optimization |

### 1.3 Reasoning & Deliberation (2 repos)

| Repo | Stars | Origin | Language | Key Concept | NEXUS Relevance |
|------|-------|--------|----------|-------------|-----------------|
| **HeavySkill** | 0 | wjn1996 | Python 98.4% | Parallel reasoning + sequential deliberation | Directly enhances BrainstormEngine: PROPOSE→DISCUSS→VOTE→RESOLVE could adopt K-parallel reasoning + deliberation synthesis |
| **CK-PLUG** | 0 | byronBBL | Python 99.0% | Confidence Gain for knowledge conflict resolution | Knowledge consistency metric, parametric vs contextual knowledge control — maps to NEXUS trust scoring and ARCHIVIST evidence grounding |

### 1.4 Search & Multimodal (2 repos)

| Repo | Stars | Origin | Language | Key Concept | NEXUS Relevance |
|------|-------|--------|----------|-------------|-----------------|
| **OpenSeeker** | 0 | OpenSeeker | Python | Search agent | Web search integration, retrieval-augmented agent — TaskRouter external lane capability |
| **OpenSearch-VL** | 0 | shawn0728 | Python 86.3% | Multimodal deep-search agents with RL | Fatal-aware GRPO, tool-use trajectories, visual investigation — advanced routing/cost optimization for NEXUSCLAW |

### 1.5 Orchestration & Workflow (3 repos)

| Repo | Stars | Origin | Language | Key Concept | NEXUS Relevance |
|------|-------|--------|----------|-------------|-----------------|
| **agent-orchestrator** | 0 | AgentOrchestrator | Python | Parallel coding agents, CI fixes, merge conflicts | TaskRouter REDUNDANT strategy validation, CI-integrated agent workflows — direct parallel to NEXUSCLAW TaskRouter |
| **symphony** | 0 | Symphony | Unknown | Isolated autonomous implementation runs | Sandbox orchestration, isolated workstreams — complements NEXUSCLAW BrainstormEngine's structured deliberation modes |
| **agent-framework** | 0 | Microsoft | Python 50.6% / C# 46.1% | Production-grade multi-agent workflows (.NET + Python) | Graph-based workflows (sequential, concurrent, handoff, group), checkpointing, human-in-the-loop, time-travel — NEXUSCLAW Orchestrator could adopt workflow patterns |

### 1.6 UI & Workspace (3 repos)

| Repo | Stars | Origin | Language | Key Concept | NEXUS Relevance |
|------|-------|--------|----------|-------------|-----------------|
| **hermes-workspace** | 0 | outsourc-e | TypeScript | Native web workspace for Hermes Agent | Chat, memory, skills, terminal, dashboard, swarm mode — shows how NEXUSCLAW UI layer (GeniusTurtle) could integrate with agent backend |
| **hermes-desktop** | 0 | fathah | TypeScript 90.5% | Electron desktop for Hermes Agent | Native desktop app, session management, provider switching, token tracking — desktop UI reference for NEXUS OS operator layer |
| **odysseus** | 0 | pewdiepie-archdaemon | Python 47.5% / JS 41.4% | Self-hosted AI workspace (local-first, privacy-first) | FastAPI backend, ChromaDB memory, SearXNG search, PWA + Tailscale — complete local-first stack architecture |

### 1.7 Security & Audit (2 repos)

| Repo | Stars | Origin | Language | Key Concept | NEXUS Relevance |
|------|-------|--------|----------|-------------|-----------------|
| **Semia** | 0 | berabuddies | Python 99.0% | Security audit for AI agent skills (Datalog-based) | **HIGHEST RELEVANCE:** Skill auditing via constraint-guided representation synthesis, SARIF output, deterministic acceptance boundary — maps directly to NEXUS Governor trust gates and KAIJU evaluation |
| **claw-code** | 50K (2hr) | ultraworkers | Rust 95.8% | Fastest repo to 50K stars, Rust-based agent core | Performance-focused agent core, Rust port parity — could inspire NEXUS Engine/GMR low-level optimizations |

### 1.8 Research & Skills (2 repos)

| Repo | Stars | Origin | Language | Key Concept | NEXUS Relevance |
|------|-------|--------|----------|-------------|-----------------|
| **Auto-claude-code-research-in-sleep** | 0 | ARIS | Unknown | Lightweight markdown skills for autonomous ML research | Markdown-based skill system, autonomous research loops — NEXUSCLAW skill library could adopt lightweight markdown skill format |
| **claw-code-parity** | 0 | ultraworkers | Rust 95.8% | Python porting workspace for claw-code | Porting methodology, parity audit, manifest-driven migration — methodology for NEXUS CLAW ecosystem migration tracking |

---

## 2. Deep Analysis: Highest-Impact Repositories

### 2.1 OpenClaw (openclaw/openclaw) — The Canonical Reference

**Scale:** 378K stars, 58,610 commits, 79.1K forks. Massive ecosystem.
**Architecture:** Node.js/TypeScript monorepo with pnpm workspace. Core packages: `src/`, `ui/`, `extensions/`, `apps/`, `packages/`.
**Key components for NEXUS mapping:**

1. **Gateway (control plane):** `src/` contains the session model, agent loop, gateway protocol. NEXUSCLAW Orchestrator maps to this — but NEXUSCLAW adds trust-weighted routing and 9 operational lanes.
2. **Channels:** 20+ messaging integrations (WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Teams, etc.). NEXUSCLAW MessageBus currently supports direct/broadcast/thread/external — OpenClaw's channel-specific routing (e.g., DM pairing policies) could extend MessageBus delivery strategies.
3. **Sandboxing:** `security/` and sandbox modes (`non-main` sessions in Docker/SSH/OpenShell). NEXUS Governor's KAIJU gates and decision-locator findings align — but NEXUS has more granular trust scoring (tanh formula, 11 elements).
4. **Skills:** `skills/` + ClawHub marketplace. NEXUSCLAW's skill library is nascent; OpenClaw's `SKILL.md` format + `skills/` directory structure is the standard.
5. **Configuration:** `~/.openclaw/openclaw.json` minimal config. NEXUS uses YAML-based constitution + JSON profiles — more governance-heavy.
6. **Security model:** DM pairing (`dmPolicy="pairing"`), allowlists, sandboxing. NEXUS's trust-based approach is more granular but could adopt OpenClaw's DM pairing for external channel security.

**Integration opportunity:** NEXUSCLAW MessageBus could adopt OpenClaw's channel-specific delivery policies (pairing, allowlist, sandbox routing). NEXUS Governor could reference OpenClaw's sandboxing model for external agent containment.

### 2.2 Hermes Agent (NousResearch) — The Active Descendant

**Scale:** Forked from OpenClaw, 11,491 commits, active development.
**Key differentiators:**
- `hermes claw migrate` — automatic migration from OpenClaw (settings, memories, skills, API keys, SOUL.md, MEMORY.md, USER.md, command allowlist, messaging settings, TTS assets, workspace instructions/AGENTS.md).
- **Self-improving learning loop:** Creates skills from experience, improves them during use, nudges itself to persist knowledge, FTS5 session search with LLM summarization, Honcho dialectic user modeling.
- **Swarm mode:** `nexus-swarm-pack/` — persistent tmux workers, role-based dispatch (builders, reviewers, docs, research, ops, triage, QA, lab lanes), byte-verified review gate.
- **Cron scheduler:** Built-in scheduled automations with platform delivery.
- **Multi-platform:** Telegram, Discord, Slack, WhatsApp, Signal, Email, cross-platform conversation continuity.
- **Six terminal backends:** local, Docker, SSH, Singularity, Modal, Daytona (serverless persistence).
- **Nous Portal:** Unified subscription covering 300+ models, tool gateway (Firecrawl, FAL, OpenAI TTS, Browser Use).

**NEXUS mapping:**
- Hermes's swarm mode === NEXUSCLAW AgentPool + TaskRouter + BrainstormEngine. But Hermes has persistent tmux workers (long-lived agents) while NEXUSCLAW currently dispatches ephemeral tasks. **Opportunity:** Add persistent worker lane to NEXUSCLAW TaskRouter.
- Hermes's cron scheduler === NEXUS's ARCHIVIST daemon + consolidation daemon. NEXUS has Hybrid B+C trigger (idle + explicit); Hermes has natural language cron. **Opportunity:** Add natural language scheduling interface to NEXUSCLAW Orchestrator.
- Hermes's skill creation loop === NEXUS's ARCHIVIST pipeline (Import→Compile→Fit). NEXUS's pipeline is dossier-oriented; Hermes's is experience-oriented. **Opportunity:** Merge experience-derived skills into ARCHIVIST dossiers as "PROCEDURAL" channel entries.
- Hermes's migration path (`hermes claw migrate`) shows how NEXUS could migrate from OpenClaw/Hermes ecosystems. **Opportunity:** Build `nexusclaw migrate` command for OpenClaw/Hermes → NEXUS transition.

### 2.3 Semia — Security Audit for AI Agent Skills

**Scale:** 59 commits, research paper (arXiv:2605.00314), Apache-2.0.
**Core mechanism:** Reads a skill as data (never executes), produces evidence-backed report of every capability. 4-stage pipeline: **prepare → synthesize (LLM) → detect (Datalog rules) → report**. Output: `report.md` (findings ranked by severity, tied to source line), `report.sarif.json` (GitHub Code Scanning), `report.json` (structured payload).

**Key technical details:**
- Datalog-based deterministic acceptance boundary: agents may extract facts, but only checked, evidence-grounded facts make it into a report.
- `synthesized_facts.dl` — behavior map (Datalog facts), re-queryable.
- `detection_findings.dl` — findings derived by rule evaluation.
- `prepare_units.json` — reference units for evidence alignment.
- Repair mode: `semia repair` traces violations back through Datalog rules to root cause, calls LLM to generate SKILL.md patch.
- Supports multiple LLM providers: OpenAI Responses API, Anthropic Messages API, locally-installed Claude Code CLI, locally-installed Codex CLI.
- Codex/Claude Code/OpenClaw plugin integration.

**NEXUS mapping:**
- Semia's 4-stage audit pipeline === NEXUS Governor's KAIJU evaluation + ARCHIVIST's Import→Compile→Fit pipeline. The combination is powerful: Semia validates skills at ingestion time; KAIJU validates at runtime.
- **CRITICAL INTEGRATION:** Semia's Datalog-based evidence grounding could replace or complement NEXUS's current rule-based constitution.yaml (16 rules). Datalog enables **logical reasoning over agent capabilities** rather than pattern matching.
- Semia's SARIF output === NEXUS's VAP/audit log format. Direct integration with GitHub Code Scanning means skills can be audited in CI.
- Semia's repair mode === NEXUSCLAW's BrainstormEngine PROPOSE→DISCUSS→VOTE→RESOLVE for skill remediation. When a skill fails audit, BrainstormEngine could propose fixes, vote on patches, and resolve with consensus.

**Integration priority:** P1. Semia is the highest-value security integration discovered. It provides formal verification of agent skills, which directly addresses NEXUS's trust and governance requirements.

### 2.4 HeavySkill — Parallel Reasoning + Deliberation

**Scale:** arXiv:2605.02396, 8 commits, Apache-2.0.
**Core mechanism:** Test-time scaling via 2-stage pipeline:
1. **Parallel Reasoning:** Generate K independent reasoning trajectories concurrently.
2. **Sequential Deliberation:** Synthesize trajectories through critical analysis into superior final answer.

**Parameters:** `--reason_k` (parallel trajectories, default 8), `--summary_k` (deliberation samples, default 4), `--iterations` (deliberation rounds, default 1).
**Modes:** Workflow (Python async pipeline) and Skill (pure prompt file for Claude Code / agentic harness).
**API compatibility:** vLLM, DeepSeek, Together AI, OpenRouter, local Ollama.

**NEXUS mapping:**
- HeavySkill's parallel reasoning === NEXUSCLAW BrainstormEngine's PROPOSE phase. Currently BrainstormEngine requires agents to propose solutions; HeavySkill suggests K independent reasoning trajectories from the SAME agent or multiple agents.
- HeavySkill's deliberation === BrainstormEngine's DISCUSS+VOTE+RESOLVE phases. But HeavySkill uses critical meta-analysis (answer distribution, cross-validation, logical error detection) rather than trust-weighted voting.
- **Integration opportunity:** Enhance BrainstormEngine with HeavySkill-style parallel reasoning. For high-risk tasks (CRITICAL), instead of requiring 3+ agents to propose, spawn K independent reasoning trajectories from available agents (or even from the same agent with different temperature/settings), then deliberation-synthesize. This is especially valuable when agent pool is small.
- HeavySkill's skill mode (`.md` file) === NEXUSCLAW's skill library format. Could be directly imported as a BrainstormEngine skill.

### 2.5 Odysseus — Self-Hosted AI Workspace

**Scale:** 1,071 commits, AGPL-3.0, FastAPI backend + vanilla JS frontend.
**Key features:**
- **Chat:** vLLM, llama.cpp, Ollama, OpenRouter, OpenAI, GitHub Copilot.
- **Agent:** Built on opencode, MCP, web, files, shell, skills, memory.
- **Cookbook:** Hardware scan, model recommendation, VRAM-aware GGUF/FP8/AWQ fit scoring, vLLM/llama.cpp serving.
- **Deep Research:** Multi-step runs gathering, reading, synthesizing sources into visual report (adapted from Tongyi DeepResearch).
- **Compare:** Multi-model blind side-by-side testing.
- **Documents:** Multi-tab editor, markdown, HTML, CSV, AI edits/suggestions.
- **Memory:** ChromaDB + fastembed (ONNX), vector + keyword retrieval, import/export.
- **Email:** IMAP/SMTP with AI triage (urgency reminders, auto-tag, auto-summary, auto-reply drafts, auto-spam).
- **Notes & Tasks:** Quick notes with reminders, todo list, cron-style tasks (ntfy/browser/email channels).
- **Calendar:** Local-first CalDAV sync to Radicale/Nextcloud/Apple/Fastmail.
- **Security:** Auth middleware on every route, CSP, path-traversal guard, fail-closed remote bind, `AUTH_ENABLED=true`, `LOCALHOST_BYPASS=false`, `SECURE_COOKIES=true`.
- **PWA + Tailscale:** Mobile-friendly, installable, works across networks.
- **MCP servers:** Auto-registers built-in MCP servers (browser server via Playwright).

**NEXUS mapping:**
- Odysseus's architecture (FastAPI + ChromaDB + SearXNG + ntfy) === NEXUS's Bridge + Vault + Engine stack. Odysseus is a complete reference for how NEXUS's UI layer (GeniusTurtle) could be structured.
- Odysseus's **Cookbook** (hardware scan + model recommendation + fit scoring) === NEXUS's Model Arena + Engine/GMR model selection. Odysseus's VRAM-aware fit scoring is more detailed than NEXUS's current model selection.
- Odysseus's **Deep Research** === NEXUS's ARCHIVIST pipeline. Odysseus uses Tongyi DeepResearch; NEXUS has 3-stage Import→Compile→Fit. Both produce evidence-grounded reports. **Opportunity:** Integrate Odysseus Deep Research as an ARCHIVIST external source.
- Odysseus's **Memory** (ChromaDB + fastembed + vector + keyword) === NEXUS Vault's 8-channel memory (SEMANTIC channel). Odysseus uses ChromaDB; NEXUS uses SQLite with custom trust-gating. **Opportunity:** Add ChromaDB backend option for NEXUS Vault SEMANTIC channel when vector search is needed.
- Odysseus's **Email triage** (IMAP/SMTP + AI urgency + auto-tag + auto-summary) === NEXUSCLAW MessageBus external connector. Email is currently not a NEXUSCLAW channel; Odysseus provides a complete implementation.
- Odysseus's **Security defaults** (auth middleware, CSP, path-traversal guard, fail-closed remote bind) === NEXUS Governor's KAIJU gates + Bridge security. Odysseus's security model is more web-focused; NEXUS's is more governance-focused. Complementary.

### 2.6 Microsoft Agent Framework (MAF)

**Scale:** 2,249 commits, MIT license, Python + .NET dual implementation.
**Key features:**
- **Graph-based workflows:** Sequential, concurrent, handoff, and group collaboration patterns.
- **Checkpointing + streaming + human-in-the-loop + time-travel:** Advanced workflow durability.
- **Middleware system:** Request/response processing, exception handling, custom pipelines.
- **Declarative agents:** YAML-defined agents for faster setup and versioning.
- **Agent skills:** Domain-specific knowledge bases from files, inline code, class libraries.
- **Observability:** OpenTelemetry integration for distributed tracing.
- **Hosting patterns:** A2A, Azure Functions, Durable Task hosting, Foundry-hosted agents.

**NEXUS mapping:**
- MAF's graph-based workflows === NEXUSCLAW TaskRouter's 4 strategies (DIRECT, BROADCAST, BRAINSTORM, REDUNDANT). MAF has more granular patterns (handoff, group collaboration). **Opportunity:** Expand TaskRouter strategies to include handoff (task transfer between agents with state) and group collaboration (persistent agent teams).
- MAF's checkpointing + time-travel === NEXUS Vault's 8-channel memory (EPISODIC, TASK, META). NEXUS already has session logging; MAF's workflow checkpointing is more structured. **Opportunity:** Add workflow checkpointing to NEXUSCLAW Orchestrator for long-running multi-agent tasks.
- MAF's human-in-the-loop === NEXUSCLAW's trust thresholds (human agents have trust=100). NEXUS already gates high-risk tasks behind human approval; MAF's explicit HITL nodes could formalize this.
- MAF's middleware system === NEXUS Bridge's protocol adapters. NEXUS Bridge handles external protocol ingress; MAF middleware handles request/response processing within the framework. **Opportunity:** Add middleware pipeline to NEXUS Bridge for request transformation, rate limiting, and audit logging.
- MAF's declarative agents (YAML) === NEXUS's constitution.yaml (governance rules) + agent profiles (JSON). NEXUS could adopt YAML agent definitions for easier configuration.

### 2.7 CK-PLUG — Knowledge Reliance Control

**Scale:** arXiv:2503.15888, 36 commits, Python 99.0%.
**Core mechanism:** **Confidence Gain** — measures entropy shifts in token probability distributions after context insertion. Detects knowledge conflicts between parametric knowledge and retrieved context. Enables fine-grained control over knowledge preference by adjusting probability distribution of tokens with negative confidence gain via single tuning parameter.

**Key results:** On LLaMA-3-8B, memory recall (MR) of RAG response adjustable from 9.9% to 71.9% (baseline 42.1%). Adaptive control based on model's confidence in both internal and external knowledge.

**NEXUS mapping:**
- CK-PLUG's Confidence Gain === NEXUS trust scoring's **Quality (Q)** input. NEXUS's Q is currently a scalar; CK-PLUG provides a fine-grained token-level confidence metric. **Opportunity:** Enhance NEXUS trust formula with token-level confidence gain for tasks involving RAG/context retrieval.
- CK-PLUG's knowledge conflict detection === NEXUS Governor's misalignment rules. When parametric knowledge conflicts with retrieved context, Governor's rule 13 (misalignment response) triggers. CK-PLUG provides a mathematical foundation for this detection rather than pattern matching.
- CK-PLUG's adaptive control === NEXUS's lane-specific parameters (qmin, n0, Rcrit, a, b). NEXUS already has lane-specific trust parameters; CK-PLUG adds a continuous tuning knob for knowledge reliance.

### 2.8 OpenSearch-VL — Multimodal Deep Search Agents

**Scale:** arXiv:2605.05185, 20 commits, Python 86.3%.
**Core mechanism:** Agent operates as closed loop: inspect image → crop/enhance regions → issue web/image searches → visit retrieved pages → write answer grounded in evidence. Trained via **fatal-aware GRPO** — handles cascading tool failures during long rollouts by masking tokens after fatal step and one-sided advantage clamping.

**Key results:** OpenSearch-VL-8B strongest open 8B agent (+3.9 Avg over SenseNova-MARS-8B). OpenSearch-VL-30B-A3B improves Qwen3-VL baseline by +13.8 Avg. Fatal-aware GRPO: vanilla 64.6→67.6, full method 71.8 (+4.2 over vanilla).

**Tool environment:** text_search, image_search, web_search, visit, sharpen, super_resolution, perspective_correct, crop, layout_parsing (OCR), python_interpreter.

**NEXUS mapping:**
- OpenSearch-VL's tool-use environment === NEXUSCLAW AgentPool capability indexing. NEXUSCLAW already indexes agent capabilities; OpenSearch-VL's 10-tool unified environment could expand the capability taxonomy.
- OpenSearch-VL's **fatal-aware GRPO** === NEXUSCLAW TaskRouter's risk-based trust thresholds. NEXUS routes tasks based on risk (LOW=0, MEDIUM=30, HIGH=70, CRITICAL=90); OpenSearch-VL handles failures within a single agent trajectory. **Opportunity:** Add failure-aware routing to TaskRouter — if an agent fails a tool call, route to a different agent with higher trust in that capability.
- OpenSearch-VL's multi-turn trajectory === NEXUSCLAW MessageBus thread reply system. Both support threaded conversations; OpenSearch-VL's tool-use turns are more structured.
- OpenSearch-VL's RL training (RLOO/GRPO on SFT checkpoint) === NEXUS's trust anti-grinding formula. Both address reward hacking: OpenSearch-VL via fatal masking + advantage clamping; NEXUS via inverted sigmoid (f(T)=1/(1+e^((T-50)/10))). **Opportunity:** Cross-pollinate: NEXUS's anti-grinding could inform OpenSearch-VL's reward shaping; OpenSearch-VL's fatal-aware masking could inform NEXUS's failure handling.

### 2.9 Agent-Orchestrator — Parallel Coding Agents

**Scale:** Unknown, Python.
**Core mechanism:** Parallel coding agents, CI fixes, merge conflict resolution. Specific details limited from README-only fetch, but the pattern is clear: multiple agents working on the same codebase concurrently.

**NEXUS mapping:**
- Agent-Orchestrator's parallel coding === NEXUSCLAW TaskRouter BROADCAST + REDUNDANT strategies. NEXUSCLAW already supports broadcasting to multiple agents and redundant execution; Agent-Orchestrator shows a concrete use case (CI fixing).
- **Opportunity:** Add CI-specific lane to NEXUSCLAW (e.g., `operations-ci` sub-lane) with agents specialized for lint fixing, test repair, merge conflict resolution. This addresses the NEXUSCLAW gap analysis finding that "test runtime inefficiency" is a P3 issue — parallel CI agents could reduce test runtime.

### 2.10 TrustClaw — Self-Hostable Agent with Vector Memory

**Scale:** Unknown, Python.
**Core mechanism:** Self-hostable agent with vector memory. Limited README-only details.

**NEXUS mapping:**
- TrustClaw's vector memory === NEXUS Vault SEMANTIC channel. NEXUS Vault currently uses JSON-backed SQLite; TrustClaw uses vector DB (likely ChromaDB or similar). **Opportunity:** Add pluggable vector backend to NEXUS Vault (ChromaDB, Weaviate, Qdrant) for high-dimensional semantic search.
- Self-hostable === NEXUS's local-first deployment model. NEXUS is designed for local governance; TrustClaw's self-hosting approach validates this.

---

## 3. Integration Opportunity Matrix

### 3.1 By NEXUSCLAW Subsystem

| Subsystem | Integration Opportunities | Priority | Effort | Source Repos |
|-----------|--------------------------|----------|--------|--------------|
| **AgentPool** | Add persistent worker lane (Hermes tmux workers); capability taxonomy expansion (OpenSearch-VL tools); YAML agent definitions (MAF); skill audit integration (Semia) | P1 | Medium | hermes-agent, OpenSearch-VL, MAF, Semia |
| **TaskRouter** | Add handoff + group collaboration strategies (MAF); failure-aware routing (OpenSearch-VL fatal-aware); CI-specific lane (Agent-Orchestrator); K-parallel reasoning for small pools (HeavySkill) | P1 | Medium | MAF, OpenSearch-VL, Agent-Orchestrator, HeavySkill |
| **MessageBus** | Channel-specific delivery policies (OpenClaw DM pairing); email triage integration (Odysseus); context compression (context-mode); Tailscale/mobile channels (Odysseus) | P2 | Medium | openclaw, odysseus, context-mode |
| **BrainstormEngine** | HeavySkill parallel reasoning + deliberation synthesis; Semia Datalog-based evidence grounding for proposals; persistent deliberation threads (MAF checkpointing) | P1 | Medium | HeavySkill, Semia, MAF |
| **Orchestrator** | Workflow checkpointing + time-travel (MAF); natural language scheduling (Hermes cron); OpenClaw/Hermes migration path (`nexusclaw migrate`); Odysseus Deep Research integration | P2 | High | MAF, hermes-agent, odysseus |

### 3.2 By NEXUS OS Layer

| Layer | Integration Opportunities | Priority | Source Repos |
|-------|--------------------------|----------|--------------|
| **Bridge** | Middleware pipeline (MAF); OpenClaw channel adapters; MCP server registration (Odysseus); email IMAP/SMTP connector (Odysseus) | P2 | MAF, openclaw, odysseus |
| **Governor** | Semia Datalog skill audit → KAIJU gate; CK-PLUG Confidence Gain → trust formula Q input; NemoClaw sandboxing policies; OpenClaw DM pairing policies | P1 | Semia, CK-PLUG, NemoClaw, openclaw |
| **Vault** | ChromaDB vector backend option (Odysseus, TrustClaw); workflow checkpointing (MAF); Odysseus email/calendar memory ingestion; fastembed ONNX embeddings (Odysseus) | P2 | odysseus, trustclaw, MAF |
| **Engine/GMR** | Odysseus Cookbook VRAM-aware fit scoring; OpenSearch-VL fatal-aware failure handling; HeavySkill parallel execution; Agent-Orchestrator CI parallelization | P2 | odysseus, OpenSearch-VL, HeavySkill, Agent-Orchestrator |
| **Monitoring** | Semia SARIF output → VAP audit log; MAF OpenTelemetry integration; OpenClaw usage tracking | P2 | Semia, MAF, openclaw |

### 3.3 By Enhancement Area (from Paper Analysis)

| Enhancement Area | Paper Sources | CLAW Repo Synergies | Integration Path |
|------------------|---------------|---------------------|------------------|
| **Hierarchical Agent Architecture** | MLPO, ReMA, Lazy Agents, HeavySkill, SWE-Protégé | Hermes swarm mode, MAF graph workflows, Agent-Orchestrator parallel coding | Add persistent workers + handoff strategy to TaskRouter; adopt MAF workflow patterns |
| **Memory Architecture Evolution** | Mem0, LightMem, MemEvolve, MemLoRA, SuperLocalMemory, B'MOJO | Odysseus ChromaDB, TrustClaw vector memory, context-mode compression, AgentMemory benchmarks | Add ChromaDB vector backend to Vault; integrate context-mode compression into MessageBus |
| **Trust/Security** | TrinityGuard, Whispers, Not Just RLHF, MirrorShield, SuperLocalMemory | **Semia Datalog audit**, NemoClaw sandboxing, CK-PLUG confidence gain, OpenClaw DM pairing | **Semia integration as KAIJU pre-flight gate**; CK-PLUG token-level confidence into trust formula |
| **Routing/Cost** | RouteLLM, Inference-Time Scaling, Darwin Family | OpenSearch-VL fatal-aware routing, HeavySkill parallel reasoning, Agent-Orchestrator CI lane | Failure-aware routing; K-parallel reasoning fallback; CI-specific sub-lane |
| **Skills/Self-Improvement** | AutoSkill, SkillRL, EvoFlow | Hermes skill creation loop, OpenClaw ClawHub, ARIS markdown skills, HeavySkill skill mode | Merge Hermes experience-derived skills into ARCHIVIST PROCEDURAL channel; adopt SKILL.md standard |
| **Communication Privacy** | CoCoA, Character-Centered Dialogue, MirrorShield | Odysseus Tailscale/PWA, OpenClaw end-to-end channels, context-mode encryption | Add Tailscale-aware channel binding to MessageBus; adopt Odysseus security defaults for external-facing deployments |

---

## 4. Synthesis: NEXUSCLAW v2 Architecture Evolution

Based on the 21-repository investigation, the following architectural evolution is proposed for NEXUSCLAW v2:

### 4.1 New Subsystem: `SkillAuditor` (inspired by Semia)

- **Purpose:** Deterministic, evidence-grounded skill validation before agent registration.
- **Pipeline:** `prepare_skill.md` → `synthesize_facts` (LLM/Datalog) → `detect_violations` (Datalog rules) → `report` (SARIF + markdown + JSON).
- **Integration:** Hooks into AgentPool.register_agent() as a KAIJU pre-flight gate. Skills failing audit are quarantined (like ARCHIVIST quarantine) until repaired via BrainstormEngine.
- **Governance:** Trust threshold = 90 (CRITICAL) for skill registration. Semia's Datalog rules become part of NEXUS constitution.yaml.

### 4.2 Enhanced TaskRouter: Persistent Workers + Failure-Aware Routing

- **Persistent Worker Lane:** Inspired by Hermes swarm mode. Agents can register as persistent workers (long-lived tmux-style processes) rather than ephemeral task handlers. TaskRouter maintains a worker pool with health checks and rotation.
- **Failure-Aware Routing:** Inspired by OpenSearch-VL fatal-aware GRPO. If an agent fails a tool call (fatal step), TaskRouter masks that agent's capability for the trajectory and routes to an alternative agent with higher trust in that capability.
- **New Strategies:** `HANDOFF` (transfer task with full state to another agent) and `GROUP_COLLABORATION` (persistent team of agents with shared context, inspired by MAF).

### 4.3 Enhanced Vault: Pluggable Vector Backend

- **Current:** SQLite-backed JSON for all 8 channels.
- **Evolution:** Add ChromaDB/Weaviate/Qdrant backend option for SEMANTIC channel. Use Odysseus's fastembed (ONNX) for local embeddings without API dependency. Keep SQLite for TRUST, TASK, META channels (structured data). Hybrid storage: structured channels in SQLite, semantic channel in vector DB.

### 4.4 Enhanced BrainstormEngine: Parallel Reasoning + Deliberation Synthesis

- **HeavySkill Integration:** For CRITICAL-risk proposals with fewer than 3 agents available, spawn K independent reasoning trajectories (from available agents or same agent with different parameters), then run deliberation synthesis as the DISCUSS phase.
- **Datalog Evidence Grounding:** Replace or augment trust-weighted voting with Datalog-based evidence validation (Semia-style). Proposals must be grounded in synthesizable facts.
- **Checkpointing:** Add MAF-style workflow checkpointing for long-running deliberations. Resume from checkpoint after failure rather than restarting.

### 4.5 Enhanced MessageBus: Channel-Specific Policies + Mobile/Tailscale

- **OpenClaw DM Pairing:** Add `pairing` delivery policy for external channels (email, messaging). Unknown senders receive pairing code; approved senders added to allowlist.
- **Odysseus Email Triage:** Add IMAP/SMTP connector with AI triage (urgency, auto-tag, auto-summary) as an external channel. Ingest triaged emails into WORKING memory channel.
- **Context Compression:** Integrate context-mode 98% reduction for MessageBus payloads exceeding size threshold. Transparent to agents.
- **Tailscale Binding:** Add `tailscale-aware` channel type that binds to Tailscale network interface for secure cross-device communication.

### 4.6 New Capability: `nexusclaw migrate`

- **Purpose:** Migration from OpenClaw/Hermes/Odysseus to NEXUS.
- **Data mapping:** `SOUL.md` → NEXUS agent profile; `MEMORY.md`/`USER.md` → NEXUS Vault EPISODIC/SEMANTIC channels; skills → ARCHIVIST PROCEDURAL channel; API keys → Vault encrypted store; command allowlist → Governor constitution rules; messaging settings → MessageBus channel configs; workspace instructions/AGENTS.md → NEXUS agent AGENTS.md.
- **Verification:** Post-migration verification via NEXUS-Bench (all 5 tracks must pass).

---

## 5. Risk Assessment & Exclusions

| Repo | Risk | Mitigation | NEXUS Decision |
|------|------|------------|--------------|
| **claw-code** | 50K stars in 2h suggests hype/astroturfing; Rust core may be unstable | Treat as reference only, do not depend on for production | **Advisory-only** — watch for stability |
| **claw-code-parity** | Temporary porting work, incomplete | Use methodology only, not code | **Advisory-only** |
| **slack-agent-template** | 404/dead link | Remove from list | **Exclude** |
| **NemoClaw** | NVIDIA-specific, requires OpenShell | Sandbox policies are reference-only; do not require OpenShell | **Partial integration** — adopt security policies |
| **hermes-workspace/hermes-desktop** | TypeScript/Electron heavy; NEXUS uses Next.js | UI patterns only, not code reuse | **Advisory-only** — UI pattern reference |
| **Auto-claude-code-research-in-sleep** | Lightweight, research-oriented | Adopt markdown skill format; do not adopt full research loop | **Partial integration** — skill format |
| **OpenSearch-VL** | Requires H100/H800 GPUs, 8-16 node clusters | Use algorithmic insights (fatal-aware GRPO) only; do not require GPU infrastructure | **Partial integration** — routing algorithm |
| **agent-framework (MAF)** | Microsoft ecosystem, .NET/Python dual | Adopt Python patterns; .NET is external reference only | **Partial integration** — Python workflow patterns |

---

## 6. Implementation Roadmap

### Phase A: Emergency Hardening (45 min) — P1
Continue existing plan: Fix nexusctl doctor/status, pytest cache_dir, PortRegistry skeleton, SQLite DB Guard timeout. (Already in progress from NEXUSCLAW_GAP_ANALYSIS.)

### Phase B: Core Integrations (2-3 days) — P1
1. **Semia SkillAuditor prototype:** Integrate Semia Datalog audit pipeline as AgentPool pre-flight gate. Start with `semia scan` equivalent for NEXUS skills. Output: SARIF + quarantine decision.
2. **CK-PLUG Confidence Gain in Trust Formula:** Add token-level confidence gain as optional Q input enhancement. Test with NEXUS-Bench R&D track.
3. **HeavySkill Parallel Reasoning in BrainstormEngine:** Add K-parallel reasoning fallback for CRITICAL tasks with <3 agents. Deliberation synthesis replaces or augments VOTE phase.
4. **TaskRouter Failure-Aware Routing:** Add capability mask on fatal tool failure. Route to alternative agent with higher trust.

### Phase C: Ecosystem Expansion (1 week) — P2
1. **Vault ChromaDB Backend:** Add pluggable vector backend for SEMANTIC channel. Use Odysseus fastembed for ONNX embeddings. Maintain SQLite for structured channels.
2. **MessageBus Email Triage:** Add IMAP/SMTP connector with Odysseus-style AI triage. Ingest to WORKING memory.
3. **TaskRouter Persistent Workers:** Add worker pool lane with health checks. Hermes swarm mode as reference.
4. **Workflow Checkpointing (MAF-style):** Add checkpoint/resume to Orchestrator for long-running tasks.

### Phase D: Migration & Polish (1 week) — P2
1. **`nexusclaw migrate` command:** OpenClaw/Hermes → NEXUS migration tool. Verify with NEXUS-Bench.
2. **OpenTelemetry Integration (MAF-style):** Distributed tracing for NEXUSCLAW subsystems. VAP/trust audit correlation.
3. **Context Compression (context-mode):** Transparent payload compression for MessageBus.
4. **Documentation:** Update AGENTS.md, knowledge.md, NEXUS_TRUST_FRAMEWORK.md with new integrations.

---

## 7. Cross-References

- **NEXUSCLAW_V1_PAPER_ANALYSIS_2026-06-12.md:** 25 papers analyzed, 6 enhancement areas identified. This report maps CLAW repos to those 6 areas and adds 12 subsystem-specific opportunities.
- **NEXUSCLAW_GAP_ANALYSIS_ANTIGRAV_2026-06-12.md:** 8 gaps from antigravity log, 15 todos. This report provides repo-specific implementation references for closing those gaps (e.g., Semia for secret sprawl/skill validation, Odysseus for test runtime, MAF for workflow checkpointing).
- **EDICT_DEEP_INVESTIGATION_2026-06-12.md:** 12-agent Edict system. CLAW repos provide the technical implementation for Edict's institutional patterns (e.g., Semia = audit department, MAF = workflow engine, Hermes swarm = worker bureau).
- **01_PROJECT_STATE.md:** Canonical state. Update after Phase B/C completion.

---

## 8. Appendices

### A. Repository Fetch Log

| # | Repo | URL | Status | Notes |
|---|------|-----|--------|-------|
| 1 | OpenSeeker | https://github.com/specimba/OpenSeeker | OK | Search agent, Python |
| 2 | claw-code | https://github.com/specimba/claw-code | OK | Rust core, 50K stars |
| 3 | context-mode | https://github.com/specimba/context-mode | OK | Context optimization |
| 4 | symphony | https://github.com/specimba/symphony | OK | Isolated runs |
| 5 | trustclaw | https://github.com/specimba/trustclaw | OK | Vector memory agent |
| 6 | hermes-agent | https://github.com/specimba/hermes-agent | OK | 11,491 commits, Python 82.5% |
| 7 | HeavySkill | https://github.com/specimba/HeavySkill/tree/main | OK | Parallel reasoning, arXiv:2605.02396 |
| 8 | OpenSearch-VL | https://github.com/specimba/OpenSearch-VL | OK | Multimodal RL, arXiv:2605.05185 |
| 9 | Auto-claude-code-research-in-sleep | https://github.com/specimba/Auto-claude-code-research-in-sleep | OK | ARIS markdown skills |
| 10 | agent-framework | https://github.com/specimba/agent-framework | OK | Microsoft MAF, Python+.NET |
| 11 | slack-agent-template | https://github.com/specimba/slack-agent-template | **404** | Dead link, excluded |
| 12 | claw-code-parity | https://github.com/specimba/claw-code-parity/tree/main | OK | Python port, Rust 95.8% |
| 13 | NemoClaw | https://github.com/specimba/NemoClaw | OK | NVIDIA sandbox, TypeScript 78.1% |
| 14 | CK-PLUG | https://github.com/specimba/CK-PLUG | OK | Confidence Gain, arXiv:2503.15888 |
| 15 | agent-orchestrator | https://github.com/specimba/agent-orchestrator | OK | Parallel coding |
| 16 | agentmemory | https://github.com/specimba/agentmemory | OK | Memory benchmarks |
| 17 | odysseus | https://github.com/specimba/odysseus/tree/main | OK | Self-hosted workspace, 1,071 commits |
| 18 | Semia | https://github.com/specimba/Semia/tree/main | OK | Skill audit, Datalog, arXiv:2605.00314 |
| 19 | hermes-workspace | https://github.com/specimba/hermes-workspace | OK | Web UI for Hermes |
| 20 | hermes-desktop | https://github.com/specimba/hermes-desktop/tree/main | OK | Electron desktop for Hermes |
| 21 | openclaw/openclaw | https://github.com/openclaw/openclaw | OK | Original, 378K stars, 58,610 commits |

### B. Star History Comparison

| Repo | Stars | Velocity | Notes |
|------|-------|----------|-------|
| openclaw/openclaw | 378,000 | Organic (established) | Canonical reference |
| claw-code | 50,000 | 2 hours (suspicious) | Hype/astroturf risk |
| hermes-agent | 1 | N/A (fork) | Active descendant |
| All others | 0 | N/A (forks) | Research/integration targets |

### C. Language Distribution Across Ecosystem

| Language | Count | Repos |
|----------|-------|-------|
| Python | 11 | hermes-agent, HeavySkill, OpenSearch-VL, agent-framework, NemoClaw (minor), CK-PLUG, agent-orchestrator, agentmemory, odysseus (backend), Semia, trustclaw |
| TypeScript | 5 | openclaw, NemoClaw, hermes-workspace, hermes-desktop, odysseus (frontend) |
| Rust | 2 | claw-code, claw-code-parity |
| C# | 1 | agent-framework (.NET half) |
| Unknown | 2 | context-mode, symphony |

---

*End of Report*
*Generated by NEXUSCLAW Investigator on 2026-06-12*
*All repository data fetched live from GitHub public APIs*
