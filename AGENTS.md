# NEXUS OS — Workspace Root Memory

## Identity
- **Handle**: specimba
- **Role**: MIND curator — building modular agent governance systems
- **Zo Computer**: canonical home of NEXUS OS development

## Git Status
- Branch: `master` (clean, committed)
- Remote: `origin` → https://github.com/specimba/NEXUS-A2A-OS
- HEAD: `45fa452` — "complete system: 9/9 — relay+observability+gspp endpoints"
- 8 commits total on this branch
- **NOT** connected to local Windows machine git repos

## Active Systems

### NEXUS OS v3.0 (canonical)
`Skills/nexus-os/` — Modular agent governance framework — **9/9 PASS**

| Pillar | Path | Purpose | Status |
|--------|------|---------|--------|
| Bridge | `src/nexus_os/bridge/` | HMAC auth, JSON-RPC, MCP-Auth | ✅ |
| Engine | `src/nexus_os/engine/` | Hermes/Domain routing + Metis ToolGates | ✅ |
| Governor | `src/nexus_os/governor/` | KAIJU, TrustScorer v2.1, RigorLLM, ShieldGemma, AEGIS | ✅ |
| Vault | `src/nexus_os/vault/` | 8-channel S-P-E-W + Attention-Sink KV compression | ✅ |
| GMR | `src/nexus_os/gmr/` | SpeculativeRouter, HALF_OPEN circuit breaker, TALEEstimator | ✅ |
| Swarm | `src/nexus_os/swarm/` | deer-flow Foreman + P2b auction allocation | ✅ |
| Monitor | `src/nexus_os/monitoring/` | TokenGuard, TokenTracker | ✅ |
| Skillsmith | `src/nexus_os/skillsmith/` | Auto-register skill discovery | ✅ |
| StressLab | `src/nexus_os/stresslab/` | ISC-Bench TVD runner | ✅ |
| Relay | `src/nexus_os/relay/` | OpenAI-compatible API + GSPP endpoints + /dashboard/stats | ✅ |
| Observability | `src/nexus_os/observability/` | VAP L1+L2 proof chain + Langfuse | ✅ |
| Config | `src/nexus_os/config/` | Constitution | ✅ |

**Test**: `python3 Skills/nexus-os/NEXUS-TEST.py` → `9/9 PASS`

### GMR Model Stack
```
minimax-m2.7   tier=95  [reason, code, research, fast, sec]
claude-code    tier=90  [reason, sec, code]
openrouter     tier=75  [code, reason]
groq           tier=70  [code, fast]
cerebras       tier=65  [fast, research]
```
Sub-agents spawned via `/zo/ask` API.

### Git Commit History
```
45fa452  complete system: 9/9 — relay+observability+gspp endpoints
51662c7 P2 complete: MCP-Auth, A2A, deer-flow, KV, TALE, auction
9b2d0e8  P1b/P1c/P1e: 8-ch vault, Metis gates, skillsmith
475a2f7 P0b/P0c/P0d: half-open circuit, OR-Bench lanes, deer-flow
8b22ee1 P1 complete: speculative router, TALE, stresslab
63438e5 NEXUS OS v3.0 boot
```

## System Specs
- Python 3.12.1, Node 22.22.1, Bun 1.3.11
- RAM: 4GB (2.8GB available), CPU: 3 cores
- DuckDB 1.4.2, Playwright 1.52.0, pytest 9.0.3

## Governance Limits
- Max agents/hour: 5 | Max concurrent: 2
- Max API calls/session: 20 | Max file writes: 30

## Active Persona
**No-Nonsense Determinist** (id: 6d4a1915-58a6-409c-955f-27a02feb0e6b)

## Inspiration Sources
See `INSPIRATION.md` for full research synthesis.
