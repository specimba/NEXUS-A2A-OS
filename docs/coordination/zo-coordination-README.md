---
id: NODE-MIG-ZO_COORDINATION_README
authority_scope: experimental
origin_sha256: 37f7a84aec642897a215177269778b26014ced2dc0e88b2ca5333193c1e2e7b9
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-8A8669
---
# Zo Always-On NEXUS Coordination

<!-- CANARY: 7d592127052ff7d2e720a2288b23acbc -->
Created: 2026-05-22  
Scope: read-only Zo grounding, routine checks, and proposal-bound coordination.

## Role Split

Zo is the cloud watchtower. It reads state, detects drift, summarizes deltas, and routes work. It must not execute local infrastructure changes without explicit operator approval.

Local NEXUS is the execution authority. Docker, secrets, TWAVE, ModelRelay, local tests, commits, private research, and raw evidence stay on the Windows/NEXUS side.

## Current Grounding

Zo must treat these local files as canonical before using chat memories or external reports:

- `01_PROJECT_STATE.md`
- `knowledge.md`
- `worklog.md`
- `docs/handoff/zo-coordination/NEXUS_STATE_DIGEST.json`

Historical Zo facts such as `canonical-617`, `642 passed`, or prior force-push summaries are evidence only. They are superseded unless revalidated against the current NEXUS checkout.

## Non-Negotiable Boundaries

- No `.env` or secret material in public repos, Slack, Notion, Zo chats, or handoff packets.
- No raw DoppelGround sessions, private research dumps, model weights, or confidential DERDDRE/red-team files in public-facing output.
- No direct merge, force-push, service restart, process kill, credential rotation, or file movement without explicit approval.
- No repeated `check` messages or high-frequency gateway polling.
- If a file or research artifact cannot be classified confidently, route it to `MIXED` for operator review.

## Read-Only State Bridge

Use `scripts/zo_nexus_state_bridge.py` to generate a sanitized state digest and optionally serve it over a narrow localhost bridge.

Generate a digest:

```powershell
python scripts/zo_nexus_state_bridge.py snapshot --output docs/handoff/zo-coordination/NEXUS_STATE_DIGEST.json
```

Serve the digest locally:

```powershell
$env:ZO_NEXUS_BRIDGE_TOKEN = "<operator-generated-token>"
python scripts/zo_nexus_state_bridge.py serve --snapshot docs/handoff/zo-coordination/NEXUS_STATE_DIGEST.json --host 127.0.0.1 --port 9191
```

Allowed endpoints:

- `/state`
- `/git`
- `/queue`
- `/nexusctl`
- `/ports`
- `/docker`
- `/handoff`

The server serves the existing snapshot only. It does not expose arbitrary file reads, `.env`, shell execution, mutation endpoints, or live Docker control.

## Zo Routine Rules

Zo should run as a quiet coordinator:

- Morning brief: daily, delta-only, with explicit data gaps.
- Heartbeat: hourly, alert only on stale state or changed blockers.
- PR watcher: every 2 hours, deployment/security gates override mergeable status.
- Agent response ledger: every 2-4 hours, track blocked/unreachable agents without mass-pinging.
- Research triage: classify links/files into proposed buckets, do not move them.
- Claw spam guard: detect repeated bot messages, report once, do not stop services without approval.

## Acceptance Gate

Zo is considered grounded when it can state:

- active branch and HEAD from the latest digest,
- latest verified test baseline,
- open PR/deployment status if present in the digest,
- critical blockers from `01_PROJECT_STATE.md`,
- which information is stale or unavailable.

Zo is not considered execution-ready until TrustKernel approval paths, dedupe, rate limits, and audit logging are proven stable.
