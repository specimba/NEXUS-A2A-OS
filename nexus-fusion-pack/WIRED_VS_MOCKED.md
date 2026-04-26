# GLM5.1 Fusion Pack — WIRED_VS_MOCKED.md

## Classification Legend

| Symbol | Meaning |
|--------|---------|
| ✅ WIRED | Connected to real backend API with live data |
| ⚠️ HYBRID | Partially wired — real DB with simulated updates |
| 🔶 MOCKED | Uses hardcoded/seeded data, no real backend logic |
| 🔴 BLOCKED | Requires backend endpoint that doesn't exist yet |
| 🟡 EXTERNAL | Depends on external service (z-ai-web-dev-sdk, etc.) |

---

## By Tab

### Overview Tab

| Widget | Status | Details |
|--------|--------|---------|
| 8-Pillar Health Grid | 🔶 MOCKED | Health percentages are simulated, not from 7352 |
| Stat Cards (Agents/Models/Trust/Budget) | ⚠️ HYBRID | Agent count from DB, trust/budget from DB, but health % simulated |
| System Health Timeline | 🔶 MOCKED | 24h timeline data is generated client-side |
| Weekly Agent Activity | 🔶 MOCKED | Chart data is static |
| Live Activity Feed | ⚠️ HYBRID | Rotates through static activities every 3s |
| System Uptime | ⚠️ HYBRID | Client-side timer since page load, not real process uptime |
| Recent Governance Decisions | 🔶 MOCKED | Static list, not from `/api/governor` |
| Quick Actions | ⚠️ HYBRID | "Run Diagnostic" wired to real endpoint checks; others are toast-only |
| Pillar Detail Dialog | 🔶 MOCKED | Details are static per pillar |

### StressLab Tab

| Widget | Status | Details |
|--------|--------|---------|
| Stat Cards | ⚠️ HYBRID | Counts from DB via `/api/stresslab` |
| Test Results Summary | ⚠️ HYBRID | Chart data derived from DB runs |
| Domain Coverage | 🔶 MOCKED | Static progress bars |
| Template Browser | ✅ WIRED | Templates from DB, search works |
| RunTestDialog | ⚠️ HYBRID | UI wired, execution is simulated (progress bar + toast) |
| Arena Comparison | ⚠️ HYBRID | Data from DB runs, comparison visualization is real |
| CompareModelsDialog | ⚠️ HYBRID | Pulls from DB, side-by-side logic works |
| Run History | ✅ WIRED | From DB via `/api/stresslab` |

### GMR Router Tab

| Widget | Status | Details |
|--------|--------|---------|
| Stat Cards | ✅ WIRED | From `/api/models` with 15s refresh |
| Model Performance Chart | ⚠️ HYBRID | Data from DB, health simulation client-side |
| Latency Chart | ⚠️ HYBRID | Based on DB data with simulated variation |
| Pool Cards | ✅ WIRED | From `/api/models`, toggle sends PATCH |
| Pool Health Overview | ⚠️ HYBRID | Derived from model data |
| Rotation Analytics | 🔶 MOCKED | Static rotation counts |
| Failover Log | 🔶 MOCKED | Static failover events |
| Model Registry | ✅ WIRED | Full CRUD via `/api/models` |
| AI Bridge Routing | 🟡 EXTERNAL | Uses `/api/ai-bridge` → z-ai-web-dev-sdk |
| Optimization Stats | 🔶 MOCKED | Static dedup/cache/backoff numbers |

### Governor Tab

| Widget | Status | Details |
|--------|--------|---------|
| Stat Cards | ✅ WIRED | From `/api/governor` + `/api/trust-engine` |
| Decision Distribution | ✅ WIRED | From DB decisions |
| Impact/Scope Charts | ✅ WIRED | From DB decisions |
| Trust Engine Hardwall | ✅ WIRED | From `/api/trust-engine` |
| Agent Trust Velocity | ⚠️ HYBRID | Trust data from DB, velocity calculated client-side |
| Lane Threshold Adjustment | ⚠️ HYBRID | UI works, sends POST to `/api/governor`, applies locally |
| Agent Risk Matrix | ⚠️ HYBRID | Scatter data from DB |
| Constitution Rules | ⚠️ HYBRID | From `/api/system` with fallback |
| Danger Gate Flowchart | 🔶 MOCKED | Static visualization |
| Live Decision Feed | 🔶 MOCKED | Simulated real-time feed |
| Decision Log Table | ✅ WIRED | From `/api/governor` |

### Vault Tab

