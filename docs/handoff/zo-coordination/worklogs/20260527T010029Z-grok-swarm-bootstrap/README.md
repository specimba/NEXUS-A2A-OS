# Grok-Swarm Bootstrap — Worklog 2026-05-27 01:00 UTC

## Trigger

Operator (speci) shared Grok's sandbox archive (`opusmanSEEKv4` + Phase 6 MCP server + `persistent_grok_agent.py`). Asked for "deep search and deep think" solutions for Grok 4.3's unstable agentic team, with focus on MCP workarounds because Grok has custom MCP and skills.

## What I read (full file list in conversation workspace)

```
/home/.z/workspaces/con_Q7zuyvaa7MyIV484/grok-sandbox/
├── NEXUS_WORKFLOW_UPGRADE_2026-05-26.md
├── PERSISTENT_LONG_RUN_GROK_AGENT_DESIGN_2026-05-26.md
├── PHASE6_MCP_SERVER_DESIGN.md
├── OPENROUTER_AUTO_INTEGRATION_NEXUS_MCP_2026-05-25.md
├── RED_BLUE_PURPLE_Papers_Analysis_Report.md
├── persistent_grok_agent.py          ← imports modules that don't exist
├── mcp_server/governed_mcp_server.py ← clean stdio scaffold, stub TrustKernel
├── mcp_server/trustkernel/           ← stub/real adapter pattern
├── mcp_server/connectors/{telegram,notion}_connector.py  ← stub
├── mcp_server/security_tests/        ← 6 test files, Category 1-5
└── NEXUS_Red_Team_Lab/docs/MCP_Red_Team_Lab_Specification.md
```

## Diagnosis — what's actually broken on Grok's side

1. **Ephemeral sandbox + short bursts.** Sessions reset; `/home/workdir/artifacts/` wiped. No durable memory.
2. **`persistent_grok_agent.py` crashes on import.** It uses
   `from long_research_mode import LongResearchMode`,
   `from trustkernel import log_audit_event`,
   `from governance_orchestrator import GovernanceOrchestrator`,
   `from drift_monitor import DriftMonitor`,
   `from swarm_claw_client import SwarmClawClient`.
   None of those modules are present in the archive. The script is aspirational, not runnable.
3. **MCP server is stdio-only and stub-backed.** Cannot be reached from outside Grok's sandbox. TrustKernel is a hardcoded allow/deny list. Connectors return fake IDs (`tg_stub_XXXX`).
4. **Provider routing fights `openai/gpt-5.5`** — same bug we already documented on Zo's OpenClaw side, just inside a different sandbox.
5. **No external coordinator.** The design wants a "Claw Swarm Meta-Controller" but no implementation exists.

## Strategy — split authority, make Zo the durable side

Mirror the principle Grok's own design states: *"Skills = Policy, MCP = Execution Bridge."*

- **Zo (persistent)** = durable memory + queue + heartbeat + meta-controller.
- **Grok (ephemeral)** = stateless burst worker. Pulls tasks, runs them, reports back, dies cleanly.
- **Operator** = task source. Drops JSON files into `queue/pending/` either via UI, API, or file commit.

This dodges every Grok limitation by moving the durable parts to a side that's actually durable.

## What I built (Phase 1 — shipped, committed)

| Artifact | Location | Size |
|---|---|---|
| Architecture doc | `docs/grok-coordination/README.md` | 150 lines |
| Unified API route | zo.space `/api/grok-swarm` | 5 actions |
| Python client (stdlib only) | `docs/grok-coordination/clients/nexus_swarm_client.py` | 183 lines |
| Integration recipe | `docs/grok-coordination/clients/INTEGRATE_INTO_GROK.md` | 163 lines |
| Storage skeleton | `docs/grok-coordination/{queue,progress,synthesis,heartbeats}/` | empty dirs |

### Route surface

```
GET  /api/grok-swarm?action=status       — queue depths + last heartbeat
POST /api/grok-swarm?action=next         — atomic task claim (1h lease)
POST /api/grok-swarm?action=add          — operator: add task
POST /api/grok-swarm?action=report       — Grok: progress|done|failed
POST /api/grok-swarm?action=heartbeat    — Grok: liveness ping
```

