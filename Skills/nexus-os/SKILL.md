---
name: nexus-os
description: |
  NEXUS OS v3.0 — modular agent governance framework for Zo. Provides intent routing
  (Hermes/Engine), trust scoring (Governor/Kaiju), S-P-E-W memory (Vault), model rotation
  (GMR), worker pool (Swarm), and token budget tracking (Monitoring). Boot the OS,
  run the test suite, and iterate. Use when building agent systems, multi-model pipelines,
  or governance layers on Zo.
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

| Pillar | Module | Purpose |
|--------|--------|---------|
| Bridge | `src/nexus_os/bridge/` | HMAC auth, JSON-RPC |
| Engine | `src/nexus_os/engine/` | Intent routing |
| Governor | `src/nexus_os/governor/` | Auth, trust scoring |
| Vault | `src/nexus_os/vault/` | S-P-E-W memory |
| GMR | `src/nexus_os/gmr/` | Model rotation → /zo/ask spawn |
| Swarm | `src/nexus_os/swarm/` | Worker pool |
| Monitor | `src/nexus_os/monitoring/` | Token budget & audit |
| Config | `src/nexus_os/config/` | Constitution governance |

## Boot Sequence

```bash
cd /home/workspace
python3 Skills/nexus-os/NEXUS-TEST.py
```

Expected: `8/8 passed`

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
