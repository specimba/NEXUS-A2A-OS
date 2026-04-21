# Task 3: Fix Text Visibility and Contrast Issues

## Agent: main
## Status: COMPLETED

## Summary
Fixed all light mode text visibility and contrast issues across the NEXUS OS Command Center dashboard. The app was nearly unusable in light mode due to Tailwind `-400` color variants (designed for dark backgrounds) being used everywhere without light mode alternatives.

## Changes Made

### 1. globals.css
- Darkened `--muted-foreground` from `oklch(0.5)` to `oklch(0.42)` for better contrast
- Enhanced `.glass-card` light mode: background 90%→95%, border `oklch(0.9)`→`oklch(0.85)`

### 2. notification-center.tsx
- All typeConfig colors: `-400` → `-600` with `dark:` fallback
- All sourceColors: added `dark:` variants for 8 source types
- Bell icon, unread badge, clear button, unread dot: all fixed

### 3. system-logs.tsx
- levelColors: `-400` → `-600` with `dark:` fallback
- sourceColors: all 8 badges fixed
- Terminal/Play icon colors fixed

### 4. All 8 tab components + 10 nexus components (bulk fix)
- 200+ instances of `text-{color}-400` → `text-{color}-600 dark:text-{color}-400`
- Also fixed `hover:text-{color}-400` and opacity variants

### 5. Bug fixes found during work
- Duplicate imports in overview-tab.tsx (Tooltip, DiagnosticsPanel)
- Pre-existing lint error in gmr-tab.tsx (setState in effect)
- Parsing error in system-logs.tsx (extra brace from edit)

## Result
- Light mode is now fully usable with proper contrast
- Dark mode styling completely unchanged (preserved via `dark:` prefix)
- Lint passing (0 errors, 1 pre-existing warning)
- Dev server running cleanly (200)
