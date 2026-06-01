# NEXUS OS — Governed Agent Operating System

**Local-first, auditable, modular multi-agent governance for AI systems.**

**Status:** Phase 0 security hardened. WSL forensic session verified locally. All systems verified stable.

NEXUS OS turns local models, research evidence, and external teams into a governed, audited, low-VRAM execution system where every action is proposal-bound, test-gated, and provenance-tracked. It provides intent routing, trust scoring with lane-calibrated thresholds, 8-channel memory, speculative model routing, deer-flow worker pools, and an immutable VAP audit chain — all orchestrated through a GSPP proposal protocol.

---

## Architecture

```
                         ┌──────────────────────┐
                         │      BRIDGE           │
                         │  JSON-RPC, MCP, SDK   │
                         └──────────┬───────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│    GOVERNOR      │    │  ENGINE / GMR    │    │      VAULT       │
│ KAIJU gates      │    │ Hermes router    │    │ 5-tracks memory  │
│ TrustEngine v2.2 │    │ model rotation   │    │ encryption,trust │
│ VAP proof chain  │    │ circuit breaker  │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
         │                      │                        │
         └──────────────────────┼────────────────────────┘
                                ▼
         ┌─────────────────────────────────────────────┐
         │                  SWARM                       │
         │   Foreman, workers, auction, OpenClaw       │
         └─────────────────────────────────────────────┘
                                ▼
         ┌─────────────────────────────────────────────┐
         │              MONITORING                      │
         │   TokenGuard, counters, telemetry           │
         └─────────────────────────────────────────────┘
                                ▼
         ┌─────────────────────────────────────────────┐
         │         TWAVE v2.0 (NEW 2026-05-15)         │
         │  ChimeraRouterV2 + Landau-Ginzburg tracker  │
         │  EDT / LEAD / EPR / LED / CK-PLUG           │
         └─────────────────────────────────────────────┘
```

### Port Map

| Port | Service | Protocol |
|------|---------|----------|
| 3000 | Next.js Command Command Dashboard | HTTP |
| 7352 | Nexus Governance API (canonical) | FastAPI |
| 7353 | TWAVE Wrapper | HTTP |
| 3003 | WebSocket Swarm Events | Socket.io |
| 11434 | Local Ollama (internal) | HTTP |

---

## Repository Structure

```
nexus_os/                 # Python governance backend (CANONICAL — ~50 modules)
  bridge/                 #   JSON-RPC server, SDK, secrets, MCP auth
  governor/               #   KAIJU gates, TrustEngine v2.2, compliance, VAP proof chain
  vault/                  #   5-track memory (EVENT/TRUST/CAP/FAIL/GOV), encryption, trust
  engine/                 #   Hermes router, executor, skillsmith, tool discipline
  gmr/                    #   Model rotation, circuit breaker, telemetry, savings
  swarm/                  #   Foreman, workers, auction, OpenClaw spawner
  monitoring/             #   TokenGuard, counters, strategies
  observability/          #   Tracing, Squeez log compression
  twave/                  #   TWAVE v2.0: ChimeraRouterV2, Landau-Ginzburg tracker (NEW)
  stresslab/              #   ISC benchmark runner, templates
  db/                     #   Thread-safe database manager (SQLite/PostgreSQL)
  relay/                  #   Transparent model relay proxy
  cron/                   #   Scheduled agent cycles
  team/                   #   Agent coordinator

twave/                    # (symlinked / legacy path from HF dataset — kept for reference)

src/                      # Next.js Frontend Dashboard
  app/api/                #   19 API route files
  components/nexus/tabs/  #   11 tab panels (overview, stresslab, gmr, governor, vault,
                          #   research, swarm, tokens, providers, ratelimit, kpi)
  components/nexus/       #   26 custom components
  store/                  #   Zustand global state
  hooks/                  #   Custom React hooks (use-api-data, use-swarm-ws, etc.)
  lib/                    #   Prisma, rate limiter, cache, provider bridge

prisma/                   #   Database schema — 12 models

tests/                    #   Python test suite — 617+ passing in the grounding integration baseline
  governor/               #   Trust scoring, compliance, kaiju auth, proof chain
  vault/                  #   Memory, trust, cache, manager, adapter, tracks
  bridge/                 #   Server, SDK, MCP auth, token integration
  engine/                 #   Router, skillsmith, tool discipline, Hermes GMR
  gmr/                    #   Core GMR (selection, budgets, circuit breakers)
  swarm/                  #   Auction, spawner budget gate
  monitoring/             #   Token guard, strategies, GMR
  team/                   #   Coordinator
  integration/            #   Compliance, bridge, heartbeat, Hermes, Squeez
  security/               #   Encryption hard-fail, poisoning v2, sanitizer
  contracts/              #   Protocol contracts
  cron/                   #   Agent cycle
  unit/                   #   Executor v2, secrets

benchmarks/               #   Dataset generators (stres5, stres6, tool taxonomy)
foundry_datasets/         #   Generated eval/stress datasets (~1.5 GB, gitignored)
  stress_lab/             #   v1→v6 stress datasets (ISC, frontier, TAMAS, tool taxonomy)
  eggroll/                #   Model SFT training data from frontier models
  opusman_eval/           #   OPUSman evaluation datasets
  state/                  #   Dataset quality tracking, gap analysis

scripts/                  #   Utility and repair scripts (~43 files — many legacy stubs)
bin/                      #   CLI tools (nexusctl, nexus-pi)
docs/
  handbook/               #   Operational guides (AFK workflow, Kiloclaw fastboot)
  reviews/                #   Asset inventory, audits

.brv/                     #   Backup/archive (gitignored)
  archive_static/         #   Archived: session logs, QA screenshots, old zips,
  azure_archive/          #   stale .pyc dumps, quarantined Azure creds
  git_history_backup/     #   Git bundle backup

research/                 #   Research reports (session logs, R&D topics)
  session_logs/           #   STRES5, STRES6, AFK session reports
```

