# Task 5+6+7 — research-fix-agent

## Summary
Fixed 3 issues in the NEXUS OS Command Center:

### Issue 1: Daily Practice Timer Persistence
- Added timer state to Zustand store (`timerStartedAt`, `timerIsRunning`, `timerDuration`, `timerElapsedOnPause`)
- Timer computes elapsed from `timerStartedAt` so it persists across tab switches
- Files: `src/store/nexus-store.ts`, `src/components/nexus/tabs/research-tab.tsx`

### Issue 2: Alphaxiv API Fix
- Removed restrictive `include_domains: ["alphaxiv.org"]` from Tavily requests
- Changed query from `site:alphaxiv.org ${query}` to `alphaxiv AI research paper ${query}`
- Added fallback chain: Tavily → broader Tavily query → Jina AI → broader Jina query
- Files: `src/app/api/alphaxiv/route.ts`

### Issue 3: Rate Limit Preview Mode
- Added preview data constants when `summary.totalRequests === 0`
- Shows "Preview Mode — No live data yet" yellow banner
- Real data automatically replaces preview when API requests are made
- Files: `src/components/nexus/tabs/rate-limit-tab.tsx`

All lint checks pass. Dev server clean.

