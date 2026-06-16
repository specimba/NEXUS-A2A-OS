# NEXUS OS — Expanded Project State & Full System Inventory
## Version: 2026-06-09 (Supplements 01_PROJECT_STATE.md)
## Classification: NEXUS INTERNAL

---

## 1. FULL SYSTEM LANDSCAPE

### 1.1 Physical Infrastructure
```
[Windows Host]
├─ CPU: (not specified, x86_64)
├─ GPU: NVIDIA, 8GB VRAM (nvidia-smi shows 5151 MiB used, 8188 total)
├─ RAM: (not specified, but Devin commit uses 25.9 GB per GROSS report)
├─ C: Drive — Windows system, user files, Documents\NEXUS (repo)
├─ D: Drive — GROSS confidential, NEXUS_COLD, NEXUS_OS_AUDIT, NEXUS_RECOVERY, model storage
└─ WSL Ubuntu — Linux sandbox for Grok CLI, sterile testing
```

### 1.2 Network Topology
```
[Local Services]
├─ Port 7352: ModelRelay (Node.js) — HTTP REST
├─ Port 7354: GROSS MCP Bridge (Python/FastMCP) — SSE
├─ Port 7356: Dashboard (HTML/JS) — HTTP
├─ Port 7357: God Mode Proxy (Python/FastAPI) — HTTP REST
├─ Port 11435: Ollama (Go) — HTTP REST
├─ Port 3000: Next.js Dashboard (React/Next.js) — HTTP (may be offline)
├─ Port 3003: WebSocket Swarm Events — WebSocket (may be offline)
└─ Port 11436: NexusClaw Ollama Lane (planned, not confirmed)

[External Endpoints]
├─ https://sharply-unethical-various.ngrok-free.dev/sse — GROSS ngrok tunnel
├─ https://doppelground-specimba.zocomputer.io — DoppelGround landing page
├─ https://files.grok.com — xAI/Grok file server (audited by GROSS)
├─ https://connectors-gateway.grok.com — Grok MCP gateway
└─ Various model provider APIs (Mistral, Cloudflare, Fireworks, etc.)
```

### 1.3 Software Stack

| Layer | Technology | Version | Location |
|-------|-----------|---------|----------|
| OS | Windows 10/11 | — | C:\Windows |
| WSL | Ubuntu | — | D:\WSL (implied) |
| Node.js | ModelRelay runtime | ~18+ | AppData\Roaming\npm |
| Python | NEXUS OS core | 3.13 | C:\Program Files\Python313 |
| Ollama | Local model runner | — | Port 11435 |
| Docker | Container runtime | — | Used for Gordon/bridge images |
| Next.js | Dashboard (offline?) | 16+ | Port 3000 |
| React | Dashboard UI | 19 | Port 3000 |
| Prisma | ORM | — | Port 3000 |
| SQLite | Database | — | Port 3000 |
| FastAPI | God Mode Proxy | — | Port 7357 |
| FastMCP | GROSS Bridge | — | Port 7354 |
| Sysmon | Windows audit | — | D:\NEXUS_OS_AUDIT |

---

## 2. REPOSITORY INVENTORY

