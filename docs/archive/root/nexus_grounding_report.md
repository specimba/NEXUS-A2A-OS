---
id: NODE-MIG-NEXUS_GROUNDING_REPORT
authority_scope: experimental
origin_sha256: 578094b990ecb7ad48ced4fb34bb1dae4249284fd922b0eb28925836a90ec9df
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-CA0683
---
# NEXUS OS — Grounded Knowledge Report

<!-- CANARY: 3dc1f3aa6e3ae84baea56deb05824e73 -->
> **Date:** 2026-05-19  
> **Branch:** `codex/specimba/1805mainSpeci`  
> **Test Baseline:** 664 passed (`PYTHONPATH=.;src;bin python -m pytest tests/ -v --tb=short`)  
> **Python:** ≥3.10 | **Node:** Next.js 16 + Bun  

---

## Core Thesis

NEXUS OS is a **governed, local-first agent operating system**. Every action is proposal-bound, test-gated, and provenance-tracked. It coordinates 5 layers:

| Layer | Role |
|-------|------|
| **DoppelGround** | Evidence preparation |
| **Nexus OS** | Governance, routing, audit, approval (Python/FastAPI — **canonical brain**) |
| **TWAVE** | Low-VRAM model execution (HOLD — wrapper/API only) |
| **GeniusTurtle** | Operator UX layer (UI/API only — no weights/secrets) |
| **Model Arena** | Report-only model performance evaluation |

---

## Architecture — 6 Pillars

```
            ┌─────────────┐
            │   BRIDGE     │  Port 7352 (FastAPI)
            │ JSON-RPC/MCP │
            └──────┬───────┘
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ GOVERNOR │ │  ENGINE  │ │  VAULT   │
│KAIJU/CDR │ │ Hermes   │ │ 5-track  │
│Trust v2.2│ │ GMR/DAG  │ │ memory   │
└──────────┘ └──────────┘ └──────────┘
    │              │              │
    └──────────────┼──────────────┘
                   ▼
         ┌─────────────────┐
         │      SWARM      │  Foreman/Workers/Auction
         └─────────────────┘
                   ▼
         ┌─────────────────┐
         │   MONITORING    │  TokenGuard/Counters/Telemetry
         └─────────────────┘
                   ▼
         ┌─────────────────┐
         │   TWAVE v2.0    │  ChimeraRouterV2 + Landau-Ginzburg
         └─────────────────┘
```

### Port Map

| Port | Service | Protocol |
|------|---------|----------|
| 3000 | Next.js Dashboard | HTTP |
| 7352 | Nexus Governance API | FastAPI |
| 7353 | TWAVE Wrapper | HTTP |
| 3003 | WebSocket Swarm Events | Socket.io |
| 11434 | Local Ollama | HTTP (internal) |

---

## Repository Layout

### Python Backend (`nexus_os/` — ~50 modules)

| Directory | Files | Purpose |
|-----------|-------|---------|
| `nexus_os/governor/` | `base.py`, `trust_engine_v2.py`, `trust_kernel.py`, `trust_scoring.py`, `kaiju_auth.py`, `compliance.py`, `proof_chain.py`, `autoharness.py`, `constitution.yaml` | KAIJU 4-var auth, TrustEngine v2.2 (HARDWALL), compliance, CDR state machine |
| `nexus_os/bridge/` | `server.py` (681 lines), `sdk.py`, `secrets.py`, `mcpaauth.py`, `vault.py`, `cloudflare_bypass.py` | A2A Bridge (JSON-RPC 2.0), HMAC-SHA256 auth, FastAPI app, provider secrets |
| `nexus_os/vault/` | `memory_tracks.py`, `memory_adapter.py`, `memory.py`, `cache.py`, `trust.py`, `trust_store.py`, `poisoning.py`, `manager.py`, `decay_worker.py` | 5-track memory (EVENT/TRUST/CAPABILITY/FAILURE_PATTERN/GOVERNANCE), encryption |
| `nexus_os/engine/` | `hermes.py` (450 lines), `router.py`, `executor.py`, `skill_adapter.py` (47KB!), `skill_smith.py`, `forge.py`, `heartbeat.py`, `tool_discipline.py`, `hermes_experience.py` | Hermes router, GMR integration, skill matching, cost optimization |
| `nexus_os/gmr/` | `rotator.py`, `circuit_breaker.py`, `domain_mapping.py`, `latency_monitor.py`, `savings.py`, `telemetry.py`, `scheduler.py`, `trust_adapter.py`, `context_packet.py` | Genius Model Rotator: circuit breakers, domain mapping, savings tracking |
| `nexus_os/swarm/` | `foreman.py`, `worker.py`, `auction.py`, `openclaw_spawner.py` | Worker orchestration, task auction, OpenClaw spawning |
| `nexus_os/monitoring/` | `token_guard.py` (599 lines), `counters.py`, `strategies.py`, `trust_scorer.py` | TokenGuard budgets, semantic cache, model routing, VAP audit |
| `nexus_os/twave/` | `chimera_router_v2.py`, `landau_ginzburg_tracker_v2.py` | TWAVE v2.0: tiered model routing, hallucination tracking (EDT/LEAD/EPR/LED/CK-PLUG) |
| `nexus_os/db/` | `manager.py` | Thread-safe DatabaseManager (SQLite/PostgreSQL) |
| `nexus_os/observability/` | *(not fully explored)* | Squeez log compression, tracing |
| `nexus_os/stresslab/` | *(not fully explored)* | ISC benchmark runner, templates |
| `nexus_os/relay/` | `model_relay.py` | Transparent model relay proxy |
| `nexus_os/security/` | *(empty — pycache only)* | Runtime security (code likely elsewhere) |

