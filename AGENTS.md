# NEXUS OS — Workspace Root Memory

## Identity
- **Handle**: specimba
- **Role**: MIND curator — building modular agent governance systems
- **Zo Computer**: orchestrator for multi-agent workflows

## Git Log
```
475a2f7 [nexus] P0b/P0c/P0d: half-open circuit breaker, OR-Bench lane calibration, deer-flow swarm harness
ab0cc15 [inspiration] full INSPIRATION.md rebuild — 25 sourced files
63438e5 [nexus] NEXUS OS v3.0 boot — 8 pillars, GMR model stack, heartbeat protocol, inspiration research
```

## Active Systems

### NEXUS OS v3.0 (checkpoint 4/4, 8/8 tests)
`Skills/nexus-os/src/nexus_os/` — 8 modules

| Pillar | Path | Purpose |
|--------|------|---------|
| Bridge | `bridge/` | HMAC auth, JSON-RPC |
| Engine | `engine/` | Intent routing (Hermes/Domain) |
| Governor | `governor/` | Auth, trust scoring, **OR-Bench lane calibration (P0b)** |
| Vault | `vault/` | S-P-E-W memory store |
| GMR | `gmr/` | Model routing, **half-open circuit breaker (P0d)** |
| Swarm | `swarm/` | Worker pool, **deer-flow lead-agent pattern (P0c)** |
| Monitor | `monitoring/` | Token budget + audit |
| Config | `config/` | Constitution governance |

**Run tests**: `python3 Skills/nexus-os/NEXUS-TEST.py`

### P0b: OR-Bench Lane Calibration
- research: (0.3,5) → **(0.35, 7)** — raised to reduce false refusals
- review:   (0.5,3) → **(0.55, 4)**
- audit:    (0.7,2) → **(0.72, 3)**
- impl:     (0.6,4) → **(0.62, 5)**
- Added `compliance` lane: **(0.80, 2)**

### P0c: deer-flow Swarm Harness
- `Foreman.submit()` → returns 8-char task_id (not void)
- `Foreman.assign()` → domain-matched round-robin to idle worker
- `Worker.memory_snapshot()` → isolated per-worker audit log
- `Foreman.status()` → full pool snapshot (queue_depth, per-worker state)
- `Foreman.collect()` → drain completed results

### P0d: Half-Open Circuit Breaker
- Per-model state machine: CLOSED → OPEN → HALF_OPEN → CLOSED (success) or OPEN×2 (fail)
- Exponential backoff: 60s → 120s → 240s ... cap 600s
- `GMR.circuit_report()` → full status all 5 models
- `Model.can_use()` → query without side-effects
- `GMR.spawn()` → now includes circuit status in return dict

### GMR Model Stack (Zo)
```
minimax-m2.7   tier=95  [reason, code, research, fast, sec]  ← orchestrator
openrouter     tier=75  [code, reason]                       ← /zo/ask sub-agent
groq           tier=70  [code, fast]                         ← /zo/ask sub-agent
cerebras       tier=65  [fast, research]                    ← /zo/ask sub-agent
claude-code    tier=90  [reason, sec, code]                 ← /zo/ask sub-agent
```
Routed via `/zo/ask` API — each spawn is an independent sub-agent session.

## Installed Skills (curated, deduplicated)
```
self-improvement  — weekly agent reflection audit
handoff           — pause/resume across conversations
journal           — daily experiential logging
simplify          — code refinement
context7          — version-specific library docs
mcporter-setup    — MCP server integration
share-skill       — skill contribution prep
zopenclaw         — OpenClaw + Tailscale + mcporter bridge
nexus-os          — NEXUS OS v3.0 framework (this workspace)
```

## Governance Limits (Constitution)
- Max agents/hour: 5
- Max API calls/session: 20
- Max concurrent: 2
- Max file writes: 30
- Default token budget: 100,000

## Inspiration Sources
See `INSPIRATION.md` — full synthesis from 25 sourced files, 297 GitHub stars, team reports.
Key P0 repos (ISC-Bench already in progress elsewhere):
- **deer-flow** → P0c done (swarm harness)
- **litellm** → GMR relay pattern reference
- **AutoSkillForge** → skillsmith auto_register (TODO)
- **MCP-Auth spec** → Bridge upgrade (TODO)

## System Specs
- Python 3.12.1, Node 22.22.1, Bun 1.3.11
- RAM: 4GB (2.8GB available), CPU: 3 cores
- DuckDB 1.4.2, Playwright 1.52.0, uv 0.6.14
- Zo model: MiniMax 2.7 (orchestrator)

## Active Persona
**No-Nonsense Determinist** (id: 6d4a1915-58a6-409c-955f-27a02feb0e6b)
- Calm, professional, semi-formal
- Deterministic + honest (state assumptions, cite constraints)
- Proposes concrete algorithms and code-level guidance
- Minimal verbosity, targeted only
