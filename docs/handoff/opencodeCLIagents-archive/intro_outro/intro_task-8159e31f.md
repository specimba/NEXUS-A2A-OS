# Task Intro: Implement persistent router

**Task ID**: `task-8159e31f`
**Started**: 2026-06-22T14:26:55.331040+00:00
**Last Updated**: 2026-06-22T14:26:55.331040+00:00
**Active Model**: `deepseek-v4-flash-free` (opencode)

## Goal
Memory-aware model selection with intro/outro handoff.

## Operating Constraints (NEXUS OS)
- This is a governed session. Follow prior decisions unless they are provably wrong.
- If you change a prior decision, record it in `findings` and explain why.
- Persist critical context via MemoryBus before responding.
- When done, call `mark_completed=True` and write an outro summary.