### Next.js Dashboard (`src/`)

| Path | Purpose |
|------|---------|
| `src/app/page.tsx` | Main dashboard page |
| `src/app/layout.tsx` | Root layout |
| `src/app/api/` | 19 API route files |
| `src/components/nexus/tabs/` | 11 tab panels (Overview, StressLab, GMR, Governor, Vault, Research, Swarm, Tokens, Providers, RateLimit, KPI) |
| `src/components/nexus/` | 26+ custom components |
| `src/store/` | Zustand global state |
| `src/hooks/` | Custom hooks (use-api-data, use-swarm-ws, etc.) |
| `src/lib/` | Prisma, rate limiter, cache, provider bridge |

**Stack:** Next.js 16, React 19, TailwindCSS 4, shadcn/ui (Radix), Prisma 6, Zustand, Recharts, Framer Motion, z-ai-web-dev-sdk

### CLI (`nexusctl/`)

| Command | Status |
|---------|--------|
| `nexusctl cycle-check` | ✅ Working — checks `.nexus_pi/state/` for halt/compact files |
| `nexusctl doctor version` | ✅ Working — git state, required files, docs drift |
| `nexusctl doctor memory` | ✅ Working — module presence checks |
| `nexusctl status` | ⚠️ Stub — "legacy entrypoint not restored" |
| `nexusctl handoff` | ⚠️ Stub — not restored |

### Test Suite (`tests/`)

22 test subdirectories mirroring the `nexus_os` pillars:
`governor/`, `vault/`, `bridge/`, `engine/`, `gmr/`, `swarm/`, `monitoring/`, `team/`, `integration/`, `security/`, `contracts/`, `cron/`, `unit/`, `opusman/`, `benchmarks/`, `cli/`, `api/`, `mocks/`, `observability/`, `pi/`, `relay/`

---

## Key Module Deep-Dives

### TrustEngine v2.2 (`nexus_os/governor/trust_engine_v2.py`)

The mathematical core of governance. Implements HARDWALL defenses:

- **Logistic Scaling:** `f(T) = 1/(1 + e^(-(T-50)/10)) × difficulty` — gains harder at high trust
- **Adaptive Decay:** `λ(t) = base_λ × (1 + disagreement_rate)` — decay accelerates with validator disagreement
- **Non-Compensatory CRITICAL:** DangerLevel.CRITICAL always applies `-20.0` delta, forces CDR CASCADE
- **6-Stage CDR State Machine:** Normal → Degraded Reasoning → Memory Corruption → Output Hallucination → Cascade → Collapse
- **Asymptotic Plateau:** Max score 99.5, never 100
- **Baseline:** 25.0, Collapse threshold: 15.0, Escalation threshold: 30.0
- **Vault Integration:** Persists to 5-track vault via `store_track`/`retrieve_track`

### NexusGovernor (`nexus_os/governor/base.py`)

