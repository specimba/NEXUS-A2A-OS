# Task ID: 2 — API Route Fixes & New Endpoints

## Agent: api-builder

## Task: Fix existing API routes to return correct formats and add missing POST/PUT endpoints

### Work Completed

1. **Fixed `/api/models/route.ts`**
   - Changed GET response from flat array to `{ models: ModelData[] }` format
   - Added POST endpoint with two actions:
     - `toggle`: flips the `isActive` field on a model
     - `health_check`: updates `lastChecked` timestamp
   - Proper validation: checks modelId exists, model exists in DB, valid action

2. **Added POST to `/api/stresslab/route.ts`**
   - Accepts `{ action: "run_test", templateId, modelName, mode }`
   - Validates required fields and valid modes (single, icl, agentic)
   - Verifies template exists in DB
   - Finds available idle agent (highest trust score) for the test
   - Creates TestRun in DB with status "pending"
   - Returns 201 with created testRun including relations

3. **Added POST to `/api/governor/route.ts`**
   - Three actions supported:
     - `appeal`: creates GovernorDecision with decision "HOLD", requires agentId
     - `update_threshold`: upserts SystemConfig key "governor_thresholds" with JSON thresholds
     - `add_pattern`: appends to SystemConfig key "danger_patterns" JSON array
   - Proper validation and 404 checks for agents

4. **Added POST to `/api/vault/route.ts`**
   - Accepts `{ action: "verify_chain" }`
   - Queries all vault entries in chronological order
   - Performs comprehensive chain verification:
     - Checks entries exist
     - Validates agent references, tracks, keys
     - Validates JSON values
     - Checks chronological ordering
     - Validates score ranges [0, 1]
   - Returns `{ valid, entryCount, issues }` 

5. **Added PUT to `/api/research/route.ts`**
   - Accepts `{ paperId, updates: { priorityTier?, isVetted?, implementationTask? } }`
   - Validates paper exists, validates priorityTier values (P0, P1, P2)
   - Only updates allowed fields (whitelist approach)
   - Returns updated paper

6. **Added POST to `/api/tokens/route.ts`**
   - Accepts `{ action: "log_usage", agentId?, model, promptTokens, completionTokens, cost?, apiEndpoint? }`
   - Creates TokenUsageLog entry with computed totalTokens
   - Updates active SessionBudget (usedBudget + remainingBudget)
   - Updates agent's totalTokens and lastActive if agentId provided
   - Returns 201 with created usageLog

7. **Created `/api/swarm/route.ts`**
   - GET: Returns agents formatted as swarm workers with computed stats
     - Workers include: id, name, type, status, domain, trustScore, totalTokens, tasksDone, tasksFailed, lastActive, recentActivity
     - Stats: totalWorkers, busyWorkers, idleWorkers, errorWorkers, offlineWorkers, totalTasks, avgTrust
   - POST: Two actions:
     - `reassign_task`: sets worker to busy, optionally changes domain
     - `terminate_worker`: sets worker to offline
   - Proper validation, 404 checks, error handling

### Design Decisions
- All routes use `import { db } from '@/lib/db'` for Prisma access
- All routes use try/catch with `NextResponse.json({ error: String(error) }, { status: 500 })`
- Consistent error response format: `{ error: string }`
- Input validation before DB operations (400 for bad input, 404 for missing entities)
- Action-based POST/PUT pattern for multi-operation endpoints
- Whitelist approach for update fields (only allowed fields can be modified)
- Preserved all existing GET functionality in modified routes

### Lint Status
- `bun run lint` passes with zero errors
