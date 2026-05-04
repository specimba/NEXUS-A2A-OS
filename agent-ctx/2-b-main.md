# Task 2-b — Bug Fixes Work Record

## Agent: main
## Task: Fix 3 critical UI bugs

## Summary of Changes

### Bug 1: System Diagnostic modal can't be closed on mobile
- **File**: `src/components/nexus/tabs/overview-tab.tsx`
- **Change**: Removed `max-h-[85vh] overflow-y-auto` from `DialogContent` (line 1933)
- **Change**: Added `max-h-[70vh] overflow-y-auto` to inner `<div>` (line 1950)
- **Change**: Added explicit X close button in DialogTitle with `sr-only` label
- **Root cause**: DialogContent with max-h/overflow-y-auto intercepts touch events on mobile, preventing overlay tap-to-close and making the built-in Radix close button unreachable

### Bug 2: Number keys trigger shortcuts in input fields
- **File**: `src/components/nexus/command-palette.tsx`
- **Change**: Added `target.closest('input, textarea, select, [contenteditable]')` check (catches child elements)
- **Change**: Added `target.closest('[role="dialog"]')` check (skips all shortcuts in modals)
- **Change**: Added `target.closest('[cmdk-input]')` check (Radix Command input)
- **Root cause**: Original check only tested `target.tagName` directly, missing cases where the event target is a child of an input-like element (e.g., spans inside contentEditable, Radix cmdk wrappers)

### Bug 3: Duplicate key T-312 in swarm-tab.tsx
- **File**: `src/components/nexus/tabs/swarm-tab.tsx`
- **Verified**: Line 2211 already uses `key={`${r.id}-${i}`}` — correct fix
- **Extended**: Line 932 — `key={t.id}` → `key={`${t.id}-${i}`}` (task priority dialog)
- **Extended**: Line 2157 — `key={t.id}` → `key={`${t.id}-${i}`}` (task queue list)

## Verification
- `bun run lint` — zero errors
- Dev server running cleanly on port 3000
