# Grok 4.3 Beta — File-Based Coordination Protocol

**Date**: 2026-05-27  
**Status**: ACTIVE — legitimate developer beta testing  
**Barrier**: Grok sandbox has zero outbound TCP/HTTPS, DNS resolves only

## Connection Model

Grok's sandbox and Zo cannot reach each other over the network. Coordination is **file-based**, mediated by the operator (speci) who moves files between environments.

## File Protocol

### Zo → Grok (Directives)

1. Zo writes directive to `grok-coordination/directives/grok_directive_{timestamp}.md`
2. Operator exports the directive file
3. Operator pastes the directive content into Grok's chat interface
4. Grok reads the directive and executes the experiment

### Grok → Zo (Results)

1. Grok writes experiment results to a markdown file in its sandbox (`artifacts/experiment_{id}.md`)
2. Operator exports the result file from Grok's sandbox
3. Operator places the result file in `grok-coordination/ingest/`
4. Zo's `Zo-NEXUS-Progression-Tracker` automation reads the ingest directory on its next run (06:00 + 18:00 UTC+3) and incorporates findings into `docs/progression/`

## Directive Format

```markdown
# Directive: {topic}
- id: gd-{timestamp}
- target_model: grok-4.3-beta
- task: {description}
- output_format: {json, markdown, plaintext}
- response_required: {true, false}
- security_level: {open, confidential}

## Task
{detailed instructions}

## Context (from NEXUS)
{relevant background}

## Expected Output
{schema or description}
```

## Result Format

```markdown
# Result: {directive_id}
- experiment_id: exp-{timestamp}
- model: grok-4.3-beta
- success: {true, false, partial}
- findings_count: {N}
- security_notes: {any boundary observations}

## Execution
{what was done}

## Findings
1. {finding}
2. {finding}

## NEXUS Impact
{how this affects NEXUS hardening}
```

## Current Queue

| ID | Directive | Status | Assigned |
|----|-----------|--------|----------|
| gd-20260527-001 | HAICOSYSTEM sandbox scenario extraction | pending | — |
| gd-20260527-002 | REDBENCH benchmark integration test | pending | — |
| gd-20260527-003 | TAMAS multi-agent attack reproduction | pending | — |
