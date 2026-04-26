# Screen Strengths — GLM5 NEXUS OS Command Center

## Strongest Screens/Components

### 1. Research Tab ★★★★★
**Why strongest:** Complete end-to-end research pipeline — Alphaxiv integration with real external API calls, papers auto-saved to DB, working priority changes, status updates, add-to-queue, search across tiers, and daily practice timer. This is the most operationally complete tab.

**Differentiator:** No other lane likely has working Alphaxiv integration with DB persistence and real CRUD on paper priority/status.

### 2. Swarm Tab ★★★★★
**Why strongest:** Full worker lifecycle management — spawn (with capacity guard), terminate, restart, reassign, trust adjustment (+/- 0.05), vault logging of all actions. Every action creates a VaultEntry audit trail.

**Differentiator:** Complete CRUD + audit trail for worker management. Capacity indicators and constitution enforcement.

### 3. Governor Tab ★★★★☆
**Why strongest:** Trust scoring with CDR stages, interactive lane threshold adjustment with agent impact warnings, danger pattern management, decision appeals, and full decision log with charts.

**Differentiator:** Interactive threshold adjustment with real-time "affected agents" warnings. Decision distribution and impact analysis charts.

### 4. StressLab Tab ★★★★☆
**Why strongest:** Real LLM test execution via z-ai-web-dev-sdk with keyword-based validation, collapse detection, batch runs, and compare-models dialog.

**Differentiator:** Actually executes LLM completions and validates responses. Not just visual.

### 5. GMR Router Tab ★★★★☆
**Why strongest:** Real health checks via z-ai-web-dev-sdk, interactive model toggles with pool guards, and comprehensive pool/rotation visualizations.

**Differentiator:** Real model health pings with latency tracking. Pool guard prevents deactivating last model in a pool.

## Weakest Screens/Components

### 1. Rate Limit Control Tab ★★☆☆☆
**Why weak:** Shows 0 requests unless API calls have been explicitly logged. No automatic request interception. Data depends on manual logging via `rate-limiter.ts`.

**Fix needed:** Auto-log all API calls through the rate limiter middleware.

### 2. Overview Live Activity Feed ★★☆☆☆
**Why weak:** Simulated client-side feed with realistic but fake messages. Not connected to real system events.

**Fix needed:** Connect to VaultEntry stream or WebSocket for real events.

### 3. System Logs Panel ★★☆☆☆
**Why weak:** All log messages are generated client-side with no connection to real system events.

**Fix needed:** Bridge to Nexus backend log stream.

## Visually Strong but Operationally Shallow

| Component | Visual Quality | Operational Depth | Gap |
|-----------|---------------|-------------------|-----|
| Overview Health Timeline | ★★★★☆ | ★★☆☆☆ | Seeded pseudo-random, not real time-series |
| Swarm Task Queue | ★★★☆☆ | ★☆☆☆☆ | Hardcoded fallback, no real task queue |
| GMR Rotation Analytics | ★★★★☆ | ★☆☆☆☆ | Hardcoded rotation counts |
| GMR Failover Log | ★★★★☆ | ★☆☆☆☆ | Hardcoded failover events |
| Token Heatmap | ★★★★☆ | ★★☆☆☆ | Distributed from totals, not real hourly data |
| Cost Optimization | ★★★☆☆ | ★☆☆☆☆ | Hardcoded suggestions |

## Operationally Strong but Visually Weak

| Component | Operational Quality | Visual Quality | Gap |
|-----------|--------------------|-----------------|-----|
| Rate Limit Status | ★★★★☆ (real data) | ★★★☆☆ | Dense layout, could use better cards |
| Settings/Config | ★★★★☆ (full CRUD) | ★★☆☆☆ | Basic form, needs polish |
| Token Usage Logs | ★★★★☆ (real data) | ★★★☆☆ | Table-heavy, could use more charts |

## Key Differentiators vs. Other Lanes

1. **Working Alphaxiv Integration** — Real external API calls → DB persistence → working CRUD
2. **Real LLM Test Execution** — StressLab actually calls z-ai-web-dev-sdk, validates responses
3. **Real Model Health Checks** — GMR pings models and updates health/latency in DB
4. **Full Worker Audit Trail** — Every Swarm action logs a VaultEntry
5. **Interactive Governor Thresholds** — Sliders with real-time affected-agent warnings
6. **Constitution Enforcement** — Max agent limit in Swarm, pool guard in GMR
7. **Data Source Badges** — Honest labeling of real vs mock vs seed vs computed data
8. **Port Map + Thesis Card** — Clear architecture representation for public demo