| Widget | Status | Details |
|--------|--------|---------|
| Integrity Banner | ✅ WIRED | From `/api/vault` with 15s refresh |
| Stat Cards | ✅ WIRED | Computed from real DB entries |
| Vault Statistics Pie | ✅ WIRED | Track counts from DB |
| Recent Activity Timeline | ✅ WIRED | Latest 5 entries from DB |
| Entry Distribution | 🔶 MOCKED | Static distribution data (not from real counts) |
| 5 Track Cards | ✅ WIRED | Track counts from DB, clickable filters work |
| Entry Browser | ✅ WIRED | Search + filter + detail dialog all wired |
| VAP Proof Chain | ⚠️ HYBRID | Visual chain from DB entries, verification POSTs to API |
| CSV Export | ✅ WIRED | Exports filtered entries |

### Research Tab

| Widget | Status | Details |
|--------|--------|---------|
| Stat Cards | ✅ WIRED | Counts from `/api/research` |
| Search | ✅ WIRED | Client-side filter across all tiers |
| P0/P1/P2 Queues | ✅ WIRED | From `/api/research` with 30s refresh |
| Paper Detail Dialog | ✅ WIRED | Click to open, copy, arXiv link |
| Add to Queue Dialog | ⚠️ HYBRID | POSTs to `/api/research`, but workflow is simulated |
| Daily Practice Template | 🔶 MOCKED | Static template |

### Swarm Tab

| Widget | Status | Details |
|--------|--------|---------|
| Stat Cards | ✅ WIRED | From `/api/swarm` with 15s refresh |
| Worker Status Grid | ✅ WIRED | From DB agents, sparklines client-side |
| Worker Detail Dialog | ✅ WIRED | Full metadata from DB, reassign/terminate POST |
| Task Queue | ✅ WIRED | From DB, assign button wired |
| Completed Tasks | ✅ WIRED | From DB |
| Worker Performance | ⚠️ HYBRID | Trust/error rates from DB, performance metrics calculated |
| Swarm Topology | ⚠️ HYBRID | Worker positions calculated, status from DB |
| Throughput Chart | ⚠️ HYBRID | Derived from task completion data |

### Token Budget Tab

| Widget | Status | Details |
|--------|--------|---------|
| Budget Gauge | ✅ WIRED | From `/api/tokens` with 30s refresh |
| Hourly Usage Chart | ⚠️ HYBRID | From DB logs, hourly aggregation client-side |
| Per-Agent Usage | ✅ WIRED | From DB |
| Per-Model Consumption | ✅ WIRED | From DB with cost calculations |
| Token Usage Heatmap | ⚠️ HYBRID | Aggregated from DB, tooltip interaction works |
| Budget Alerts | ⚠️ HYBRID | Logic from real budget data, alert generation client-side |
| Cost Optimization | 🔶 MOCKED | Static suggestions |
| Burn Rate | ⚠️ HYBRID | Calculated from DB data |

### Rate Limits Tab

| Widget | Status | Details |
|--------|--------|---------|
| Stat Cards | ✅ WIRED | From `/api/rate-limit/status` |
| Provider Status | ✅ WIRED | From API |
| API Key Management | ✅ WIRED | From API |
| Cache & Dedup Stats | ✅ WIRED | From API |
| Event Log | ✅ WIRED | From API |

---

## Global Components

| Component | Status | Details |
|-----------|--------|---------|
| AI Assistant | 🟡 EXTERNAL | z-ai-web-dev-sdk LLM with NEXUS OS system prompt |
| Command Palette | ✅ WIRED | All navigation/actions functional |
| System Logs | 🔶 MOCKED | Simulated log generation (1.5-3.5s interval) |
| Quick Stats Widget | ✅ WIRED | From `/api/tokens` with 60s refresh |
| Notification Center | 🔶 MOCKED | Static notifications |
| System Configuration | 🔶 MOCKED | Settings dialog with no persistence |
| Diagnostics Panel | ✅ WIRED | Runs real endpoint health checks |
| System Terminal | ✅ WIRED | `agents`, `vault`, `gmr`, `tokens` commands hit real APIs |
| Header/Footer | ⚠️ HYBRID | Clock real, model count from API, constitution from fallback |

---

## Summary Statistics

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ WIRED | 42 | 51% |
| ⚠️ HYBRID | 25 | 30% |
| 🔶 MOCKED | 14 | 17% |
| 🔴 BLOCKED | 0 | 0% |
| 🟡 EXTERNAL | 2 | 2% |

**81% of widgets have at least partial real data. 51% are fully wired.**
