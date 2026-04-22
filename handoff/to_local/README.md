# Handoff Directory — To Local Agent

This directory contains task files for the Local Execution Agent.

## Protocol (GVAW)

1. Cloud Orchestrator writes `.task.md` files here
2. Local Agent reads, executes, and writes results to `../from_local/`
3. Cloud Agent reviews results and synthesizes

## Task File Format

```markdown
# Task: [Title]

## Description
[What needs to be done]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Deadline
[When this should be completed]

## Priority
[CRITICAL / HIGH / MEDIUM / LOW]

## Notes
[Any additional context]
```

## Current Tasks

No tasks pending. Awaiting Cloud Orchestrator assignment.
