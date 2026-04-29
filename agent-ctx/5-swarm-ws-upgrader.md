# Task 5: Connect Swarm WebSocket to Real DB State

## Agent: swarm-ws-upgrader
## Status: COMPLETED

## Summary
Rewrote the Swarm WebSocket mini-service to connect to real database state via the main Next.js app's API endpoints, replacing purely synthetic data generation with real data when available, while preserving synthetic fallback.

## Files Modified
- `/home/z/my-project/mini-services/swarm-ws/index.ts` — Complete rewrite (242 → 420+ lines)

## Changes Made

### 1. API Integration Layer
- Added `API_BASE = 'http://localhost:3000/api'` constant
- Created `safeFetch<T>()` helper with:
  - AbortController with 5s timeout
  - Error handling that sets `usingSyntheticFallback` flag
  - Automatic recovery detection (logs when switching back to real data)
  - Generic type parameter for response typing

### 2. Real Worker State (GET /api/swarm)
- `fetchSwarmState()` polls every 3 seconds
- Caches `cachedWorkers[]` and `cachedStats`
- Emits `swarm:worker-update` for workers whose status changed or are busy
- On client connect: emits initial state for all cached workers + current metrics
- `previousWorkerStatuses` tracking to avoid redundant emits

### 3. Real Task Assignment (POST /api/swarm)
- `swarm:assign-task` handler now calls `reassignTaskViaApi()`
- On success: emits real worker update from API response
- On failure: falls back to synthetic confirmation

### 4. Real Metrics (computed from agent data)
- `buildMetricsFromReal(workers, stats)`:
  - throughput = tasksDone / 10 (tasks per minute estimate)
  - successRate = tasksDone / (tasksDone + tasksFailed)
  - utilization = busyWorkers / totalWorkers
  - avgDuration = estimated from avgTrust (higher trust → faster)
  - totalTokens = sum of all agent totalTokens

### 5. Vault Activity Feed (GET /api/vault)
- Polls every 5 seconds
- Tracks `lastSeenVaultEntryId` and `lastVaultPollTime`
- Maps vault tracks to activity types: FAIL→error, GOV→info, TRUST→success, CAP→warning, EVENT→info
- Maps vault tracks to sources: FAIL→Engine, GOV→Governor, TRUST→Vault, CAP→Swarm, EVENT→Monitor
- Builds descriptive messages from vault entry category + key + parsed JSON value
- Emits new entries in chronological order

### 6. Synthetic Fallback
- All original synthetic generators preserved unchanged
- `usingSyntheticFallback` flag controls when synthetic events are emitted
- Metrics timer only emits synthetic metrics when in fallback mode
- Activity timer only emits synthetic activities when in fallback mode
- Task completion blends real worker data with synthetic when real workers exist

## Verification
- Service starts on port 3003 with `bun index.ts`
- Loads 5 real workers on startup: "✅ Loaded 5 real workers from DB"
- API polls visible in dev.log: `GET /api/swarm 200`, `GET /api/vault 200`
- No new dependencies needed (Bun built-in fetch)
- Frontend event format fully compatible (all event names and payload shapes unchanged)
