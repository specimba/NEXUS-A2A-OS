---
name: nexus-os
description: |
  NEXUS OS v3.0 — modular agent governance framework for Zo. Provides intent routing
  (Hermes/Engine), trust scoring (Governor/Kaiju), 8-channel memory (Vault),
  speculative model routing (GMR), worker pool (Swarm), TALE token budgeting
  (Monitoring), skill auto-discovery (Skillsmith), and ISC-Bench TVD runner (StressLab).
  Boot the OS, run the test suite, iterate.
compatibility: Requires Python 3.10+
metadata:
  author: specimba
  category: Agent Framework
  display-name: NEXUS OS v3.0
  tags: nexus, agent, governance, swarm, vault, token-tracking, model-routing
---
# nexus-os

NEXUS OS v3.0 — modular agent governance framework.

## Architecture

| Pillar | Module | Purpose | Priority |
|--------|--------|---------|----------|
| Bridge | `src/nexus_os/bridge/` | HMAC auth, JSON-RPC | P0 |
| Engine | `src/nexus_os/engine/` | Intent routing + Metis v2 ToolGates | P1c |
| Governor | `src/nexus_os/governor/` | Auth, trust scoring (OR-Bench calibrated lanes) | P0b |
| Vault | `src/nexus_os/vault/` | 8-channel S-P-E-W memory | P1b |
| GMR | `src/nexus_os/gmr/` | Speculative routing + half-open circuit breaker | P0d/P1a |
| Swarm | `src/nexus_os/swarm/` | deer-flow worker pool | P0c |
| Monitor | `src/nexus_os/monitoring/` | TokenGuard + TALE budget estimator | P1d |
| Skillsmith | `src/nexus_os/skillsmith/` | Auto-register skill discovery | P1e |
| StressLab | `src/nexus_os/stresslab/` | ISC-Bench TVD runner | P2 |
| Config | `src/nexus_os/config/` | Constitution governance | P0 |

## Boot Sequence

```bash
cd /home/workspace
python3 Skills/nexus-os/NEXUS-TEST.py
```

Expected: `10/10 passed`

## Token Protocol

```python
import sys
sys.path.insert(0, "Skills/nexus-os/src")
from nexus_os.monitoring import start_tracking, track_api_call, get_usage

start_tracking(total_tokens=100000)
track_api_call("agent", 1500, 800, "minimax-m2.7")
print(get_usage()["remaining"])  # 976700
```

## GMR Model Stack

| Model | Tier | Domains |
|-------|------|---------|
| minimax-m2.7 | 95 | reason, code, research, fast, sec |
| claude-code | 90 | reason, sec, code |
| openrouter | 75 | code, reason |
| groq | 70 | code, fast |
| cerebras | 65 | fast, research |

Sub-agents spawned via `/zo/ask` API — each is an independent session.

## P1 Priority Matrix

| | Feature | Source | Status |
|---|---|---|---|
| P1a | Speculative routing proxy (62% cost reduction) | ArXiv 2604.09213 | ✅ Done |
| P1b | 8-channel vault (TEMPORAL_CAUSAL, ONTOLOGICAL) | HuggingFace Apr 2026 | ✅ Done |
| P1c | Metis v2 tool discipline gates | Metis v2 paper | ✅ Done |
| P1d | TALE token budget estimator | ArXiv 2603.08425 | ✅ Done |
| P1e | Skillsmith auto-register | AutoSkillForge | ✅ Done |

## Git Log

```
9b2d0e8  P1b/P1c/P1e  9/9 PASS
475a2f7  P0b/P0c/P0d  8/8 PASS
ab0cc15  inspiration
63438e5  boot
```

Rollback: `git reset --hard <commit>`
