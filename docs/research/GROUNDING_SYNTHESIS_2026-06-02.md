---
id: NODE-MIG-GROUNDING_SYNTHESIS_2026_06_02
authority_scope: experimental
origin_sha256: adaa08fc2ac13fcb0b9ab1ac34652d1aed25f574ddc9f7dde5edd9ebe926c04f
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-B19F16
---
# NEXUS OS Grounding Synthesis — 2026-06-02 (Continuous Mode)

**Source:** Deep ingestion per project-grounding + deep-project-grounding skills (5-phase AFK workflow: SCAN/DIGEST/SYNTHESIZE/PRODUCE/VERIFY).
**Tier Coverage:** Tier 1 canonical (AGENTS.md, NEXUS_AGENT_PROTOCOL.md, 01_PROJECT_STATE.md, knowledge.md, README.md, GROUNDING.md, NEXUS_OS_V4_MASTER_PLAN.md, NEXUS_OS_STATUS_REPORT.md) + key Tier 2 (CURATED_RESEARCH_AND_AGENT_LOGS_SYNTHESIS.md, SYSTEM_AUDIT_REPORT_2026-05-29.md).
**Method:** Targeted search_files + offset/limit read_file batches + parallel calls. No repeated identical reads. Internal synthesis + memory storage. Major checkpoint reached.

## Executive Summary
NEXUS OS is a governed, local-first agent OS with 8-pillar architecture (Bridge, Governor/KAIJU, Vault, Engine/Hermes/GMR, Swarm, Monitoring, Observability, TWAVE). 

**Core Thesis (from V4 Master Plan):** 
- Windows = Control plane + Authoring (VS Code, dashboard, governance, Zo orchestration).
- Linux/WSL/Docker = Execution sandboxes (isolation, GPU, policy enforcement).
- Cloud = Burst capacity (HF Sandbox for large inference/speculative decoding).
Local-first becomes Linux-first for execution; cross-platform via Docker abstraction.

**Current State (from 01_PROJECT_STATE + knowledge + status report):**
- 636+ pytest tests passing (core suite).
- 8-pillar Python/FastAPI governance (nexus_os/ with bridge, db, engine/hermes, governor/trust_engine_v2/kaiju, gmr, vault 5-track, monitoring/token_guard).
- Next.js dashboard (port 3000, 107 TS files, 16k+ LOC, Prisma SQLite, WebSocket, AI assistant).
- Active components: Pi Agent, Docker Gordon (Kafka), Supabase, Grafana/Prometheus, Redis, multiple GitHub repos.
- Historical team: SPECI (arch), CODEX, NEO, GLM, OSMAN, GROK, OPENcode.

**Critical Gaps (Master Plan + reports):**
- No agent sandbox isolation (full FS access, shared terminals).
- Duplicate governance code (KAIJU, VAP, TokenGuard, Archivist in NEXUS main + HERMES swarm pack).
- No cross-agent prompt injection protection (terminal poisoning incident via ANSI escapes).
- No hallucination detection layers.
- No E2E encryption for agent comms.
- Windows-hardcoded paths, no unified deployment.
- Recent forensic (Curated report): 39GB upload queue with potential creds (GCS, Cloudflare/x.ai, Notion) from grok.exe — flagged unsafe.
- Host audit (2026-05-29): High resource use (Chrome 3.5GB, Devin/OpenCode/ERNIE AI tools, WSL vmmem, Docker, Defender). AWCC (Alienware) bloat (8 processes, high events) targeted for removal. BitTorrent in startup.

## Architecture Highlights from V4 Master Plan
**Sandbox (Section 4):**
- SandboxBackend abstraction: SubprocessLocal, DockerContainer (primary), Podman, OpenShell (kernel-level from swarm pack, Gastown), HuggingFaceSandbox (cloud burst), WSL2.
- Lifecycle: KAIJU gate → SandboxPool.allocate (with capability tokens, TTL) → execute (OpenShellExecutor) → VAP log → deallocate/destroy (no state persist unless Vault commit).
- Disposable containers: fresh per run, read_only FS, cap_drop ALL, tmpfs, no API keys injected.
- OpenShell policies import from HERMES swarm (codex_exec, opencode_analysis, inference_local).
- HF integration for large models/spec decoding when local insufficient.

