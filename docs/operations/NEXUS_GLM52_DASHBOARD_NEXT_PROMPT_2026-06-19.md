# NEXUS GLM-5.2 Dashboard Continuation Prompt

Date: 2026-06-19

Use this as the next instruction for the Z.ai GLM-5.2 dashboard workspace.

## Grounded Status

Local Codex verification found a split between the Z.ai sandbox claims and the current NEXUS checkout.

- The Z.ai log claims v0.12-v0.14 are complete: GLM-5.2 echo-label fix, PanelStatus badges, all governance tab headers using real Brain API polling, 110 tests passing, and Brain API live on 7352.
- The current local NEXUS checkout does not yet contain those v0.12-v0.14 fixes. Local search still finds `completion.model || ...` in StressLab, Vault, and Research routes, and no `PanelStatus` or `usePanelStatus` implementation is present.
- The port-ruleset work is partially grounded locally: `tests/bridge/test_port_registry.py` and `tests/nexus_cli_ctl/test_dashboard_sync.py` pass locally, 41/41.
- Local Brain API imports with 53 routes, but prior sink checks show `/api/stress/report` has route presence without reliable worklog/ARCHIVIST sink integration.
- Browser interaction with the Z.ai chat is authenticated but unstable from Codex Chrome control: shell loads, then DOM/screenshot commands can hang. Treat browser-visible claims as advisory unless they are mirrored into code, tests, or a downloadable patch/diff.

## Required Next Slice

Do not continue greenfield UI polish yet. First reconcile the Z.ai sandbox improvements into the real NEXUS checkout through a reviewable patch plan.

### Task 1: Produce A Patch Manifest

Create a file-level manifest for v0.12-v0.14 with exact changed files, exact symbols, and test names:

- GLM echo fix:
  - `src/lib/ai-provider-bridge.ts`
  - `src/app/api/stresslab/route.ts`
  - `src/app/api/ai/stresslab/run/route.ts`
  - `src/app/api/ai/vault/query/route.ts`
  - `src/app/api/ai/research/search/route.ts`
  - `src/app/api/ai/research/analyze/route.ts`
- Status UI:
  - `PanelStatus` component
  - `usePanelStatus` hook
  - governor, vault, overview, provider, modelrelay, and tasks tab header integrations
  - aggregate Brain API status route used by the hook

For each file, include the before/after intent and a rollback tag or commit hash from the Z.ai sandbox.

### Task 2: Export Minimal Diff, Not A Whole Archive

Provide the minimal unified diff for the v0.12-v0.14 changes only. Do not include generated assets, screenshots, caches, node_modules, database files, credentials, or unrelated dashboard experiments.

If a direct diff export is impossible, output exact patch blocks per file with enough context for Codex to apply manually.

### Task 3: Fix GLM Echo Semantics Correctly

Do not hardcode fake success globally. The rule should be:

- Preserve `requestedModel`, `provider`, and `providerResponseModel` separately.
- Display `actualModel` as the requested canonical route only when provider is `z-ai` and requested model is GLM-5.x and the response echo is the known legacy alias `glm-4-plus`.
- Keep the raw echoed model in diagnostics as `providerResponseModel`.
- Add tests proving the UI displays `glm-5.2` while diagnostics preserve the provider echo.

### Task 4: Honest Status UI

Panel badges must be driven by real status data only:

- `LIVE` only if the panel's backing endpoint returns a successful response and the payload is non-mock.
- `DEGRADED` if the endpoint responds but a backing sink is missing, mocked, stale, or partially unavailable.
- `OFFLINE` if the endpoint is unreachable.
- Never show green for a hardcoded/default object.

The overview card should report live/degraded/offline counts from the same aggregate source as the tab badges.

### Task 5: Verify Against Current NEXUS, Not Only Sandbox

Run or provide commands for these exact checks:

```powershell
python -m pytest tests/bridge/test_port_registry.py tests/nexus_cli_ctl/test_dashboard_sync.py -q --tb=short
rg -n "completion\\.model \\|\\||actualModel: completion\\.model|glm-4-plus|PanelStatus|usePanelStatus" src tests
bunx tsc --noEmit
```

If the sandbox cannot run local NEXUS tests, mark the result `ADVISORY_PATCH_READY`, not `COMPLETE`.

## Output Contract

Return exactly:

1. `PATCH_MANIFEST`
2. `MINIMAL_DIFF_OR_PATCH_BLOCKS`
3. `TEST_PLAN_AND_RESULTS`
4. `KNOWN_GAPS`
5. `NEXT_RECOMMENDED_SLICE`

No screenshots as evidence unless paired with code and tests. No broad claims like "fully honest" unless the current NEXUS checkout has the patch and tests passing.