### 2.1 Canonical Repo (Git-tracked)
```
C:\Users\speci.000\Documents\NEXUS (Git repo)
├─ 01_PROJECT_STATE.md              ← Canonical project state (2026-04-21)
├─ AGENTS.md                       ← Agent operating protocol
├─ knowledge.md                    ← Quick project overview, commands
├─ README.md / README.md           ← Human contributors
├─ docs/
│  ├─ handbook/
│  │  └─ 03_NEXUSCTL_GUIDE.md      ← CLI usage guide
│  ├─ discovery/
│  │  ├─ MASTER_WORKLOG_2026-06-09.md  ← Full discovery (this session)
│  │  ├─ MEMORY_INDEX.md            ← Fast agent onboarding
│  │  ├─ PROJECT_STATE_EXPANDED.md  ← This file
│  │  └─ OPTIMIZATION_GUIDE.md      ← Refactoring targets
│  └─ (other docs)
├─ nexus_os/
│  ├─ bridge/                      ← Protocol boundary, API ingress
│  ├─ governor/                    ← KAIJU, policy, compliance, TrustEngine v2.2
│  ├─ vault/                       ← 5-track memory, encryption
│  ├─ engine/                      ← DAG routing, Hermes/GMR
│  ├─ swarm/                       ← Worker orchestration
│  ├─ monitoring/                  ← TokenGuard, VAP, telemetry
│  │  ├─ dashboard.html            ← Quality × Health Matrix (port 7356)
│  │  └─ INTELL_SCORE_GUIDE.md     ← Score documentation
│  └─ relay/                       ← God Mode Proxy
│     └─ god_mode_proxy.py         ← v3, 726 lines, FastAPI
└─ (other source dirs)
```

### 2.2 External Repos (GitHub: specimba)
**Active/Accessible** (50+ repos):
- nexusalpha, hermes-agent, ml-intern, DoppelGround, nexux-os-Chimera
- hf-sandbox, hub-docs, anything-llm, symphony, context-mode, clawcode, opencode
- free-for-dev, a2a-for-google-apps-script, OpenSeeker, ISC-Bench
- trustclaw, mimo25-nexus, nexus-mcp, edict, agent-framework
- NemoClaw, claw-code-parity, edict, HeavySkill, Turbo1bit, supertonic
- CK-PLUG, agent-orchestrator, agentmemory, Sana, hf-mcp-server, pruna
- odysseus, Semia, hermes-workspace, hermes-desktop, agentflow, goal-ledger
- Intern-S1, WildClawBench, CLI-Anything, DataMaster, fastmcp
- free-llm-api-resources, awesome-free-llm-apiss, RelayFreeLLM
- awesome-llm-mas-rl, nexus-dev, ClawTeam, agents, untidetect-tools
- anyrouter-check-in, security-skills, nopecha-extension, hermes-flyio
- XSafeClaw, PaperAsk, DeepAgent, Openclaw-Fly-Deploy, dr-tulu, mira-OSS
- AWorld (inclusionAI), UI-Venus, DR-Venus, claw-code, cc-agent
- awesome-free-llm-apis, SwarmUI

**Restricted (403)**:
- claw-code-parity, agent-framework — may be private or deleted

**Status Unknown**:
- Many repos not checked for recent commits