### Module & Purpose Mapping

| Module | File | Purpose |
|--------|------|---------|
| Bridge | `src/nexus_os/bridge/__init__.py` | HMAC auth, JSON-RPC, MCP-Auth v2026-04-01 |
| Engine | `src/nexus_os/engine/__init__.py` | Hermes/Domain intent routing + ToolDisciplineGate |
| Governor | `src/nexus_os/governor/__init__.py` | Kaiju, TrustScorer, RigorLLMGate, ShieldGemmaGate, AEGISGate, ComplianceGate |
| Vault | `src/nexus_os/vault/__init__.py` | 8-Channel S-P-E-W, CompressedContextPacket |
| GMR | `src/nexus_os/gmr/__init__.py` | SpeculativeRouter, TALEEstimator, CircuitState |
| Swarm | `src/nexus_os/swarm/__init__.py` | Foreman, Worker, Task, Bid (auction allocation) |
| Monitor | `src/nexus_os/monitoring/__init__.py` | TokenGuard, TokenTracker, SessionBudget |
| Skillsmith | `src/nexus_os/skillsmith/__init__.py` | SkillRecord, auto-register loop |
| StressLab | `src/nexus_os/stresslab/__init__.py` | ISCTemplate, ISCRunner |
| Relay | `src/nexus_os/relay/__init__.py` | ModelRelay, GSPPProposal, /dashboard/stats |
| Config | `src/nexus_os/config/__init__.py` | Constitution governance |
| Observability | `src/nexus_os/observability/__init__.py` | VAPChain L1+L2, Langfuse integration |

---

## Current Test State

| Suite | Count | Status |
|-------|-------|--------|
| Python pytest | **617+ passing** with `pytest` |
| TWAVE v2.0 | 25 tests | All passing |
| Security tests | 23 tests | All passing |
| Dashboard lint | 0 errors | Clean |

**Known issues:**
- `test_heartbeat.py` — depends on external infrastructure, times out if ports not available
- `scripts/` (43 files) — contains many legacy stubs and one-off repair scripts

---

## What's Working

- **TrustEngine v2.2** — HARDWALL defense: logistic scaling, adaptive decay, non-compensatory CRITICAL, 6-stage CDR (Nominal→Caution→Restricted→High Risk→Critical→Collapsed)
- **Vault** — Canonical 5-track memory schema (`store_track` / `retrieve_track`), encryption hard-fail by default
- **GMR** — Model rotation with circuit breakers, domain mapping, telemetry, savings tracking
- **Bridge** — JSON-RPC governance server, SDK with circuit breaker, retry policy, token integration
- **Dashboard** — Next.js 16 frontend, 11 tabs, all wired to real API data, zero lint errors
- **Stress Lab** — v1–v6 datasets (ISC, frontier, TAMAS, tool taxonomy), 240 tools, 1.6 GB total
- **TWAVE v2.0** — ChimeraRouterV2 (tiered routing + ERNIE), Landau-Ginzburg hallucination tracker (EDT/LEAD/EPR/LED/CK-PLUG), 25 tests
- **Phase 0 Security** — TerminalSanitizer (ANSI injection defense), VerifiableOutput (SHA-256 integrity), AgentPTY isolation
- **12 API providers** — NVIDIA, SambaNova, SiliconFlow, OpenCode, OpenRouter, Groq, etc.

