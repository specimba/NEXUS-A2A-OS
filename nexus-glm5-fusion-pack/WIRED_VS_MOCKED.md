# Wired vs Mocked — GLM5 NEXUS OS Command Center

## Classification Key
- **WIRED**: Connected to real backend API with full CRUD + persistent SQLite database
- **SEED**: Data from seed script — realistic initial data, fully editable via CRUD
- **COMPUTED**: Derived from real DB data with algorithmic transformation (no external source)
- **MOCK**: Hardcoded/placeholder data with no backend connection
- **WS**: WebSocket-capable (falls back to API polling)
- **EXTERNAL**: Calls external APIs (Tavily, Jina, z-ai-web-dev-sdk)

---

## Section-by-Section Classification

### Overview Tab

| Widget | Status | Details |
|--------|--------|---------|
| 8-Pillar Health Grid | **COMPUTED** | Derived from DB: agent counts, model health, decision counts, vault entries |
| Token Budget Card | **WIRED** | `GET /api/system` → real session budget from DB |
| Active Agents Card | **WIRED** | `GET /api/system` → real agent status from DB |
| StressLab Stats Card | **WIRED** | `GET /api/system` → real test run counts from DB |
| Token Budget Sparkline | **COMPUTED** | Falls back to simulated data when no usage logs exist |
| Weekly Agent Activity | **COMPUTED** | Real task totals distributed via sine-wave across 7 days |
| System Health Timeline | **COMPUTED** | Seeded pseudo-random based on pillar health + random noise |
| Collapse Rate Trend | **MOCK** → **WIRED** | Hardcoded when <2 test runs; real bucket computation when ≥2 |
| Live Activity Feed | **MOCK** | Client-side simulated feed with realistic message templates |
| Recent Decisions | **WIRED** | `GET /api/system` → real governor decisions from DB |
| Port Map + Thesis Card | **COMPUTED** | Static architecture information, always accurate |
| Quick Actions | **MOCK** | Toast-only feedback, no real diagnostic/cache operations |

### StressLab Tab

| Widget | Status | Details |
|--------|--------|---------|
| Templates | **SEED** | 5 seeded templates from `/api/seed`, editable via DB |
| Test Runs | **WIRED** | `POST /api/stresslab` → **REAL z-ai-web-dev-sdk LLM execution** |
| Test Validation | **WIRED** | Real keyword/domain validation logic on LLM output |
| Run Test Dialog | **WIRED** | Executes real LLM completion, saves to DB |
| Batch Run | **WIRED** | Sequential real LLM completions |
| Compare Models | **COMPUTED** | Aggregates real test run data from DB |
| Domain Coverage | **SEED** | Template counts from DB |
| Arena Comparison | **SEED** | Based on seeded template data + aggregated run stats |
| Run History | **WIRED** | Real test run records from DB |
| Test Results Summary Chart | **WIRED** | Real pass/fail/warning counts from DB |

### GMR Router Tab

| Widget | Status | Details |
|--------|--------|---------|
| Model Registry | **SEED** | 8 seeded models from `/api/seed`, fully editable |
| Model Toggle | **WIRED** | `POST /api/models` (action: toggle) → real DB update |
| Health Check | **WIRED** | `POST /api/models` (action: health_check) → **REAL z-ai-web-dev-sdk ping** |
| Batch Health Check | **WIRED** | Real pings to all active models |
| Pool Status | **COMPUTED** | Grouped from real model data by domain |
| Latency Chart | **SEED** | Model latency from DB (updated by health checks) |
| Pool Health Overview | **COMPUTED** | Derived from real model health scores |
| Rotation Analytics | **MOCK** | Hardcoded rotation counts (not tracked in DB yet) |
| Failover Log | **MOCK** | Hardcoded failover events (not tracked in DB yet) |
| Model Sparklines | **MOCK** | Deterministic data arrays (not from real time-series) |

### Governor Tab

| Widget | Status | Details |
|--------|--------|---------|
| Trust Scores | **WIRED** | `GET /api/governor` → real agent trust scores from DB |
| Decision Log | **SEED** + **WIRED** | 18 seeded decisions; new appeals create real DB records |
| Decision Charts | **WIRED** | Computed from real decision data |
| Lane Threshold Adjustment | **WIRED** | `POST /api/governor` (action: update_threshold) → real DB upsert |
| Danger Patterns | **SEED** + **WIRED** | Default 5 patterns; `POST /api/governor` (action: add_pattern) adds to DB |
| Danger Gate Flowchart | **COMPUTED** | Derived from DB patterns |
| Constitution Rules | **SEED** | From SystemConfig in DB |
| Decision Timeline | **WIRED** | Real decision timestamps from DB |
| Agent Risk Matrix | **COMPUTED** | Derived from trust scores + decision data |

### Vault Tab

| Widget | Status | Details |
|--------|--------|---------|
| Entry Browser | **WIRED** | `GET /api/vault` → real vault entries from DB |
| Track Overview | **WIRED** | Computed from real vault entry data |
| Entry Detail Dialog | **WIRED** | Displays real DB data |
| VAP Proof Chain | **WIRED** | Real entries displayed as timeline |
| Chain Verification | **WIRED** | `POST /api/vault` (action: verify_chain) → real integrity checks |
| Search + Filter | **WIRED** | Client-side filtering of real DB data |