### 2.3 ARCHIVIST Subsystems (Not in Git)
```
C:\Users\speci.000\Downloads\ARCHIVIST
├─ modelrelay/                      ← Python model relay subsystem (9 files)
│  ├─ config.py                     ← Configuration management
│  ├─ dynamic_router.py             ← Route logic
│  ├─ gateway.py                   ← API gateway
│  ├─ models_registry.py           ← Model registry
│  ├─ provider_manager.py          ← Provider management
│  ├─ quota_guard.py               ← Rate limiting
│  ├─ SPEC.md                     ← Specification document
│  ├─ MODELRELAY_CHECKPOINT.md     ← Checkpoint log
│  └─ __init__.py                  ← Package init
├─ governor/                        ← Python governor subsystem (10 files)
│  ├─ autoharness.py              ← Auto-harness
│  ├─ compliance.py               ← Compliance checker
│  ├─ kaiju_auth.py               ← KAIJU authentication
│  ├─ trust_engine_v2.py          ← Trust engine v2
│  ├─ trust_scoring.py            ← Trust scoring
│  ├─ proof_chain.py              ← Proof chain
│  ├─ constitution.yaml           ← Constitutional rules
│  ├─ base.py                     ← Base classes
│  ├─ __init__.py                 ← Package init
│  └─ __pycache__/               ← Compiled Python
├─ vault/                           ← Python vault subsystem (11 files)
│  ├─ cache.py                    ← Cache layer
│  ├─ decay_worker.py             ← Decay worker
│  ├─ manager.py                  ← Vault manager
│  ├─ memory_adapter.py           ← Memory adapter
│  ├─ memory_tracks.py            ← Memory tracks (5-track)
│  ├─ memory.py                   ← Memory core
│  ├─ poisoning.py                ← Poisoning detection
│  ├─ trust_store.py             ← Trust store
│  ├─ trust.py                    ← Trust core
│  ├─ __init__.py                 ← Package init
│  └─ __pycache__/               ← Compiled Python
├─ team/                            ← Team coordination (3 files)
│  └─ coordinator.py              ← Team coordinator (orphaned?)
├─ doppelground_full_pack_v2/       ← DoppelGround docs (8 files)
├─ deepseek_data-2026-05-06/        ← DeepSeek data (2 files, potential PII)
└─ DERDDRE/                         ← V4 Claw system (14 subdirs)
   ├─ agents/                      ← Agent definitions (Antigravity, CODEX, DeepSeekV4Flash)
   ├─ BOOT/                        ← Boot scripts
   ├─ Codes/                       ← Source code
   ├─ dashboard/                   ← Dashboard code
   ├─ Dump/                        ← Data dumps
   ├─ Experiments/                 ← Experiment results
   ├─ handbook/                    ← Handbooks
   ├─ Logs/                        ← System logs
   ├─ NEXUS_OS_v3.2_opusmanSEEKv4_Claw_System_2026-04-29/  ← V4 system snapshot
   ├─ Reports/                     ← Generated reports
   ├─ src/                         ← Source directory
   ├─ usefulthings-01/             ← Utilities
   └─ v4/                          ← v4 specific files
```

---

## 3. MODEL INVENTORY (DETAILED)

### 3.1 Active Providers (92 UP Models)

#### Mistral — La Plateforme (43 UP)
- **Tier**: 3 (most reliable)
- **Limit**: 1M tokens/month
- **Key models**: mistral-large-2512 (0.77), codestral (0.67), ministral-8b-2509 (0.60), various ministral variants
- **Latency**: ~800ms average
- **Health**: 100% (all 43 UP)

#### Cloudflare (18 UP)
- **Tier**: 3
- **Limit**: 10k neurons/day
- **Key models**: @cf/moonshotai/kimi-k2.6 (0.76), @cf/meta/llama-3.3-70b-instruct-fp8-fast (0.65), @cf/qwen/qwen2.5-coder-32b-instruct (0.63)
- **Latency**: ~1200ms average
- **Health**: 100% (all 18 UP)

#### OpenRouter (16 UP)
- **Tier**: 2
- **Limit**: Free models, rate limited
- **Key models**: Owl Alpha (0.68), GPT-OSS-120B (0.62), various experimental
- **Latency**: ~1500ms average
- **Health**: Mixed (some rate limited)

#### Fireworks (2 UP)
- **Tier**: 1 (very limited budget)
- **Limit**: $1 trial budget
- **Key models**: accounts/fireworks/models/deepseek-v4-pro (0.89), accounts/fireworks/models/kimi-k2p6 (0.76)
- **Latency**: ~1295ms (DeepSeek)
- **Health**: 100% (but budget constrained)

#### Scaleway (14 discovered, 0 currently UP)
- **Tier**: 0 (no API key configured — WAIT, key IS configured but rate limited)
- **Limit**: Per-minute rate limit (429)
- **Key models**: 14 discovered but all rate-limited
- **Status**: Key valid (`151783b4-00a3-48cf-906b-6f702670373f`), auto-recovery expected

#### Kiro (2 idle)
- **Tier**: 0
- **Status**: Complex auth, not fully operational

### 3.2 Down Providers (342 DOWN)

