# NEXUS Progression Tracker — Output Index

This folder holds dated deltas from the `Zo-NEXUS-Progression-Tracker` automation.

## What lives here

Each run writes one file:

```
docs/progression/YYYY-MM-DD-HH.md
```

Even when nothing changed — that's a useful signal too. Empty windows still get a one-line entry.

## File shape

```markdown
# NEXUS Progression — 2026-MM-DD HH:00 UTC

## Δ since last run
- HEAD:  <short-sha> "<subject>" (was <short-sha>)
- Files touched: <N>
- Commits in window: <N>

## What advanced
- <one bullet per merged or pushed change, tied to its commit sha>

## What's documented as next
(Pulled from AGENTS.md / 01_PROJECT_STATE.md "next" sections)
- <bullet>

## What's blocked
(Pulled from open worklogs under docs/handoff/zo-coordination/worklogs/)
- <bullet with blocker name + path to evidence>

## One-line forecast
<single line: what the next 12 hours probably needs>
```

## Cadence

Twice daily — 06:00 and 18:00 Istanbul time. Two runs per day = enough signal without noise.

## Operator boundaries

- **Read-only on the live system.** No file edits outside `docs/progression/`.
- **Fast-forward push only.** No force-push, no branch rewrites.
- **No service restarts**, no `paired.json` edits, no `telegram-claw-gateway` re-enable.
- **No tokens** in any note.
