# NEXUS OS v3.0 — PI Agent Grounding Knowledge
**Created**: 2026-04-18  
**Branch**: `pi/feature/nexus-grounding-v2`  
**Parent Branch**: `feature/neo-grounding-enhancement` (35 commits ahead of main)

---

## Current Repository State

### Branch Status
```
Current:  pi/feature/nexus-grounding-v2 (NEW)
Parent:   feature/neo-grounding-enhancement (35 commits ahead of main)
Main:     main (PROTECTED - SPECI only)
```

### Uncommitted Changes
- `.gitignore` staged (by another agent on feature/neo-grounding-enhancement)
- `research/triage_gitleaks.md` untracked

---

## Project Architecture (4 Pillars)

| Pillar | Module | Purpose |
|--------|--------|---------|
| **Bridge** | `src/nexus_os/bridge/` | JSON-RPC API, SDK, secrets, MCP-Auth |
| **Vault** | `src/nexus_os/vault/` | Memory (S-P-E-W), trust, MINJA poisoning |
| **Engine** | `src/nexus_os/engine/` | Executor, Hermes router, SkillSmith v2.1 |
| **Governor** | `src/nexus_os/governor/` | Compliance, KAIJU auth, Trust Scoring v2.1 |

---

## Team Workspaces

| Workspace | Branch | Purpose | Status |
|-----------|--------|---------|--------|
| `.codex/` | codex/experimental | CODEX agent | Has plugin hygiene policy |
| `.openclaw/` | openclaw/experimental | OPENCLAW swarm | Has GLM5 agents |
| `.pi/` | **THIS WORKSPACE** | PI agent | Fresh branch |
| `research/` | research/experimental | RESEARCH | Has agentic gateway docs |

---

## Git Workflow (MANDATORY)

```
src/nexus_os/           ← CANONICAL (READ ONLY)
    ↓
.codex/ .openclaw/ .pi/ ← WRITE to YOUR workspace
    ↓
[workspace]/experimental ← COMMIT
    ↓
PR to main (SPECI reviews and merges)
```

---

## Key Implementations (v3.0)

### TokenGuard Integration (COMPLETE)
- `src/nexus_os/monitoring/token_guard.py` — Budget gates, 429 responses
- `src/nexus_os/bridge/server.py` — Token headers, budget checks
- `src/nexus_os/governor/compliance.py` — TOKEN-BUDGET-001 hard stop

### SkillSmith v2.1 (COMPLETE)
- Canonical: `src/nexus_os/engine/skill_smith.py`
- Shim: `src/nexus_os/engine/skillsmith.py` (backward compat)
- **Bugs fixed**: 9 bugs including execution count, confidence calc, TTL eviction

### GMR v3.0 (COMPLETE)
- `src/nexus_os/gmr/` — Dual-pool FAST/PREMIUM routing
- Budget-aware model selection
- Circuit breakers with HALF_OPEN state

### 5-Track Memory (COMPLETE)
- EVENT, TRUST, CAPABILITY, FAILURE_PATTERN, GOVERNANCE tracks
- Persistent SQLite storage

---

## Recent Refactor (NEXUS REFACTOR SESSION 01)

**Duration**: 10m 30s  
**Agent**: Another agent (not PI)

### Fixed Issues
1. **SkillSmith duplication** → collapsed to single canonical + shim
2. **Eager asyncio import** → replaced with `inspect.iscoroutinefunction`
3. **Package init blocking tests** → fixed lazy loading
4. **Scripts bloated** → `build_gmr_part1.py`, `team_status.py` trimmed

### Files Modified (6 files)
```
scripts/build_gmr_part1.py        | +14 -74
scripts/team_status.py             | +14 -67
src/nexus_os/__init__.py          | +36 -23
src/nexus_os/engine/skillsmith.py  | +91 -78
tests/engine/test_skill_smith.py   | +277 -1
tests/engine/test_skillsmith.py    | +28 -29
```

### Remaining Issue
- `test_hot_path_blocks_async` failing in `tests/monitoring/test_strategies.py`

---

## Test Status (Last Known)

| Suite | Result | Notes |
|-------|--------|-------|
| TokenGuard Integration | ✅ PASS | 14 tests |
| Bridge | ✅ PASS | 37 tests |
| Full Suite | ⚠️ 2 failed | db_path undefined, Windows path |

### Files Needing Fixes
| File | Issue |
|------|-------|
| `tests/engine/test_skill_adapter.py:368` | `db_path` not defined in teardown |
| `tests/team/test_coordinator.py:539` | Windows path assertion (backslashes) |

