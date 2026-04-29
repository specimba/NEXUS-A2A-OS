# Task 3: Paper Pipeline Builder — Work Record

## Task
Build automated paper analysis pipeline API at `/api/research/analyze`

## Produced Artifacts
- `src/app/api/research/analyze/route.ts` — Full API route with GET, POST, PUT handlers

## Key Decisions
1. **relevanceScore computation**: `ClassificationResult` interface doesn't include `relevanceScore` (it's computed in `classifyPaper` but not in the type). Fixed by computing locally as `dgFinalScore / 15` instead of accessing from the classification object.
2. **Pipeline stage classification**: Determined by DB state — `classifyStage()` checks `isVetted`, `implementationTask`, `admissionTier`, `researchRole`, `dgFinalScore` to classify a paper's current stage.
3. **Never use HOLD in DB**: Priority tier "HOLD" is mapped to "P2" for database storage (matching the arxiv route pattern).
4. **P0/P1 task enrichment**: P0 papers get `[URGENT]` prefix + concept details; P1 papers get concept details appended.
5. **Delivery guardrails**: Papers need `implementationTask !== 'Pending review'` AND `dgFinalScore >= 3` to be delivered.

## API Endpoints Summary
- **GET /api/research/analyze** — Pipeline status with stage counts, distributions, throughput metrics, bottleneck analysis
- **POST /api/research/analyze** — Run pipeline stages with `{ stage?, paperIds?, dryRun? }`
- **PUT /api/research/analyze** — Re-analyze single paper with `{ paperId, force? }`

## Verification
- `bun run lint` — zero errors
- `npx tsc --noEmit` — zero errors in the new file (pre-existing errors in other files are unrelated)
