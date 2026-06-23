# NEO Agent + HERMES Alignment Analysis

Date: 2026-06-19
Sources: C:\Users\speci.000\Documents\NEO agent, C:\Users\speci.000\Documents\HERMES\hermes-agent, C:\Users\speci.000\Documents\NEXUS, C:\Users\speci.000\Downloads\NEXUSlogs

---

## Executive Summary

NEO agent and HERMES are both active experimental AI agent frameworks that partially overlap with the NEXUS OS canonical codebase. Both have diverged from NEXUS main in significant ways: NEO maintains a standalone copy of nexus_os under src/, while HERMES has its own state management, plugin system, and memory architecture.

Key findings:
- NEO src/nexus_os/ is a diverged copy of NEXUS main
- HERMES uses SessionDB (SQLite+FTS5) vs NEXUS 8-channel MemoryChannelManager
- NEO has git corruption, dead Azure Foundry references, and Python 3.13 incompatibility
- HERMES has mature plugin/gateway systems NEXUS lacks
- Both lack NEXUS governance (KAIJU, VAP, TrustEngine v2.2)

---

## 1. NEO Agent Baseline

### Structure
- src/nexus_os/ : Active development copy (likely diverged from main)
- nexus-integration/enhanced/integration/ : Token budget + trust scorer bridges
- chimera/ : Compression router (BonsaiTurtle, TWAVE plugins)
- GROK_nexus_agent.py, joker_opus_agent.py : Model-specific agents
- .autoclaw/ : Autoclaw orchestrator with comms/dispatch

### Current Blockers (from AGENTS.md)
1. Git repository corrupted
2. Azure Foundry DEAD
3. Pi Coding Agent BROKEN (Python 3.13)
4. Node.js toolchain corrupted

### Architecture Patterns
- Uses dataclass specs, Enum state machines, deque rate limiting
- Windows compatibility: lazy openai imports, forward slashes
- Database: direct SQLite via db/manager.py

---

## 2. HERMES Baseline

### Structure
- run_agent.py (~12k LOC) : AIAgent core loop
- cli.py (~11k LOC) : Interactive CLI
- hermes_state.py : SessionDB with FTS5, WAL fallback
- agent/ : Provider adapters, memory, caching
- gateway/ : 20+ platform adapters
- plugins/ : 15+ plugin categories
- ui-tui/ : Ink terminal UI

### Design Decisions
- WAL mode fallback for NFS/SMB compatibility
- FTS5 full-text search across sessions
- Single external memory provider policy
- Context fencing with <memory-context> tags
- Profile-aware paths via get_hermes_home()

---

## 3. NEXUS Main Reference

### Canonical State
- Phases A-D + 1-8 COMPLETE
- 2,146+ tests pass
- 53 Brain API routes on port 7352
- 8-channel Vault memory
- NEXUSCLAW v1 operational

### Key Differences
NEXUS uses:
- MemoryChannelManager (8 channels)
- GovernedMemoryBroker
- ConsolidationDaemon
- PortRegistry (thread-safe)
- KAIJU + VAP + TrustEngine v2.2

NEO/HERMES use:
- Direct SQLite state
- Single-context memory
- No governance gates
- Direct provider API calls

---

## 4. Alignment Gaps

| # | Gap | NEO | HERMES | NEXUS Main | Priority |
|---|-----|-----|-------|------------|----------|
| 1 | Diverged NEXUS copy | src/nexus_os/ standalone | N/A | canonical nexus_os/ | HIGH |
| 2 | Git corruption | Broken | Clean | Clean | HIGH |
| 3 | Memory architecture | VaultManager+SuperLocal | SessionDB+FTS5 | 8-channel MemoryChannelManager | HIGH |
| 4 | State persistence | nexus.db files | state.db WAL | Vault 5-track + channels | HIGH |
| 5 | Governance | kaiju_auth partial | None | Full KAIJU+VAP+TrustEngine | HIGH |
| 6 | Model access | Direct provider APIs | Direct provider APIs | ModelRelay :7350 | MEDIUM |
| 7 | Token optimization | DOVA/MARS/RotorQuant | Not present | TokenGuard+Compactor | MEDIUM |
| 8 | Plugin system | Not present | 15+ plugin dirs | SkillRegistry+GMR | MEDIUM |
| 9 | Dashboard | Not present | Ink TUI | Next.js :3001 | LOW |
| 10 | Dead code | Azure Foundry refs | N/A | Removed | MEDIUM |

---

## 5. Upgrade Opportunities

### For NEO Agent
1. Replace src/nexus_os/ with symlink to main NEXUS
2. Adopt MemoryChannelManager for 8-channel memory
3. Migrate state.db to Vault persistence
4. Wire kaiju_auth to KAIJU gates
5. Remove Azure Foundry dead code

### For HERMES
1. SessionDB -> NEXUS memory channels (read path first)
2. Gateway platforms -> Brain API /api/messaging
3. Plugin discovery -> NEXUS SkillRegistry
4. Model routing -> ModelRelay :7350
5. nexus-swarm-pack.zip -> formal submodule

---

## 6. Recommended Next Steps

1. Immediate: Fix NEO git, remove Azure refs
2. Short-term: Alignment script + memory migration
3. Medium-term: Governance integration
4. Governance: All changes pass nexusctl cycle-check + pytest

---

Full upgrade roadmap in companion doc: NEO_HERMES_UPGRADE_OPPORTUNITIES_2026-06-19.md
