# Grok-Swarm Coordination Layer

**Purpose**: give Grok 4.3 (running in an ephemeral sandbox with short bursts) a durable, external **memory + task queue + heartbeat + quality-gate** that lives on Zo's persistent filesystem and is reachable over HTTPS.

Created: 2026-05-27  
Status: Phase 1 — file-backed queue + 3 HTTP routes. Real MCP tool routing comes in Phase 2.

---

## The problem this solves

| Grok sandbox limit | Effect |
|---|---|
| Short bursts (sessions reset frequently) | Loses context, restarts from scratch |
| Ephemeral storage (`/home/workdir/artifacts/`) | Wiped between sessions |
| No external coordinator | Cannot pull next task when idle |
| Stub `SwarmClawClient` in their `persistent_grok_agent.py` | Imports `swarm_claw_client` which doesn't exist; script crashes on import |
| MCP server they built is stdio-only | Cannot be reached from outside the Grok sandbox |

## What Zo provides

Zo's `/home/workspace/` is persistent across container restarts. zo.space runs continuously. We make Zo the **memory home** and **meta-controller** so Grok can be stateless and just hit our endpoints.

---

## Architecture

```
Grok sandbox (ephemeral)                       Zo (persistent)
─────────────────────────                      ───────────────
persistent_grok_agent.py                       /home/workspace/docs/grok-coordination/
       │                                       ├── queue/
       │   import nexus_swarm_client               ├── pending/   <- next tasks to run
       │                                           ├── claimed/   <- currently being worked on
       │   ┌─────────────────────┐                 ├── done/      <- completed results
       └───>  NexusSwarmClient   ├──HTTPS─────>    └── failed/    <- stalled / failed
           │  (bearer-token gated)│                ├── progress/  <- Grok's checkpoints
           └─────────────────────┘                 ├── synthesis/ <- quality-gate outputs
                    │                              ├── heartbeats/<- liveness pings
                    │                              └── clients/   <- drop-in Python client
                    │
                    └── POST /api/grok-swarm/report
                        GET  /api/grok-swarm/queue/next
                        POST /api/grok-swarm/heartbeat
                        GET  /api/grok-swarm/status
                        POST /api/grok-swarm/queue/add  (operator only)
```

**Authority split** (mirrors NEXUS principle "Skills = Policy, MCP = Execution"):
- **Zo (us)** = durable memory + queue + coordinator. We never run Grok's work.
- **Grok (them)** = stateless burst worker. Pulls task, runs it, reports back. We never see their model weights or API keys.
- **Operator (speci)** = task source. Adds tasks to `queue/pending/` either via UI, file commit, or `POST /queue/add`.

---

## File-backed storage shape

Every artifact is a single JSON file. Filenames are sortable. No DB.

### `queue/pending/<task-id>.json`
```json
{
  "id": "task-2026-05-27-001",
  "created_at": "2026-05-27T01:00:00Z",
  "priority": 5,
  "kind": "research|synthesis|review",
  "prompt": "...",
  "context_files": ["docs/research/scout/2026-05-25-09.md"],
  "deadline_iso": null,
  "max_cycles": 4
}
```

### `queue/claimed/<task-id>.json`
Same shape as `pending`, plus:
```json
{
  "claimed_by": "grok-sandbox-abc123",
  "claimed_at": "2026-05-27T01:05:00Z",
  "lease_expires_at": "2026-05-27T02:05:00Z"
}
```
A claim **expires after 1 hour**. If Grok doesn't `done` or `progress` within the lease, the task moves back to `pending` for re-pickup (anti-stuck).

### `queue/done/<task-id>.json`
Final result, references `progress/` entries.

### `progress/<run-id>/<cycle-NNN>.json`
One file per cycle so we never lose work.

### `heartbeats/<sandbox-id>.json`
Replaced on every ping. Stale (>10 min) means Grok is dead/reset.

---

## API routes

| Route | Method | Purpose | Auth |
|---|---|---|---|
| `/api/grok-swarm/status` | GET | queue depths, last heartbeat, last progress | bearer |
| `/api/grok-swarm/queue/next` | GET | atomically claim next pending task | bearer |
| `/api/grok-swarm/queue/add` | POST | operator-only: add a task to pending | bearer + operator scope |
| `/api/grok-swarm/report` | POST | Grok posts progress / done / failed | bearer |
| `/api/grok-swarm/heartbeat` | POST | Grok pings to say it's alive | bearer |

Bearer = `GROK_SWARM_TOKEN` env var (you create it in [Settings → Advanced](/?t=settings&s=advanced)).

---

## Hard boundaries (baked into every route)

- **No secret echo**. Token is constant-time compared; never returned in responses.
- **No fs writes outside `/home/workspace/docs/grok-coordination/`**.
- **No task contents > 64 KiB** (file safety).
- **Claim lease = 1 hour**; auto-expires back to `pending`.
- **No model calls from these routes** — they're pure storage + queue mechanics. Grok runs its own models.
- **No git commits from the routes** — operator commits manually after review.

---

## Why this fixes Grok's instability

| Grok problem | Fix |
|---|---|
| Loses context between resets | On wake, Grok calls `queue/next` → gets the same task back if its lease was still active, or the next priority task. Context files referenced inline. |
| `persistent_grok_agent.py` crashes on import | Replace `from swarm_claw_client import SwarmClawClient` with `from nexus_swarm_client import NexusSwarmClient` — real, working drop-in shipped in `clients/`. |
| No external meta-controller | This is the meta-controller. Stale heartbeat ⇒ alert. Lease expiry ⇒ auto-requeue. |
| Stub MCP server with no network | Phase 2 will add `/api/grok-mcp` exposing real MCP-spec `tools/list` and `tools/call` Grok can hit. |
| Provider routing fights `openai/gpt-5.5` | Out of scope here (already fixed on Zo side: NIM via ModelRelay). Grok can use its own provider; the queue is provider-agnostic. |

---

## What's intentionally NOT here yet

- **No real MCP tool exposure** — Phase 2 adds `/api/grok-mcp` MCP-spec endpoint.
- **No TrustKernel** — operator approves new tasks by writing to `queue/pending/`. No semantic gate.
- **No Tailscale-based hybrid** — HTTPS over public zo.space is the only path today.
- **No auto-task generation** — Grok works on what speci or Zo automations put in the queue, not what it imagines.

These are deliberate: ship a small, working core that solves the durability problem first.

---

## Next phase

- Phase 2: `/api/grok-mcp` MCP-spec endpoint (initialize / tools/list / tools/call) backed by Zo's real tool inventory (file read, search, model relay).
- Phase 3: Approval gate on `queue/add` — operator-signed JWT for high-risk task kinds.
- Phase 4: Cross-link with NEXUS automations — research-scout findings auto-become queue tasks.

See worklog: `docs/handoff/zo-coordination/worklogs/20260527T0***-grok-swarm-bootstrap/`
