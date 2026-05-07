# Task 3: BatchHarnessDialog Complete Rewrite

## Agent: batch-harness-rewriter
## Status: COMPLETED

## Summary
Completely rewrote the `BatchHarnessDialog` component in `/home/z/my-project/src/components/nexus/tabs/stresslab-tab.tsx` from a single-request simple progress bar to a 3-phase per-template sequential execution system with scientific result analysis.

## Key Changes

### Architecture Change
- **Before**: Single `batch_harness` POST → simple progress bar → basic results
- **After**: Individual `run_test` requests with `mode='harness'` sent sequentially → real per-template progress → scientific analysis

### New Interface
```typescript
interface HarnessTemplateResult {
  templateId, templateName, templateDomain, templateDifficulty,
  status: 'pending' | 'running' | 'completed' | 'error',
  result?, durationMs?, tokensUsed?, validationScore?, collapseDetected?,
  provider?, actualModel?, stageTimings?, failedAtStage?,
  errorMessage?, outputSnippet?, vapProofHash?
}
```

### 3-Phase UI
1. **Pre-Execution**: Pipeline stage visualization, template count, 14-model selector
2. **During Execution**: Progress bar, running/pending/completed counts, elapsed timer, scrollable template list with status indicators, pipeline dots, result badges
3. **Post-Execution**: Summary stats, scientific metrics (95% CI, latency percentiles, score distribution, Cohen's d), per-domain breakdown table, failure analysis with horizontal bar chart, collapsible execution log

### Bug Fixes
- Fixed stale closure in elapsed timer (captured `now` as local variable)
- Fixed syntax error in template literal (missing parenthesis)

### Constraints Met
- Function signature unchanged
- No new imports
- No changes to other components
- ESLint passes clean
- Dialog wider: `sm:max-w-2xl max-h-[85vh]`
