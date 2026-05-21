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

### UI/UX Grounding Point (2026-04-18)

Created a comprehensive disaster recovery snapshot for the current good UI/UX state:

1. **Created `GROUNDING.md`** — Comprehensive UI/UX grounding document covering:
   - Architecture overview (Next.js 16 + React 19 + Zustand + SWR + Framer Motion)
   - Complete color scheme in oklch (dark theme CSS variables)
   - NEXUS custom colors (emerald accent system)
   - Full component file structure (shell, tabs, features, MCP, dashboards, UI primitives)
   - Sidebar design with all 13 navigation items and active state styles
   - Header design with all elements and system config dialog
   - Footer design with pool status, errors, rate limits, uptime
   - AI Assistant design (floating button, SSE streaming, model selector, localStorage persistence)
   - Zustand state management structure
   - Key design pattern code snippets (cards, badges, status dots, progress bars, ping dots)
   - All CSS animation classes documented
   - API routes reference
   - Keyboard shortcuts reference
   - Responsive design breakpoints
   - Recovery instructions
   - Dependency versions

2. **Git tag `grounding-uiux-v3.1`** — Annotated tag pushed to remote
   - Commit: `feat: NEXUS-OS v3.1 UI/UX grounding point - working dashboard with real data`
   - Pushed to `origin/grounding-uiux-v3.1` on GitHub

3. **Created `scripts/backup-ui-snapshot.sh`** — Backup script that:
   - Archives 159 key UI files (components, styles, config, store, hooks, lib)
   - Saves as `backups/ui-snapshot-YYYYMMDD-HHMMSS.tar.gz`
   - Generates SHA-256 manifest for all included files
   - Tested successfully: 448K archive created

4. **Tested backup script** — Confirmed working:
   - Archive: `backups/ui-snapshot-20260521-231132.tar.gz` (448K)
   - Manifest: `backups/MANIFEST-20260521-231132.txt`

### Recovery Procedure
- `git checkout grounding-uiux-v3.1` — full restore to grounding point
- `git diff grounding-uiux-v3.1 -- <file>` — compare specific files
- `bash scripts/backup-ui-snapshot.sh` — create new timestamped snapshot
- `tar -xzf backups/ui-snapshot-*.tar.gz -C /path/to/project` — restore from archive

## Previous Session Summary

- Built NEXUS-OS v3.1 dashboard with Next.js 16.1.3 + Turbopack
- Had critical UI bugs: flashing, overflow, dark theme broken, stale/mock data
- Attempted to merge DASHBOARD-GLM51 branch (320+ files) — failed due to unrelated histories
- Switched to selective integration approach
- Fixed AI chat tab crash, dark theme patches in research tab
- Server kept dying — sandbox kills Node.js after ~15 seconds
