# NEXUS OS — Memory Index (Fast Agent Onboarding)
## Version: 2026-06-09
## Purpose: 5-minute read for any new agent to become productive immediately

---

## 1. SYSTEM AT A GLANCE

```
NEXUS OS = Governed agent operating system
├─ Bridge (API ingress, protocol adapters)
├─ Governor (KAIJU gates, policy, compliance)
├─ Vault (5-track memory, encryption)
├─ Engine/GMR (task routing, execution flow)
├─ Swarm (worker orchestration)
├─ Monitoring (TokenGuard, VAP, telemetry)
└─ ModelRelay (model routing + health checks)
```

**Core rule**: Actions are evidence-grounded, proposal-bound, test-gated, auditable.

---

## 2. WHERE THINGS LIVE

### Canonical Repo (ACTIVE DEVELOPMENT)
```
C:\Users\speci.000\Documents\NEXUS
├─ 01_PROJECT_STATE.md       ← START HERE (canonical system state)
├─ AGENTS.md                  ← Agent operating rules, git discipline, safety
├─ docs/handbook/             ← nexusctl guide, safety procedures, troubleshooting
├─ docs/discovery/            ← Discovery reports (this worklog, etc.)
├─ nexus_os/relay/            ← God Mode Proxy, ModelRelay integration
│  └─ god_mode_proxy.py       ← v3, 7 profiles, DeepSeek V4 Pro selected
├─ nexus_os/monitoring/       ← dashboard.html, INTELL_SCORE_GUIDE.md
├─ nexus_os/governor/         ← KAIJU, policy, compliance
├─ nexus_os/vault/            ← 5-track memory, encryption
└─ nexus_os/engine/           ← GMR, Hermes, routing
```

### Downloads Folders (SUPPORTING MATERIALS)
```
C:\Users\speci.000\Downloads\ARCHIVIST     ← 283 files: research, plans, logs, subsystems
C:\Users\speci.000\Downloads\NEXUSlogs      ← 61 log files: system logs, agent worklogs
C:\Users\speci.000\Downloads\PAPERS        ← 6 paper folders + datasets (research library)
```

### Confidential Project (READ-ONLY)
```
D:\GROSS                      ← Grok audit/forensics project (72 files)
├─ grok_mcp_server.py         ← MCP bridge (port 7354, 17 tools)
├─ evidence/                  ← Forensic evidence
├─ phase2/                   ← Turn-by-turn reconnaissance (turn1-26)
├─ phase3/                   ← ERNIE missions, state reports, analysis
├─ nexus-observations/        ← Live capture archive
└─ audit_trail/              ← Tamper-evident audit logs
```

### D:\ Other
```
D:\NEXUS_COLD                ← Cold storage, migrations, quarantine
D:\NEXUS_OS_AUDIT            ← Sysmon auditing infrastructure (README.md has guide)
D:\NEXUS_RECOVERY            ← Recovery snapshots
D:\MyModels                  ← Ollama model blobs + manifests
D:\YE2026                    ← Unknown purpose (arkisıla, curated best)
D:\Ollama_Backup            ← Ollama model backups
D:\ollama_models            ← Active Ollama model storage
```

---

## 3. ACTIVE SERVICES (PORTS)

| Port | Service | What It Does | How to Check |
|------|---------|-------------|--------------|
| 7352 | ModelRelay (Node.js) | Model health, discovery, routing | `curl http://localhost:7352/api/models` |
| 7354 | GROSS MCP Bridge | Forensic audit bridge to Grok | `curl http://localhost:7354/health` |
| 7356 | Dashboard (HTML) | Quality × Health Matrix | Open browser to `http://localhost:7356` |
| 7357 | God Mode Proxy v3 | Smart model routing, 7 profiles | `curl -X POST http://localhost:7357/v1/chat/completions` |
| 11435 | Ollama | Local model runner (GPU) | `curl http://localhost:11435/api/tags` |

**Offline**: 3000 (Next.js dashboard), 3003 (WebSocket Swarm) — may need restart

---

## 4. MODEL ROUTING QUICK REFERENCE

### Best Working Model (Current)
```
accounts/fireworks/models/deepseek-v4-pro
  Intelligence: 0.89 (MMLU-Pro 87.5%, LiveCodeBench 93.5%)
  Latency: ~1295ms
  Context: 131,072 tokens
  Provider: Fireworks (tier 1, $1 trial budget)
```

