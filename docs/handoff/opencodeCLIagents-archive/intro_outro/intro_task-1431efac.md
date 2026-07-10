# Task Intro: Implement persistent model router

**Task ID**: `task-1431efac`
**Started**: 2026-06-22T14:33:09.785956+00:00
**Last Updated**: 2026-06-22T14:33:09.785956+00:00
**Active Model**: `nim/z-ai/glm-5.1` (nvidia)

## Goal
Memory-aware model selection with intro/outro handoff for NEXUS Model Relay.

## Operating Constraints (NEXUS OS)
- This is a governed session. Follow prior decisions unless they are provably wrong.
- If you change a prior decision, record it in `findings` and explain why.
- Persist critical context via MemoryBus before responding.
- When done, call `mark_completed=True` and write an outro summary.