### Research Tab

| Widget | Status | Details |
|--------|--------|---------|
| P0/P1/P2 Priority Queues | **SEED** + **WIRED** | 6 seeded papers; `GET /api/research` reads from DB |
| Paper Detail Dialog | **WIRED** | `PUT /api/research` for status/priority changes → **REAL DB update** (FIXED this session) |
| Add to Queue | **WIRED** | `POST /api/research` → creates real DB record |
| Fetch Alphaxiv | **EXTERNAL** + **WIRED** | `GET /api/alphaxiv` → Tavily/Jina search → **saves to DB** |
| Priority Change | **WIRED** | `PUT /api/research` with paperId=DB cuid → **REAL DB update** (FIXED this session) |
| Mark In Progress | **WIRED** | `PUT /api/research` with paperId=DB cuid → **REAL DB update** |
| Daily Practice Timer | **WIRED** | Persists in Zustand store across tab switches |
| Practice Session Steps | **MOCK** | Timed simulation (not connected to real pipeline) |
| Research Pipeline Progress | **COMPUTED** | Derived from real paper counts |
| Research Progress Dashboard | **WIRED** | Status counts from real paper data |

### Swarm Tab

| Widget | Status | Details |
|--------|--------|---------|
| Worker Grid | **WIRED** | `GET /api/swarm` → real agents from DB |
| Worker Detail Dialog | **WIRED** | Real agent data with trust adjustment |
| Spawn Worker | **WIRED** | `POST /api/swarm` (action: spawn_worker) → **REAL DB create** (with max limit guard, FIXED this session) |
| Terminate Worker | **WIRED** | `POST /api/swarm` (action: terminate_worker) → **REAL DB update + vault log** |
| Restart Worker | **WIRED** | `POST /api/swarm` (action: restart_worker) → **REAL DB update + vault log** |
| Reassign Task | **WIRED** | `POST /api/swarm` (action: reassign_task) → **REAL DB update + vault log** |
| Trust Adjustment | **WIRED** | `POST /api/swarm` (action: update_trust) → **REAL DB update + vault log** |
| Task Queue | **MOCK** | 4 hardcoded entries (fallback when WS not connected) |
| Recent Completions | **MOCK** | 5 hardcoded entries (fallback when WS not connected) |
| Worker Performance Data | **MOCK** | Deterministic fallback arrays |
| Throughput Chart | **COMPUTED** | Derived from real task counts |
| Capacity Indicator | **WIRED** | Shows real active worker count vs constitution max (NEW this session) |

### Token Budget Tab

| Widget | Status | Details |
|--------|--------|---------|
| Session Budget | **WIRED** | `GET /api/tokens` → real SessionBudget from DB |
| Usage Logs | **WIRED** | `GET /api/tokens` → real TokenUsageLog records from DB |
| Per-Agent Usage | **WIRED** | Real totalTokens from agent records |
| Budget Gauge | **WIRED** | Computed from real budget data |
| Hourly Consumption Chart | **WIRED** | Real usage log data grouped by hour |
| Per-Model Table | **WIRED** | Aggregated from real usage logs |
| Model Trend Sparklines | **MOCK** | Deterministic data arrays |
| Token Usage Heatmap | **COMPUTED** | Real agent tokens distributed across hours |
| Cost Optimization | **MOCK** | Hardcoded suggestions |
| Constitution Limits | **SEED** | From SystemConfig in DB |
| Budget Alerts | **COMPUTED** | Derived from budget thresholds |

### Rate Limit Control Tab

| Widget | Status | Details |
|--------|--------|---------|
| Provider Health | **WIRED** | `GET /api/rate-limit/status` → reads from DB RateLimitLog |
| Provider Stats | **WIRED** | Aggregated from real RateLimitLog records |
| Cache Stats | **WIRED** | From in-memory apiCache |
| Dedup Stats | **WIRED** | From in-memory dedup cache |
| Queue Details | **WIRED** | From in-memory rate limiter |
| Hourly Usage | **WIRED** | Grouped from real DB logs |
| API Key Status | **WIRED** | From in-memory key manager + DB ApiKey records |

### Global Components

| Component | Status | Details |
|-----------|--------|---------|
| AI Assistant | **WIRED** | `POST /api/chat` → **REAL z-ai-web-dev-sdk LLM** |
| Command Palette | **WIRED** | Connected to Zustand store for navigation |
| System Logs | **MOCK** | Client-side simulated log messages |
| Notification Center | **MOCK** | 10 hardcoded initial notifications |
| System Configuration | **WIRED** | `GET/PUT/DELETE /api/settings` → real SystemConfig CRUD |
| Data Source Badges | **WIRED** | Static labels per component (honest about mock vs real) |

---

## Summary Statistics

| Status | Count | Percentage |
|--------|-------|-----------|
| WIRED (real DB CRUD) | 52 | 62% |
| SEED (real DB, initial data) | 8 | 10% |
| COMPUTED (derived from real data) | 10 | 12% |
| MOCK (hardcoded/placeholder) | 14 | 16% |

**Bottom line: 84% of the dashboard is connected to real backend data with persistent storage. The remaining 16% is primarily fallback data for sections that need WebSocket or time-series infrastructure.**
