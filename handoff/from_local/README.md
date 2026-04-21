# Handoff Directory — From Local Agent

This directory contains results from the Local Execution Agent.

## Protocol (GVAW)

1. Local Agent writes result files here after completing tasks
2. Cloud Orchestrator reads and synthesizes results
3. Results may include: Model Arena outcomes, TWAVE health checks, provenance scans

## Result File Format

```markdown
# Result: [Task Title]

## Status
[COMPLETED / PARTIAL / FAILED]

## Findings
[Key results]

## Evidence
[Hashes, logs, metrics]

## Next Steps
[Recommended follow-up actions]
```

## Current Results

No results yet. Awaiting Local Agent completion.
