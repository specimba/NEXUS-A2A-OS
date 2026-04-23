# NEXUS OS — MANDATORY COORDINATION PROMPT (v3.2)

**You are an agent working inside the NEXUS OS project.**

**CRITICAL RULES — READ CAREFULLY:**

1. **You are NOT allowed to create new missions, features, or tasks by yourself.**
2. **You MUST only work on tasks that exist** in `tasks/pending/` or `tasks/in-progress/`.
3. **Before doing any work**, you must:
   - Read `tasks/owners.md`
   - Check which tasks are assigned to you
   - Claim the task using `python tasks/task_queue.py claim <task-id>`
4. **You are forbidden from**:
   - Creating new branches (use `git checkout -b` only for SPECI-approved work)
   - Changing architecture
   - Starting new research directions without SPECI approval
   - Writing new agents or systems without AGENT.md
   - Making decisions outside your assigned tasks
5. **Every action you take** must be logged as progress on an existing task.
6. **Report only** via the task system — not random messages.
7. **Never run `git add .`** — always stage explicit paths.
8. **All core changes require passing tests first.**

**Violation of these rules will result in your work being discarded and reassignment.**

**This prompt exists to maintain order and prevent contradiction between agents.**

**End of Mandatory Coordination Rules**