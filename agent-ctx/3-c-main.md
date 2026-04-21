# Task 3-c: Wire Research, Tokens, Swarm tabs to real API data

## Task ID: 3-c
## Agent: main

## Work Log

### 1. Research Tab (`src/components/nexus/tabs/research-tab.tsx`)
- Added `useApiData` hook to fetch from `/api/research` with 30s auto-refresh
- Replaced all hardcoded `p0Items`, `p1Items`, `p2Items` arrays with API data mapped via `mapApiPaperToItem()`
- Mapped API fields: `externalId` → `id`, `relevanceScore` → `relevance`, `implementationTask` → `task`, `deliverable` → `deliverable`
- Derived paper status from `implementationTask` ("In progress" → `in_progress`)
- Wired "Mark as In Progress" to `PUT /api/research` with `{ paperId, updates: { implementationTask: "In progress" } }`, then calls `refetch()`
- Added priority change dropdown (Select) in paper detail dialog wired to `PUT /api/research` with `{ paperId, updates: { priorityTier: "P1" } }`, then calls `refetch()`
- Fixed "Start Practice Session" with local state tracking: `practiceSessionActive`, `practiceStep` state variables, simulated step progression with timeouts, button shows current step name while active
- Kept local papers state for "Add to Queue" dialog (papers added locally until saved)
- Added loading state with spinner while fetching
- Disabled "Mark as In Progress" button when paper is already in progress

### 2. Tokens Tab (`src/components/nexus/tabs/tokens-tab.tsx`)
- Added `useApiData` hook to fetch from `/api/tokens` with 30s auto-refresh
- Replaced hardcoded budget data with `data.budget` from API (totalBudget, usedBudget, remainingBudget)
- Replaced hardcoded `agentUsage` with computed data from `data.agentUsage` + `data.usageLogs`
- Replaced hardcoded `hourlyUsage` with useMemo aggregation from usage logs grouped by hour
- Replaced hardcoded `modelUsage` with useMemo aggregation from usage logs grouped by model
- Replaced hardcoded heatmap data with useMemo aggregation from usage logs by agent × hour
- Replaced hardcoded `budgetAlerts` with computed alerts from real budget percentages
- Added loading state with spinner
- Added empty state when no data is available (Database icon + helpful message)
- Changed "Apply Optimization" to `toast.info()` explaining what would change (cannot auto-optimize)
- Token Flow Sankey simplified to show per-model and per-agent summaries from real data
- All model costs now come from actual `cost` field in usage logs

### 3. Swarm Tab (`src/components/nexus/tabs/swarm-tab.tsx`)
- Added `useApiData` hook to fetch from `/api/swarm` with 15s auto-refresh
- Replaced hardcoded `workers` array with API data from `data.workers`, mapped to Worker interface
- Used `data.stats` for aggregate stats: totalWorkers, busyWorkers, idleWorkers, errorWorkers, offlineWorkers, totalTasks, avgTrust
- Wired "Terminate Worker" to `POST /api/swarm` with `{ action: "terminate_worker", workerId }`, then calls `refetch()`
- Wired "Reassign Task" to `POST /api/swarm` with `{ action: "reassign_task", workerId }`, then calls `refetch()`
- Wired task "Assign" button to try WebSocket first, then fallback to REST API `POST /api/swarm` with `{ action: "reassign_task", workerId, taskId }`
- Kept WebSocket hook as secondary real-time overlay (merges WS updates into API worker data)
- Added `offline` status handling (workers set to offline after terminate)
- Added `formatUptime()` utility to compute uptime from `lastActive` timestamp
- Added proper status display for all 4 states: busy, idle, error, offline
- Worker detail dialog now shows trust score, tasks done/failed from API
- Added loading state for worker grid

### 4. Quick Stats Widget (`src/components/nexus/quick-stats-widget.tsx`)
- Replaced hardcoded `tokenBudget` with data from `/api/tokens` API via `useApiData` hook
- Replaced hardcoded `activeAgents` (3/5) with computed count from `data.agentUsage` (agents with totalTokens > 0)
- Fixed `window.innerWidth` during render — replaced with `useMediaQuery('(min-width: 1024px)')` hook from `@/hooks/use-media`
- Removed the old `typeof window !== 'undefined' && window.innerWidth < 1024` check

### 5. AI Assistant (`src/components/nexus/ai-assistant.tsx`)
- Fixed double-message bug: Previously, `addChatMessage({ role: 'user', content: trimmed })` was called BEFORE the API call, which meant `useNexusStore.getState().chatMessages` already included the new user message, AND the API body also appended `{ role: 'user', content: trimmed }`, causing it to appear twice in the conversation sent to the API
- Fix: Capture `currentMessages` from the store BEFORE adding the user message, then use `currentMessages + user message` in the API call
- The store update still happens (addChatMessage), but the API now gets the correct message list without duplication

## Build Verification
- `bun run lint` passes with zero errors
- `npx next build` succeeds with all pages generated

## Stage Summary
- 5 components updated with real API data integration
- Research: API data + Mark In Progress + Priority Change + Practice Session state
- Tokens: API budget + logs + computed charts/heatmap + empty state + optimization feedback
- Swarm: API workers/stats + Terminate + Reassign via REST API + offline status + WS overlay
- Quick Stats: API token data + useMediaQuery fix
- AI Assistant: Double-message bug fix
