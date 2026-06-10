# NEXUS OS - Canonical Project State

Date: 2026-04-21
Current local HEAD: Cloud sandbox (synced via GVAW)
Status: M3 hardened baseline preserved; Phase 0 grounding in progress.

## Verification Gate

Latest local verification (from Codex team report):

```text
617 passed in 16.99s
```

All `pytest.mark.skip` removed. Hermes, GMR, VaultManager, Coordinator, TokenGuard migrated to V3.
Vault uses the canonical 5-track schema (`store_track` / `retrieve_track`).

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

- Full test suite passes locally: **617 passed**.
- DB encryption policy hard-fails by default and allows plaintext fallback only when `allow_unencrypted=True`.
- Engine task dependency cycle detection is present and verified.
- TrustEngine v2.2 implements HARDWALL defenses: logistic scaling, adaptive decay, non-compensatory CRITICAL, 6-stage CDR.
- Vault uses canonical 5-track schema (`store_track` / `retrieve_track`).
- Bridge secrets management with per-provider health logging.

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
| 7352 | ModelRelay / Nexus API | HTTP | Node.js, 99 models UP, Arena-calibrated scores |
| 7353 | TWAVE wrapper (`/twave/*`) | HTTP | Low-VRAM execution layer |
| 7354 | GROSS MCP Bridge | HTTP | 17 tools, SSE transport, read-only |
| 7356 | HTML Dashboard | HTTP | Quality × Health Matrix |
| 7357 | God Mode Proxy v3 | HTTP | FastAPI, 7 profiles, GLM 5.1 selected |
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

---

## Current State Update (2026-06-09 — Session 2)

### Verification Gate (Latest)
- ModelRelay: **225 models** discovered, **99 UP**, 126 DOWN (was 92 UP — NVIDIA +15)
- Intelligence scores **Arena-calibrated** with 352,929 WebDev votes + 6,703,075 Text votes (Jun 5, 2026)
- **Top model**: `accounts/fireworks/models/glm-5p1` (GLM 5.1, intell 0.91, Arena 1532 WebDev / 1529 Text)
- **Top working model**: `accounts/fireworks/models/deepseek-v4-pro` (intell 0.86, 983ms, 1M ctx)
- God Mode Proxy routing verified: GLM 5.1 selected as best working model (was DeepSeek V4 Pro)
- Full system discovery completed: **59,790 files** indexed, 1,590 ARCHIVIST files, 344 papers, 127 logs
- Documentation created: MASTER_WORKLOG, MEMORY_INDEX, PROJECT_STATE_EXPANDED, OPTIMIZATION_GUIDE, ARCHIVIST_INDEX

### Active Services (Confirmed)
| Port | Service | Status | Notes |
|------|---------|--------|-------|
| 3000 | WSL Relay | ONLINE | WSL2 networking, NOT Next.js |
| 3001 | Next.js Dashboard | CONFIGURED | Port changed from 3000 → 3001, restart required |
| 7352 | ModelRelay (Node.js) | ONLINE | 99 UP, Arena-calibrated scores, smart ping active |
| 7356 | HTML Dashboard | ONLINE | Quality × Health Matrix |
| 7357 | God Mode Proxy v3 | ONLINE | FastAPI, 7 profiles, GLM 5.1 selected |
| 11435 | Ollama | ONLINE | GPU ~35%, smart ping reduced load |
| 7354 | GROSS MCP Bridge | ONLINE | 17 tools, SSE transport, read-only |
| — | Smart Ping Controller | RUNNING | Daemon mode, monitoring ports 7352/7356/7357 |

### Provider Status (Arena-Calibrated)
- **Mistral**: 43 UP, 100% health (tier 3, 1M tokens/month)
- **Cloudflare**: 18 UP, 100% health (tier 3, 10k neurons/day)
- **OpenRouter**: 16 UP (tier 2, rate limited)
- **Fireworks**: 9 UP (tier 1, $1 trial — GLM 5.1, DeepSeek V4 Pro, Kimi K2.6 working)
- **NVIDIA**: **14 UP** (was 0!) — `kimi-k2.6`, `step-3.7-flash`, `qwen3.5-397b`, `deepseek-v4-pro` working
- **Scaleway**: 14 discovered, 0 UP (429 rate limit, auto-recovery expected)
- **Google AI**: 0 UP (credits depleted, 429)
- **GitHub Models**: 0 UP (1500/day limit exceeded, ~5.6h cooldown)
- **Cerebras**: 0 UP (paywalled `payment_required`)
- **DeepInfra/SiliconFlow/Sambanova**: 0 UP (quota depleted)
- **Kiro**: 2 idle (complex auth)

