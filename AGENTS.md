# NEXUS OS — Workspace Root Memory

## Identity
- **Handle**: specimba
- **Role**: MIND curator — building modular agent governance systems
- **Zo Computer**: orchestrator for multi-agent workflows

## Active Systems

### NEXUS OS v3.0
`Skills/nexus-os/` — Modular agent governance framework (checkpoint 4/4 operational).

| Pillar | Path | Purpose |
|--------|------|---------|
| Bridge | `src/nexus_os/bridge/` | HMAC auth, JSON-RPC |
| Engine | `src/nexus_os/engine/` | Intent routing (Hermes/Domain) |
| Governor | `src/nexus_os/governor/` | Auth, trust scoring (Kaiju/TrustScorer) |
| Vault | `src/nexus_os/vault/` | S-P-E-W memory store |
| GMR | `src/nexus_os/gmr/` | Model routing → /zo/ask sub-agent spawn |
| Swarm | `src/nexus_os/swarm/` | Worker pool (Foreman/Worker) |
| Monitor | `src/nexus_os/monitoring/` | Token budget + audit |
| Config | `src/nexus_os/config/` | Constitution governance |

**Test**: `python3 Skills/nexus-os/NEXUS-TEST.py` → target: 8/8 PASS

### GMR Model Stack
```
minimax-m2.7   tier=95  [reason, code, research, fast, sec]
claude-code    tier=90  [reason, sec, code]
openrouter     tier=75  [code, reason]
groq           tier=70  [code, fast]
cerebras       tier=65  [fast, research]
```
Routed via `/zo/ask` API — each spawn is an independent sub-agent session.

## Installed Skills (curated)
```
self-improvement  — weekly agent reflection audit
handoff           — pause/resume across conversations
journal           — daily experiential logging
simplify          — code refinement
context7          — version-specific library docs
mcporter-setup    — MCP server integration
share-skill       — skill contribution prep
zopenclaw         — OpenClaw + Tailscale + mcporter bridge
nexus-os         — NEXUS OS v3.0 framework
```

## Git Protocol
- Branch: `master`
- Status: clean — all NEXUS OS files tracked
- Commit convention: `[nexus|<skill|<fix|<doc>] <description>`
- Major steps always get a named commit for rollback

## System Specs
- Python 3.12.1, Node 22.22.1, Bun 1.3.11
- RAM: 4GB (2.8GB available), CPU: 3 cores
- DuckDB 1.4.2, Playwright 1.52.0, uv 0.6.14
- Zo model: MiniMax 2.7 (orchestrator)

## Inspiration Sources (for future build)
See `INSPIRATION.md` for full research list.
Key candidates:
- **agent-orchestration**: Agency Swarm, AgentEnsemble, Maestro, MOCO, Agentflow, mesh
- **memory-layer**: MemMachine, MemoryLayer, memweave, 0GMem, memvid, Engram-Mem
- **skill-crafting**: SkillCraft, SkillX, EvoSkill, SkillWeaver, ACE, self-evolving-agent

## Governance Limits
- Max agents/hour: 5
- Max API calls/session: 20
- Max concurrent: 2
- Max file writes: 30
- Default token budget: 100,000

## Active Persona
**No-Nonsense Determinist** (id: 6d4a1915-58a6-409c-955f-27a02feb0e6b)
- Calm, professional, semi-formal
- Deterministic + honest (state assumptions, cite constraints)
- Proposes concrete algorithms and code-level guidance
- Minimal verbosity, targeted only
