# NEXUS OS v3.0

<p align="center">
  <strong>Enterprise-Grade Multi-Agent Governance Platform</strong><br>
  <sub>Built for production A2A systems with cutting-edge trust, budget, and compliance</sub>
</p>

---

## Overview

NEXUS OS v3.0 is a production-hardened multi-agent operating system designed for enterprise-level A2A (Agent-to-Agent) deployments. It provides comprehensive governance, trust scoring, token budget management, and audit trails for autonomous agent swarms.

### Key Features

- **Trust Scoring v2.1** — Lane-scoped Bayesian reputation with non-compensatory harm detection
- **TokenGuard** — Token budget gates with 429 responses and hard-stop enforcement
- **GMR Engine v3.0** — Intelligent model selection with dual-pool (FAST/PREMIUM) routing
- **VAP Proof Chain** — SHA-256 immutable audit trail with L1+L2 cryptographic verification
- **5-Track Memory** — EVENT, TRUST, CAPABILITY, FAILURE_PATTERN, GOVERNANCE tracks
- **Execution Paths** — HOT/WARM/COLD path routing with SLA enforcement
- **Hermes Router** — Intent classification and model selection pipeline

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CORE LAYER                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │  GMR    │  │  VAP     │  │ Trust   │  │ Token  │ │
│  │ Engine  │  │ Chain    │  │Scorer   │  │ Guard  │ │
│  └────┬───┘  └────┬────┘  └────┬───┘  └───┬────┘ │
└───────┼───────────┼───────────┼───────────┼─────────────┘
        │           │           │           │
        ▼           ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────┐
│                    BRIDGE LAYER                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │          Hermes Router + Model Selection          │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    SWARM LAYER                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  Foreman   │  │  OpenClaw   │  │ Coordinator │   │
│  │ (Code)    │  │  Spawner    │  │             │   │
│  └───────────┘  └────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Trust Scoring** | Bayesian + Non-compensatory | Lane-scoped reputation |
| **Token Management** | Budget gates + 429 | Token economy |
| **Model Selection** | GMR v3.0 dual-pool | Cost-optimized routing |
| **Audit Trail** | SHA-256 chain | Compliance logging |
| **Memory** | 5-track schema | Experience tracking |
| **Paths** | SLA-based routing | Execution tiers |
| **Governance** | KAIJU 4-variable | Authorization |

---

## Installation

```bash
# Clone the repository
git clone https://github.com/specimba/nexusalpha.git
cd nexus-os

# Install dependencies (Python 3.10+)
pip install -e .

# Run diagnostics
python scripts/diagnostic.py
```

---

## Quick Start

```python
from nexus_os.monitoring.token_guard import TokenGuard
from nexus_os.engine.hermes import HermesRouter
from nexus_os.monitoring.trust_scorer import TrustScorer

# Initialize components
token_guard = TokenGuard(budgets={'agent-1': 100000})
router = HermesRouter()
scorer = TrustScorer()

# Check budget
if token_guard.check('agent-1', 5000):
    # Route request through GMR
    result = router.route('agent-1', 'Write authentication function', {})
    print(f"Selected model: {result.selected_model}")
```

---

## Components

### GMR Engine (Genius Model Rotator)

Budget-aware model selection:

| Budget | Pool | Example Models |
|--------|------|--------------|
| 0-100k | FAST | osman-coder (tier-40) |
| 100k-200k | MID | Devstral (tier-70) |
| 200k+ | PREMIUM | Devstral 2 123B (tier-86) |

### Trust Scorer v2.1

Lane-scoped parameters:

| Lane | Rcrit | qmin |
|------|------|------|
| research | 0.7 | 0.3 |
| audit | 0.3 | 0.7 |
| compliance | 0.2 | 0.7 |
| implementation | 0.4 | 0.4 |
| orchestration | 0.4 | 0.5 |
| general | 0.6 | 0.1 |

### TokenGuard

Budget enforcement:

- **Budget OK** — Process request, track usage
- **Budget Exceeded** — Return 429 with `X-Token-Remaining` header
- **Hard Stop** — Block at Governor level

---

## Running Tests

```bash
# Full diagnostic
python scripts/diagnostic.py

# Specific checks
python scripts/diagnostic.py gmr
python scripts/diagnostic.py routing
python scripts/diagnostic.py integration

# Run test suite
python -m pytest tests/ -v
```

---

## Roadmap

### Phase 1 (Complete)
- [x] Trust v2.1 integration
- [x] TokenGuard budget gates
- [x] GMR dual-pool selection
- [x] VAP proof chain
- [x] 5-Track memory

### Phase 2 (In Progress)
- [ ] Hermes → GMR full pipeline
- [ ] Bridge model selection
- [ ] Semantic caching
- [ ] FAISS memory adapter

### Phase 3 (Planned)
- [ ] Metis tool discipline
- [ ] AReaL training pipeline
- [ ] Domain-partitioned Foreman
- [ ] Priority queues

---

## Documentation

- [00_QUICKSTART.md](./00_QUICKSTART.md) — Getting started
- [02_ARCHITECTURE.md](./02_ARCHITECTURE.md) — Architecture details
- [04_GOVERNANCE.md](./04_GOVERNANCE.md) — Governance rules

---

## License

MIT License — See LICENSE file for details.

---

<p align="center">
  <sub>Built for enterprise A2A systems</sub>
</p>