### God Mode Profiles (7)
| Profile | Use Case | Top Priority |
|---------|----------|------------|
| `god-mode` | General balanced | Intelligence + Health + Latency |
| `god-smart` | Research, coding | Intelligence first (DeepSeek V4 Pro) |
| `god-fast` | Quick responses | Latency first |
| `god-code` | Programming | Code-capable models (DeepSeek, Qwen Coder) |
| `god-reason` | Reasoning tasks | Reasoning models (DeepSeek-R1, o3) |
| `god-creative` | Writing, stories | Creative models (Claude, Gemini) |
| `god-1m` | Long documents | Context > 1M tokens (Mistral, Gemini) |

**Usage**:
```bash
curl -X POST http://localhost:7357/v1/chat/completions \
  -H "Authorization: Bearer god-smart" \
  -d '{"model":"god-smart","messages":[{"role":"user","content":"Hello"}]}'
```

### Intelligence Tiers (0-1 scale)
- **Frontier (0.88-0.92)**: Gemini 3.1 Pro (0.91), Gemini 2.5 Pro (0.90), DeepSeek V4 Pro (0.89), Claude Sonnet 4.5 (0.88)
- **Strong (0.75-0.87)**: Mistral Large 2512 (0.77), Kimi K2.6 (0.76), Qwen 3.5 397B (0.76)
- **Capable (0.60-0.74)**: DeepSeek V4 Flash (0.85), Codestral (0.67), various capable models
- **Basic (<0.60)**: Smaller models, older versions

**Source**: `scores.js` in ModelRelay node_modules (must restart ModelRelay to reload)

---

## 5. PROVIDER STATUS (QUICK REFERENCE)

| Provider | Status | UP Models | Key Limitation |
|----------|--------|-----------|---------------|
| Mistral | ONLINE | 43 | 1M tokens/month |
| Cloudflare | ONLINE | 18 | 10k neurons/day |
| OpenRouter | ONLINE | 16 | Rate limited |
| Fireworks | ONLINE | 2 | $1 trial budget |
| Scaleway | RATE-LIMITED | 14 | Per-minute 429, auto-recovery |
| Google AI | OFFLINE | 0 | Credits depleted (429) |
| GitHub Models | OFFLINE | 0 | 1500/day exceeded |
| Cerebras | OFFLINE | 0 | Paywalled |
| NVIDIA | OFFLINE | 0 | All 404 (wrong model IDs?) |
| DeepInfra | OFFLINE | 0 | Quota depleted |
| SiliconFlow | OFFLINE | 0 | Quota depleted |
| Sambanova | OFFLINE | 0 | Quota depleted |
| Kiro | IDLE | 2 | Complex auth |

**Total**: 92 UP, 342 DOWN (out of 434 discovered)

---

## 6. CRITICAL CONFIG FILES

### ModelRelay Config
```
C:\Users\speci.000\.modelrelay.json
```
- 18 provider keys, API endpoints, rate limits
- **IMPORTANT**: Run from `AppData\Roaming\npm\node_modules\modelrelay\bin\modelrelay.js`
- **NOT** from npx (npx cache overwrites patches)

### Intelligence Scores
```
C:\Users\speci.000\AppData\Roaming\npm\node_modules\modelrelay\scores.js
```
- Single source of truth for model rankings
- Must restart ModelRelay to reload after edits

### Model Sources
```
C:\Users\speci.000\AppData\Roaming\npm\node_modules\modelrelay\sources.js
```
- Provider model lists, Scaleway recently added

### God Mode Proxy
```
C:\Users\speci.000\Documents\NEXUS\nexus_os\relay\god_mode_proxy.py
```
- v3, 726 lines, FastAPI
- 7 profiles, fallback chains, provider diversity

---

## 7. GROSS PROJECT (CONFIDENTIAL — READ ONLY)

**What it is**: Forensic audit of Grok/xAI data flows
**Classification**: NEXUS INTERNAL — GROSS OPERATIONAL INTELLIGENCE
**Rule**: Read-only. No modifications without SPECI approval.

### Key Facts
- Grok CLI was staging 37.42 GB of local files for xAI cloud upload
- Not stolen secrets, but massive privacy violation (no consent)
- Queue now: 5 files / 21,898 bytes (post opt-out)
- Hades K8s cluster mapped (hades-openbar namespace)
- 17 MCP tools exposed to browser Grok for audit
- Full host namespace compromise achieved via nsenter

