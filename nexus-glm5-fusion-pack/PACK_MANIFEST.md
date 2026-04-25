# GLM5 Fusion Pack — NEXUS OS Command Center

**Team:** GLM5 Dashboard Lane  
**Build:** 2026-04-18 · v3.1 · canonical-617 branch  
**Status:** Mixed — public-safe demo shell + internal prototype quality  
**Dashboard Thesis:** A trust-governed multi-agent OS command center where every request is authenticated, routed by intent, vetted by trust score, and audit-logged immutably — with elastic model supply, parallel worker execution, real-time budget enforcement, and constitutional guardrails.

---

## What Changed Since Last Pack

### Critical Fixes (this session)
- **Research paper ID bug FIXED**: Priority/status changes now use DB cuid instead of externalId — "Paper not found" errors eliminated
- **Spawn worker 403 error FIXED**: Clear capacity indicator + client-side guard + max worker limit display in spawn dialog
- **Governor duplicate React keys FIXED**: `key={a.name}` → `key={a.id}`, hover state tracking also fixed to use `a.id`
- **Overview terminal section REMOVED**: Replaced decorative terminal with Port Map + NEXUS Thesis card showing 8-pillar architecture

### Architecture Changes (prior sessions)
- All 14 API routes now connected to Prisma/SQLite with full CRUD
- Research papers saved to DB via Alphaxiv integration — priority/status changes persist
- StressLab tests execute via z-ai-web-dev-sdk with real LLM completions
- GMR health checks ping models via z-ai-web-dev-sdk with latency/health tracking
- Token usage logging and session budget enforcement operational
- Vault chain verification implemented
- Trust Engine v2.2 with CDR stages computed from real agent data
- Governor thresholds and danger patterns persisted in SystemConfig

### What Is Public-Safe Now
- Overview with 8-pillar health grid, token budget, agent activity, port map thesis
- Governor with trust scores, decision log, threshold adjustment, danger patterns
- Vault with 5-track memory browser, entry detail dialog, chain verification
- Research with P0/P1/P2 priority queues, Alphaxiv integration, add-to-queue
- Swarm with worker CRUD (spawn/terminate/restart/reassign/trust adjustment)
- StressLab with real LLM test execution, ISC-Bench templates
- GMR with model registry, health checks, pool status, rotation analytics
- Token budget with session tracking, usage logs, agent/model consumption
- Rate limit status dashboard with provider health, queue details, cache stats
- AI Assistant chat panel (z-ai-web-dev-sdk LLM)
- Command Palette (Ctrl+K) with navigation + actions
- System Logs panel (Ctrl+L) with real-time log streaming

### What Still Depends on Mock/Fallback Data
- Swarm task queue (4 hardcoded entries when WebSocket not connected)
- Swarm recent completions (5 hardcoded entries as fallback)
- Swarm worker performance data (deterministic fallback arrays)
- Overview health timeline (seeded pseudo-random based on pillar health)
- Overview token history (simulated when no usage logs exist)
- Overview agent activity (sine-wave distribution from real totals)
- Overview collapse rate trend (hardcoded values when <2 test runs)
- Notifications in store (10 hardcoded initial notifications)
- Error details in worker detail dialog (hardcoded error message/badges)
- Research practice session steps (timed simulation)
