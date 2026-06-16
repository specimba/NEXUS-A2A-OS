---
id: NODE-MIG-NEO_NEXUS_GROUNDING
authority_scope: experimental
origin_sha256: 9281d847184344f261692a48a8276a54f595b30a29a64cf618a8b3ef95429c0c
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-0F8C9C
---
# NEO Agent ↔ NEXUS Main Repository Grounding Guide

**Date**: 2026-05-19  
**NEXUS Canonical Commit**: `7272f6a` (fix(recovery): restore package sources and diagnostics)  
**Purpose**: Bridge NEO agent's Nexus OS v0.9.0 with NEXUS Main Repository v3.0.0

<!-- CANARY: 871c48ab31c09db6ec1bc30d5ef49823 -->
---

## 1. Executive Summary

This document establishes the canonical integration path between:
- **NEO Agent Folder**: `C:\Users\speci.000\Documents\NEO agent\` - Contains Nexus OS v0.9.0 with S-P-E-W Memory, A2A Bridge, Hermes Router
- **NEXUS Main**: `C:\Users\speci.000\Documents\NEXUS\` - Contains NEXUS Sovereign OS v3.0.0 with Dashboard, nexusctl CLI, and hardened OS modules

**Integration Strategy**: NEO's advanced modules (Hermes, MARS, S-P-E-W Vault) should extend NEXUS's canonical structure while respecting its governance, CLI, and dashboard architecture.

---

## 2. NEXUS Canonical Structure (Commit 7272f6a)

### 2.1 Core Directory Layout
```
NEXUS/
├── AGENTS.md                    # Canonical agent operating protocol
├── 01_PROJECT_STATE.md          # Source of truth for system state
├── README.md                    # Project overview
├── pyproject.toml              # Python package config (nexus-os v3.0.0)
│
├── nexusctl/                   # CLI Management Layer
│   ├── __init__.py
│   ├── __main__.py             # Entry point: python -m nexusctl
│   └── cli.py                  # Commands: doctor, cycle-check, handoff, status
│
├── nexus_os/                   # Root compatibility modules
│   ├── bridge/
│   │   ├── cloudflare_bypass.py
│   │   ├── mcpaauth.py
│   │   ├── sdk.py
│   │   ├── secrets.py
│   │   ├── server.py
│   │   └── vault.py
│   ├── gmr/
│   │   └── latency_monitor.py
│   ├── governor/
│   │   └── trust_kernel.py     # 631 lines, Bayesian trust scoring
│   ├── relay/
│   │   └── model_relay.py      # Model routing
│   └── twave/
│       ├── chimera_router_v2.py
│       └── landau_ginzburg_tracker_v2.py
│
├── src/nexus_os/              # Source-tracked OS modules
│   ├── governor/
│   │   ├── __init__.py
│   │   ├── trust_kernel.py     # Canonical trust scoring
│   │   └── trust_scoring.py    # 258 lines
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── token_guard.py      # 811 lines, token budget enforcement
│   │   └── token_policy.py     # 521 lines
│   ├── bridge/
│   ├── db/
│   ├── engine/
│   ├── gmr/
│   ├── relay/
│   ├── swarm/
│   ├── security/
│   ├── vault/
│   └── team/
│
├── src/app/api/               # Next.js API Routes
│   ├── agents/
│   ├── ai-bridge/
│   ├── alphaxiv/
│   ├── arxiv/
│   ├── chat/
│   ├── claude/
│   ├── foundry/
│   ├── governance/
│   ├── governor/
│   ├── keys/
│   ├── logs/
│   ├── models/
│   ├── providers/
│   ├── rate-limit/
│   ├── research/
│   ├── stresslab/
│   ├── swarm/
│   ├── system/
│   ├── tokens/
│   └── vault/
│
├── src/components/nexus/      # React Dashboard Components
│   ├── overview-tab.tsx
│   ├── stresslab-tab.tsx
│   ├── gmr-tab.tsx
│   ├── governor-tab.tsx
│   ├── vault-tab.tsx
│   ├── research-tab.tsx
│   ├── swarm-tab.tsx
│   ├── tokens-tab.tsx
│   ├── ai-assistant.tsx
│   ├── command-palette.tsx
│   ├── notification-center.tsx
│   ├── quick-stats-widget.tsx
│   └── global-export-dialog.tsx
│
├── tasks/                     # Task Queue System
│   ├── pending/
│   ├── done/
│   └── failed/
│
├── docs/
│   ├── handoff/              # Recovery & optimization notes
│   └── operations/           # Worklogs
│
├── tests/                    # Test Suite (664 passing)
│   ├── api/
│   ├── benchmarks/
│   ├── bridge/
│   ├── cli/
│   ├── contracts/
│   ├── cron/
│   └── engine/
│
└── scripts/                  # PowerShell controllers
    ├── nexus_docker_profile.ps1
    └── nexus_docker_secret_audit.ps1