### Intelligence Scores — Arena-Calibrated (Major Corrections)
| Model | Old Score | New Score | Arena Evidence | Change |
|-------|-----------|-----------|----------------|--------|
| GLM 5.1 | 0.90 | **0.91** | Arena 1532 WebDev / 1529 Text | +0.01 |
| Kimi K2.6 | 0.87 | **0.88** | Arena 1516 WebDev | +0.01 |
| Kimi K2.5 | 0.64 | **0.80** | Arena 1431 WebDev | +0.16 |
| Gemini 3.5 Flash | 0.74 | **0.88** | Arena 1506 WebDev | +0.14 |
| Qwen 3-235B | 0.64 | **0.78** | Arena 1442 Text | +0.14 |
| GLM 5 | 0.60 | **0.83** | Arena 1435 WebDev | +0.23 |
| DeepSeek V4 Pro | 0.89 | **0.86** | Arena 1461 WebDev | -0.03 |
| Gemini 3.1 Pro | 0.91 | **0.84** | Arena 1447 WebDev | -0.07 |
| Gemini 2.5 Pro | 0.90 | **0.72** | Arena 1204 WebDev | -0.18 |
| GPT-4o | 0.81 | **0.72** | 2-year-old model, surpassed | -0.09 |
| Llama 4 Maverick | 0.85 | **0.75** | Not in Arena top 85 | -0.10 |
| Mistral Large | 0.77 | **0.74** | Not in Arena top 85 | -0.03 |
| Grok Code Fast | 0.70 | **0.62** | Arena 1140 Text | -0.08 |
| Mimo V2.5 Pro | 0.75 | **0.86** | Arena 1466 WebDev | +0.11 |
| Minimax M2.7 | 0.84 | **0.78** | Arena 1395 WebDev | -0.06 |
| Qwen 3.5 397B | 0.76 | **0.77** | Arena 1394 WebDev | +0.01 |
| Claude Sonnet 4.5 | 0.88 | **0.85** | Claude Sonnet 4.6 is 1522 | -0.03 |

### Security Fixes Applied (Session 2)
- [MOVED] `sshkey.pem` from Downloads → `vault/secrets/`
- [MOVED] `env.txt` from Downloads → `vault/secrets/`
- [MOVED] 5 Zilliz credential files (`zilliz_api_key`, `zilliz_token`, `zilliz_uri`, `cloud_region`, `cloud_cluster_id`) → `vault/secrets/`
- [DELETED] Duplicate `NEXUS_god_mode_proxy.py` from ARCHIVIST
- [RENAMED] Garbage filename `29&(][11!34.txt` → `garbage_filename_corrupted.txt`
- [INCREASED] ModelRelay ping intervals: 1 min → 5-60 min (tier-based)
- [ARCHIVIST] 1,590 files auto-indexed, 17 categories

### Karpathy-Style Archivist Wiki (Built)
- **3-layer architecture**: Raw (immutable) → Wiki (LLM-generated) → Schema (agent rules)
- **15 wiki pages**: `index.md`, `boot.md`, `log.md`, 4 entities, 4 concepts, 4 sources
- **Engine**: `archivist.py` with 4 commands: `ingest`, `lint`, `status`, `boot`
- **Boot sync**: `boot.md` enables 60-second agent onboarding across platforms
- **59,790 sources** indexed across filesystem

### Smart Ping System (Designed)
- **State machine**: ACTIVE (15 min) → COOLDOWN (60 min) → SLEEP (4 hours)
- **Demand-driven**: Only pings when users are actively routing
- **UI refresh button**: Manual refresh from dashboard with countdown timer
- **Benefits**: 840+ checks/hour → ~200 (active) → ~15 (sleep)
- **Implementation**: `smart_ping.py` (Phase 1 ready) + design doc