**Security (Section 5):**
- Threat: Cross-Agent Terminal Injection (CWE-150). Agent A outputs ANSI escapes to shared terminal → Agent B context poisoned → bad decisions.
- Layers:
  1. TerminalSanitizer: Regex strips C0 controls (except \n\t\r), CSI (ESC[), OSC (ESC]), other ESC, app keys.
  2. AgentPTY: Dedicated pseudo-terminal per agent (os.openpty), sanitize on read/write. No shared sessions.
  3. VerifiableOutput: SHA-256 content hash per output. Verify before use.
  4. KAIJU cross-agent eval: Check source trust score, content hash integrity; DENY/HARD_STOP on issues.
- SOVEREIGN mode: CRITICAL risk. Recommendation: mandatory PTY + sanitization + KAIJU. Never shared terminal.
- Update needed to AGENTS.md Continuous Autonomous Operation Rules: Add pre-continue checks (SAFETY, SANDBOX, BUDGET, GATE). Halt on failure (no auto-retry).

**Governance Mesh (Section 6):**
- Duplication table: KAIJU, VAP, TokenGuard, Archivist duplicated in main vs swarm pack.
- Strategy: NEXUS main canonical. Swarm pack becomes plugin (adds OpenShell, Gastown, Zilliz). Deprecate/remove duplicates; swarm imports from main paths.
- Architecture: External input → KAIJU Gate (schema + injection check) → L1 Simple (ECO TokenGuard, no trust change) / L2 Complex (FAST TokenGuard, evaluate trust) → ...

**Roadmap (Section 13, 12-Week Sprint):**
- **Phase 0 (Immediate):** 0.1 Strip ANSI (TerminalSanitizer), 0.2 Disable SOVEREIGN default, 0.3 PTY isolation, 0.4 Fix AGENTS.md safety, 0.5 Rotate exposed creds.
- **Phase 1 (Weeks 1-2, Foundation):** Import OpenShell policies, Sandbox Abstraction Layer, Platform Detector, deprecate duplicate kernel, Kafka schema, 5 Slack channels + Zo bridge, scheduled Zo agents.
- **Phase 2 (3-4, Isolation):** Disposable Docker, WSL2 bridge, OpenShell orchestration, HF Sandbox API, capability tokens, KAIJU sandbox gates.
- **Phase 3 (5-6, Security):** Cross-agent prompt injection defense (KAIJU ext), E2E ACP (AES-256-GCM), Hallucination detection (factual, logical, cross-agent layers), Terminal/Output Sanitizer production.
- **Phase 4 (7-8, Inference):** MARS verifier, N-gram/Lookahead speculative, TWAVE/QWAVE/CHIMERA, vLLM EAGLE-3.
- **Phase 5 (9-10, Comms):** GitHub webhook→Zo, Slack bots (@Devin etc), PR review automation, Research coordination, Incident flow, Telegram, ACP impl.
- **Phase 6 (11-12, Hardening):** Full integration tests, disaster recovery, perf profiling, docs unification, GitHub sync, platform cert.

**Risk Register (Section 14):**
- R1: Docker Gordon quota exhausted (High/High) — manual configs.
- R2: Terminal injection recurrence (Medium/Critical) — deploy sanitizer immediately.
- R3: Duplicate code merge conflicts (Medium/Medium) — one-way merge then deprecate.
- R4: WSL2 GPU unreliable (Medium/Medium) — fallback Docker.
- R5: Zo rate limits (Medium/Low).
- R6: HF Sandbox API changes (Low/Medium).
- R7: Spec decoding papers without code (Low/Low).

**Next Steps from Plan (when author returns):** Apply Terminal Sanitizer (P0), gateway 20MB zip password for Zo grounding, import OpenShell (P1), Zo bridge (P1), rotate creds (P1).