```

### 2.2 Key Canonical Files

| File | Purpose | NEO Should |
|------|---------|------------|
| `AGENTS.md` | Operating protocol, safety gates, git discipline | Read and follow strictly |
| `01_PROJECT_STATE.md` | Current system state | Check before operations |
| `nexusctl/cli.py` | CLI commands | Extend with NEO-specific commands |
| `pyproject.toml` | Package config | Merge NEO dependencies |
| `src/nexus_os/governor/trust_kernel.py` | Trust scoring | Use as canonical, extend NEO's |
| `src/nexus_os/monitoring/token_guard.py` | Token budgets | Integrate with NEO's TokenGuard |

---

## 3. NEO Agent Architecture Overview

### 3.1 NEO's Module Structure
```
NEO agent/
├── AGENTS.md                    # NEO's agent rules (different from NEXUS)
├── PROJECT_KNOWLEDGE_BASE.md    # NEO's Nexus OS v0.9.0 docs
├── README.md                    # Multi-Agent AI Hub description
├── pyproject.toml              # NEO's Python config
│
├── src/nexus_os/               # NEO's OS implementation
│   ├── bridge/                 # A2A Bridge (server.py, sdk.py, router.py, secrets.py)
│   ├── core/                   # aesthetics.py, trust.py
│   ├── db/                     # manager.py (thread-safe SQLite)
│   ├── engine/                 # executor.py, hermes.py, mars.py, router.py, heartbeat.py, forge.py, skill_adapter.py
│   ├── gmr/                    # rotator.py, pool_config.py, context_packet.py, modelmap.py, telemetry.py
│   ├── governor/               # base.py, kaiju_auth.py, compliance.py, contracts.py, trust_scoring.py, autoharness.py, proof_chain.py, privacy.py
│   ├── vault/                  # manager.py, trust.py, poisoning.py, mem0_adapter.py, faiss_index.py, mempalace.py, superlocal.py
│   ├── swarm/                  # coordinator.py, foreman.py
│   ├── monitoring/             # token_guard.py, token_compactor.py, tracing.py
│   ├── observability/          # squeez.py, tracing.py, langfuse_tracker.py
│   └── skills/                 # fortify.py, adeu_redlining.py
│
├── nexus-integration/          # NEO's integration docs & code
│   ├── NEXUS_HERMES_NEO_GROUNDING_REPORT.md
│   ├── INTEGRATION_GUIDE.md
│   ├── INTEGRATION_ROADMAP.md
│   ├── nexus-os-hardening/     # Hardened modules (test dbs, cron jobs)
│   └── enhanced/               # Enhanced modules (token efficiency, bridges)
│
├── .agent/                     # Agent configuration
├── .cursor/                    # Cursor IDE rules
├── .clinerules/              # Cline rules
├── .devin/                     # Devin knowledge
├── .kilo/                      # Kilo package
├── benchmarks/
├── tests/
└── configs/
```

### 3.2 NEO's Key Innovations

| Module | Innovation | Integration Point |
|--------|-----------|-------------------|
| `engine/hermes.py` | Experience-based model router (3-layer: classify→score→cost-optimize) | Extend NEXUS's `/api/ai-bridge` |
| `engine/mars.py` | Multi-token autoregressive speculative decoding (1.5-1.7x throughput) | Add to NEXUS's GMR |
| `vault/` | S-P-E-W Memory Hierarchy (Session→Project→Experience→Wisdom) | Extend NEXUS's Vault tab |
| `governor/kaiju_auth.py` | 4-variable authorization (scope, impact, clearance, intent) | Merge with NEXUS's Governor |
| `gmr/rotator.py` | Genius Model Rotator with intent-based routing | Extend NEXUS's GMR |
| `monitoring/token_guard.py` | Token budget enforcement | Merge with NEXUS's TokenGuard |

---

## 4. Integration Mapping: NEO → NEXUS

### 4.1 Module Integration Strategy

```
NEO Module                    →   NEXUS Canonical Location
─────────────────────────────────────────────────────────────
src/nexus_os/bridge/          →   src/nexus_os/bridge/ + nexus_os/bridge/
src/nexus_os/vault/           →   src/nexus_os/vault/ (NEW)
src/nexus_os/engine/hermes.py →   src/nexus_os/engine/ (NEW)
src/nexus_os/engine/mars.py   →   src/nexus_os/engine/ (NEW)
src/nexus_os/governor/        →   Merge with src/nexus_os/governor/
src/nexus_os/gmr/             →   Merge with src/nexus_os/gmr/ + nexus_os/gmr/
src/nexus_os/swarm/           →   src/nexus_os/swarm/ (exists)
src/nexus_os/monitoring/      →   Merge with src/nexus_os/monitoring/
src/nexus_os/observability/   →   src/nexus_os/observability/ (NEW)
src/nexus_os/skills/          →   src/nexus_os/skills/ (NEW)
```

### 4.2 API Route Integration

NEO's capabilities should extend NEXUS's existing API structure:

```
NEXUS Existing                NEO Addition
─────────────────────────────────────────────────
/api/ai-bridge               + Hermes routing endpoint
/api/models                  + MARS inference endpoint
/api/vault                   + S-P-E-W memory endpoints
/api/governor                + KAIJU auth endpoints
/api/swarm                   + Coordinator endpoints
/api/tokens                  + Enhanced TokenGuard
```

### 4.3 Dashboard Tab Integration

NEO's features map to NEXUS's 8-pillar dashboard:

| NEXUS Tab | NEO Feature | Integration |
|-----------|-------------|-------------|
| Overview | S-P-E-W Memory stats | Add memory layer metrics |
| StressLab | Hermes routing tests | Add model routing tests |
| GMR | MARS inference, Model Rotator | Add throughput metrics |
| Governor | KAIJU auth, Compliance | Add 4-variable auth UI |
| Vault | S-P-E-W Memory | Extend vault with memory layers |
| Research | (existing) | No change needed |
| Swarm | Coordinator, Foreman | Extend worker management |
| Tokens | TokenGuard | Merge token budget features |

---

## 5. Canonical Operational Interface

### 5.1 NEO Must Use NEXUS's nexusctl

```bash
# Pre-flight checks (REQUIRED before operations)
python -m nexusctl doctor
python -m nexusctl doctor memory --report-only