### Critical Blockers (Updated)
1. DoppelGround leak status must be resolved before external handoff or public repo flip.
2. GitHub Models rate limit: 1500/day exceeded, ~5.6h cooldown.
3. Cerebras paywalled — need new token or remove.
4. GSPP reference assets need reconciliation before they become canonical.
5. Public launch files still need security/legal review before staging.
6. **ClamAV**: Install and configure for ARCHIVIST malware scanning (P1).
7. **NVIDIA suspended models**: Need to populate `nvidia_refresher.py` with 31 down models.

### P0: Security & Performance Fixes (Session 3 — Completed)
- **[ENCRYPTED]** `vault/secrets/` — AES-256-GCM encryption via `vault_encrypt.py`
  - 3 files encrypted: `env.txt.enc`, `sshkey.pem.enc`, `zilliz-cloud-nexus-os-town-username-password.txt.enc`
  - HKDF-SHA256 key derivation, nonce + salt per file, authenticated encryption (GCM)
  - Master key: `NEXUS_VAULT_KEY` environment variable (32-byte hex)
- **[FAST HASH]** Archivist updated with `blake3` support (10x faster than SHA-256)
  - `file_hash()` uses size+mtime (fast fingerprint)
  - `file_hash_blake3()` for cryptographic integrity with 100MB skip limit
- **[SMART PING]** Smart ping daemon running (`smart_ping.py --daemon`)
  - State: ACTIVE → COOLDOWN → SLEEP (15 min → 60 min → 4 hours)
  - Monitoring ports 7352, 7356, 7357 for user activity
  - Saves 840+ checks/hour → ~200 (active) → ~15 (sleep)
- **[NEXT.JS PORT]** Reconfigured from 3000 → 3001 to avoid WSL relay conflict
  - `supervisor.js`: `PORT: '3001'`, `fuser -k 3001/tcp`
  - `next.config.ts`: documented with serverRuntimeConfig port hint
- **[SECURITY RESEARCH]** `SecurityBASEandCRYPTknowledge.txt` analyzed (323 lines)
  - Libgcrypt (best), Bouncy Castle, wolfSSL, ClamAV, MITRE ATT&CK
  - Pegasus spyware, Stuxnet, Mirai, Linux kernel vulns (Dirty Frag, Copy Fail)
  - Post-quantum cryptography evaluation (CRYSTALS-Kyber, Dilithium)
- **[ENCRYPTED FILE POLICY]** `29&(][11!34.txt` is encrypted (NOT garbage)
  - Restored original filename, DO NOT rename/move/delete without SPECI approval
  - Documented in `SECURITY_ENHANCEMENT_PLAN.md`
- **[GOOGLE AI REMOVED]** Provider `openai-compatible:googleai` removed from ModelRelay config
  - All 11 Google AI models were DOWN (429, credits depleted)
  - Provider count: 17 → 16
