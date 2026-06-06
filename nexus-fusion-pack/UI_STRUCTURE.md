# GLM5.1 Fusion Pack — UI_STRUCTURE.md

## Latest UI Structure

### Navigation Model

**Primary:** Collapsible sidebar with 8 tab navigation items + system controls
**Secondary:** Command Palette (Ctrl+K) for power-user navigation
**Tertiary:** Keyboard shortcuts (1-8 for tabs, Ctrl+L for logs, ? for shortcuts)

```
┌──────────┬──────────────────────────────────────────────────┐
│          │  Header: Title + Token Budget + Clock + Actions  │
│          ├──────────────────────────────────────────────────┤
│ Sidebar  │                                                  │
│ (8 tabs) │  Main Content Area                               │
│          │  (tab panels with drill-down dialogs)             │
│          │                                                  │
│          ├──────────────────────────────────────────────────┤
│          │  Footer: Constitution Rules + Uptime + Status    │
└──────────┴──────────────────────────────────────────────────┘

Overlays:
  - AI Assistant (floating button → slide-in panel)
  - Command Palette (Ctrl+K modal)
  - System Logs (Ctrl+L bottom panel)
  - Quick Stats Widget (desktop bottom-left)
  - Keyboard Shortcuts (? key)
  - Notification Center (bell icon in header)
  - System Configuration (settings icon in header)
  - Diagnostics Panel (accessible from overview)
```

### Tab Structure & Widgets

#### 1. Overview Tab
```
OverviewTab
├── Welcome Banner (gradient, server/node status indicators)
├── 4 Gradient Stat Cards (Agents, Models, Trust, Budget)
├── 8-Pillar Health Grid (color-coded cards with pulse animation)
├── System Health Timeline (stacked area chart, 6h/12h/24h selector)
├── Weekly Agent Activity (bar chart)
├── Live Activity Feed (auto-updating every 3s)
├── System Uptime Clock (days/hours/minutes/seconds)
├── Recent Governance Decisions (mini-table with scope badges)
├── Quick Actions (Run Diagnostic, Export Report, Clear Cache)
└── Diagnostic Results (pillar health by domain)
```

#### 2. StressLab Tab
```
StressLabTab
├── 4 Gradient Stat Cards (Templates, Pass Rate, Collapse Rate, Avg Duration)
├── Test Results Summary (donut chart: PASS/FAIL/WARNING)
├── Domain Coverage (progress bars per domain)
├── Template Browser (searchable, filterable)
│   └── RunTestDialog (model/mode selection, simulated execution)
├── Arena Comparison (commercial vs heretic, animated gradient bars)
│   └── CompareModelsDialog (side-by-side model comparison)
├── Run History (compact list with result badges)
└── Recent Runs Table (detailed with collapse detection)
```

#### 3. GMR Router Tab
```
GmrTab
├── 4 Gradient Stat Cards (Models Online, Avg Health, Active Pool, Calls)
├── Model Performance Comparison (grouped bar chart)
├── Latency Over Time (area chart)
├── 4 Pool Cards (PREMIUM/MID/FAST/FREE_RESEARCH)
│   └── Per-model rows with sparklines, toggle switches
├── Pool Health Overview (stacked horizontal bars)
├── Rotation Analytics (most rotated to/from)
├── Failover Log (5 recent events with severity badges)
├── Model Registry (full list with active/inactive toggle)
├── AI Bridge Routing Simulator (query → pool → model)
└── Optimization Stats (dedup, cache, backoff metrics)
```

#### 4. Governor Tab
```
GovernorTab
├── 4 Gradient Stat Cards (Decisions, Allow Rate, Deny Rate, Avg Trust)
├── Decision Distribution (pie chart)
├── Impact Distribution (pie chart)
├── Scope Distribution (bar chart)
├── Trust Engine Hardwall Config (baseline, deltas, decay, CDR thresholds)
├── Agent Trust Velocity (sparklines per agent)
├── Lane Trust Thresholds (with interactive slider adjustment)
│   └── Warning system when agents fall below threshold
├── Agent Risk Matrix (scatter chart: trust vs activity)
├── Constitution Rules Summary
├── Danger Gate Flowchart (visual decision tree)
├── Live Decision Feed (real-time stream)
└── Decision Log Table (filterable, with scope/impact badges)
```

