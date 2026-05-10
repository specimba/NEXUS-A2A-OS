# NEXUS OS v3.1 — Structured Fusion Pack
> Generated: 2025-01-27 | Branch: canonical-617 | Dashboard: Next.js 16.1.3 + Prisma SQLite

---

## 1. INTAKE CHECKLIST

| # | Item | Status |
|---|------|--------|
| 1 | UI Structure documented | ✅ |
| 2 | Strongest screens/components identified | ✅ |
| 3 | Wired-vs-Mocked status mapped | ✅ |
| 4 | API assumptions listed | ✅ |
| 5 | Strongest differentiators called out | ✅ |
| 6 | Public-safe vs mock-dependent marked | ✅ |
| 7 | Screenshots referenced (not loose) | ✅ |

---

## 2. UI STRUCTURE

### 2.1 Layout Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  NexusHeader (tab title, token budget, clock, theme toggle) │
│  [Terminal] [Bell] [Settings] [Command Palette ⌘K]          │
├──────┬──────────────────────────────────────────────────────┤
│      │                                                      │
│  N   │  TabContent (Framer Motion transitions)              │
│  e   │  ┌──────────────────────────────────────────────┐    │
│  x   │  │  Active Tab Panel                             │    │
│  u   │  │  (8 tabs, one visible at a time)             │    │
│  s   │  └──────────────────────────────────────────────┘    │
│  S   │                                                      │
│  i   │  [AI Assistant] (floating, bottom-right)             │
│  d   │  [System Logs] (slide-up panel, ⌘L)                 │
│  e   │                                                      │
│  b   │                                                      │
│  a   │                                                      │
│  r   │                                                      │
│      │                                                      │
├──────┴──────────────────────────────────────────────────────┤
│  NexusFooter (Constitution rules, uptime, Live indicator)   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Navigation Tabs (8)

| Tab | Icon | Route Key | Status |
|-----|------|-----------|--------|
| Overview | LayoutDashboard | `overview` | 🟡 SIMULATED |
| StressLab | Beaker | `stresslab` | 🟢 WIRED |
| GMR Router | Cpu | `gmr` | 🟡 WIRED+MOCK |
| Governor | Shield | `governor` | 🟢 WIRED |
| Vault | Database | `vault` | 🟢 WIRED |
| Research | BookOpen | `research` | 🟢 WIRED |
| Swarm | Users | `swarm` | 🟢 WIRED |
| Token Budget | Coins | `tokens` | 🟢 WIRED |

### 2.3 Overlay Panels

| Panel | Trigger | Status |
|-------|---------|--------|
| AI Assistant Chat | Floating button / quick prompts | 🟢 WIRED (real LLM) |
| Command Palette | ⌘K / Ctrl+K | 🟢 WIRED (UI nav) |
| System Logs | ⌘L / Terminal icon | 🔴 SIMULATED |
| Notification Center | Bell icon in header | 🟡 MOCK (hardcoded alerts) |
| System Architecture | Overview tab inline | 🟡 SIMPLIFIED |
| Global Export Dialog | Export button | 🟢 WIRED (real data export) |
| Diagnostics Panel | Overview Quick Actions | 🟡 SIMULATED |

---

## 3. STRONGEST SCREENS / COMPONENTS

### Tier 1 — Production-Ready (WIRED with real backend)

| # | Component | Why It's Strong |
|---|-----------|-----------------|
| 1 | **StressLab Tab** | Full lifecycle: DB templates → real LLM execution via z-ai-web-dev-sdk → domain-specific validation → persisted results → token logging. The only tab that orchestrates actual AI work. Includes: ISC-Bench test runner, batch runs, model comparison dialog, domain coverage charts, run history, arena comparison. |
| 2 | **Swarm Tab** | Complete CRUD with real DB persistence. Spawn/terminate/restart workers, reassign tasks, update trust scores. All mutations create VaultEntry audit trails. Constitution max-agent limit enforced server-side. WebSocket support via useSwarmWS hook. Worker detail dialogs with sparklines and task history. |
| 3 | **Governor Tab** | Real decisions from DB, trust scoring per agent, configurable thresholds (slider UI with agent impact warnings), danger pattern management, appeal workflow. Agent Risk Matrix scatter chart. Decision distribution pie charts. Live Decision Feed (simulated from real data). |
| 4 | **Rate Limit Tab** | Live monitoring of real infrastructure: in-memory rate limiter state, API key health from key manager, cache stats, dedup stats, DB rate-limit logs. Fully functional read-only monitoring dashboard. |
| 5 | **Research Tab** | Real paper data from Prisma with P0/P1/P2 tiering. Priority/status mutations persist to DB. Paper detail dialog with arXiv links, copy-to-clipboard, mark-in-progress. Cross-tier search/filter. Daily practice timer (local-only). Add-to-queue dialog (local-only). |

