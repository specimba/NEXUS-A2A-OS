# Brain API Gap Audit (v5 Step 7)

Date: 2026-06-18

## Current API Endpoints

### GET
| Endpoint | Status | Notes |
|---|---|---|
| `/` | ✅ | Root health |
| `/health` | ✅ | Health check |
| `/api/agents` | ✅ | List agents |
| `/api/agents/{agent_id}` | ✅ | Get agent |
| `/api/tasks` | ✅ | List tasks |
| `/api/state` | ✅ | Get state |
| `/api/trust` | ✅ | All trust scores |
| `/api/trust/agent/{agent_id}` | ✅ | Agent trust |
| `/api/providers` | ✅ | Uses ProviderHealthMonitor |
| `/api/providers/{provider_id}` | ✅ | Single provider from ProviderHealthMonitor |
| `/api/relay/health` | ✅ | ModelRelay health proxy |
| `/api/relay/health/ready` | ✅ | ModelRelay readiness |
| `/api/relay/metrics` | ✅ | ModelRelay metrics |
| `/api/relay/models` | ✅ | ModelRelay model list |
| `/api/models` | ✅ | Registry model list |
| `/api/models/{model_id}` | ✅ | Single registry model |
| `/api/models/select/{task_type}` | ✅ | Model selection by task |
| `/api/integrations` | ✅ | Merged state + Mimo + Relay |
| `/api/wiki/*` (6) | ✅ | Full wiki CRUD |
| `/api/messaging/*` (3) | ✅ | Messaging status/history |
| `/api/dashboard/sync` | ✅ | Dashboard sync |
| `/api/stats` | ✅ | Stats |

### POST
| Endpoint | Status | Notes |
|---|---|---|
| `/api/relay/chat` | ✅ | Chat via ModelRelay |
| `/api/intervene` | ✅ | Intervention |
| `/api/halt` | ✅ | System halt |
| All others | ✅ | Agents, tasks, messages, brainstorm, wiki, messaging |

### WebSocket
| Endpoint | Status | Notes |
|---|---|---|
| `/ws` | ✅ | Topic-based pub/sub |

## Gaps (from v5 Plan)

### 1. `/api/models/health` — MISSING
No dedicated model registry health endpoint.
**Fix**: Add `GET /api/models/health` that checks registry is loadable, returns model count and lane availability.

### 2. WebSocket `model_change` topic — NOT CONFIRMED WIRED
The WS manager handles arbitrary topics but no code publishes to a `model_change` topic.
**Fix**: Wire registry model add/remove events → publish to `model_change` WS topic.

### 3. ProviderHealth full integration — PARTIAL
`/api/providers` and `/api/providers/{id}` use get_health_monitor() correctly, but:
- No `/api/providers/stress` endpoint to correlate StressLab results with ProviderHealth
- ProviderHealthMonitor doesn't receive model-registry health data
**Fix**: Add `/api/providers/refresh` to trigger async health recheck; wire model registry status into ProviderHealthMonitor.refresh_all().

### 4. No `eval` endpoint — MISSING
No API endpoint to trigger or query VibeThinker/StressLab evaluations.
**Fix**: Add `POST /api/eval/vibethinker` and `GET /api/eval/results` endpoints.

### 5. No stress-lab writeback — MISSING
StressLab CLI runs locally but doesn't POST results to Brain API.
**Fix**: Add `POST /api/stress/report` to ingest StressReport for audit.

## Priority Order
1. `/api/models/health` — 1 hour (adds registry health check)
2. WS `model_change` topic — 2 hours (adds event publishing to registry)
3. `POST /api/eval/vibethinker` — 2 hours (exposes eval as API)
4. ProviderHealth refresh endpoint — 2 hours
5. Stress report writeback — 1 hour

Total estimated: ~8 hours
