# Task 2-a: Wire Swarm Tab to Real API Calls

## Summary
Wired all Swarm tab buttons to real API calls with rate-limit awareness, added new dialogs (Spawn Worker, Reassign Task), added Restart Worker and Trust Adjustment features, and improved visual styling.

## Changes Made
- **File**: `src/components/nexus/tabs/swarm-tab.tsx` — Complete rewrite with:
  - `callSwarmApi()` shared helper with 429 rate-limit detection and network error handling
  - `SpawnWorkerDialog` — name/type/domain form calling `spawn_worker`
  - `ReassignTaskDialog` — newDomain/newTask form calling `reassign_task`
  - `WorkerDetailDialog` — enhanced with Restart Worker button, Trust Adjustment panel (+/- 0.05)
  - All 5 API actions wired: reassign_task, terminate_worker, restart_worker, spawn_worker, update_trust
  - Per-button loading states via `actionLoading` state
  - `refetch()` called after every successful API response
  - Optimistic trust score update on selectedWorker
  - Visual improvements: pulse rings, gradient accents, shimmer, trust bars, hover effects

## API Endpoint
- `POST /api/swarm` — already implemented with all 5 actions (confirmed working with curl tests)

## Lint Status
- All lint checks pass (zero errors)
- Dev server running cleanly on port 3000
