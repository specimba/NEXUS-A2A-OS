# Fusion Recommendations — GLM5 NEXUS OS Command Center

## Pieces to Take Into Demo NOW

### Must-Have (Public-Safe, Operationally Real)
1. **Research Tab** — Complete pipeline with Alphaxiv integration, working CRUD, daily practice timer
2. **Swarm Tab** — Full worker lifecycle with audit trail, capacity enforcement, trust adjustment
3. **Governor Tab** — Trust scoring with CDR stages, threshold adjustment, danger patterns
4. **Vault Tab** — 5-track memory browser, chain verification, entry detail dialogs
5. **StressLab Tab** — Real LLM test execution with validation, batch runs, model comparison
6. **GMR Router Tab** — Real health checks, model toggles with pool guard, pool visualizations
7. **Port Map + Thesis Card** — Clear architecture representation (new, replaces terminal)

### Should-Have (Public-Safe, Mostly Real)
8. **Overview Tab** — Pillar health grid, token budget, agent activity, recent decisions
9. **Token Budget Tab** — Session tracking, usage logs, budget gauge, per-agent/per-model data
10. **AI Assistant** — Working chat with z-ai-web-dev-sdk and NEXUS system prompt
11. **Command Palette** — Ctrl+K with navigation and actions

### Nice-to-Have (Requires Caveats)
12. **Rate Limit Control** — Real data pipeline but needs automatic request logging
13. **System Logs** — Client-side only, should be labeled as simulation
14. **Notification Center** — Seed data only, not connected to real events

## Pieces to Stay Experimental

1. **Live Activity Feed** — Currently simulated; needs WebSocket connection to real event stream
2. **Health Timeline** — Seeded pseudo-random; needs real time-series storage
3. **Rotation Analytics / Failover Log** — Hardcoded; needs event tracking in DB
4. **Cost Optimization Suggestions** — Hardcoded; needs analysis engine
5. **Practice Session Steps** — Timed simulation; needs real pipeline integration

## Pieces for Permanent Dashboard Fusion

### From GLM5 (This Pack)
- **Research pipeline architecture** (Alphaxiv → DB → CRUD → UI)
- **Swarm worker lifecycle model** (spawn/terminate/restart/reassign with audit trail)
- **Governor threshold interaction** (sliders + affected-agent warnings)
- **StressLab real execution model** (z-ai-web-dev-sdk → validation → DB)
- **GMR health check model** (real pings → DB health/latency updates)
- **Data Source Badge system** (honest mock/real labeling)
- **Port Map thesis representation** (architecture clarity for demo)
- **Constitution enforcement patterns** (max agents, pool guards, threshold lines)

### Should Be Fused Later
- **Real-time event stream** (WebSocket → all feeds, logs, activity)
- **Time-series storage** (health timeline, token usage, model latency over time)
- **Automatic request logging** (middleware for all API calls → RateLimitLog)
- **Governance proposal bridge** (our decisions → Nexus 7352 proposals)
- **Task heartbeat bridge** (our Swarm → Nexus task status/result)
- **Rotation event tracking** (DB model for GMR rotation + failover events)

## Known Risks If Our Design Is Adopted

1. **SQLite scaling** — Current DB is SQLite; production would need PostgreSQL migration
2. **No authentication** — Dashboard has no user auth; needs session management for multi-operator use
3. **In-memory rate limiting** — Lost on server restart; needs Redis or DB-backed persistence
4. **WebSocket fragility** — Swarm WS falls back to polling gracefully, but needs reconnection logic
5. **No HTTPS** — Local dev only; production needs TLS termination
6. **Seed data dependency** — Fresh DB starts empty; seed route must be called first
7. **No API versioning** — Routes are unversioned; breaking changes need migration strategy
8. **z-ai-web-dev-sdk dependency** — LLM features depend on SDK availability; need fallback for offline

## Backend Gap List Against Nexus 7352

| Our Route | Nexus 7352 Route | Gap | Priority |
|-----------|------------------|-----|----------|
| — | `GET /health` | Missing health check endpoint | HIGH |
| `GET /api/system` | `GET /dashboard/stats` | Different shape, need adapter | MEDIUM |
| — | `POST /tasks/heartbeat` | Missing task heartbeat bridge | HIGH |
| — | `POST /tasks/result` | Missing task result submission | HIGH |
| — | `GET /tasks/status/{id}` | Missing task status query | MEDIUM |
| `GET /api/governor` | `GET /governance/proposals` | Different decision model | MEDIUM |
| `POST /api/governor` appeal | `POST /governance/approve/{id}` | Different approval flow | MEDIUM |
| — | `POST /skills/propose` | Missing skill proposal endpoint | LOW |
| — | `GET /skills/status/{id}` | Missing skill status query | LOW |