#### 5. Vault Tab
```
VaultTab
├── Vault Integrity Banner (operational status + export button)
├── 4 Gradient Stat Cards (Total Entries, Active Tracks, Latest, Avg Score)
├── Vault Statistics (pie chart with track distribution)
├── Recent Activity Timeline (color-coded by track)
├── Entry Distribution (donut chart)
├── 5 Track Cards (EVENT/TRUST/CAP/FAIL/GOV — clickable filter)
├── Entry Browser (searchable, filterable table)
│   └── Entry Detail Dialog (full metadata, JSON viewer, copy, VAP link)
├── VAP Proof Chain (timeline-style with hash verification)
│   └── Verify Chain Integrity (POST to /api/vault)
└── CSV Export
```

#### 6. Research Tab
```
ResearchTab
├── 3 Gradient Stat Cards (P0/P1/P2 counts)
├── Search Input (cross-tier search)
├── P0 Priority Queue (critical papers)
├── P1 Priority Queue (important papers)
├── P2 Priority Queue (background papers)
│   └── Paper Detail Dialog (relevance, task, deliverable, arXiv link)
├── Add to Queue Dialog (submit new paper)
└── Daily Practice Template (research workflow)
```

#### 7. Swarm Tab
```
SwarmTab
├── Swarm Health Banner (capacity utilization indicator)
├── 4 Gradient Stat Cards (Workers, Throughput, Avg Duration, Success Rate)
├── Throughput Bar Chart
├── Worker Status Grid (cards with sparklines, gradient backgrounds)
│   └── Worker Detail Dialog (full metadata, task history, reassign/terminate)
├── Task Queue (with assign buttons)
├── Completed Tasks Table
├── Worker Performance Table (with trust scores, error rates)
└── Swarm Topology View (circular layout with status colors)
```

#### 8. Token Budget Tab
```
TokensTab
├── Budget Gauge (large radial progress)
├── Hourly Token Usage (area chart)
├── Per-Agent Usage (horizontal bars with trend sparklines)
├── Per-Model Consumption (table with cost, calls, trend sparklines)
├── Token Usage Heatmap (agents × hours with tooltips)
├── Budget Alerts (with dismiss/view actions)
├── Cost Optimization Suggestions (4 actionable items with impact badges)
├── Burn Rate & Time Remaining
└── Constitution Limits Progress Bars
```

#### 9. Rate Limits Tab
```
RateLimitTab
├── 4 Gradient Stat Cards (Total Requests, Active Keys, Error Rate, Cache Hit Rate)
├── Provider Status Grid (per-provider health, rate limit status)
├── API Key Management (key cards with health indicators)
├── Cache & Dedup Statistics
├── Rate Limit Event Log
└── Request Summary (by provider, by status)
```

### Overlay Components

| Component | Trigger | Function |
|-----------|---------|----------|
| AI Assistant | Floating button (bottom-right) | LLM chat with NEXUS OS system prompt |
| Command Palette | Ctrl+K / Cmd+K | 8 navigation + 6 action commands |
| System Logs | Ctrl+L / Terminal icon | Real-time log streaming with filters |
| Quick Stats | Desktop only (bottom-left) | Token budget, active agents, uptime |
| Notification Center | Bell icon (header) | Alert feed with dismiss actions |
| System Configuration | Settings icon (header) | Dashboard settings dialog |
| Diagnostics Panel | "Run Diagnostic" button | Step-by-step endpoint health check |
| Keyboard Shortcuts | ? key | Full shortcut reference |

### Operator Flow: Top-Level → Deep Drilldown

```
1. Operator opens dashboard → Overview shows 8-pillar health at a glance
2. Click any pillar card → Pillar Detail Dialog shows latency, uptime, specifics
3. Notice degraded pillar → Switch to relevant tab (e.g., Governor for trust issues)
4. Governor tab → See agent trust scores, adjust thresholds with slider
5. Threshold change triggers warning → See affected agents in real-time
6. Need evidence → Vault tab, search by track, open Entry Detail Dialog
7. Need to test → StressLab tab, run test with specific model/mode
8. Need to route → GMR tab, check pool health, toggle models, simulate routing
9. Need to assign work → Swarm tab, view idle workers, assign tasks
10. Budget concern → Tokens tab, check burn rate, apply optimization
11. Need logs → Ctrl+L opens system logs, filter by level/source
12. Need AI help → Floating button opens AI Assistant with NEXUS context
```