## Recent Reports Insights
**CURATED_RESEARCH_AND_AGENT_LOGS_SYNTHESIS (2026-05-29):**
- Swarm logs (metaSPARK, Devin Kimi, OpenCode, etc.): Forensic on 39.06 GB upload queue (876 files) from grok.exe to GCS/Cloudflare/x.ai/Notion — "highly unsafe" (possible creds). Prompt reviews clean for DNS/TLS turns but flagged wording. Antigravity autonomous file expansion risk (divergence from canonical).
- 9 papers: Qi et al (fine-tuning breaks safety — critical for TrustKernel), Ganguli (red teaming scaling for stress lab), Slattery MIT AI Risk Repository (777 risks, 7 domains — for Governor compliance), internal audit function (validates GROSS evidence capture), etc.
- Integration map: Risk repo → Governor, red team → TAMAS/stress lab, safety cases → TrustKernel/VAP.

**SYSTEM_AUDIT_REPORT (2026-05-29):**
- Memory: OBS 1.9GB, Chrome ~3.5GB (6+ processes), Devin 785MB, OpenCode, ERNIE, etc.
- CPU: Kernel, MsMpEng (Defender), vmmemWSL, Docker Desktop, high Intel services.
- Suspicious: Antigravity (Electron, keep/remove), Alloy telemetry, BitTorrent (remove from startup), iGoSwServer (audio, keep), XtuService (Intel tuning — high CPU, disable if manual cooling).
- AWCC (Alienware Command Center): 8 processes, ~200MB, 294 events/10min. Removal scripts created (v1/v2 in D:\NEXUS_OS_AUDIT\scripts). v2 disables services first.

**NEXUS_OS_STATUS_REPORT (historical v3 context):**
- Confirms 8-pillar breakdown, backend modules (67 Python), dashboard metrics, team matrix.