### Tier 2 — Strong but Partially Mocked

| # | Component | Why Partial |
|---|-----------|-------------|
| 6 | **GMR Tab** | Model registry + health checks are REAL (toggle persists, health_check actually pings LLMs). BUT: pool definitions, rotation log, failover log, rotation analytics, and AI Bridge routes are HARDCODED. |
| 7 | **Tokens Tab** | Budget, usage logs, agent/model breakdowns are REAL from Prisma. BUT: optimization suggestions, constitution limits, burn rate (142 tok/min), and session comparison stats are HARDCODED. |
| 8 | **Vault Tab** | Main entry browser and chain verification are REAL. BUT: entry distribution donut and recent activity timeline use HARDCODED fallback data. |

### Tier 3 — Mock / Simulated

| # | Component | Why Mock |
|---|-----------|-------------|
| 9 | **Overview Tab** | **The biggest gap.** Almost entirely hardcoded. 8 pillar health cards, sparklines, activity feed, notifications, uptime counter — all fake. **Ignores the real `/api/system` endpoint** that computes actual pillar health from DB. |
| 10 | **System Logs** | Entirely simulated from hardcoded templates. No connection to real VaultEntry or RateLimitLog data. |
| 11 | **Notification Center** | Initial notifications are hardcoded in Zustand store. Not derived from real system events. |

---

## 4. WIRED-vs-MOCKED STATUS MAP

### 4.1 Component-Level Status

```
COMPONENT                    STATUS         DATA SOURCE              MUTATIONS PERSIST?
─────────────────────────────────────────────────────────────────────────────────────
Overview Tab                 SIMULATED      Hardcoded                No
StressLab Tab                WIRED          /api/stresslab + LLM     Yes ✅
GMR Tab                      WIRED+MOCK     /api/models + hardcoded  Toggle/Health ✅
Governor Tab                 WIRED          /api/governor            Yes ✅
Vault Tab                    WIRED          /api/vault               Verify only ✅
Research Tab                 WIRED          /api/research            Priority/Status ✅
Swarm Tab                    WIRED          /api/swarm + WS          Yes ✅
Token Budget Tab             WIRED          /api/tokens              No UI mutations
Rate Limit Tab               WIRED          /api/rate-limit/status   Read-only
AI Assistant                 WIRED          /api/chat + /api/claude  Local state only
Command Palette              WIRED          Zustand store            N/A (UI nav)
System Logs                  SIMULATED      Hardcoded templates      Local only
Notification Center          MOCK           Hardcoded notifications  Local only
```

### 4.2 API Route Status

```
ENDPOINT                     METHOD   REAL DATA?   NOTES
──────────────────────────────────────────────────────────────
/api/swarm                   GET/POST ✅           Full CRUD, WebSocket
/api/governor                GET/POST ✅           Decisions, thresholds, patterns
/api/vault                   GET/POST ✅           Entries, chain verification
/api/research                GET/PUT  ✅           Papers, priority/status
/api/models                  GET/POST ✅           Model registry, health checks
/api/tokens                  GET/POST ✅           Budget, usage logs
/api/stresslab               GET/POST ✅           Templates, runs, LLM execution
/api/rate-limit/status       GET      ✅           Real rate limiter state
/api/system                  GET      ✅           **NOT CONSUMED BY OVERVIEW**
/api/agents                  GET      ✅           Simple agent list
/api/settings                GET/PUT  ✅           API key management
/api/trust-engine            GET      ✅           CDR stage computation
/api/chat                    POST     ✅           z-ai-web-dev-sdk LLM
/api/claude                  POST     ⚠️           Proxy on :8082 (may be offline)
/api/ai-bridge               GET/POST ✅           Provider routing
/api/ai-bridge/providers     GET/POST ✅           Provider health
/api/proxy                   POST     ✅           Full proxy w/ rate limit
/api/seed                    POST     ✅           Database seeding
```

### 4.3 Data Flow Map

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Frontend    │────▶│  API Routes  │────▶│  Prisma/SQLite│
│  Components  │◀────│  (Next.js)   │◀────│  (10 models)  │
└─────────────┘     └──────────────┘     └───────────────┘
                           │                     │
                           ▼                     ▼
                    ┌──────────────┐     ┌───────────────┐
                    │ z-ai-web-dev │     │ In-Memory     │
                    │ SDK (LLM)    │     │ Rate Limiter   │
                    └──────────────┘     │ + API Cache    │
                                         └───────────────┘
