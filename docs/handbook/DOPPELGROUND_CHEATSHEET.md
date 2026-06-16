# DoppelGround Operator Cheat Sheet — Nexus OS

## Lane Lifecycle
- **Sterile start**: no active lanes, no pending approvals
- **OPS lane**: lock path truth / trust state / next order
- **GOV lane**: lock contract truth only
- **BLD lane**: patch one bounded surface only
- **VAL lane**: read-only audit only
- **PRM lane**: promotion / merge / carry-forward review
- **EXP lane**: scratch-only, never production authority

## Golden Rules
- One lane = one purpose
- One lane = one execution surface
- Lane ID block is authority, UI title is cosmetic
- Scratch docs are never authoritative
- Trust raw terminal output over summaries
- No substitute surface: if target file is missing, stop

## Approval Packet
Always require all 5 before approving any risky action:
1. `LANE_ID`
2. `WORKTREE / CWD`
3. exact command
4. approval scope (`once` vs `session`)
5. expected file targets

If any item is missing: reject.

## Terminal Truth Packet
Before action:
```powershell
git status --short
git branch --show-current
pwd
```
After action:
```powershell
git status --short
git diff --name-status
```

## Build-Lane Checklist
- target worktree exists
- branch exists
- canonical file exists
- patch surface is file-specific
- validate only approved files
- commit only approved files

## Codex Profiles
See `.codex/config.toml` for Production-local and Research-web profiles.

## Commits
```powershell
git status --short
git add path/to/file1 path/to/file2
git commit -m "<scoped message>"
git status --short
```