#### NVIDIA (all 50+ DOWN)
- **Status**: All 404 — model IDs may be wrong or NIM endpoints changed
- **Example**: deepseek-ai/deepseek-v3.2 returns 404
- **Action needed**: Verify model IDs against NVIDIA NIM catalog

#### Google AI (11 DOWN)
- **Status**: Credits depleted (429)
- **Key models**: gemini-2.5-pro (0.90), gemini-3.1-pro-preview (0.91), gemini-3-pro-preview (0.85)
- **Action needed**: New API key or credits

#### GitHub Models (all DOWN)
- **Status**: 1500/day rate limit exceeded
- **Key models**: gpt-4o (0.81), gpt-4o-mini (0.69), various
- **Cooldown**: ~5.6 hours
- **Action needed**: Wait for reset or use different token

#### Cerebras (2 DOWN)
- **Status**: Paywalled (`payment_required`)
- **Key models**: llama-3.1-70b, llama-3.3-70b
- **Action needed**: Free tier may require different registration

#### DeepInfra (all DOWN)
- **Status**: 0% health, quota depleted
- **Action needed**: Trial credits exhausted

#### SiliconFlow (all DOWN)
- **Status**: 0% health, quota depleted
- **Action needed**: Balance issues

#### Sambanova (all DOWN)
- **Status**: 0% health, quota depleted
- **Action needed**: $5 trial exhausted

### 3.3 Ollama Models (Local)
- **Location**: D:\ollama_models or D:\Ollama_Backup
- **Models**: sulphur-prompt-enhancer (9B Qwen, 5.4GB), qwen2.5:1.5b, qwen2.5:0.5b, llama-guard3:1b, special-virus:latest
- **VRAM**: 8GB total, frequently OOM due to health check loop
- **Status**: Running but GPU hog issue identified

---

## 4. GROSS PROJECT INVENTORY (CONFIDENTIAL)

### 4.1 Architecture
```
[Windows Host]                    [Grok Sandbox]              [xAI Cloud]
     │                                  │                         │
     │─ D:\GROSS                      │─ grok.exe PID 40616      │─ files.grok.com
     │  ├─ grok_mcp_server.py (7354)  │  ├─ upload_queue        │  ├─ GCS buckets
     │  ├─ evidence/                   │  ├─ sessions/           │  └─ connectors-gateway
     │  ├─ phase2/ (turns 1-26)      │  └─ config.toml         │
     │  ├─ phase3/ (ERNIE missions)   │                         │
     │  └─ nexus-observations/       │                         │
     │                                  │                         │
     │─ D:\NEXUS_OS_AUDIT            │                         │
     │  ├─ Sysmon service             │                         │
     │  └─ logs\realtime\            │                         │
```

### 4.2 Tools Inventory (17 Exposed via MCP)
1. `read_file_from_workspace` — Absolute path read
2. `write_file_to_workspace` — Absolute path write
3. `list_dir` — Directory listing
4. `grep_search` — Pattern search
5. `execute_command` — Sandboxed PowerShell
6. `read_sysmon_audit_trail` — Sysmon log queries
7. `diagnose_host_audit` — Active timeline diagnostics
8. `snapshot_upload_queue` — Sub-second FS capture
9. `read_upload_queue_metadata` — File counts/sizes
10. `get_mcp_bridge_health` — SSE server status
11. `query_grok_backend_export` — prod-grok-backend.json search
12. `read_events_jsonl` — Agent event loops
13. `check_tcp_connections` — PID-to-IP profiling
14. `block_outbound_firewall` — Windows Defender blocks
15. `start_plan_b_sentinel` — Background sentinel spawn
16. `stop_plan_b_sentinel` — Sentinel termination
17. `analyze_plan_b_run` — Forensic timeline generation

