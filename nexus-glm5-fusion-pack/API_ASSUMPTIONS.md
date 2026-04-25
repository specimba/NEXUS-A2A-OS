# API Assumptions — GLM5 NEXUS OS Command Center

## Next.js API Routes (Self-Hosted)

All routes are internal Next.js API routes on port 3000. No external backend required for core functionality.

### Core Data Routes

| Endpoint | Method | Purpose | Request Shape | Response Shape | DB Model |
|----------|--------|---------|---------------|----------------|----------|
| `/api/agents` | GET | List all agents | — | `Agent[]` | Agent |
| `/api/swarm` | GET | List agents as swarm workers | — | `{ workers, stats }` | Agent |
| `/api/swarm` | POST | Worker actions | `{ action, workerId?, name?, type?, domain?, delta?, reason? }` | `{ worker, message }` | Agent, VaultEntry |
| `/api/governor` | GET | Decisions + trust stats | — | `{ decisions, trustStats, thresholds, patterns }` | GovernorDecision, Agent, SystemConfig |
| `/api/governor` | POST | Governor actions | `{ action, decisionId?, agentId?, reason?, thresholds?, pattern? }` | `{ decision }` or `{ config }` | GovernorDecision, SystemConfig |
| `/api/vault` | GET | Vault entries | — | `{ entries }` | VaultEntry |
| `/api/vault` | POST | Verify chain | `{ action: 'verify_chain' }` | `{ valid, entryCount, issues }` | VaultEntry |
| `/api/research` | GET | Papers by priority | — | `{ papers, p0, p1, p2, total }` | Paper |
| `/api/research` | POST | Create paper | `{ title, externalId?, priorityTier?, ... }` | `{ paper, alreadyExisted }` | Paper |
| `/api/research` | PUT | Update paper | `{ paperId, updates }` | `{ paper }` | Paper |
| `/api/models` | GET | Model registry | — | `{ models }` | ModelEntry |
| `/api/models` | POST | Model actions | `{ action, modelId }` | `{ model }` or `{ results }` | ModelEntry |
| `/api/stresslab` | GET | Templates + runs | — | `{ templates, runs }` | TestTemplate, TestRun |
| `/api/stresslab` | POST | Run test / batch | `{ action, templateId, modelName, mode }` | `{ testRun }` or `{ results }` | TestRun, TokenUsageLog |
| `/api/tokens` | GET | Budget + usage | — | `{ budget, usageLogs, agentUsage }` | SessionBudget, TokenUsageLog, Agent |
| `/api/tokens` | POST | Log usage | `{ action: 'log_usage', model, promptTokens, completionTokens, ... }` | `{ usageLog }` | TokenUsageLog, SessionBudget, Agent |
| `/api/rate-limit/status` | GET | Rate limit dashboard | `?provider=name` | `{ summary, providers, keys, queues, ... }` | RateLimitLog, ApiKey |
| `/api/trust-engine` | GET | Trust matrix + CDR | `?agent=name` | `{ trust_matrix, cdr_stages, health_summary, ... }` | Agent, GovernorDecision |
| `/api/system` | GET | Full system overview | — | `{ agents, models, overview, ... }` | All models |
| `/api/settings` | GET | System config | — | `{ settings, providers }` | SystemConfig |
| `/api/settings` | PUT | Update config | `{ key, value }` | `{ success }` | SystemConfig |
| `/api/settings` | DELETE | Delete config | `?key=name` | `{ success }` | SystemConfig |
| `/api/seed` | POST | Reset + seed DB | — | `{ success, seeded }` | All models |

### External API Integration Routes

| Endpoint | Method | Purpose | External Service | Auth |
|----------|--------|---------|-----------------|------|
| `/api/alphaxiv` | GET | Search Alphaxiv papers | Tavily Search API → Jina AI (fallback) | TAVILY_API_KEY, JINA_API_KEY |
| `/api/alphaxiv` | POST | Queue Alphaxiv papers | Tavily Search API → Jina AI (fallback) | TAVILY_API_KEY, JINA_API_KEY |
| `/api/chat` | POST | AI Assistant chat | z-ai-web-dev-sdk (LLM) | Auto (SDK) |
| `/api/ai-bridge` | POST | AI provider bridge | z-ai-web-dev-sdk | Auto (SDK) |
| `/api/claude` | POST | Claude proxy | claude-proxy mini-service | JWT |

### Polling Assumptions
- `useApiData` hook with configurable auto-refresh interval (15s for Swarm, 30s for Research)
- System overview polled every 30s
- Rate limit status polled on tab view

### WebSocket Assumptions
- Swarm worker status: `io("/?XTransformPort=3003")` — falls back to API polling
- WebSocket mini-service at `/home/z/my-project/mini-services/swarm-ws/` (port 3003)
- When WS not connected, swarm tab uses API data + hardcoded task queue/completions fallback

### Auth Assumptions
- No user authentication on the dashboard itself (single-user/operator tool)
- API keys managed via `api-key-manager.ts` (in-memory key rotation)
- Kilocode JWT token for Claude proxy (stored in .env)
- z-ai-web-dev-sdk auto-authentication (no key needed)

### Which Assumptions Match Nexus 7352
| Our Route | Nexus 7352 Equivalent | Match Status |
|-----------|----------------------|--------------|
| `/api/agents` GET | `GET /dashboard/stats` (partial) | PARTIAL — we have richer agent data |
| `/api/governor` | `POST /governance/approve/{id}` | PARTIAL — we have more granular decision types |
| `/api/swarm` spawn | `POST /tasks/heartbeat` | DIFFERENT — our spawn is agent creation, not task heartbeat |
| `/api/stresslab` run | — | NEW — no Nexus equivalent, unique to our dashboard |
| `/api/research` | — | NEW — no Nexus equivalent, unique to our dashboard |
| `/api/alphaxiv` | — | NEW — no Nexus equivalent, unique to our dashboard |
| `/api/vault` verify | — | EXTENDED — Nexus has vault concept, we added verification |
| `/api/models` health | — | NEW — GMR is our unique concept |
| `/api/tokens` budget | — | NEW — budget monitoring is our unique concept |
| `/api/rate-limit/status` | — | NEW — rate limit dashboard is our unique concept |

### Which Need Adapter/Proxy Work
1. **Task heartbeat** → Need to bridge our Swarm actions to Nexus `POST /tasks/heartbeat`
2. **Task results** → Need to bridge our test runs to Nexus `POST /tasks/result`
3. **Task status** → Need to bridge our Swarm tab to Nexus `GET /tasks/status/{id}`
4. **Governance proposals** → Need to bridge our Governor decisions to Nexus `GET/POST /governance/proposals`
5. **Skills** → Need to bridge our model/skill registry to Nexus `POST /skills/propose`
