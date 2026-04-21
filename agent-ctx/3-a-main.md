# Task 3-a: Wire GMR Router and StressLab tabs to real API data

## Summary
Successfully wired both the GMR Router tab and StressLab tab to real API data, replacing all hardcoded static data with live API calls that read from and write to the SQLite database via Prisma.

## Changes Made

### GMR Tab (`src/components/nexus/tabs/gmr-tab.tsx`)
1. **Model toggle → API**: `POST /api/models { action: "toggle", modelId }` with optimistic update + rollback on failure
2. **Refresh Models button**: Added next to Reset to Default, calls `refetch()`
3. **Health Check button**: Iterates all models, calls `POST /api/models { action: "health_check", modelId }` for each
4. **Dynamic sparklines**: Replaced hardcoded `modelSparklines` with `getModelSparklines(models)` that generates data from real model health values
5. **Dynamic performance chart**: `ModelPerformanceComparison` now uses real model data (health, successRate, latency score computed from latencyMs)
6. **Reset button**: Now also calls `refetch()` after clearing overrides

### StressLab Tab (`src/components/nexus/tabs/stresslab-tab.tsx`)
1. **API data fetching**: `useApiData<StressLabData>('/api/stresslab', 15000)` with 15s auto-refresh
2. **Type-safe mapping**: Added `ApiTemplate`, `ApiTestRun`, `StressLabData`, `UITemplate`, `UIRun` interfaces + `mapTemplate()`, `mapRun()`, `formatTimeAgo()` helpers
3. **Dynamic templates**: Replaced hardcoded array with `apiData.templates.map(mapTemplate)`, fallback to static data when empty
4. **Dynamic runs**: Replaced hardcoded `recentRuns` with `apiData.runs.map(mapRun)`
5. **Real test creation**: RunTestDialog calls `POST /api/stresslab { action: "run_test", templateId, modelName, mode }`, progress stalls at 90% until API responds
6. **Real batch run**: BatchRunDialog calls API for each selected template sequentially
7. **Clipboard export**: CompareModelsDialog "Export Comparison" button now calls `navigator.clipboard.writeText()`
8. **Dynamic stats**: testCount, collapseCount, collapseRate, passCount all computed from real run data
9. **Dynamic charts**: TestResultsSummaryChart, DomainCoverageSection, DifficultyPieChart, RunHistoryCard all accept real data as props

## API Format Used
- `GET /api/models` → `{ models: ModelData[] }`
- `POST /api/models` → `{ action: "toggle", modelId }` or `{ action: "health_check", modelId }`
- `GET /api/stresslab` → `{ templates: ApiTemplate[], runs: ApiTestRun[] }`
- `POST /api/stresslab` → `{ action: "run_test", templateId, modelName, mode }`

## Verification
- `bun run lint` — zero errors
- `npx next build` — successful build
