# GLM5.1 Fusion Pack — API_ASSUMPTIONS.md

## Endpoints Currently Used

### Internal Dashboard APIs (Next.js API Routes)

| Endpoint | Method | Used By | Request Shape | Response Shape | Status |
|----------|--------|---------|---------------|----------------|--------|
| `/api/agents` | GET | SystemTerminal, AgentHealthMonitor | — | `Agent[]` | ✅ Working |
| `/api/models` | GET | GmrTab, QuickStats, Footer, Diagnostics | — | `{ models: ModelData[] }` | ✅ Working |
| `/api/models` | PATCH | GmrTab (toggle active) | `{ id, isActive }` | `{ success }` | ✅ Working |
| `/api/tokens` | GET | TokensTab, QuickStats, Diagnostics | — | `{ budget, usageLogs, agentUsage }` | ✅ Working |
| `/api/vault` | GET | VaultTab | — | `{ entries: VaultEntryAPI[] }` | ✅ Working |
| `/api/vault` | POST | VaultTab (verify chain) | `{ action: 'verify_chain' }` | `{ valid, entryCount, issues[] }` | ✅ Working |
| `/api/governor` | GET | GovernorTab | — | `GovernorAPIResponse` | ✅ Working |
| `/api/governor` | POST | GovernorTab (threshold adjust) | `{ action, lane, value }` | `{ success }` | ✅ Working |
| `/api/stresslab` | GET | StressLabTab | — | `StressLabData` | ✅ Working |
| `/api/stresslab` | POST | StressLabTab (run test) | `{ templateId, model, mode }` | `{ success, runId }` | ✅ Working |
| `/api/swarm` | GET | SwarmTab | — | `SwarmApiResponse` | ✅ Working |
| `/api/swarm` | POST | SwarmTab (assign/reassign) | `{ action, workerId, taskId }` | `{ success }` | ✅ Working |
| `/api/research` | GET | ResearchTab | — | `ResearchApiResponse` | ✅ Working |
| `/api/research` | POST | ResearchTab (add paper) | `{ title, priorityTier, ... }` | `{ success }` | ✅ Working |
| `/api/system` | GET | OverviewTab, GovernorTab, Diagnostics | — | `SystemAPIResponse` | ✅ Working |
| `/api/trust-engine` | GET | GovernorTab | — | `TrustEngineAPIResponse` | ✅ Working |
| `/api/ai-bridge` | GET/POST | GmrTab (routing sim) | `{ query, domain }` | `{ routedModel, pool, confidence }` | ✅ Working |
| `/api/rate-limit/status` | GET | RateLimitTab | — | Rate limit status data | ✅ Working |
| `/api/chat` | POST | AI Assistant (fallback) | `{ messages, systemPrompt? }` | `{ response }` | ✅ Working |
| `/api/claude` | POST | AI Assistant (primary) | `{ messages, model? }` | `{ response, model? }` | ⚠️ Proxy errors |
| `/api/seed` | POST | Database seeding | — | Seed confirmation | ✅ Working |
| `/api/settings` | GET/POST | System Configuration | — | Settings data | ✅ Working |
| `/api/proxy` | POST | API proxy | Various | Various | ✅ Working |

### External Services

| Service | Endpoint | Purpose | Auth | Status |
|---------|----------|---------|------|--------|
| z-ai-web-dev-sdk | Chat Completions API | AI Assistant responses | SDK-managed | ✅ Working |

---

## Polling Assumptions

| Component | Interval | Endpoint | Behavior |
|-----------|----------|----------|----------|
| GmrTab | 15s | `/api/models` | Full model list refresh |
| GovernorTab | 15s | `/api/governor` | Decision + agent refresh |
| GovernorTab | 30s | `/api/trust-engine` | Trust config refresh |
| GovernorTab | 60s | `/api/system` | Constitution config refresh |
| VaultTab | 15s | `/api/vault` | Entry list refresh |
| SwarmTab | 15s | `/api/swarm` | Worker + task refresh |
| ResearchTab | 30s | `/api/research` | Paper list refresh |
| TokensTab | 30s | `/api/tokens` | Budget + usage refresh |
| QuickStatsWidget | 60s | `/api/tokens` | Budget overview |
| AgentHealthMonitor | 15s | `/api/agents` | Agent status refresh |

**No WebSocket connections** — all data updates via polling. System Logs panel uses client-side `setInterval` for simulated log generation.

---

## WebSocket Assumptions

**None currently.** All real-time updates are simulated client-side:
- Live Activity Feed: `setInterval` rotation through static items
- Live Decision Feed: `setInterval` rotation through static items
- System Logs: `setInterval` generating random log entries

**Future need:** WebSocket for real worker status updates and live governance decisions from 7352.

---

## Auth Assumptions

**None currently.** Dashboard has no authentication layer. All API routes are open.

**Future need:** Auth layer that respects Nexus governance scopes (SELF, PROJECT, CROSS, SYSTEM/CRIT).

---

## Mapping to Canonical Nexus 7352 Backend

| Dashboard Endpoint | Nexus 7352 Equivalent | Match? | Adapter Needed? |
|--------------------|-----------------------|--------|-----------------|
| `/api/agents` | — | ❌ | 7352 has no agent list endpoint; need adapter from governance state |
| `/api/models` | — | ❌ | GMR model registry is dashboard-local; 7352 doesn't expose model routing |
| `/api/tokens` | — | ❌ | Token budget is dashboard-local; 7352 doesn't track API tokens |
| `/api/vault` | — | ❌ | Vault is dashboard-local; 7352 vault is different schema |
| `/api/governor` | `GET /governance/proposals` | ⚠️ Partial | Governor decisions ≠ governance proposals; need mapper |
| `/api/governor` POST | `POST /governance/approve/{id}` | ⚠️ Partial | Threshold adjust ≠ proposal approve; different semantics |
| `/api/swarm` | `GET /tasks/status/{id}` | ⚠️ Partial | Swarm workers ≠ individual task status; need aggregation |
| `/api/stresslab` | — | ❌ | StressLab is dashboard-local testing framework |
| `/api/system` | `GET /health`, `GET /dashboard/stats` | ⚠️ Partial | System health maps partially; stats shape differs |
| `/api/trust-engine` | — | ❌ | Trust engine config is dashboard-local |
| `/api/chat` | — | ❌ | AI assistant is dashboard-local; not a governance concept |
| `/api/rate-limit/status` | — | ❌ | Rate limiting is infrastructure concern, not governance |
| `/api/research` | — | ❌ | Research pipeline is dashboard-local |

### Critical Gap Analysis

**Only 2 of 14 dashboard endpoints have any Nexus 7352 equivalent.** The dashboard was built as a self-contained governance visualization, not as a consumer of the 7352 governance plane.

To align with canonical Nexus:
1. **Governor tab** needs to consume `GET /governance/proposals` instead of local decisions
2. **Governor approval flow** needs to use `POST /governance/approve/{id}` 
3. **Swarm tab** needs to consume `POST /tasks/heartbeat` and `POST /tasks/result`
4. **System health** needs to consume `GET /health` and `GET /dashboard/stats`
5. **Skills proposal** should use `POST /skills/propose` and `GET /skills/status/{id}`

The remaining tabs (Vault, GMR, StressLab, Tokens, Research, Rate Limits) are **dashboard-local concepts** that have no 7352 equivalent. These would remain self-contained but should be clearly labeled as operational tooling, not governance truth.