Unified authorization gate with 4-layer pipeline:
1. **Token Budget Check** (pre-KAIJU) — 75% warning, 95% hard-stop
2. **KAIJU 4-Variable Authorization** — scope × clearance, impact × clearance, intent × action → ALLOW/DENY/HOLD
3. **CVA Trait Verification** — stub (returns OK), designed for agent trait alignment
4. **Compliance Engine** — OWASP, CSA, IMDA, IETF VAP post-checks

### BridgeServer (`nexus_os/bridge/server.py`)

JSON-RPC 2.0 A2A server with:
- HMAC-SHA256 authentication via SecretStore
- KAIJU authorization via NexusGovernor
- Endpoints: `/tasks/submit`, `/tasks/status`, `/vault/read`, `/vault/write`, `/` (JSON-RPC router), `/health`
- A2A v1.1 agent card support
- TokenGuard integration with per-request token tracking
- Full FastAPI integration via `create_app()`

### Hermes Router (`nexus_os/engine/hermes.py`)

Task routing engine with:
- **TaskClassifier:** Keyword-based domain/complexity classification (CODE/ANALYSIS/REASONING/etc.)
- **ExperienceScorer:** Bayesian-smoothed scoring from `model_performance` table
- **CostOptimizer:** Cost-aware model selection (trivial→cheapest, critical→local preference)
- **GMR Integration:** GeniusModelRotator for dual-pool budget-aware routing
- **Skill Fast-Path:** Direct model routing for skills with ≥3 executions

### TokenGuard (`nexus_os/monitoring/token_guard.py`)

Budget enforcement and audit:
- Per-category budgets: agent(50K), skill(10K), swarm(200K), session(500K)
- `check()`, `track()`, `check_and_reserve()` — non-blocking hot path
- VAP-compliant audit trail with SHA-256 signatures
- Semantic caching (warm path) and model routing
- Trend analysis (cold path for SkillSmith)

### 5-Track Memory (`nexus_os/vault/memory_tracks.py`)

| Track | Purpose |
|-------|---------|
| EVENT | Raw task outcomes (success/failure/partial) |
| TRUST | Bayesian reputation per lane (research/audit/compliance/implementation/orchestration/general) |
| CAPABILITY | Skill profiling with EMA confidence updates |
| FAILURE_PATTERN | Recurring weakness tracking with severity escalation |
| GOVERNANCE | Rule violation records |

---

## Known Stubs & Incomplete Work

| Component | File | Issue |
|-----------|------|-------|
| AsyncBridgeExecutor | `engine/executor.py:115` | Returns `success=False` — not wired to Bridge RPC |
| CVAVerifier | `governor/base.py:329` | Always returns `(True, "OK")` — no real trait scoring |
| Worker execute_task | `swarm/worker.py:180` | Fake simulated outputs |
| TaskClassifier | `engine/hermes.py:401` | Keyword-based heuristic only |
| ISC-Runner templates | `stresslab/isc_runner.py:79` | Only 1 template per domain |
| `nexusctl status` | `nexusctl/cli.py:229` | Not restored |
| `nexusctl handoff` | `nexusctl/cli.py:241` | Not restored |

---

## Critical Blockers

1. Docker secret hardening incomplete (inline secrets, Kafka credentials, Redis/Supabase localhost binding)
2. DoppelGround leak status unresolved → blocks external handoff
3. Dashboard uses mock/proxy layer instead of real Python governance API on 7352
4. ~15 bare `except: pass` blocks
5. 43 legacy repair scripts in `scripts/`
6. 3 of 11 dashboard tabs never QA'd

---

## Development Commands

```bash
# Python backend tests
$env:PYTHONPATH=".;src;bin"
python -m pytest tests/ -v --tb=short

# CLI
python -m nexusctl cycle-check
python -m nexusctl doctor version --report-only
python -m nexusctl doctor memory --report-only

# Dashboard
bun install
bun run dev  # Port 3000

# TWAVE demo
python -m nexus_os.twave.demo_e2e_v2 --prompt "Explain quantum entanglement" --policy auto
```

## Hygiene Rules

- **NEVER** `git add .` — explicit paths only
- **NEVER** commit `.env`, `foundry_datasets/`, `node_modules/`, `venv/`, `session-*.md`, `*.zip`
- Verify tests before staging
- Datasets stay in `foundry_datasets/` (gitignored, 1.5+ GB)
- Research goes in `research/session_logs/`
- Backups go in `.brv/`