### Files to Read (if working on GROSS)
1. `D:\GROSS\GROSS_PROJECT_GROUNDED_STATE_SYNTHESIS_2026-05-31.md` — Authoritative state
2. `D:\GROSS\GROSS_PROJECT_STATE_4AGENT.md` — Agent briefing
3. `D:\GROSS\MCP_BLACKBOX_PROBE_DESIGN_2026-05-28.md` — Probe design
4. `D:\GROSS\INTELLIGENCE_CONCLUSION_2026-05-28.md` — Findings summary

### Never Do
- Modify GROSS files without explicit SPECI approval
- Share GROSS evidence outside NEXUS
- Run GROSS probes without KAIJU approval
- Auto-commit GROSS findings to public repos

---

## 8. COMMON COMMANDS

### Check System Status
```bash
# ModelRelay health
curl -s http://localhost:7352/api/models | python -c "import sys,json; d=json.load(sys.stdin); print(f'Total: {len(d[\"models\"])}, UP: {len([m for m in d[\"models\"] if m[\"status\"]==\"up\"])}')"

# God Mode Proxy status
curl -s http://localhost:7357/god/status

# GROSS bridge health
curl -s http://localhost:7354/health

# Active ports
netstat -an | findstr "LISTENING"
```

### Restart ModelRelay (after score changes)
```bash
# Find and kill old process
taskkill /F /IM node.exe 2>nul
# Start from local node_modules (NOT npx)
node C:\Users\speci.000\AppData\Roaming\npm\node_modules\modelrelay\bin\modelrelay.js --port 7352 --config C:\Users\speci.000\.modelrelay.json
```

### Test Chat via God Mode
```bash
curl -X POST http://localhost:7357/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer god-smart" \
  -d '{"model":"god-smart","messages":[{"role":"user","content":"Hello"}],"max_tokens":50}'
```

### Check GPU
```bash
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv
```

### Git Discipline
```bash
# Check before staging
git status --short
git diff
git log --oneline -10

# Stage explicit paths only (NEVER git add .)
git add path/to/file.py
```

---

## 9. WHEN YOU NEED HELP

### First Read (in order)
1. `01_PROJECT_STATE.md` — Canonical system state
2. `AGENTS.md` — Operating rules, safety, git discipline
3. `docs/handbook/03_NEXUSCTL_GUIDE.md` — CLI commands
4. `docs/discovery/MASTER_WORKLOG_2026-06-09.md` — Full discovery findings
5. `docs/discovery/OPTIMIZATION_GUIDE.md` — What needs fixing

### If Something Is Broken
1. Check `docs/handbook/` for troubleshooting
2. Run `nexusctl doctor --suggest-fixes` (if available)
3. Check `NEXUSlogs` for error patterns
4. Check `ARCHIVIST` for similar past issues
5. Check `PAPERS` for research-backed solutions

### If Adding a New Model/Provider
1. Add to `sources.js` (model list + endpoint)
2. Add score to `scores.js` (with benchmark evidence)
3. Add provider tier to `PROVIDER_TIER` in `god_mode_proxy.py`
4. Restart ModelRelay to pick up changes
5. Test with `curl http://localhost:7352/api/models`
6. Verify dashboard shows new model
7. Update `MEMORY_INDEX.md` (this file)

---

## 10. QUICK DECISION TREE

```
New task arrives
├─ Is it GROSS-related?
│  └─ Read GROSS_PROJECT_STATE_4AGENT.md first
│  └─ Read-only unless SPECI approves
├─ Is it model/provider related?
│  └─ Check scores.js, sources.js, restart ModelRelay
├─ Is it code change?
│  └─ Read AGENTS.md (git rules, test requirements)
│  └─ Run tests before commit
├─ Is it security-sensitive?
│  └─ Read AGENTS.md (hard-fail defaults, escape hatches)
│  └─ KAIJU approval required
└─ Is it documentation?
   └─ Update canonical docs in Documents\NEXUS\docs\
   └─ Update this MEMORY_INDEX if structure changes
```

---

## 11. CHANGE LOG

| Date | Change | Agent |
|------|--------|-------|
| 2026-06-09 | Created MEMORY_INDEX | NEXUS Auditor |
| 2026-06-09 | Corrected intelligence scores (DeepSeek 0.89, GPT-4o 0.81) | NEXUS Auditor |
| 2026-06-09 | Discovered ARCHIVIST chaos, GROSS state, NEXUSlogs patterns | NEXUS Auditor |
| 2026-06-09 | Verified 92 UP models, 8 active providers | NEXUS Auditor |
| 2026-06-09 | Fixed God Mode routing to DeepSeek V4 Pro | NEXUS Auditor |

---

*This is a living document. Update it when the system changes.*