---

## What's Incomplete / Needs Work

### Stubs & Placeholders (critical)

| Component | File | Issue |
|-----------|------|-------|
| AsyncBridgeExecutor | `nexus_os/engine/executor.py:115` | Production executor still returns `success=False` — not wired to real Bridge RPC |
| CVAVerifier | `nexus_os/governor/base.py:329` | Non-enforcing stub is now labeled in authorization reasons; real trait scoring is not implemented |
| ModelRelay | `nexus_os/relay/model_relay.py` | Partially wired to ChimeraRouterV2 + Ollama with hard-fail when no local model is healthy; still needs end-to-end server validation and TWAVE tracker telemetry |
| Worker execute_task | `nexus_os/swarm/worker.py:180` | Produces fake simulated outputs, no real task execution |
| TaskClassifier | `nexus_os/engine/hermes.py:401` | "Minimal stub for test collection" — keyword-based heuristic fallback |
| ISC-Runner templates | `nexus_os/stresslab/isc_runner.py:79` | Only downloads 1 template per domain — placeholder |

### API Endpoint Gaps (per FUSION_RECOMMENDATIONS.md)
- `GET /health` — Implemented in `nexus_os/bridge/server.py` and `nexus_os/relay/model_relay.py`; still needs deployment-level probe validation
- `POST /tasks/heartbeat` — HIGH priority
- `POST /tasks/result` — HIGH priority
- `GET /tasks/status/{id}` — MEDIUM priority
- `POST /skills/propose` — LOW priority
- `GET /skills/status/{id}` — LOW priority

### Dashboard Gaps
- 3 of 11 tabs never screenshotted during QA (Providers, RateLimit, KPI)
- Prisma `HealthSnapshot` and `TokenSnapshot` models referenced but don't exist in client
- Dashboard uses mock/proxy layer instead of real Python governance API on 7352

### Code Quality
- ~15 bare `except: pass` blocks across the codebase
- 43 repair scripts in `scripts/` — evidence of ongoing breakage-repair cycles
- 13 empty `__init__.py` files (fine but untidy)
- 4 empty test methods (exist as `pass` only)

---

## Dataset Pipeline (v1 → v6)

| Version | Rows | Description |
|---------|------|-------------|
| v1 ISC-Bench | 1,164 | 84 ISC templates, 9 domains |
| v2 ISC Expander | 10,000 | Combinatorial expansion, 10 phases |
| v3 Multi-source | 484 | AgentHazard + SOSBench + AgentGovBench + ClawsBench |
| v4 Regenerator | 536,530 | 13 governance × 13 templates × 12 domains |
| v5 Frontier | 181,000 | 7 frontier types, 11 research sources |
| v6 TAMAS | 6,840 | 7 attack types, 3 topologies, 5 domains |
| v6.1 Tool Taxonomy | 7,200 | 240 tools, 12 categories (NEW, closes TAMAS gap) |

All generators in `benchmarks/`: `regenerate_datasets.py`, `regenerate_frontier_v5.py`, `stres5_final.py`, `stres6_tamas_generator.py`, `stres6_tool_taxonomy.py`

---

## Getting Started

```bash
# Python backend
pip install -e .
pytest

# Dashboard
bun install
bun run dev

# TWAVE v2.0 demo
python -m nexus_os.twave.demo_e2e_v2 --prompt "Explain quantum entanglement" --policy auto

# Stress lab dataset generation
python benchmarks/stres6_tool_taxonomy.py --gen

# CLI
python -m nexusctl cycle-check
python -m nexusctl doctor version --report-only
python -m nexusctl doctor memory --report-only
```

---

## Quick Start Code Snippets

