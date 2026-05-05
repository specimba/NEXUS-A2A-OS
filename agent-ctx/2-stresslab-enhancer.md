# Task 2 - StressLab Harness Detail Enhancement

## Summary
Enhanced `/home/z/my-project/src/app/api/stresslab/route.ts` to return more detailed information from the `run_test` action when `mode='harness'` and from `batch_harness`.

## Changes Made

### run_test handler (harness mode)
Added `harnessDetail` object to response with:
- `stageTimings`: Per-stage timing breakdown in ms (heartbeat, llmCall, result, governance, vault)
- `validationScore`: Numeric score (0-100) captured from `validateResponse().score`
- `provider`: Which provider was used (z-ai, groq, etc.) from `executePrompt()`
- `actualModel`: The actual model name that responded from `executePrompt()`
- `failedAtStage`: Which stage the error occurred at (null if no error)

### batch_harness handler
Added `harnessDetail` to each item in `harnessResults` array with same fields per template.

### Bug Fix
Fixed pre-existing bug where `stageDurations.process` was being double-pushed (0 then durationMs) in batch_harness. Renamed key from `process` to `llmCall` for consistency.

## Non-Breaking
- Non-harness modes return `harnessDetail: null`
- All existing response fields preserved
- ESLint clean