Bearer-token gated via `GROK_SWARM_TOKEN` env var. Constant-time compare. No token echo.

### Safety boundaries baked in

- No fs writes outside `/home/workspace/docs/grok-coordination/`.
- Body cap 64 KiB.
- Claim lease 60 min, auto-requeue on expiry.
- No model calls from these routes (provider-agnostic).
- No git commits from the routes.
- Sandbox ID sanitized to `[a-zA-Z0-9._-]` before use as filename.

### Verifications run

- Route live: `curl /api/grok-swarm?action=status` → `401` with proper JSON error (route loaded).
- `get_space_errors` → 0 active errors after final write.
- `nexus_swarm_client.py --selftest` → 3/3 pass (missing-token surface, construct, methods present).

## What's intentionally NOT in Phase 1

- **No MCP-spec endpoint.** Phase 2 will add `/api/grok-mcp` with `initialize` / `tools/list` / `tools/call` so Grok's MCP client can connect to Zo as a real MCP server.
- **No TrustKernel semantic gate.** Operator approval is the gate — they decide what enters `queue/pending/`.
- **No Tailscale-based hybrid.** HTTPS over public zo.space is the only path.
- **No auto-population from research-scout findings.** Phase 4. For now, tasks are added manually or via the `?action=add` endpoint.
- **No commit of grok-sandbox archive contents.** They're in the conversation workspace only; if speci wants them in the repo, that's a separate operator decision.

## Operator action required to activate

1. **Generate a token** (any 32+ char string, e.g. `openssl rand -hex 32`).
2. **Set on Zo side**: [Settings → Advanced → Secrets] → add `GROK_SWARM_TOKEN` = `<token>`.
3. **Set in Grok's sandbox env**: `NEXUS_SWARM_TOKEN=<same token>`.
4. **Copy the client**: `nexus_swarm_client.py` from this repo into Grok's sandbox at `/home/workdir/artifacts/`.
5. **Apply the patch** in `INTEGRATE_INTO_GROK.md` to `persistent_grok_agent.py`.
6. **Smoke test** from inside Grok's sandbox per section 5 of `INTEGRATE_INTO_GROK.md`.

The token never appears in any committed file or response. It is the only shared secret between the two sides.

## What this fixes vs what it doesn't

| Grok problem | Fixed by Phase 1? |
|---|---|
| Loses context between resets | ✅ task lease + progress files survive on Zo |
| `persistent_grok_agent.py` crashes on import | ✅ real client drops in for the stub |
| No external meta-controller | ✅ heartbeat + queue is the controller |
| MCP server is unreachable from outside | ⏳ Phase 2 |
| TrustKernel is hardcoded stub | ⏳ Phase 3 (operator-approval gate first; semantic gate later) |
| Provider routing fights `openai/gpt-5.5` | Out of scope — already solved on Zo via NIM/ModelRelay; Grok handles its own |
| Connectors are fake stubs | Out of scope — Grok keeps its own; or Phase 2 exposes Zo's real ones via MCP |

## Phase 2 preview

- `/api/grok-mcp` — real MCP-spec endpoint exposing Zo's read-only tools (file_read, grep_search, web_research, model_relay_chat). Same bearer-token auth.
- TrustKernel-adapter style: every `tools/call` checks the action against an allowlist before executing.
- Audit log appended to `docs/grok-coordination/mcp-audit/YYYY-MM-DD.jsonl`.

## Commits in this slice

To be added in the commit that includes this worklog.

## Boundaries respected

- No force push.
- No secrets in any committed file.
- No service restarts beyond the one normal `restart_space_server` to recover from the 502 at start of slice.
- No edits to `paired.json`, `auth-profiles.json`, OpenClaw config, or any non-zo-coordination location.
- No re-enable of `telegram-claw-gateway`.
- Did NOT call this swarm-ready. Phase 1 only — durable queue + heartbeat. Phase 2+ needed for full MCP swarm.