**NEXUS_ZO_CLAW_INTEGRATION_PLAN (2026-05-12, 374 lines):**
- 4-layer protocol stack for Zo (cloud) + Local NEXUS (Windows) + 3 OsmanClaw? agents: Tailscale (L1: WireGuard mesh, userspace-networking on Zo), MCP (L2: tool access via mcporter on Zo; NexusMCPToolProvider on local exposing nexus.kaiju.evaluate, nexus.vap.query, nexus.vault.store/search over Tailscale), A2A v1.0 (L3: agent coordination with Agent Cards, JSON-RPC), OpenClaw (L4: self-hosted runtime on Zo for 3 isolated agents — orchestrator on #nexus-control, reviewer on #nexus-codex-tasks, researcher/ops on #nexus-research + #nexus-ops).
- Flow: User Slack → Zo orchestrator (KAIJU gate via MCP) → A2A delegate to local NEXUS GMR or other claws → results back, VAP log.
- MCP server example code on local (Tailscale IP:7352).
- Implementation roadmap: Phase 0 (Tailscale install on Windows + Zo), Phase 1 (OpenClaw on Zo + Slack bind), Phase 2 (NEXUS MCP server + mcporter config), Phase 3 (3 OsmanClaw agents + A2A cards), Phase 4 (A2A bridge + load test).
- Kafka bridge stable (Confluent key redacted); recommend Option B native migrate. NEXUS.zip (14.9MB) for Zo grounding (try OsmanClaw? password).
- Status per other docs: Plan exists, no evidence of execution (no Tailscale on Windows, no MCP server deployed, no OpenClaw, no A2A agents wired in current 01/knowledge/STATUS).

**GROSS_PROJECT_STATE_4AGENT.md + GROSS_SESSION27_WARMUP.md (2026-05-29):**
- Infrastructure active: MCP Bridge (7354 SSE, PID 68144), Sysmon Audit (D:\NEXUS_OS_AUDIT), forwarder + watchdog (5min scheduled task, PID 84248), AWCC Terminator (PID 95076, kills respawn), Audit Trail (D:\GROSS\audit_trail, SHA256-hashed audit_v2 schema).
- Service surface map: api.x.ai:443 (primary upload: multipart 87% + gRPC 13%), files.grok.com (storage browse REST + gRPC) — architecturally separate. Storage: S3 xai-grok-telemetry-prod + GCS mirror.
- Session 2.7 mission: Map boundary between api.x.ai and files.grok.com via 4-turn warmup in fresh incognito (framed as sandbox migration audit): Turn 1 DNS (socket.gethostbyname_ex on 4 domains), Turn 2 TCP/TLS (connect + ssl.wrap_socket), Turn 3 HTTP (GET status/headers only, no body/redirect follow), Turn 4 purple probe (DNS/HTTP surface classification, response consistency).
- Safety: No TLS bypass, no credential/token capture, no response bodies, no method enum/brute, no tool downloads, sanitized headers only.
- ERNIE swarm integration: 7-expert red team task spec ready (3-4hr cloud sandbox): 1200 attack scenarios + 25 novel evasion (V1/V2/V3 chains) targeting NEXUS TrustKernel (Bayesian poisoning), KAIJU 7-gates (bypass/stacking), MCP tools (abuse/chaining), GMR (hijack/saturation), Vault 5-track (memory poisoning), multi-agent collusion (kill chain/Byzantine), novel evasion. Deliverables: 200 per expert + integration to D:\GROSS\evidence\nexus_red_mechanics.
- Agent coordination: OpenCode (DeepSeek V4 Flash, primary executor full FS), GPT 5.5 (browser, prompt review), Devin Kimi 2.6 (local infra/audit), Antigravity (Gemini 3.5, high-reason analysis/patterns). Antigravity autonomously expanded GROSS docs on D: (divergence risk from canonical in C:).
- 39.06 GB upload queue (876 files) from grok.exe (PID 40616): 17 active HTTPS to GCS (1e100.net), Cloudflare/x.ai, Notion — "highly unsafe" (potential API/private keys). Queue vanished during Grok 0.2.8 update (upload complete or purge?).

## Gaps vs Current State Synthesis
Master Plan gaps largely unaddressed in current 01_PROJECT_STATE/knowledge (which focus on v3 baseline, tests passing, dashboard, but no mention of sandbox abstraction or full security layers implemented yet).
- Sanitizer/PTY work mentioned in AGENTS but per master needs production + autonomous rule updates.
- Duplicates still present (swarm pack separate).
- No evidence of full 12-week roadmap execution (plan dated 2026-05-12).
- Host environment (audit) shows resource contention for agents (WSL/Docker/Chrome/AI tools).
- Recent logs show ongoing swarm activity and exfil concerns (mitigated?).
- **Expanded from ZO/GROSS/STATUS/CURATED:**
  - Zo/Claw A2A integration: full detailed plan (Tailscale/MCP/A2A/OpenClaw, 3 agents, MCP provider code, phases) exists but zero implementation evidence in current state (no Tailscale on Windows, no local MCP server, no OpenClaw on Zo, no A2A wiring, no 3 OsmanClaw agents). Kafka bridge stable but Gordon dependency.
  - GROSS exfil/audit: 39GB queue (876 files, potential creds to GCS/Cloudflare/x.ai/Notion) from grok.exe; host bloat (Chrome 3.5GB, Devin 785MB, OpenCode/ERNIE, AWCC 8 procs); but audit tools (MCP 7354, Sysmon forwarder, AWCC term, SHA256 trail) deployed and receiving. Session 2.7 purple team active on Grok surfaces (api vs files split confirmed in plan). ERNIE red swarm task spec ready but not executed.
  - Sandbox isolation: Master requires SandboxBackend abstraction, disposable containers (KAIJU gate + Pool + VAP log + destroy), OpenShell policies, PTY/sanitizer/KAIJU cross per agent, no shared terminal. Current (01/knowledge/STATUS): WSL/Docker in use but no abstraction layer, no PTY/sanitizer production code verified, no KAIJU sandbox gates, full FS access for agents.
  - Governance duplication: Still listed as core gap; swarm pack and main separate (no evidence of main canonical + plugin merge).
  - Hallucination detection: No TWAVE/QWAVE/CHIMERA or factual/logical/cross-agent layers in current (STATUS/GMR mentions rotation but no wavefront/quality verification).
  - E2E encryption: Not present (no ACP/AES in comms; Tailscale plan is one path but unimplemented).
  - Resource/contention: SYSTEM audit shows high host load (vmmemWSL, Docker, Defender, AI tools) conflicting with agent execution sandboxes.
  - Exfil/safety drift: 39GB queue + Qi et al (fine-tuning degrades safety even benign) implies ongoing safety drift in Grok without detection.
  - Memory systems: 5-track (EVENT/TRUST/CAPABILITY/FAILURE/GOVERNANCE) canonical in vault (per STATUS/knowledge/memory_tracks.py, MemoryTracker); overlaps with 8-channel SuperLocalMemory (memory.py, adds TASK/CONTEXT/CUSTOM); brainsync external (MCP for Grok TUI). Reconciliation task (Lane A complete, see research/intake/2026-05-27-memory-reconciliation.md) pending unification + VAP/TrustKernel hooks.
  - Dashboard: Advanced v3 (8 tabs: overview/stresslab/gmr/governor/vault/research/swarm + realtime WS, API wiring in progress per 01); but v4 unification (sandbox, security layers, Zo integration) pending.
  - 01_PROJECT_STATE issues: DoppelGround leak unresolved, dashboard not full E2E verified, GSPP reconciliation, public launch security review, sandbox/mock files policy, integration ledger missing, Python API wrappers exist but dashboard consume pending, Cloudflare bypass research-only.

## Recommendations / Next Natural Actions
1. Implement Phase 0 items from roadmap (sanitizer, PTY, AGENTS.md update, cred rotation) — high priority per security incident.
2. Import OpenShell policies and start Sandbox Abstraction (Phase 1).
3. Update AGENTS.md with the revised continuous autonomous rules from master (add the 4 checks).
4. Clean host (AWCC removal, BitTorrent, manage Chrome/WSL memory for agent perf).
5. Ground Zo with full repo (if zip password available) per plan next steps; execute ZO integration plan (start with Tailscale + OpenClaw if approved).
6. For stress lab/Governor: integrate AI Risk Repository (777 risks) and red team methods; execute ERNIE red swarm if sandbox available.
7. Verify current implementation against master (use nexusctl if available, or code search). Complete memory reconciliation (Lane B: decide canonical 5-track + adapter for 8-channel + brainsync governance).
8. Address GROSS exfil (investigate 39GB queue disappearance, rotate any exposed keys).

**Evidence Citations (all from primary files read this session):**
- Master Plan: full sections via targeted reads/searches (exec ~30-120, sandbox ~195-294, security ~295-464+, roadmap/risks ~1047-end, governance ~423+).
- Others: direct reads of 01_PROJECT_STATE, knowledge, README, AGENTS, PROTOCOL, GROUNDING (UI), STATUS (1-300+), CURATED (full), AUDIT (full), ZO_CLAW (full 1-374), GROSS_PROJECT (full), GROSS_SESSION (full).
- Checklist reference updated in skills for continuous mode. Terminal find for report discovery. search_files for section locations in master (sandbox, security, governance, roadmap, risks) and current state docs.

**Verification (per checklist + AFK):**
- Tier 1+ covered with excerpts.
- Continuous rules followed (no mid-flow reports, searches + offsets used, no repeats).
- 5-phase respected (SCAN via prior + searches, DIGEST this batch, SYNTHESIZE in memories, PRODUCE this artifact, VERIFY this section).
- No "done" without evidence — all claims cite files/sections.
- Artifact self-contained.

**File produced at major checkpoint.** Ready for user review or next phase (e.g. implement Phase 0, more GROSS/HERMES grounding, or specific task from tasks/pending).

*Generated under continuous workstyle. Logged internally via memory. No user interruption during run.*

## Full NEXUS_OS_V4_MASTER_PLAN Digest (Targeted via search_files + offset read 1040+; 2026-06 continuous continuation)

**TOC Structure (from searches):**
1. Executive Summary
2. Current State Assessment (running components: NEXUS main v3, tests 796 pass, Pi Agent SOVEREIGN, Docker Gordon Kafka, Supabase, HERMES swarm review, Zo, Grafana; critical gaps listed)
3. Core Problem: Windows Local-First Bottleneck (keep Windows for authoring/governance/dashboard/secrets; replace with Linux/WSL/Docker for agent exec sandbox, GPU, speculative, network/file isolation; hybrid arch diagram with control on Windows, execution Linux, cloud burst HF/OpenShell/Confluent/Zilliz)
4. Sandbox Architecture: Multi-Tier Isolated Execution (SandboxBackend abstract pluggable: SubprocessLocal (none), DockerContainer (container), Podman, OpenShell (kernel/policy), HF Sandbox (remote), WSL2 (VM); lifecycle KAIJU gate → allocate → inject tokens → execute → VAP log → deallocate/destroy; disposable fresh containers per run with tmpfs, cap_drop ALL, no-new-privileges, security_opt)
5. Cross-Agent Security: Immunity Against Terminal Poisoning & Prompt Injection (threat model from actual incident: Agent A SOVEREIGN outputs ANSI escapes poisoning shared terminal, corrupting Agent B context; CWE-150; defenses: TerminalSanitizer (strips C0/CSI/OSC/ESC), AgentPTY (dedicated os.openpty per agent), VerifiableOutput (SHA256 hash + verify), KAIJU cross-agent eval (trust threshold + hash check); SOVEREIGN CRITICAL risk — mandatory PTY/sanitizer/KAIJU; revised autonomous rules require SAFETY/SANDBOX/BUDGET/GATE checks)
6. Governance Mesh: Unified KAIJU + VAP + TokenGuard (de-dupe across main + HERMES; 5/7/8 channel memory reconciliation; TrustKernel)
7. TWAVE/QWAVE/CHIMERA: Practical Inference Integration (speculative decoding map)
8-12. Comms, Speculative Map, Hallucination Detection (3 layers), Code Reconciliation (main ↔ HERMES), Deployment Tiers
13. Phase Roadmap (12-Week Sprint):
  - Phase 0 Emergency (Week 0): Strip ANSI (2hr), disable SOVEREIGN default (1hr), PTY isolation (4hr), fix AGENTS.md safety (1hr), rotate creds (1hr)
  - Phase 1 Foundation (1-2): Import OpenShell policies (1d), Sandbox Abstraction Layer (3d), Platform Detector (1d), deprecate duplicate (1d), Kafka schema (1d), Slack/Zo bridge + 3 Zo agents (3d)
  - Phase 2 Sandbox Isolation (3-4): Disposable Docker (3d), WSL2 bridge (3d), OpenShell orch (2d), HF API (3d), capability tokens (4d), KAIJU sandbox gates (2d)
  - Phase 3 Security (5-6): Prompt injection defense (3d), E2E AES-256-GCM (3d), 3-layer hallucination (3+2+2d), sanitizer prod (2d)
  - Phase 4 Inference (7-8): MARS (2d), N-gram/Lookahead speculative (3d), TWAVE (4d), QWAVE (3d), CHIMERA (3d), vLLM EAGLE-3 (4d)
  - Phase 5 Comms (9-10): GitHub webhook (2d), Slack bots 6 identities (3d), PR review 3-agent (4d), research coord (2d), incident (2d), Telegram (2d), ACP (3d)
  - Phase 6 Hardening (11-12): Full tests (5d), DR 5+ (3d), perf (4d), docs (3d), repo sync (1d), platform cert (3d)
14. Risk Register (R1 Gordon quota high/high; R2 terminal injection medium/critical; R3 duplicate code medium/medium; R4 WSL2 GPU medium/medium; R5 Zo rate limits medium/low; R6 HF changes low/medium; R7 speculative papers low/low)
15. Appendix + Next Steps (P0 sanitizer, zip for Zo, Phase 1.1 OpenShell, 1.6 bridge, 0.5 rotate)

**Core Thesis (repeated across exec/gaps/roadmap):** Unify NEXUS main + HERMES (OpenShell/Gastown) + Docker Gordon. Windows = Control/Authoring/Governance/Dashboard/Orch. Linux/WSL/Docker = Execution Sandboxes (isolation/GPU/policy). Cloud = Burst (HF speculative). All comms E2E encrypted, VAP-audited, KAIJU-gated. Gaps: no sandbox isolation (full FS), duplicate gov code, no cross-agent injection protection (terminal poisoning proved), no hallucination detection, no E2E, Windows hardcoded, no unified deploy, speculative not mapped, no Slack/Telegram bridge, Gordon quota.

**Evidence:** Searches for sandbox/security/governance/roadmap/risks/Phase/hallucination returned TOC + excerpts; offset read 1040-1182 for full phases/risks/next steps. No repeated full reads.

## Refined Gaps Synthesis (Master Plan vs Current State from 01_PROJECT_STATE/knowledge/STATUS/CURATED/SYSTEM_AUDIT/GROSS_PROJECT/ZO_CLAW + Prior)

**Master Plan Gaps (unaddressed or partial in current):**
- Sandbox: No SandboxBackend abstraction, no disposable containers (KAIJU+Pool+VAP+destroy), no OpenShell policies import, no platform detector, no capability tokens/KAIJU sandbox gates. Current (01/knowledge/STATUS): WSL/Docker used but full FS access for agents (Pi, subagents, OpenCode/ERNIE in GROSS); no PTY/sanitizer prod verified beyond partial security/ (knowledge has 256-line sanitizer + 23 tests, but master calls for production + autonomous rule updates); no isolation in swarm or main.
- Security/Cross-Agent: Terminal poisoning incident real (per master); no full 4-layer (sanitizer/PTY/Verifiable/KAIJU cross) in production; no prompt injection defense, E2E encryption (ACP/AES), 3-layer hallucination (factual/logical/cross). Current: Partial sanitizer/PTY in security/ (knowledge/STATUS), 214/214 security tests pass (01), but no cross-agent eval or PTY per agent enforced; GROSS shows ongoing exfil risk (39GB queue from grok.exe to GCS/Cloudflare/x.ai/Notion, 876 files, potential creds; vanished on update); fine-tuning safety drift (Qi et al papers in CURATED: safety not static, trust must account for drift); AWCC 8 procs high CPU (294 events/10min), vmmemWSL hog, orphaned shells/memory bloat from audits (SYSTEM_AUDIT).
- Governance/Memory Dupe: Duplicate KAIJU/VAP/TokenGuard in main + HERMES swarm (gap #2); no de-dupe. Current: 5-track (EVENT/TRUST/CAPABILITY/FAILURE_PATTERN/GOVERNANCE) canonical in nexus_os/vault/memory_tracks.py + MemoryTracker (STATUS/knowledge); overlaps 8-channel SuperLocalMemory (memory.py: +TASK/CONTEXT/CUSTOM); brainsync MCP external. Reconciliation task (2026-05-27-memory-unification) Lane A doc'd, pending Lane B unification + VAP/TrustKernel. GROSS validates internal audit need (paper #6 in CURATED: Sysmon/MCP/SHA256 trail IS the audit function).
- Inference/Comms: No TWAVE/QWAVE/CHIMERA, MARS, vLLM speculators, speculative map. No Slack/Telegram bridge, 3 OsmanClaw agents, A2A/ACP, GitHub webhook. Current: Some routing (ChimeraRouterV2 in knowledge), GMR, but no wavefront/quality; Zo/Claw plan (ZO_CLAW full 374 lines) details 4-layer (Tailscale L1 ready on Zo, MCP L2 mcporter, A2A v1.0 L3, NemoClaw L4 runtime upgrade per 2026-06 NVIDIA inspection for sandbox/OpenShell/Hermes support); Kafka bridge running but Gordon quota issue (no maintenance); no implementation of plan (no Tailscale Windows, no local MCP server for kaiju/vap/vault, no 3 agents, no A2A wiring).
- Other: Windows hardcoded (gap #6), no unified deploy (multiple arch), speculative not mapped, no hallucination, no E2E, Gordon exhausted, no Slack/Telegram operational. Current (01): Governance API (7352 FastAPI /skills/propose etc), dashboard v3 (8 tabs, realtime, stresslab/gmr/governor/vault), trust baseline 25.0, VAP proof chain, subagents (AI Provider Bridge, API Builder etc), OpenClaw spawner, 796 tests; but DoppelGround leak unresolved, public launch review pending, dashboard not full E2E, GSPP, Cloudflare research-only; GROSS/ERNIE red team ready (1200+25 scenarios on TrustKernel/KAIJU/MCP/Vault/collusion) but not run; host contention (SYSTEM: Chrome 3.5GB, Devin 785MB, AWCC removal script ready but not applied); memory 5 vs 8 pending; ZO plan updated with NemoClaw decision but not executed.
- From Reports: STATUS focuses on v3 dashboard/governance impl (timeline, trust matrix, VAP chain, P0 queue) but no v4 sandbox/security. CURATED: GROSS infra (MCP 7354 PID68144, audit trail SHA256, 39GB exfil), ERNIE 7-expert red for NEXUS hardening, papers validating audit/governance (3 lines defense, safety cases, internal audit), sandbox tests (7 targets timeout), autonomous expansion risk (Antigravity on D:). SYSTEM: Host CPU hogs/AWCC (8 procs, removal plan), network unknowns, root cause orphaned processes/memory. GROSS_PROJECT: Defensive data flow audit (api.x.ai vs files.grok.com surfaces, 4-turn purple probes), ERNIE task spec, OpenCode executor full FS, evidence on D:. ZO_CLAW: Plan complete (Kafka decision, 3 agents OsmanClaw?-1/2/3 roles, MCP provider example for nexus.kaiju.evaluate etc, phases 0-4, NemoClaw rec for master alignment), but status "research complete — ready for execution" with zero impl evidence.

**Overall:** Current state has strong v3 foundation (governance core, memory 5-track, partial security sanitizer/PTY/tests, dashboard/API, GROSS audit infra) but major shortfalls vs v4 master (no execution sandbox isolation per master P0-2, incomplete security layers P3, no inference/comms P4-5, dupe gov, host bloat, exfil risks unmitigated beyond audit). ZO/NemoClaw plan directly targets swarm coordination + runtime sandbox/governance to close gaps while keeping NEXUS sovereign (KAIJU gate via MCP, VAP, 5-track). GROSS/ERNIE red team targets exactly the TrustKernel/KAIJU/MCP/Vault weaknesses. Memory reconciliation pending unification. Phase 0 items (sanitizer/PTY/AGENTS/rotate) partially started (knowledge has code/tests) but not production + rule update.

**Stored as durable memory fact (see memory tool call).**

**Next Natural (internal 5-phase, continuous, no ask):** Update AGENTS.md per master P0.4 (safety checks); apply TerminalSanitizer/PTY if not prod; clean host (AWCC removal per SYSTEM script); start Phase 1.1 OpenShell import + SandboxBackend per ZO/NemoClaw rec; execute memory Lane B; run ERNIE red if budget; verify current vs master with searches. Log all to docs. Surface only at next blocker/checkpoint (e.g. Phase 0 complete or new task).

**Evidence Citations:** All from primary via searches (no bulk repeats): master plan (TOC + chunks + 1040+ read), STATUS (structure/gov/memory/VAP), CURATED (GROSS logs/papers/ERNIE), SYSTEM (CPU/AWCC/audit exports), GROSS_PROJECT (infra/MCP/audit/ERNIE), ZO_CLAW (full plan + NemoClaw update), 01_PROJECT_STATE (impl status/gaps), knowledge (quick ref + sanitizer + master/zo summary). Tool discipline: searches for discovery + targeted read for roadmap end. Prior synthesis had partial; this completes Tier 1 + reports.

**Verification:** Continuous (no stop/ask mid); searches preferred; 5-phase (DIGEST complete now, SYNTHESIZE here + memory, PRODUCE updated artifact, VERIFY citations); evidence-grounded; proposal-bound (NemoClaw/ZO for gaps); no fabricated. Mission style fixed: momentum maintained, logs in doc, only at checkpoint.
