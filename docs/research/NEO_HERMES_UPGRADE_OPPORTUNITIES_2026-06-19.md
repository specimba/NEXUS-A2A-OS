# NEO Agent + HERMES Upgrade Opportunities

Date: 2026-06-19

---
## Section 1: NEO Agent Structural Upgrades

### 1.1 Fix Diverged src/nexus_os/
Current: Standalone copy in NEO workspace
Recommended: Replace with symlink/junction to main NEXUS

Command: mklink /J C:\Users\speci.000\Documents\NEO agent\src\nexus_os C:\Users\speci.000\Documents\NEXUS\nexus_os

Risk: Store NEO-specific modifications in patches/ dir

### 1.2 Memory Architecture
Current: VaultManager + SuperLocalMemory + SQLite
Target: MemoryChannelManager (8-channel) + GovernedMemoryBroker

### 1.3 Git Repair
Current: git status fails
Plan: git fsck + reflog recovery OR re-clone + reapply patches

### 1.4 Remove Azure Foundry Dead References
Scan .env, AGENTS.md, .py files for azure/foundry/Azure

## Section 2: HERMES Structural Upgrades

### 2.1 Memory Unification
Current: SessionDB (SQLite+FTS5) + MemoryManager
Target: NEXUS 8-channel memory via plugin

Strategy: Create plugins/memory/nexus_memory_provider.py wrapping MemoryChannelManager
Keep SessionDB for FTS5 session search only

### 2.2 Governance Integration
Current: No governance
Target: KAIJU + VAP + TrustEngine v2.2 as plugin

### 2.3 ModelRelay Alignment
Current: Direct provider API calls
Target: http://localhost:7350/v1 via plugins/model-providers/modelrelay.py

### 2.4 Gateway -> Brain API sync
Each platform adapter can optionally POST to Brain API /api/messaging

## Section 3: Shared Upgrades

### 3.1 ModelRelay Models
Both should route through :7350 (482 models available)
Unified model selection, circuit breaking, telemetry

### 3.2 Token Optimization
Port NEO DOVA/MARS/RotorQuant/Squeez into main nexus_os/enhanced/

### 3.3 Port Governance
Add PortRegistry checks at startup
7350=ModelRelay 7352=Brain API 7355=Python fallback

## Section 4: ARCHIVIST Capability Matrix

NEXUS has capabilities NEO/HERMES lack:
- Guard Plane v13 (T2-T4: ALSB, CSI)
- TrustEngine v2.2
- MetaAttackDetector v5 (8 patterns)
- MisalignmentDetector (CDR auto-escalation)
- 8-channel memory + consolidation daemon
- ModelRelay (482 models, circuit breaker, telemetry)
- NEXUSCLAW v1 orchestration

ALL of these should be integrated as plugins in HERMES.

## Section 5: Implementation Priority

P0: Fix NEO git (1h)
P0: Remove Azure refs (30m)
P1: Symlink nexus_os (30m)
P1: Port MemoryChannelManager to HERMES (4h)
P2: Wire NEO to ModelRelay (2h)
P2: KAIJU gate plugin for HERMES (3h)
P3: Port NEO token optimization (8h)
P3: HERMES gateway -> Brain API (4h)
P4: Full arbitration VAP+TrustEngine (8h)

## Section 6: Verification Gates

Before marking complete:
- nexusctl doctor --suggest-fixes
- pytest full suite
- Verify ports 7350/7352/7355
- gitleaks scan for leaked credentials
- Update AGENTS.md + GROUNDING.md

## Section 7: Quick Start Script
See companion analysis doc for script details.

## Section 8: Risk Notes

1. RAW KEY MATERIAL in NEXUSopencodeMAINbackendgodmodelog-19.txt - rotate before merge
2. GLM-5.2 NOT cleared for autonomous execution (intell=0.45)
3. NEO/HERMES may have additional secrets in .env files
4. Both experimental paths lack NEXUS governance gates entirely

---
END OF DOCUMENT
