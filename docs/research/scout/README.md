# NEXUS Research Scout — Output Index

This folder holds dated notes from the `Zo-NEXUS-Research-Scout` automation.

## What lives here

Each run that finds something **new and NEXUS-relevant** writes one file:

```
docs/research/scout/YYYY-MM-DD-HH.md
```

If nothing new is found, no file is written and Slack stays silent. Empty days are signal, not a bug.

## File shape

Every note follows this structure so they're greppable:

```markdown
# NEXUS Research Scout — 2026-MM-DD HH:00 UTC

## Source quick-scan
- arxiv:    <N> new hits this window
- HN/Lobste.rs: <N> new threads
- GitHub trending (relevant repos): <N>

## Findings (NEXUS-relevant only)

### 1. <Title>
- Source: <url>
- Why NEXUS cares: <1–2 lines tied to specific files under src/nexus_os/>
- Suggested follow-up: <one concrete action, or "watch only">

### 2. ...

## Out-of-scope (saw, did not pursue)
- <short list, 1 line each>
```

## NEXUS-relevance filter

The scout only pursues topics that map onto current NEXUS work:

- Thermodynamic / BEC / EPR detection of hallucinations
- MCP servers, A2A protocols, agent gateways
- Adaptive circuit breakers, model routing, failover
- TrustKernel-style memory gating, vault poisoning
- Small language models (FunctionGemma class) for routing
- LLM evaluation, dataset construction for reasoning tasks

Topics outside this list go to `Out-of-scope` and are not pursued.

## Operator boundaries

- **No force-push.** All commits are fast-forward on `canonical-617`.
- **No secrets** in any note (URLs and titles only, no API keys, tokens, or pairing IDs).
- **No actions.** Scout writes notes; it does not edit code, change configs, or run services.