# Cycle validation (REQUIRED after work)
python -m nexusctl cycle-check

# Generate handoff package
python -m nexusctl handoff

# Status check
python -m nexusctl status
```

### 5.2 Git Discipline (from AGENTS.md)

```bash
# Check status before staging
git status --short

# NEVER use git add .
# Stage explicit paths only
git add src/nexus_os/engine/hermes.py
git add src/nexus_os/vault/

# Separate unrelated changes into separate commits
git commit -m "feat(hermes): add experience-based model routing

- Implements 3-layer routing: classify → score → cost-optimize
- Integrates with NEXUS's /api/ai-bridge
- Tests: 664 passing"
```

### 5.3 Task Queue System

NEO should use NEXUS's task queue:

```
tasks/pending/     → Create .task.md files here
tasks/done/        → Move completed tasks here
tasks/failed/      → Move failed tasks here with failure report
```

---

## 6. Safety Gates & Governance

### 6.1 Pre-Execution Safety Gates (from AGENTS.md)

- [SAFETY-1] Verify output integrity before passing to another agent
- [SAFETY-2] Confirm sandbox isolation is active
- [SAFETY-3] Respect token budget limits (check TokenGuard)
- [SAFETY-4] Pass all KAIJU evaluations before side effects

### 6.2 NEO's KAIJU Integration

NEO's 4-variable authorization should extend NEXUS's Governor:

```python
# NEO's KAIJU (from kaiju_auth.py)
scope: self | project | cross_project | system
impact: low | medium | high | critical
clearance: reader | contributor | maintainer | admin
intent: str (justification, min 3 chars)