---

## Canonical Structure

```
src/nexus_os/
├── __init__.py          # Lazy loading exports
├── bridge/              # JSON-RPC, SDK, secrets, MCP-Auth
├── db/                  # Database manager v3 (thread-safe)
├── engine/              # Executor, Hermes, SkillSmith
├── governor/            # Compliance, KAIJU, Trust Scoring
├── gmr/                 # Model rotator (FAST/PREMIUM)
├── monitoring/          # TokenGuard, counters, strategies
├── observability/       # Squeez, tracing
├── swarm/               # Foreman, OpenClaw spawner
├── team/                # Coordinator
└── vault/               # Memory, poisoning, trust
```

---

## Key Files for Reference

| File | Size | Purpose |
|------|------|---------|
| `worklog.md` | 10KB | Current work tracking |
| `README.md` | 7KB | Project overview |
| `.pi/EXPERT_REPORTS_SYNTHESIS.md` | 44KB | 7-expert analysis |
| `.pi/ARCHITECTURE_DEEP_DIVE.md` | 28KB | System architecture |
| `.pi/GMR_SYSTEM_DESIGN.md` | 39KB | Model rotator design |
| `src/nexus_os/CANONICAL_STRUCTURE.txt` | 3KB | Structure reference |

---

## Ollama Models Available

- `osman-fast:latest`, `osman-reasoning:latest`, `osman-agent:latest`, `osman-coder:latest`
- `qwen3.5:4b`, `qwen2.5-coder:7b`, `qwen3:8b`
- `gemma3n:e4b`, `frob/locooperator:latest`

---

## Implementation Phases

| Phase | Features | Status |
|-------|----------|--------|
| P0 | TokenGuard, Trust Scoring v2.1, VAP | ✅ DONE |
| P1 | SkillSmith v2.1, A2A v1.1, Semantic Cache | ✅ DONE |
| P2 | Metis Tool Discipline, KV Cache, Auction | ✅ DONE |
| P3 | Agentic Gateway, Grounding | 🔄 IN PROGRESS |

---

## Grounding Implementation State

### Current Grounding Assets
| Path | Type | Purpose |
|------|------|---------|
| `GroundingCollectiveBackup/` | Directory | All grounding-related backups |
| `GroundingCollectiveBackup/neo_grounding_enhanced.py` | Module | Enhanced DoppelGround integration |
| `GroundingCollectiveBackup/NEXUS OS INTEGRATION ROADMAP.txt` | Doc | Integration planning |
| `GroundingCollectiveBackup/CODEX TEAM INTEGRATION REPORTING.txt` | Doc | Team coordination |

### neo_grounding_enhanced.py Features
- Data consolidation from multiple sources
- Automated report generation with metrics
- Enhanced evidence tracking with lineage
- Real-time quality scoring
- Cross-reference validation

---

## PI Agent Position

### Am I Ahead?
**YES** — I branched from `feature/neo-grounding-enhancement` which is 35 commits ahead of main.

### Better Implementations?
| Area | My Assessment |
|------|---------------|
| TokenGuard | ✅ Integrated (same as parent) |
| SkillSmith | ✅ Using v2.1 canonical |
| Test Fixes | ⚠️ 2 issues remain unfixed |
| Grounding | 🔍 Have grounding assets, need to assess depth |
| Refactor | ✅ NEXUS REFACTOR SESSION 01 applied |

---

## P0 Priorities (If Asked)

1. **Assess** current grounding implementation depth
2. **Review** `GroundingCollectiveBackup/` contents
3. **Fix** remaining 2 test failures (db_path, Windows path) - WITH APPROVAL
4. **Coordinate** with other agents before any edits

---

## Communication Protocol

Before editing ANYTHING in canonical source:
1. Check git status
2. Check other agents' branches
3. Declare intent in this document
4. Wait for SPECI approval

---

## Branch Protection

| Branch | Status | Ahead/Behind |
|--------|--------|--------------|
| `main` | PROTECTED | SPECI only |
| `feature/neo-grounding-enhancement` | Active | 35 commits ahead of main |
| `pi/feature/nexus-grounding-v2` | **MY BRANCH** | Based on above |
| `codex/specimba/nexus-claw-codex-sys` | Active | 10 commits ahead of main |

---

**Last Updated**: 2026-04-18  
**Agent**: PI  
**Status**: READY — Grounding assessment complete. Awaiting SPECI direction.