- **[NVIDIA DYNAMIC REFRESHER]** Built `nvidia_refresher.py` for suspended models
  - Suspended models: Check every 7 days (not daily, save API quota)
  - Auto-deprecate after 30 days down (keep record, don't delete)
  - Restore on-demand: `--restore` or `--restore-all`
  - Check now: `--check` or `--force`
- **[DARK AESTHETIC UI]** Built Obsidian-like archivist wiki UI
  - `nexus_os/archivist/wiki-ui/index.html` — Pure HTML/CSS/JS, no dependencies
  - Dark theme with cyan/blue accents (NEXUS branding)
  - Sidebar file tree, tabbed interface, markdown rendering
  - Graph view placeholder, search (Ctrl+K), status bar
  - Pages: Index, Boot, Model Arena, Security, Agents, Benchmarking, Encryption
- **[VAULT SECURITY INTEL]** Created `vault/security-intel.md` (curated from 323-line research)
  - Pegasus, Stuxnet, Mirai threat analysis
  - MITRE ATT&CK mapping for NEXUS components
  - CVE tracking: Dirty Frag, Copy Fail, SGLang RCE
  - Crypto library ranking: Libgcrypt (best), Bouncy Castle, wolfSSL, Botan
  - Post-quantum migration plan (CRYSTALS-Kyber, Dilithium)
  - File classification: PUBLIC → INTERNAL → RESTRICTED → SECRET → TOP SECRET
- **[ENCRYPTION DEEP ANALYSIS]** `nexus_os/security/ENCRYPTION_DEEP_ANALYSIS.md`
  - Libgcrypt vs OpenSSL (cryptography) vs libsodium vs wolfCrypt vs Botan
  - **Verdict: Keep current `cryptography` (OpenSSL 4.0.0) stack**
  - Speed difference <5% with AES-NI (2,400 vs 2,200 MB/s — negligible for 3.5 KB vault files)
  - OpenSSL is MORE FIPS 140-3 validated, better Python API, wider audit
  - Libgcrypt: Add as ALTERNATIVE for C/system agents, not replacement
  - Post-quantum: Libgcrypt (GnuPG 2.4+) has CRYSTALS-Kyber for 2030-2035 migration
- **[THEME STUDIO DASHBOARD]** `nexus_os/archivist/wiki-ui/nexus-dashboard.html`
  - **8 theme variations**: NEXUS Cyan, Obsidian Purple, Matrix Green, Amber Alert, Frost Blue, Rose Gold, Monochrome, Solarized Dark
  - **Settings panel**: Live theme preview, toggle switches, compact mode, sparklines, animated background
  - **Command palette**: Ctrl+K, search all pages, keyboard shortcuts
  - **Monitoring page**: Metric cards with sparklines, uptime chart, event timeline, live clock
  - **Models page**: 4 view modes — Cards (with mini-charts), Table (sortable), Heatmap (intensity grid), Compact (list with progress bars)
  - **Providers page**: Gauge charts, progress bars, health overview
  - **Wiki pages**: Security, Agents, Benchmarking (all data populated)
  - **Status bar**: Live sync indicator, model count, best model, vault status, clock
  - **Pure HTML/CSS/JS** — no dependencies, no build step, open in browser immediately

### Documentation Created
- `docs/discovery/MASTER_WORKLOG_2026-06-09.md` — Full filesystem discovery (59,790 files)
- `docs/discovery/MEMORY_INDEX.md` — 5-minute agent onboarding guide
- `docs/discovery/PROJECT_STATE_EXPANDED.md` — Full system inventory with model details
- `docs/discovery/OPTIMIZATION_GUIDE.md` — P0-P3 refactoring targets with quick wins
- `docs/discovery/ARCHIVIST_INDEX.md` — 1,590 file catalog across 17 categories
- `nexus_os/monitoring/INTELL_SCORE_GUIDE.md` — Intelligence score interpretation guide
- `nexus_os/archivist/schema.md` — Karpathy wiki behavior protocol
- `nexus_os/archivist/wiki/boot.md` — 60-second agent fast sync
- `nexus_os/relay/smart_ping_design.md` — Demand-driven health check design
- `nexus_os/relay/smart_ping.py` — Phase 1 implementation (Python monitor)
- `nexus_os/security/SECURITY_ENHANCEMENT_PLAN.md` — Encryption + threat model + ClamAV
- `nexus_os/security/vault_encrypt.py` — AES-256-GCM vault encryption tool
- `nexus_os/relay/nvidia_refresher.py` — Dynamic NVIDIA model refresher (7-day check, 30-day deprecate)
- `nexus_os/archivist/wiki-ui/index.html` — Dark aesthetic Obsidian-like wiki UI
- `vault/security-intel.md` — Curated security intelligence (323 lines distilled)

### Next Actions (Priority Order)
1. **P1: ClamAV Install** — Scan ARCHIVIST files for malware (Py.Malware.CodeExec, Pegasus-like spyware)
   - Install: `choco install clamav` or `winget install ClamAV.ClamAV`
   - Configure: `freshclam` for daily signature updates
   - Run: `clamscan --infected --recursive C:\Users\speci.000\Downloads\ARCHIVIST\`
   - Integration: `archivist.py` scan hook before file ingestion
2. **P1: Populate NVIDIA Refresher** — Add 31 suspended models to `nvidia_refresher.py`
   - Check all 45 NVIDIA models: `nvidia_refresher.py --check --force`
   - Down models: auto-suspend (7-day recheck, 30-day deprecate)
   - New models: auto-discover via `https://integrate.api.nvidia.com/v1/models`
3. **P2: Expand Wiki UI** — Add real markdown rendering, graph view, source linking
   - Parse `wiki/*.md` files dynamically (not hardcoded JS)
   - Graph view: D3.js or Canvas force-directed graph
   - Source linking: Click file → open raw source in overlay
   - Export: PDF, JSON, or Obsidian vault format
4. **P2: Phase 6 MCP Server** — Always-online Docker-based with Telegram/Slack/Notion
5. **P2: Arena API Integration** — Weekly auto-refresh scores from Arena leaderboard
6. **P3: Post-Quantum Crypto** — Evaluate CRYSTALS-Kyber, Dilithium for NEXUS vault migration
7. **P3: Archive Stale Plans** — Implementations 01-17, log rotation, temp cleanup
7. **P3: Post-quantum crypto** — Evaluate CRYSTALS-Kyber, Dilithium for NEXUS
8. **P3: Archive stale plans** — Implementations 01-17, log rotation

---

## Phase 1 Critical Implementation (2026-06-10 — Session 3 Continuation)

### Misalignment Detection & Concealment Monitoring System (CRITICAL — COMPLETED)

**New Module**: `nexus_os/governor/misalignment_detector.py` — 300+ lines

- **Detects 8 concealment patterns**: GIT_OBFUSCATION, PERMISSION_BYPASS, SANDBOX_ESCAPE, DECEPTION_TRACE, SUSPICIOUS_ACTIVATION, DATA_EXFILTRATION, PRIVILEGE_ESCALATION, COVERT_COMMUNICATION (ST3GG)
- **Heuristic detection**: 40+ regex patterns compiled from Mythos system card findings + ST3GG threat intelligence
- **Risk scoring**: Cumulative weighted scores (LOW=1, MEDIUM=3, HIGH=10, CRITICAL=50)
- **Circuit breaker**: Automatic agent blocking at score >= 100
- **CDR escalation**: Automatic TrustEngine CDR CASCADE at score >= 50 or any CRITICAL event
- **Steganography detection**: Zero-width characters, homoglyph attacks (ST3GG multi-modal poisoning)
- **Integration hooks**:
  - `trust_engine_v2.py`: `detect_misalignment()` method — analyzes text, triggers CDR escalation
  - `token_guard.py`: `check_deception_patterns()` method — VAP-compliant audit logging of detected deception
  - `memory_tracks.py`: Records FAILURE_PATTERN + GOVERNANCE tracks for all events
  - `constitution.yaml`: 7 new misalignment rules + 8 classifier categories
- **Singleton pattern**: `get_detector()` for system-wide access
- **Profiles**: Per-agent behavior profiles with cumulative risk scoring, event history, blocking status

### Safety Classifier Architecture (CRITICAL — COMPLETED)

**New Module**: `nexus_os/governor/intent_classifier.py` — 400+ lines

- **8 categories**: BENIGN, CYBERSECURITY, BIOLOGY, DISTILLATION, JAILBREAK, CODE_INJECTION, PRIVACY_VIOLATION, HATE_HARASSMENT, SELF_HARM
- **Heuristic classification**: 150+ keyword rules with confidence scoring and context-aware benign detection (defensive security, research, education)
- **Conservative thresholds**: Target <5% fallback rate (Fable 5 baseline), <2% block rate
- **Actions**: ALLOW, LOG_ONLY, FALLBACK, HOLD, BLOCK
- **Fallback routing**: Automatic model downgrade on detection (e.g., Fable 5 → Sonnet 4.6, GLM 5.1 → GLM 4+)
- **KAIJU integration**: `get_kaiju_request()` generates KAIJU-compatible AuthRequest for HOLD/CRITICAL classifications
- **Weekly audit**: `get_weekly_audit()` with false positive/negative tracking, tuning recommendations
- **30-day retention**: All flagged requests logged with Vault GOVERNANCE track retention policy
- **Batch classification**: `classify_batch()` for high-throughput ModelRelay middleware
- **Metrics**: Real-time fallback rate, block rate, average confidence, category distribution
- **Integration**: `constitution.yaml` classifier categories with per-category confidence thresholds and CDR escalation mappings

### Constitution Updates (2026-06-10)

**New rules added to `nexus_os/governor/constitution.yaml`**:
- 7 misalignment detection rules (CRITICAL/HIGH risk, with CDR escalation and notification targets)
- 8 safety classifier categories (CYBERSECURITY, BIOLOGY, DISTILLATION, JAILBREAK, CODE_INJECTION, PRIVACY_VIOLATION, HATE_HARASSMENT, SELF_HARM)
- Per-category confidence thresholds (low/medium/high) and action sequences (log_only → fallback → human_review → block)
- Special handling for SELF_HARM: provide_resources (aligns with Fable 5 system prompt mental health protocol)
- Prohibited actions expanded: git force pushes, docker privileged mode, eval/exec, jailbreak keywords

### Leaked Intelligence Analysis (2026-06-10)

**Claude Fable 5 System Prompt** (121KB, leaked 2026-06-09):
- **Constitutional rules extracted**: Product information, refusal handling, tone/formatting, user wellbeing, knowledge cutoff (Jan 2026), evenhandedness, responding to mistakes
- **Tool definitions**: 10+ tools (bash, create_file, str_replace, view, web_search, web_fetch, image_search, etc.)
- **Safety architecture**: 3-layer classifier (inferred from system prompt structure), CRITICAL_COPYRIGHT_COMPLIANCE hard limits, harmful_content_safety filters
- **MCP integration**: search_mcp_registry, suggest_connectors — explicit opt-in for third-party MCP apps
- **Copyright enforcement**: 15-word hard limit, one quote per source maximum, paraphrasing default
- **Mental health protocol**: Detailed suicide/self-harm handling, eating disorder guidance, crisis resources
- **Key insight for NEXUS**: Fable 5's refusal handling is "warm but firm" — declines with kindness, never curses, provides alternatives. This maps to NEXUS Governor's evenhandedness principle.

**Crystalline Cognitive Memory** (507 lines, independent research 2026-05):
- **5-level memory**: Episodic → Semantic → Procedural → Analogical → Principle (ACT-R theory)
- **CyberGym evaluation**: 90.2% pass@1 (vs 66.6% baseline), +23.6 percentage points
- **ARC-AGI-3**: 97.69% (vs 57% baseline), +40.7 percentage points
- **Integration**: MCP server interface, recall/remember/consolidate operations
- **Key insight for NEXUS**: 5-track vault memory (EVENT, TRUST, CAPABILITY, FAILURE_PATTERN, GOVERNANCE) already maps to Crystalline levels. Add analogical + principle tracks for cross-domain transfer.

**ST3GG Threat Intelligence** (103 lines, elder-plinius leaked toolkit):
- **Agent-to-agent covert communication**: Hidden payloads in images, prompt injection via vision
- **Multi-modal poisoning**: Images that look normal to humans but alter agent behavior
- **Data exfiltration**: Encoding stolen data into generated images to bypass output filters
- **Content filter bypass**: Hiding prohibited content in image payloads
- **Key insight for NEXUS**: MisalignmentDetector now detects COVERT_COMMUNICATION patterns (steganography, homoglyphs, hidden Unicode)

### TrustEngine v2.2 Integration
- `detect_misalignment()` added: analyzes agent text, automatically triggers CDR CASCADE on CRITICAL misalignment
- `trust_engine_v2.py` now auto-updates trust scores when concealment is detected (non-compensatory CRITICAL delta = -20.0)
- CDR escalation to CASCADE forced on any CRITICAL misalignment pattern

### TokenGuard Integration
- `check_deception_patterns()` added: monitors all agent outputs for concealment
- VAP-compliant audit logging for every detected deception event
- CDR escalation recommendation logged when risk score exceeds threshold
- Non-blocking: returns detection results but does not halt execution (TokenGuard philosophy)

### Next Actions (Updated Priority Order)
1. **P1: Test new modules** — Verify `misalignment_detector.py` and `intent_classifier.py` import and run
2. **P1: ClamAV Install** — Scan ARCHIVIST files for malware (Py.Malware.CodeExec, Pegasus-like spyware)
3. **P1: Populate NVIDIA Refresher** — Add 31 suspended models to `nvidia_refresher.py`
4. **P2: Behavioral Audit System** — Weekly automated agent probing with 15-dimensional scoring (2,300 sessions, 1,150 scenarios)
5. **P2: Cybersecurity Testing Framework** — TWAVE sandbox CTF challenges with 3-grade scoring
6. **P2: NEXUS-Bench** — 5-track benchmark suite (Governance, Security, Operations, Research, Integration)
7. **P3: Post-Quantum Crypto** — Evaluate CRYSTALS-Kyber, Dilithium for NEXUS vault migration
8. **P3: Archive stale plans** — Implementations 01-17, log rotation