# Integration with NEXUS's Governor API
POST /api/governor
{
  "action": "kaiju_auth",
  "scope": "project",
  "impact": "medium",
  "clearance": "maintainer",
  "intent": "Integrate Hermes router with AI bridge"
}
```

---

## 7. Testing & Verification

### 7.1 NEXUS Test Suite

```bash
# Run full test suite (REQUIRED for core changes)
PYTHONPATH=.;src;bin python -m pytest tests/ -v --tb=short

# Current status: 664 passed, 1 warning
```

### 7.2 NEO Test Integration

NEO's tests should be added to NEXUS's test structure:

```
tests/
  ├── bridge/test_neo_bridge.py      # NEO's A2A bridge tests
  ├── engine/test_hermes.py          # Hermes router tests
  ├── engine/test_mars.py             # MARS inference tests
  ├── vault/test_spew_memory.py       # S-P-E-W memory tests
  └── governor/test_kaiju.py          # KAIJU auth tests
```

---

## 8. Action Plan for NEO Integration

### Phase 1: Foundation (Week 1)
1. [ ] Copy NEO's `src/nexus_os/` modules to NEXUS's `src/nexus_os/`
2. [ ] Merge `pyproject.toml` dependencies
3. [ ] Run `python -m nexusctl doctor` to verify
4. [ ] Run full test suite: `pytest tests/ -v`

### Phase 2: Bridge Integration (Week 2)
1. [ ] Integrate NEO's A2A Bridge with NEXUS's `/api/ai-bridge`
2. [ ] Merge NEO's Hermes router with NEXUS's provider bridge
3. [ ] Add MARS inference endpoint to `/api/models`
4. [ ] Verify with stress tests

### Phase 3: Vault & Memory (Week 3)
1. [ ] Extend NEXUS's Vault tab with S-P-E-W memory layers
2. [ ] Integrate FAISS indexing with NEXUS's database
3. [ ] Add mem0 adapter for persistent memory
4. [ ] Test memory operations via dashboard

### Phase 4: Governor & Compliance (Week 4)
1. [ ] Merge KAIJU 4-variable auth with NEXUS's Governor
2. [ ] Integrate compliance engine with NEXUS's governance API
3. [ ] Add VAP proof chain for audit trails
4. [ ] Verify with security audit

### Phase 5: Swarm & Coordination (Week 5)
1. [ ] Extend NEXUS's Swarm tab with NEO's Coordinator
2. [ ] Integrate Foreman patrol with NEXUS's worker management
3. [ ] Add task reconciliation to `/api/swarm`
4. [ ] Test multi-agent coordination

---

## 9. Key Contacts & References

### 9.1 NEXUS Canonical Documentation
- `AGENTS.md` - Agent operating protocol
- `01_PROJECT_STATE.md` - Current system state
- `docs/handoff/` - Recovery and optimization notes
- `docs/operations/worklog.md` - Operational history

### 9.2 NEO Documentation
- `PROJECT_KNOWLEDGE_BASE.md` - NEO's architecture
- `nexus-integration/NEXUS_HERMES_NEO_GROUNDING_REPORT.md` - Detailed review
- `nexus-integration/INTEGRATION_GUIDE.md` - Integration steps
- `nexus-integration/INTEGRATION_ROADMAP.md` - Roadmap

---

## 10. Verification Checklist

Before claiming integration complete:

- [ ] `python -m nexusctl cycle-check` passes
- [ ] `python -m nexusctl doctor` reports healthy
- [ ] `pytest tests/ -v` shows all tests passing
- [ ] Dashboard loads with all 8 tabs functional
- [ ] API routes respond correctly (`/api/system`, `/api/swarm`, etc.)
- [ ] No duplicate React key errors in console
- [ ] Git worktree is clean (`git status --short`)
- [ ] Documentation updated in `docs/handoff/`
- [ ] Task files moved to `tasks/done/`

---

**End of Grounding Guide**

*This document should be kept in sync with both NEO and NEXUS repositories. Last updated: 2026-05-19*
