# NEXUS-OS v3.1 — Project Worklog

## Current Project Status

The NEXUS-OS v3.1 dashboard is now **operational** with real data from the SQLite database. The critical `.map()` crash has been fixed, the database has been seeded with realistic data, and the dashboard renders correctly in the browser.

### Key Fixes Applied This Session

1. **Fixed "Cannot read properties of undefined (reading 'map')" crash**
   - Root cause: `overview-tab.tsx` accessed `data.pillars`, `data.healthTimeline`, `data.tokenHistory` directly, but the `/api/system` API returns these under `data.overview.*`
   - Fix: Destructured `data.overview` first, then used safe variable references
   - Also fixed `overview.avgTrust` and `overview.totalVaultEntries` to use optional chaining with fallbacks

2. **Seeded the database with realistic data**
   - 10 agents (workers, coordinators, specialists) with various statuses
   - 12 model entries (GLM-4.7, Claude-3.5-Sonnet, GPT-4o, Llama-3.1-70b, etc.)
   - 8 ISC Lab stress test templates
   - 18 test runs with mix of passed/failed/running
   - 12 governor decisions (ALLOW/DENY/HOLD)
   - 10 vault entries, 6 research papers, 25 token usage logs
   - 1 active session budget (34,582 / 100,000 used)
   - 2 system configs (constitution rules + nexus state)

3. **Added TabErrorBoundary to page.tsx**
   - Wrapped `TabContent` in `TabErrorBoundary` so tab-level errors don't crash the whole app
   - Previously, any tab error would trigger the global error boundary showing full-page error

4. **Configured supervisor.js for server stability**
   - Updated `package.json` dev script to use `supervisor.js` which auto-restarts the server
   - The sandbox aggressively kills Node.js processes; the supervisor ensures the server comes back

### Dashboard Rendering Status

- ✅ Sidebar with all 13 navigation tabs
- ✅ Header with token budget, agent count, notifications, clock
- ✅ System Overview with 4 metric cards (Agent Status, Token Budget, StressLab, Governance)
- ✅ 8 System Pillars with health percentages and progress bars
- ✅ Quick Stats floating widget
- ✅ Notification Center
- ✅ Footer with constitution rules and session info
- ✅ All data comes from real database (not mock data)

### Known Issues

1. **Server stability**: Sandbox kills Node.js processes frequently. The `supervisor.js` script auto-restarts, but there are brief downtime periods.
2. **Governor pillar shows 50%**: This is because the seed data has a mix of ALLOW and DENY decisions. The health is computed from the ALLOW ratio.
3. **Some lint errors exist** in pre-existing code (swarm-tab.tsx ref update, dashboards-tab.tsx setState in effect)
4. **Branch integration incomplete**: DASHBOARD-GLM51 branch new files were checked out, but conflicting files still need manual comparison and merge.

## Previous Session Summary

- Built NEXUS-OS v3.1 dashboard with Next.js 16.1.3 + Turbopack
- Had critical UI bugs: flashing, overflow, dark theme broken, stale/mock data
- Attempted to merge DASHBOARD-GLM51 branch (320+ files) — failed due to unrelated histories
- Switched to selective integration approach
- Fixed AI chat tab crash, dark theme patches in research tab
- Server kept dying — sandbox kills Node.js after ~15 seconds
