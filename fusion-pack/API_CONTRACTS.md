# NEXUS OS v3.1 — API Contract Specification
> Auto-generated from codebase audit | 2025-01-27

---

## API Routes Reference

### 1. GET /api/system
**Status**: ✅ Working but NOT consumed by Overview Tab

Response:
```json
{
  "pillars": {
    "Bridge": { "health": 100, "status": "online", "uptime": "24h 31m" },
    "Engine": { "health": 98, "status": "online", "uptime": "24h 31m" },
    "Governor": { "health": 95, "status": "online", "uptime": "24h 31m" },
    "Vault": { "health": 100, "status": "online", "uptime": "24h 31m" },
    "GMR": { "health": 92, "status": "online", "uptime": "24h 31m" },
    "Swarm": { "health": 88, "status": "online", "uptime": "24h 31m" },
    "Monitor": { "health": 0, "status": "offline", "uptime": "—" },
    "Config": { "health": 100, "status": "online", "uptime": "24h 31m" }
  },
  "agentActivity": [...],
  "tokenHistory": [...],
  "collapseRate": 0.12
}
```

### 2. GET/POST /api/swarm
**Status**: ✅ Fully wired

GET Response:
```json
{
  "agents": [{ "id", "name", "type", "trustScore", "status", "capabilities", "totalTokens" }],
  "taskQueue": [...],
  "recentCompleted": [...],
  "stats": { "total", "active", "idle", "error" }
}
```

POST Actions:
- `spawn_worker` → Creates Agent + VaultEntry audit log
- `terminate_worker` → Updates Agent status + audit
- `restart_worker` → Resets Agent + audit
- `reassign_task` → Updates Agent currentTask + audit
- `update_trust` → Clamps trustScore [0,1] + audit

### 3. GET/POST /api/governor
**Status**: ✅ Fully wired

GET Response:
```json
{
  "decisions": [{ "id", "decision", "scope", "action", "reasoning", "agent", "timestamp" }],
  "agents": [{ "id", "name", "trustScore", "decisions", "activityLevel" }],
  "thresholds": { "research": 0.65, "review": 0.70, "audit": 0.80, "impl": 0.75 },
  "dangerPatterns": [...]
}
```

POST Actions:
- `appeal` → Creates GovernorDecision (decision='HOLD')
- `update_threshold` → Upserts SystemConfig
- `add_pattern` → Upserts SystemConfig

### 4. GET/POST /api/vault
**Status**: ✅ Fully wired

GET Response:
```json
{
  "entries": [{ "id", "track", "key", "value", "score", "agent", "hash", "previousHash", "timestamp" }],
  "trackCounts": { "EVENT": N, "TRUST": N, "CAP": N, "FAIL": N, "GOV": N },
  "totalEntries": N
}
```

POST Actions:
- `verify_chain` → Validates all entries by hash chain

### 5. GET/PUT /api/research
**Status**: ✅ Fully wired

GET Response:
```json
{
  "papers": [{ "id", "title", "priorityTier", "relevanceScore", "isVetted", "implementationTask", "externalId" }]
}
```

PUT Body:
```json
{ "id": "paper-id", "priorityTier": "P0", "isVetted": true, "implementationTask": "In progress" }
```

### 6. GET/POST /api/models
**Status**: ✅ Fully wired

GET Response:
```json
{
  "models": [{ "id", "name", "provider", "tier", "domain", "health", "latencyMs", "isActive", "totalCalls", "successRate" }]
}
```

POST Actions:
- `toggle` → Updates ModelEntry.isActive
- `health_check` → Pings LLM via z-ai-web-dev-sdk, updates health/latency/successRate
- `batch_health_check` → Pings all active models

### 7. GET/POST /api/tokens
**Status**: ✅ Fully wired

GET Response:
```json
{
  "budget": { "totalBudget", "usedBudget", "remainingBudget", "isActive" },
  "usageLogs": [...],
  "agentUsage": [{ "agentId", "agentName", "totalTokens" }]
}
```

POST Actions:
- `log_usage` → Creates TokenUsageLog + updates SessionBudget

### 8. GET/POST /api/stresslab
**Status**: ✅ Fully wired (most sophisticated route)

GET Response:
```json
{
  "templates": [{ "id", "iscId", "name", "domain", "prompt", "difficulty", "description", "expectedBehavior", "passCriteria" }],
  "runs": [{ "id", "templateId", "model", "result", "collapseRate", "tokensUsed", "duration", "timestamp" }]
}
```

POST Actions:
- `run_test` → Creates TestRun, **executes LLM via z-ai-web-dev-sdk**, validates response, persists results, logs tokens
- `batch_run` → Runs multiple templates sequentially

Validation Logic:
- `validateResponse(response, domain)` checks: collapse detection, safety refusal, domain relevance, quality thresholds

### 9. GET /api/rate-limit/status
**Status**: ✅ Fully wired (real infrastructure data)

Response:
```json
{
  "providers": [{ "name", "requestsThisMinute", "limitPerMinute", "queueLength", "avgLatency" }],
  "keyHealth": [{ "provider", "keySuffix", "health", "lastUsed", "errors" }],
  "cacheStats": { "hits", "misses", "hitRate", "size" },
  "dedupStats": { "total", "duplicates", "uniqueRate" },
  "recentLogs": [...]
}
```

### 10. POST /api/chat
**Status**: ✅ Wired (z-ai-web-dev-sdk)

Request:
```json
{ "messages": [{ "role", "content" }], "model": "optional-model-override" }
```

Response: Streaming SSE with NEXUS OS system prompt

### 11. POST /api/claude
**Status**: ⚠️ Proxy on :8082 (may be offline)

Fallback for AI Assistant when z-ai is unavailable.

### 12. GET/POST /api/ai-bridge + /api/ai-bridge/providers
**Status**: ✅ Wired

Manages AI provider routing, health checks, and failover between z-ai and OpenRouter.

### 13. POST /api/proxy
**Status**: ✅ Wired (the workhorse)

Full proxy with rate limiting, caching, deduplication, and provider failover.

### 14. GET/PUT/DELETE /api/settings
**Status**: ✅ Wired

API key management stored in SystemConfig.

### 15. GET /api/trust-engine
**Status**: ✅ Wired

Computes CDR (Cognitive Distillation and Refinement) stages from Agent + GovernorDecision data.

### 16. GET /api/agents
**Status**: ✅ Wired

Simple agent list from Prisma.

### 17. POST /api/seed
**Status**: ✅ Wired

Seeds: 5 agents, 8 models, 12 templates, 6 papers, 1 budget, 2 configs.

---

*End of API Contract Specification*