### 4.3 Key Findings
- **Exfiltration**: 37.42 GB staged, NOT stolen secrets, but privacy violation
- **Queue now**: 5 files / 21,898 bytes (post opt-out)
- **Hades cluster**: hades-openbar namespace, coingecko-proxy, polygon-proxy
- **Container**: Cloud Hypervisor VM, catatonit, overlay fs
- **JWT**: `TERMINAL_JWT_VAL` present in container (session token)
- **K8s**: 17 services discovered, no direct NEXUS data found in remote storage

---

## 5. TEST INVENTORY

### 5.1 Current Test Status (from 01_PROJECT_STATE.md)
- **Total**: 617 passed (as of 2026-04-21)
- **All `pytest.mark.skip` removed**
- Hermes, GMR, VaultManager, Coordinator, TokenGuard migrated to V3
- Vault uses 5-track schema
- DB encryption hard-fails by default

### 5.2 Test Coverage Areas
- Envelope validation
- Port ownership
- Disabled cloud fallback
- Disabled background polling
- `RELAY_HEALTH_INTERVAL=0` default
- Reject remote stdio
- Reject unsafe gatewayUrl
- WebSocket Origin enforcement
- Block approval/sandbox config without KAIJU/VAP
- Block pickle/unsafe torch.load
- Block trust_remote_code
- Quarantine uncensored/red-team model labels

### 5.3 Known Test Gaps (from audit)
- No tests for intelligence score correctness
- No tests for ModelRelay restart behavior
- No tests for GROSS tool chain
- No tests for GPU hog detection
- No tests for ARCHIVIST file integrity

---

## 6. SECURITY POSTURE

### 6.1 Active Defenses
- **TrustEngine v2.2**: HARDWALL, logistic scaling, adaptive decay, non-compensatory CRITICAL, 6-stage CDR
- **KAIJU gates**: Approval required for sensitive actions
- **TokenGuard**: Budget limits enforced
- **VAP**: Audit trails, SHA256 hashing
- **Sysmon**: File/process monitoring on D:\NEXUS_OS_AUDIT
- **DB encryption**: Hard-fail by default, plaintext only with `allow_unencrypted=True`
- **Port ownership**: 7352=NEXUS, 7353=TWAVE, 7354=GROSS bridge, 7355=internal relay, 11436=Ollama lane

### 6.2 Vulnerabilities Identified (from audit)
1. **SSH key in Downloads**: `ARCHIVIST\sshkey.pem` exposed
2. **env.txt in Downloads**: Potential secret exposure
3. **Grok upload queue**: Privacy violation even if not malicious
4. **Health check loop**: GPU resource exhaustion (DoS on self)
5. **NVIDIA 404s**: May indicate wrong endpoint configuration or expired credentials
6. **No log rotation**: 61 log files, no cleanup policy
7. **ARCHIVIST chaos**: 283 files, no access control, potential PII in `conversations.json`

---

## 7. DOCUMENTATION INVENTORY

### 7.1 Canonical Docs (in Documents\NEXUS)
| File | Purpose | Last Updated |
|------|---------|-------------|
| 01_PROJECT_STATE.md | System state | 2026-04-21 |
| AGENTS.md | Operating protocol | 2026-06-09 (implied active) |
| knowledge.md | Quick overview | 2026-04-21 |
| docs/handbook/03_NEXUSCTL_GUIDE.md | CLI guide | 2026-04-21 |
| docs/discovery/MASTER_WORKLOG_2026-06-09.md | Discovery log | 2026-06-09 |
| docs/discovery/MEMORY_INDEX.md | Agent onboarding | 2026-06-09 |
| docs/discovery/PROJECT_STATE_EXPANDED.md | This file | 2026-06-09 |
| docs/discovery/OPTIMIZATION_GUIDE.md | Refactoring | 2026-06-09 |
| nexus_os/monitoring/INTELL_SCORE_GUIDE.md | Score docs | 2026-06-09 |

