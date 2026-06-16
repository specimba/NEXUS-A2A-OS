---
id: NODE-MIG-ZO_AUTOMATION_REGISTRY
authority_scope: experimental
origin_sha256: 57034b7cc749615c56090db65bc26cf72b7b80d3414d569d77766369b6171e9e
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-B15FEF
---
# Zo Automation Registry

<!-- CANARY: 87c5ad6d709d82c33338e4a8858e6170 -->
Created: 2026-05-22  
Default posture: read-only, delta-only, proposal-bound.

## Global Policy

All automations must follow these rules:

- Poll no faster than every 5 minutes.
- Post only deltas, blockers, stale data, or explicit operator-requested summaries.
- Do not run shell commands through the Zo bridge.
- Do not read `.env`, raw private research, raw DoppelGround sessions, model weights, or local archives.
- Do not mutate Git, Docker, files, Slack, Notion, or credentials without explicit approval.
- If repeated messages are detected, enter sleep mode and report once.

## Automations

| Name | Cadence | Inputs | Output | Hard Gate |
|---|---:|---|---|---|
| Zo-NEXUS-Morning-Brief | Daily | State digest, GitHub PR/checks, Slack/Notion if available | One concise brief with deltas and data gaps | No readiness claim without evidence |
| Zo-NEXUS-Heartbeat | Hourly | State digest timestamp, queue counts, PR/check status | Alert only on stale state or changed blocker | No repeated healthy pings |
| Zo-Agent-Response-Ledger | 2-4 hours | Slack thread mentions, agent replies, model/credit errors | Agent availability table | No mass-pinging |
| Zo-PR-Watcher | 2 hours | GitHub PRs, checks, deployment gates | PR status delta | Deployment failure blocks merge-ready wording |
| Zo-Research-Inbox-Triage | Daily or manual | HF/Notion/Dify/Zo links, local manifests | Proposed category list | No file moves |
| Zo-Claw-Spam-Guard | 15 minutes | Slack bot message rate, gateway evidence if exposed | Spam-risk alert with suspected source | No service stop/restart |

## Active Codex-Side Watchdogs

These are local Codex automations created on 2026-05-22 to mirror the Zo plan until Zo has a direct governed bridge.

| Automation ID | Purpose | Cadence | Mutation Policy |
|---|---|---:|---|
| `zo-nexus-heartbeat` | Stale digest, blocker, queue, dirty-state, and data-gap check | Hourly | Read-only |
| `zo-nexus-morning-brief` | Daily operator brief from canonical state and available PR/check data | Daily 08:30 | Read-only |
| `zo-nexus-pr-watcher` | PR #34/dashboard branch drift and deployment gate monitoring | 2 hours | Read-only |

2026-05-23 audit update: `zo-nexus-heartbeat`, `zo-nexus-pr-watcher`, and `nexus-whea-restart-monitor` were paused until there is an incident, active PR window, or fresh hardware instability window. Their memory logs show repeated no-change reports that are safe but token-expensive. `nexus-health-check` and `nexus-queue-runner` were downshifted from daily to Monday weekly. Keep `zo-nexus-morning-brief` as the main routine summary.

See `docs/handoff/automation-hygiene/AUTOMATION_AUDIT_2026-05-23.md`.

## Agent Roles

| Role | Responsibility | Output |
|---|---|---|
| State Scribe | Maintain current state digest and flag stale facts | Grounding note |
| PR Sentinel | Watch branch drift, PR gates, deployment failures | PR delta report |
| Research Librarian | Classify incoming research and dataset links | Proposed routing table |
| Incident Watcher | Detect Slack spam, missed replies, connector failures | Incident note |
| Bridge Auditor | Verify digest freshness and endpoint availability | Bridge health summary |

## Required Alert Shape

Every alert must include:

- timestamp,
- source,
- evidence path or URL,
- what changed,
- risk level,
- proposed next operator action.

Automations must explicitly say when a data source was unavailable rather than filling gaps from old memory.