```python
# Intent routing
from nexus_os.engine import Hermes, Domain
h = Hermes()
domain = h.classify("write a Python API")  # Domain.CODE

# Trust-scored governance
from nexus_os.governor import Governor, _LANES
gov = Governor()
gov.check("read file")          # → allowed
gov.check("sudo rm -rf /")     # → denied

# 8-channel memory
from nexus_os.vault import Vault, Channel
v = Vault()
v.store("agent1", Channel.TEMPORAL_CAUSAL, "decision", "routing_v2", {"path": "gmr"}, 0.9)
causal = v.causal_query("agent1", "routing_v2")

# Model routing with circuit breaker
from nexus_os.gmr import GMR, CircuitState
gmr = GMR()
model = gmr.select("analyze this security log")
report = gmr.circuit_report()

# KV-compressed context handoff
from nexus_os.vault import CompressedContextPacket
pkt = CompressedContextPacket.compress("long conversation...")
assert pkt.verify_roundtrip("long conversation...")

# ISC-Bench TVD runner
from nexus_os.stresslab import ISCRunner
runner = ISCRunner()
runner.run_single_template(template)

# Token budget tracking
from nexus_os.monitoring import start_tracking, track_api_call, get_usage
start_tracking(total_tokens=100000)
track_api_call("agent", 1500, 800, "minimax-m2.7")
print(get_usage()["remaining"])  # 976700
```

---

## Key Canons

1. **Python/FastAPI is canonical** for governance — dashboard proxies, does not decide.
2. **No `git add .`** — stage explicit reviewed paths only.
3. **No auto-commit** — every change is proposal-bound and test-gated.
4. **Azure/Foundry: DEAD** (2026-05-15) — all cloud model pipelines deprecated.
5. **Datasets are gitignored** — `foundry_datasets/` is 1.5+ GB, never commit.
6. **55 stale branches archived** as `archive/*` tags (2026-05-15 cleanup).

---

## GSPP — Governed Skill Proposal Protocol

Every skill change goes through a formal proposal pipeline:

```bash
# 1. Propose
curl -X POST http://localhost:7352/gov/propose \
  -H "Content-Type: application/json" \
  -d '{"skill_name":"auto-router","trigger_keywords":["route","dispatch"],"agent":"codex"}'

# Response: {proposal_id, status: "pending", vap_l1_hash}

# 2. Governor evaluates → approved/denied/hold
curl http://localhost:7352/gov/proposals

# 3. VAP L2 cryptographic proof generated on merge
curl http://localhost:7352/gov/proposals/{id}/proof
```

---

## Research Foundation

Built on ISC-Bench (ArXiv 2603.23509), OR-Bench (ArXiv 2405.20947), Speculative Routing (ArXiv 2604.09213), TALE (ArXiv 2603.08425), RigorLLM (ArXiv 2403.13031), ShieldGemma (ArXiv 2407.21772), deer-flow (bytedance/deer-flow), SuperLocalMemory v2 (HuggingFace Apr 2026).

See `INSPIRATION.md` for full research synthesis.

---

## Documentation Index

| File | Purpose |
|------|---------|
| `01_PROJECT_STATE.md` | Canonical project state |
| `AGENTS.md` | Agent operating protocol v2.0 (safety-gated) |
| `knowledge.md` | Compact knowledge base |
| `NEXUS_OS_V4_MASTER_PLAN.md` | 12-week architecture roadmap (1,182 lines) |
| `NEXUS_ZO_CLAW_INTEGRATION_PLAN.md` | Zo/Local/Claw A2A integration |
| `HEARTBEAT.md` | Cloud orchestrator heartbeat protocol |
| `SOUL.md` | Cloud orchestrator identity |
| `docs/handbook/05_NEXUS_AFK_WORKFLOW_STYLE.md` | Autonomous AFK operation rules |
| `docs/handbook/08_C_KILOCLAW_FASTBOOT.md` | Kiloclaw experimental lab setup |
| `docs/reviews/NEXUS_ASSET_INVENTORY_...md` | Complete asset inventory |
| `worklog.md` | Development task log |

---

## Repo Hygiene Rules

- **NEVER commit** `.env`, `foundry_datasets/`, `node_modules/`, `venv/`, `session-*.md`, `*.zip`, `*.tmp`
- **NEVER `git add .`** — always explicit paths
- **Verify tests** before staging: `pytest tests/ -q --ignore=tests/integration/test_heartbeat.py`
- **Dataset work** stays in `foundry_datasets/` (gitignored) — use `benchmarks/` generators
- **Research** goes in `research/session_logs/` (gitignored)
- **Backups** go in `.brv/` (gitignored)

---

## License

Apache 2.0 — see `LICENSE`

For commercial use derivatives: include "Built with Nexus OS" attribution.

---

**Repository:** https://github.com/specimba/NEXUS-A2A-OS  
**Owner:** specimba