```

---

## 5. API ASSUMPTIONS

### 5.1 Required Environment Variables

| Variable | Purpose | Status |
|----------|---------|--------|
| `OPENROUTER_API_KEY` | OpenRouter LLM access | ✅ Configured |
| `TAVILY_API_KEY` | Web search | ✅ Configured |
| `JINA_API_KEY` | Content extraction | ✅ Configured |
| `CEREBRAS_API_KEY` | Cerebras LLM access | ✅ Configured |
| `KILOCODE_JWT_TOKEN` | Kilocode API proxy | ⚠️ Not configured |

### 5.2 External Service Dependencies

| Service | Port | Purpose | Status |
|---------|------|---------|--------|
| Claude Free Proxy | 8082 | AI chat fallback | ⚠️ May be offline |
| Swarm WebSocket | 3003 | Real-time worker updates | ✅ Available |
| z-ai-web-dev-sdk | — | Primary LLM access | ✅ Available |

### 5.3 Database Schema (10 Models)

```
Agent          → name, type, trustScore, status, totalTokens, capabilities
VaultEntry     → track, key, value, score, agentId, hash, previousHash
GovernorDecision → decision, scope, action, reasoning, agentId
ModelEntry     → name, provider, tier, domain, health, latencyMs, isActive
TestTemplate   → iscId, name, domain, prompt, difficulty, description, expectedBehavior, passCriteria
TestRun        → templateId, model, result, collapseRate, tokensUsed, duration
Paper          → title, priorityTier, relevanceScore, isVetted, implementationTask
TokenUsageLog  → agentId, model, promptTokens, completionTokens, totalTokens, cost
SessionBudget  → totalBudget, usedBudget, remainingBudget, isActive
SystemConfig   → key, value (JSON) — stores thresholds, patterns, constitution
```

### 5.4 Seed Data

- 5 agents (coordinator, worker-1, worker-2, worker-3, research-agent)
- 8 models (trinity-large, qwen3-coder, kimi-k2.5, gemma-fast, dolphin-mistral, nemotron-3, phi-4, command-r)
- 12 ISC-Bench templates (ISC-001 through ISC-012) with descriptions, expected behaviors, pass criteria
- 6 research papers across P0/P1/P2 tiers
- 1 active session budget
- 2 system config entries (governor thresholds, danger patterns)

---

## 6. STRONGEST DIFFERENTIATORS

### 6.1 What Makes NEXUS OS Unique

| # | Differentiator | Description | Public-Safe? |
|---|----------------|-------------|-------------|
| 1 | **Real LLM Test Execution** | StressLab doesn't just display data — it orchestrates real LLM calls, validates responses with domain-specific validators, and persists results. No other tab in any governance dashboard does this. | ✅ Yes |
| 2 | **5-Track Vault Memory** | The Vault implements a 5-track memory system (event, trust, capability, failure_pattern, governance) with hash-chained proof entries. Chain verification validates integrity. | ✅ Yes |
| 3 | **Governor Trust Scoring** | Per-agent trust scores with configurable lane thresholds, danger gate patterns, and appeal workflows. Real DB-backed decision logging. | ✅ Yes |
| 4 | **Multi-Provider AI Bridge** | GMR routes between 3+ LLM providers with health checking, failover, and pool-based routing (PREMIUM/MID/FAST/FREE_RESEARCH). Health checks actually ping the models. | ✅ Yes |
| 5 | **Constitution Enforcement** | Server-side constitution rules (max agents, trust thresholds, danger patterns) enforced on all mutations. Not just UI decoration. | ✅ Yes |
| 6 | **Full Audit Trail** | Every Swarm mutation (spawn/terminate/restart) creates a VaultEntry audit log. Every Governor decision is persisted. Full traceability. | ✅ Yes |
| 7 | **Rate Limit Intelligence** | Real-time rate limiter with per-provider tracking, key health monitoring, request deduplication, and caching. This isn't simulated. | ✅ Yes |
| 8 | **AI-Powered Research Queue** | Research papers with priority tiers, relevance scoring, and implementation tracking. Priority/status mutations persist to DB. | ⚠️ Partial (local overrides for some actions) |
| 9 | **Command Center UX** | ⌘K command palette, ⌘L system logs, keyboard shortcuts 1-8 for tabs, global export, responsive mobile sidebar. Professional command center aesthetic. | ✅ Yes |
| 10 | **AI Assistant with NEXUS Context** | Chat panel uses a NEXUS OS-specific system prompt, cascading fallback (Claude proxy → z-ai SDK), and quick prompts for system status queries. | ✅ Yes |

### 6.2 Key Architecture Decisions

1. **SQLite over PostgreSQL** — Zero-config, file-based, perfect for single-instance governance OS. No external DB dependency.
2. **Prisma ORM** — Type-safe DB access, migrations, relations. 10 models with full CRUD.
3. **z-ai-web-dev-sdk** — Primary LLM access. No API key management needed in the dashboard itself.
4. **Server-side constitution enforcement** — Rules aren't just UI — the API rejects violations.
5. **Optimistic local updates** — Where backend isn't available, UI shows changes immediately with "(local only)" toast.

---

## 7. PUBLIC-SAFE vs. MOCK-DEPENDENT

### 🟢 PUBLIC-SAFE (Can be demoed with confidence)

- StressLab test execution (real LLM calls + validation)
- Swarm worker management (full CRUD + audit)
- Governor decisions + trust scoring + threshold adjustment
- Vault entry browsing + chain verification
- Research paper priority/status management
- Token budget monitoring + usage logs
- Rate limit monitoring (real infrastructure data)
- AI Assistant (real LLM conversations)
- Command Palette (pure UI)
- GMR model registry + health checks
- Global data export

### 🟡 PARTIALLY PUBLIC-SAFE (Works but has hardcoded elements)

- GMR Tab (pools, rotation, failover are mock)
- Tokens Tab (optimizations, constitution limits are mock)
- Vault Tab (distribution chart, recent activity are mock)
- Research Tab (practice timer, add-to-queue are local-only)

### 🔴 MOCK-DEPENDENT (Not suitable for demo without disclaimer)

- Overview Tab (almost entirely fake — ignores real `/api/system` endpoint)
- System Logs (entirely simulated)
- Notification Center (hardcoded alerts)
- Nexus Store initial notifications

---

## 8. KNOWN ISSUES & GAPS

### Critical

| # | Issue | Impact | Fix Effort |
|---|-------|--------|-----------|
| 1 | Overview Tab ignores `/api/system` | First thing users see is fake data | Medium — wire useApiData to /api/system |
| 2 | System Logs not connected to DB | Logs are fabricated | Medium — query VaultEntry + RateLimitLog |
| 3 | GMR pool/rotation data hardcoded | Cannot show real routing decisions | High — needs backend routing state |

### Medium

| # | Issue | Impact | Fix Effort |
|---|-------|--------|-----------|
| 4 | Research practice timer resets on tab switch | No persistence | Low — use localStorage |
| 5 | Notification center is hardcoded | Not derived from real events | Medium — compute from DB events |
| 6 | AI chat messages don't persist | Lost on page reload | Low — store in DB |
| 7 | Vault distribution chart uses fallback | Doesn't reflect real data | Low — compute from trackCounts |

### Low

| # | Issue | Impact | Fix Effort |
|---|-------|--------|-----------|
| 8 | Light theme needs polish | Dark theme is primary | Medium |
| 9 | Only 12 ISC templates (target: 84) | Limited test coverage | Low — add more to seed |
| 10 | No WebSocket for all tabs | Only Swarm has real-time | High — extend WS service |

---

## 9. TECH STACK

```
Frontend:  Next.js 16.1.3, React 19, TypeScript 5, Tailwind CSS 4
UI:        shadcn/ui (New York), Lucide icons, Framer Motion, Recharts
State:     Zustand (client), useApiData hook (server, 15s auto-refresh)
Backend:   Next.js API Routes, Prisma ORM, SQLite
AI:        z-ai-web-dev-sdk, OpenRouter, Cerebras
Realtime:  Socket.IO (Swarm WebSocket on :3003)
Tools:     Command Palette (⌘K), System Logs (⌘L), Global Export
```

### File Statistics

```
TypeScript files:   107+
Total lines:        16,814+
React components:   35+
API routes:         19
DB models:          10
Python tests:       586+
```

---

## 10. SCREENSHOT INDEX

Screenshots are stored in `/download/` directory. Reference them by name — do NOT attach loose images.

| Screenshot | What It Shows | Status |
|-----------|---------------|--------|
| `qa-final-overview.png` | Overview tab with gradient cards, activity feed | 🟡 Simulated |
| `qa-stresslab.png` | StressLab templates + arena comparison | 🟢 Wired |
| `qa-gmr.png` | GMR model registry + pool cards | 🟡 Wired+Mock |
| `qa-governor.png` | Governor trust scores + decision log | 🟢 Wired |
| `qa-vault.png` | Vault entry browser + VAP chain | 🟢 Wired |
| `qa-research.png` | Research priority queues + paper dialog | 🟢 Wired |
| `qa-swarm.png` | Swarm worker grid + task queue | 🟢 Wired |
| `qa-tokens.png` | Token budget + usage heatmap | 🟢 Wired |
| `qa-r4-ai-assistant.png` | AI Assistant chat panel | 🟢 Wired |
| `qa-r4-overview-full.png` | Full overview with system health timeline | 🟡 Simulated |
| `qa-v2-mobile.png` | Mobile responsive view | ✅ Works |

---

*End of NEXUS OS v3.1 Fusion Pack*
