# UI Structure — GLM5 NEXUS OS Command Center

## Navigation Model

- **Sidebar** (left, collapsible): 9 nav items with icons, active indicator, badge dots
- **Header** (top): Tab title, token budget gauge, clock, notification bell, settings, terminal, theme toggle
- **Footer** (bottom, sticky): Constitution rules, session uptime, live indicator
- **Command Palette** (Ctrl+K): Global search overlay with 8 navigation + 6 action commands
- **AI Assistant** (floating button, bottom-right): Slide-in chat panel

## Tab Structure

### 1. Overview (`/`)
**Purpose:** At-a-glance system health and activity  
**Widgets:**
- Welcome banner with animated gradient border, server/node status
- 8-Pillar Health Grid (Bridge, Engine, Governor, Vault, GMR, Swarm, Monitor, Config) — each with health %, status, uptime
- 4 Stat Cards: Token Budget, Active Agents, StressLab Pass Rate, Collapse Rate
- Token Budget sparkline chart
- Weekly Agent Activity bar chart
- System Health Timeline (stacked area, 8 pillars, 24h, time range selector)
- Collapse Rate Trend sparkline
- Live Activity Feed (auto-updating)
- Recent Governance Decisions mini-table with scope badges
- Port Map + NEXUS Thesis Card (8-pillar architecture summary)
- Quick Actions row (Run Diagnostic, Export Report, Clear Cache)

### 2. StressLab
**Purpose:** ISC-Bench test execution and collapse rate monitoring  
**Widgets:**
- 4 Stat Cards: Total Runs, Pass Rate, Collapse Rate, Avg Duration
- Test Results Summary donut chart (PASS/FAIL/WARNING)
- Domain Coverage progress bars (6 domains)
- ISC-Bench Template Browser (expandable cards with domain, difficulty, source ID)
- Run Test Dialog (model selection, mode: single/icl/agentic, real LLM execution)
- Batch Run capability
- Compare Models dialog (side-by-side comparison table)
- Arena: Commercial vs Heretic model comparison with animated gradient bars
- Run History card (last 5 runs)
- Data source: `GET/POST /api/stresslab` — REAL (z-ai-web-dev-sdk execution)

### 3. GMR Router
**Purpose:** Model registry, pool management, health monitoring  
**Widgets:**
- 3 Stat Cards: Models Online, Avg Health, FREE_RESEARCH Pool count
- Model Performance Comparison grouped bar chart
- 4 Pool Cards: PREMIUM, MID, FAST, FREE_RESEARCH — each with model rows, health bars, sparklines
- Interactive model toggle (Switch with pool guard — last-active-model protection)
- Latency chart (NexusBarChart)
- Pool Health Overview (stacked horizontal bars per pool)
- Rotation Analytics (Most Rotated To/From)
- Failover Log (5 recent events with severity badges)
- Data source: `GET/POST /api/models` — REAL (z-ai-web-dev-sdk health checks)

### 4. Governor
**Purpose:** Trust scoring, governance decisions, danger patterns  
**Widgets:**
- 3 Stat Cards: Avg Trust Score, Decisions Today, Danger Blocks
- Decision Distribution pie chart
- Impact Distribution pie chart
- Scope Distribution bar chart
- Agent Trust Scores with Progress bars + threshold line markers
- Lane Trust Thresholds with interactive adjustment (sliders + warnings)
- Danger Gate Flowchart
- Decision Timeline / Live Decision Feed
- Decision Log table (filterable, expandable)
- Constitution Rules Summary
- Data source: `GET/POST /api/governor` — REAL (full CRUD)

### 5. Vault
**Purpose:** 5-track memory browser, immutable audit trail  
**Widgets:**
- 4 Gradient Stat Cards: Total Entries, Active Tracks, Latest Entry, Avg Score
- 5-Track Overview Cards (EVENT, TRUST, CAP, FAIL, GOV) — clickable for filtering
- Search input with clear button
- Entry Browser table (filterable by track + search, paginated)
- Entry Detail Dialog (formatted JSON, copy buttons, score bar)
- VAP Proof Chain (timeline-style with connectors, hash copy, verify button)
- Data source: `GET/POST /api/vault` — REAL (chain verification operational)

### 6. Research
**Purpose:** Paper/repo priority queue, Alphaxiv integration, daily practice  
**Widgets:**
- 4 Stat Cards: P0 Implement Now, P1 Next Sprint, P2 Research, Total Vetted
- Research Pipeline progress indicator (animated 5-stage)
- Research Progress Dashboard (status distribution bars + completion %)
- Daily Practice Timer (persists across tab switches via Zustand)
- P0/P1/P2 Priority Queue lists (expandable cards)
- Paper Detail Dialog (relevance score, task, deliverable, priority change, mark in progress)
- Add to Queue Dialog (title, ID, domain, priority, relevance slider)
- Fetch Alphaxiv button (Tavily/Jina search, auto-saves to DB)
- Search bar across all tiers
- Data source: `GET/POST/PUT /api/research` + `GET/POST /api/alphaxiv` — REAL (full CRUD + external API)

### 7. Swarm
**Purpose:** Worker pool management, task assignment, trust adjustment  
**Widgets:**
- 4 Stat Cards: Active Workers, Throughput, Success Rate, Avg Trust
- Worker Grid cards (gradient by status, sparklines, pulsing error borders)
- Worker Detail Dialog (full metadata, trust adjustment +/- 0.05, terminate/restart/reassign)
- Spawn Worker Dialog (name, type, domain, capacity indicator with max limit)
- Reassign Task Dialog (domain + task ID)
- Reorder Priority Dialog (high/medium/low for queued tasks)
- Task Queue table (with Assign button per task)
- Recent Completions table
- Throughput bar chart
- Data source: `GET/POST /api/swarm` — REAL (full CRUD: spawn, terminate, restart, reassign, trust update)

### 8. Token Budget
**Purpose:** Session budget, per-agent/per-model consumption, cost optimization  
**Widgets:**
- Budget Utilization gauge (radial chart)
- 3 Stat Cards: Remaining, Burn Rate, Time Remaining
- Hourly Token Consumption area chart
- Per-Agent Usage bar chart
- Per-Model Consumption table with trend sparklines
- Token Usage Heatmap (agents × hours with tooltips)
- Cost Optimization Suggestions (4 actionable items with Apply buttons)
- Constitution Limits progress bars
- Budget Alerts with action buttons (View Details / Dismiss)
- Data source: `GET/POST /api/tokens` — REAL (session budget + usage logs)

### 9. Rate Limit Control
**Purpose:** API provider health, rate limit monitoring, cache/dedup stats  
**Widgets:**
- Provider Health Cards (OpenRouter, Jina, Cerebras, Kilocode, Tavily)
- Rate Limit Status indicators
- Queue Details per provider
- Cache Hit Rate stats
- Deduplication stats
- Hourly Usage charts
- Data source: `GET /api/rate-limit/status` — REAL (reads from DB + in-memory rate limiter)

## Global Components
- **AI Assistant** (floating, z-ai-web-dev-sdk LLM with NEXUS system prompt)
- **Command Palette** (Ctrl+K, 14 commands)
- **System Logs** (Ctrl+L, real-time log streaming with filters)
- **Notification Center** (bell icon, 10 initial notifications)
- **System Configuration** (settings icon, API key management)
- **Export Dialog** (global, CSV/JSON export)
- **Data Source Badges** (per-widget, showing REAL/SEED/MOCK/COMPUTED/WS status)