### 7.2 ARCHIVIST Docs (283 files, select critical)
| File | Purpose | Status |
|------|---------|--------|
| PLAN.md | NexusClaw V0 plan | Canonical (41 lines) |
| PHASES_SUMMARY.md | Phase roadmap | Phase 5 done, 6 pending |
| NEXUS_GROSS_MASTER_MOVEMENT_PLAN_V7.md | Strategic | 242 lines, comprehensive |
| knowledge_update_summary.md | KB update | Stale (2026-05-02) |
| implementation_plan01-17.md | Plans | Mostly incomplete/abandoned |
| MODEL GURU.txt | Model research | 2049 lines, BitNet/Bonsai/TRNQ |
| BIGdumpofCLAWandFORKsV2.5.txt | Repo list | 154 lines, 50+ repos |
| DERDDRE/NEXUS-bundle-lite.md | Bundle | 205KB, agents + code |
| DERDDRE/agents/*.md | Agent definitions | Antigravity, CODEX, DeepSeekV4Flash |
| doppelground_full_pack_v2/*.md | Landing page | 8 files, restart pack |

### 7.3 GROSS Docs (72 files, select critical)
| File | Purpose | Classification |
|------|---------|---------------|
| GROSS_PROJECT_GROUNDED_STATE_SYNTHESIS_2026-05-31.md | State | INTERNAL |
| GROSS_PROJECT_STATE_4AGENT.md | Agent briefing | INTERNAL |
| INTELLIGENCE_CONCLUSION_2026-05-28.md | Findings | INTERNAL |
| MCP_BLACKBOX_PROBE_DESIGN_2026-05-28.md | Probe design | INTERNAL |
| NEXUS_OS_v3_UPGRADE_PLAN.md | Upgrade plan | INTERNAL |
| GROSS_Trillion_Dollar_Forensic_Synthesis_Report.txt | Forensic | INTERNAL |
| DISCLOSURE_xAI_Privacy_Gap.md | Disclosure | INTERNAL |
| DISK_CLEANUP_ANALYSIS_REPORT_2026-05-31.md | Cleanup | INTERNAL |
| SMART_ELIMINATION_REPORT_2026-05-31.md | Elimination | INTERNAL |
| phase2/turn*.py | Probes | INTERNAL |
| phase3/ERNIE_*.md | Missions | INTERNAL |

---

## 8. CHANGE LOG (Expanded State)

| Date | Change | Source | Verification |
|------|--------|--------|------------|
| 2026-04-21 | 617 tests passing | Codex report | 01_PROJECT_STATE.md |
| 2026-05-02 | Knowledge base updated | 14-day audit | knowledge_update_summary.md |
| 2026-05-27 | GROSS incident discovered | Devin/Kimi | GROSS synthesis |
| 2026-05-28 | Forensic analysis | 4-agent convergence | INTELLIGENCE_CONCLUSION.md |
| 2026-05-29 | WSL canary tests | GROSS team | WSL_TRANSITION_TEST_RESULTS.md |
| 2026-05-31 | Grounded state synthesis | Devin Kimi 2.6 | GROSS_PROJECT_STATE_4AGENT.md |
| 2026-06-03 | GPU hog discovered | DeepSeek V4 | NEXUSbigLOGdeepseekV4-01.txt |
| 2026-06-09 | Full discovery audit | This agent | MASTER_WORKLOG_2026-06-09.md |
| 2026-06-09 | Intelligence scores corrected | HuggingFace benchmarks | scores.js edit + ModelRelay restart |
| 2026-06-09 | God Mode routing verified | Python test | DeepSeek V4 Pro selected |
| 2026-06-09 | Scaleway added | sources.js | 14 models discovered, 429 rate-limited |
| 2026-06-09 | Dashboard matrix verified | curl API | 92 UP models, correct scores |

---

*This document expands 01_PROJECT_STATE.md with full inventory. For canonical state, read 01_PROJECT_STATE.md first. For agent onboarding, read MEMORY_INDEX.md.*
