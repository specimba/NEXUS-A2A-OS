# NEXUS OS v3.0 — COMPREHENSIVE TECHNICAL GUIDE

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Integration Patterns](#integration-patterns)
4. [API Reference](#api-reference)
5. [Troubleshooting](#troubleshooting)
6. [Development Guide](#development-guide)
7. [Deployment](#deployment)

---

## 1. System Overview

### What is NEXUS OS?

NEXUS OS v3.0 is an enterprise-grade multi-agent governance platform designed for production A2A (Agent-to-Agent) systems. It provides:

- **Trust Management** — Lane-scoped Bayesian reputation scoring
- **Token Economy** — Budget gates with enforcement
- **Model Selection** — Cost-optimized GMR routing
- **Compliance** — SHA-256 audit trails
- **Memory** — 5-track experience tracking
- **Execution** — HOT/WARM/COLD path routing

### Core Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Zero-Trust** | Every action requires trust validation |
| **Budget-First** | Token economy before execution |
| **Audit-Everything** | VAP proof chain for all decisions |
| **Lane-Scoped** | Trust per-domain isolation |
| **Non-Compensatory** | Harm above threshold = HELD |

---

## 2. Component Architecture

### 2.1 Trust Scorer v2.1

**File:** `src/nexus_os/monitoring/trust_scorer.py`

Lane-scoped Bayesian trust with non-compensatory harm detection.

```python
from nexus_os.monitoring.trust_scorer import TrustScorer, LANE_PARAMS

# Initialize
scorer = TrustScorer()

# Get trust score
score = scorer.get_score_hotpath(
    agent_id="agent-1",
    Q=0.8,       # Quality score (0-1)
    n=10,         # Number of tasks
    U=0.7,        # Utility score (0-1)
    R=0.1,        # Risk score (0-1)
    lane="research" # Lane for isolation
)

# Lane parameters
print(LANE_PARAMS["research"].Rcrit)  # 0.7
print(LANE_PARAMS["audit"].qmin)        # 0.7
```

**Lane Parameters:**

| Lane | Rcrit | qmin | Description |
|------|------|------|-------------|
| research | 0.7 | 0.3 | Research/analysis |
| audit | 0.3 | 0.7 | Auditing tasks |
| compliance | 0.2 | 0.7 | Compliance verification |
| implementation | 0.4 | 0.4 | Code implementation |
| orchestration | 0.4 | 0.5 | Agent coordination |
| general | 0.6 | 0.1 | General tasks |

### 2.2 TokenGuard

**File:** `src/nexus_os/monitoring/token_guard.py`

Token budget management with enforcement.

```python
from nexus_os.monitoring.token_guard import TokenGuard

# Initialize with budgets
tg = TokenGuard(
    budgets={
        "agent-1": 100000,
        "agent-2": 50000,
    },
    warning_threshold=80.0,  # Warn at 80%
    hard_stop_threshold=95.0     # Hard stop at 95%
)

# Check budget
can_run = tg.check("agent-1", 5000)

# Get remaining
remaining = tg.remaining("agent-1")

# Track usage
tg.track("agent-1", 3000)
```

**Response Headers:**

| Header | Description |
|--------|-------------|
| `X-Token-Used` | Tokens consumed |
| `X-Token-Remaining` | Remaining budget |
| `X-Token-Warning` | Warning if approaching limit |

### 2.3 GMR Engine

**File:** `src/nexus_os/gmr/__init__.py`, `src/nexus_os/gmr/rotator.py`

Genius Model Rotator with budget-aware selection.

```python
from nexus_os.gmr.rotator import GeniusModelRotator
from nexus_os.gmr.telemetry import TelemetryIngest

# Initialize
tel = TelemetryIngest()
gmr = GeniusModelRotator(tel)

# Select model
selection = gmr.select(
    task_type="code",           # Domain
    budget_remaining=100000,    # Token budget
    required_tier=40           # Minimum tier (optional)
)

print(selection.primary)       # Selected model
print(selection.fallbacks)     # Fallback chain
print(selection.tier_used)    # Tier selected
print(selection.estimated_cost) # Cost estimate
```

**Budget Tiers:**

| Budget | Pool | Model | Tier | Cost/1M |
|--------|------|-------|------|---------|
| 0-100k | FAST | osman-coder | 40 | $0 |
| 100k-200k | MID | Codestral | 70 | $2 |
| 200k+ | PREMIUM | Devstral 2 123B | 86 | $4 |

### 2.4 Hermes Router

**File:** `src/nexus_os/engine/hermes.py`

Intent classification and model routing.

```python
from nexus_os.engine.hermes import HermesRouter

# Initialize
router = HermesRouter()

# Route request
result = router.route(
    agent_id="agent-1",
    prompt="Write a Python function",
    context={}  # Additional context
)

print(result.selected_model)
print(result.fallback_models)
```

### 2.5 VAP Proof Chain

**File:** `src/nexus_os/governor/proof_chain.py`

Immutable audit trail with SHA-256 verification.

```python
from nexus_os.governor.proof_chain import ProofChain

# Initialize
vap = ProofChain()

# Record action
entry = vap.record(
    agent_id="agent-1",
    action="request",
    details={"method": "tasks/submit"},
    level="INFO"
)

# Verify chain
is_valid = vap.verify_chain()

# Get summary
summary = vap.get_chain_summary()
print(summary["chain_valid"])
```

### 2.6 5-Track Memory

**File:** `src/nexus_os/vault/memory_tracks.py`

Five-track experience memory schema.

```python
from nexus_os.vault.memory_tracks import get_tracker, MemoryTrack

# Get tracker
tracker = get_tracker()

# Append to tracks
tracker.append_event("agent-1", "Task completed", "success", 150.0, 500)
tracker.append_trust("agent-1", "research", 0.75, 5)
tracker.append_capability("agent-1", ["python", "api"], 0.9)
tracker.append_failure("agent-1", "timeout", "audit")
tracker.append_governance("agent-1", "TOKEN-BUDGET-001", "warning")

# Query
events = tracker.get_events("agent-1")
trust_history = tracker.get_trust_history("agent-1", "research")
capability = tracker.get_capability("agent-1")
```

### 2.7 Execution Paths

**File:** `src/nexus_os/execution_paths.py`

HOT/WARM/COLD path routing.

```python
from nexus_os.execution_paths import get_router, hot_path, warm_path, cold_path

# Get router
router = get_router()

# Route operation
path = router.route("get status")
print(path)  # ExecutionPath.HOT

# Use decorators
@hot_path
def fast_operation():
    return "fast"

@warm_path
def slow_operation():
    return "warm"

@cold_path
def batch_operation():
    return "cold"
```

---

## 3. Integration Patterns

### 3.1 Full Request Pipeline

```python
from nexus_os.monitoring.token_guard import TokenGuard
from nexus_os.engine.hermes import HermesRouter
from nexus_os.monitoring.trust_scorer import TrustScorer

# Initialize
token_guard = TokenGuard(budgets={"agent": 100000})
router = HermesRouter()
scorer = TrustScorer()

def handle_request(agent_id, prompt):
    # 1. Check budget
    if not token_guard.check(agent_id, 5000):
        return {"error": "budget_exceeded", "code": 429}
    
    # 2. Check trust
    score = scorer.get_score_hotpath(agent_id, Q=0.5, n=1, U=0.5, R=0.1)
    if score is None:
        return {"error": "trust_held", "code": 403}
    
    # 3. Route through GMR
    result = router.route(agent_id, prompt, {})
    
    # 4. Track usage
    token_guard.track(agent_id, 1000)
    
    return {"model": result.selected_model}
```

### 3.2 Hermes + GMR Pipeline

```python
from nexus_os.engine.hermes import HermesRouter, IntentClassifier

# Classify intent
classifier = IntentClassifier()
intent = classifier.classify("Write authentication function")
print(intent)  # "code"

# Route through GMR
router = HermesRouter()
result = router.route("agent", "Write authentication function", {})

print(f"Domain: {intent}")
print(f"Selected: {result.selected_model}")
print(f"Fallbacks: {result.fallback_models}")
```

---

## 4. API Reference

### TrustScorer

| Method | Args | Returns |
|--------|------|---------|
| `get_score_hotpath` | agent_id, Q, n, U, R, lane | float or None |
| `compute_score` | ScoringInput | float or None |

### TokenGuard

| Method | Args | Returns |
|--------|------|---------|
| `check` | agent_id, tokens | bool |
| `remaining` | agent_id | int |
| `track` | agent_id, tokens | None |
| `get_status` | agent_id | dict |

### GeniusModelRotator

| Method | Args | Returns |
|--------|------|---------|
| `select` | task_type, budget, required_tier | GMRSelection |
| `update_metrics` | model_id, latency, success | None |

### HermesRouter

| Method | Args | Returns |
|--------|------|---------|
| `route` | agent_id, prompt, context | RoutingDecision |
| `classify` | prompt | str |

---

## 5. Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|------|----------|
| Import errors | PYTHONPATH | Set `PYTHONPATH=src` |
| Missing domains | Incomplete DOMAIN_MAPPING | Add missing domains |
| Budget not working | TokenGuard not initialized | Initialize with budgets dict |
| Trust returns None | Non-compensatory harm | Check R vs Rcrit |
| GMR returns low tier | Budget too low | Increase budget |

### Diagnostic Commands

```bash
# Full diagnostic
python scripts/diagnostic.py

# GMR only
python scripts/diagnostic.py gmr

# Routing only  
python scripts/diagnostic.py routing

# Check cloud_pack
python -m nexus.install --check

# Quick start
python -m nexus.quickstart
```

---

## 6. Development Guide

### Adding New Components

1. Create component in `src/nexus_os/<module>/`
2. Add to `__init__.py`
3. Create tests in `tests/<module>/`
4. Update this guide

### Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific module
python -m pytest tests/gmr/ -v

# Run C5 gate
python scripts/c5_integration_gate.py
```

---

## 7. Deployment

### Production Checklist

- [ ] Set PYTHONPATH to src
- [ ] Configure budgets in TokenGuard
- [ ] Set up VAP persistence (optional)
- [ ] Configure logging
- [ ] Run diagnostics

### Docker (optional)

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml ./

ENV PYTHONPATH=/app/src

RUN pip install -e .

CMD ["python", "scripts/diagnostic.py"]
```

---

## Appendix: File Structure

```
NEXUS/
├── src/nexus_os/
│   ├── monitoring/     # TokenGuard, TrustScorer
│   ├── engine/        # Hermes Router
│   ├── bridge/       # A2A Bridge
│   ├── governor/     # Compliance, VAP
│   ├── gmr/          # Model Rotator
│   ├── vault/        # Memory, Tracks
│   └── execution_paths.py
├── tests/            # Test suite
├── scripts/          # Build scripts
├── cloud_pack/       # Distribution
└── legacy/         # Archived
```

---

*Generated: 2026-04-17*
*NEXUS OS v3.0 Comprehensive Technical Guide*