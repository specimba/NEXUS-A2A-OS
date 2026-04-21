# Task: feature-export-functionality — Export/Download Functionality

## Work Log

- Reviewed existing ExportButton component (src/components/nexus/export-button.tsx) — already had CSV/JSON dropdown with download, flatten, escape utilities
- Enhanced ExportButton component:
  - Added columnHeaders prop (Record<string, string>) for custom CSV column header mapping
  - Added auto-formatting for dates (ISO strings → locale string), numbers (locale formatting), percentages (auto-detect "rate"/"percent" keys), trust scores (fixed 2-decimal)
  - Added ChevronDown icon to dropdown trigger for visual clarity
  - Exported utility functions (toCSV, downloadFile, flattenObject) for use by other components
- Added ExportButton to tabs that didn't have it:
  - overview-tab.tsx: Added ExportButton next to "System Pillars" header with systemStatusExport data and columnHeaders. Updated "Export Report" quick action button to generate actual JSON download
  - swarm-tab.tsx: Added ExportButton to Worker Status Grid header and Recent Completed table header with proper columnHeaders
- Updated existing ExportButton usages with columnHeaders:
  - stresslab-tab.tsx: Added stresslabRunsColumnHeaders
  - governor-tab.tsx: Added governorDecisionsColumnHeaders
  - tokens-tab.tsx: Added modelUsageColumnHeaders, filtered out `trend` field from export
- Created Global Export Dialog (src/components/nexus/global-export-dialog.tsx):
  - Full dashboard report: comprehensive JSON combining all 8 pillars + session + token budget + agents + governor + stresslab + gmr + vault + swarm + research stats
  - Individual tab data: export from specific tab (8 options)
  - Format selection: JSON or CSV with visual card-style toggle buttons
  - Date range selector: Current Session, Last 24h, All Time
  - Export summary preview, toast on success
- Integrated Global Export Dialog into header:
  - Added "Export" button in header toolbar (Download icon)
  - Added Ctrl+E / Cmd+E keyboard shortcut
  - Added "Export Dashboard" command to Command Palette (⌘E)
- Extended Zustand store: isExportDialogOpen, toggleExportDialog, setExportDialogOpen

## Stage Summary

- Enhanced ExportButton: custom column headers, auto-formatting, ChevronDown icon
- 2 new tabs with ExportButton: Overview, Swarm
- 3 existing tabs updated with columnHeaders: StressLab, Governor, Tokens
- Global Export Dialog: full dashboard report + individual tab, JSON/CSV, date range, toast
- Header integration: Export button + Ctrl+E + Command Palette command
- Zustand store extended
- All lint checks pass, zero errors
