---
id: NODE-MIG-ZO_24_7_PROVIDER_BACKUP_PLAN_2026_05_24
authority_scope: experimental
origin_sha256: c0032688665226c8066c432fd90371901e26c959862ae3442cc33a8f39461450
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-F52491
---
# Zo 24/7 Provider Backup Plan - NEXUS

<!-- CANARY: 06022030686dd53c179e7a554e03d9b6 -->
Date: 2026-05-24
Scope: Zo always-on cloud computer, provider fallback, Claw/swarm usefulness, and token-safe automations.

## Current Automation State

Local automation files show the token-burn optimization is mostly working:

- `zo-nexus-morning-brief`: `ACTIVE`, daily at 08:30, last memory update 2026-05-24 08:34.
- `zo-nexus-heartbeat`: `PAUSED`, downshifted from hourly to 6-hour interval before pause.
- `zo-nexus-pr-watcher`: `PAUSED`, downshifted from 2-hour watcher to 6-hour interval before pause.
- `nexus-health-check`: `ACTIVE`, weekly Monday 06:08.
- `nexus-queue-runner`: `ACTIVE`, weekly Monday 06:12.

No `.codex\automations` memory/config file changed in the six-hour window checked at 2026-05-24 16:39 +03:00. This indicates the repeaters are not currently generating new local automation memory churn.

## LaunchDarkly MCP

The requested Codex MCP configuration was added to:

`C:\Users\speci.000\.codex\config.toml`

```toml
[mcp_servers.launchdarkly]
url = "https://mcp.launchdarkly.com/mcp/launchdarkly"
http_headers = {  }
```

Codex CLI must be restarted before the server is loaded.

## Provider Problem Framing

Zo should not depend on one provider family. The working model is a routed provider mesh:

- Tier 0: local NEXUS state digest and cached evidence, no LLM call.
- Tier 1: cheap/free summarizers for routine no-change checks.
- Tier 2: reliable mid-cost model for blocker triage and PR/check interpretation.
- Tier 3: premium model only for deep reasoning, incident response, or public-facing writing.

Provider failures must be classified, not retried blindly:

- `auth`: key expired, quota blocked, OAuth/provider disconnected.
- `rate_limit`: temporary provider pressure; retry later or fallback.
- `model_unavailable`: route to another compatible model.
- `tool_unavailable`: do not hallucinate; report data gap.
- `safety_or_policy`: escalate to operator with evidence.
- `network`: retry with backoff, then fallback.

## Recommended Zo Provider Routing

### Routine Watchtower Checks

Use for morning briefs, queue state, stale digest checks, and simple PR deltas.

Preferred:

- OpenRouter free/low-cost fast models when available.
- KiloCode/OpenCode local or connected provider if stable.
- Small Gemini/Flash-class models through Zo built-ins when credits allow.

Rules:

- No broad repo scans.
- No full logs unless a delta exists.
- No retries beyond one cheap fallback.
- If all providers fail, output a provider-health row only.

### Incident / Security / Merge Gates

Use for suspected leaks, PR status conflicts, failed deployment gates, Docker/port warnings, or public-release decisions.

Preferred:

- GPT-5-class / Claude Opus-class / Gemini Pro-class model when available.
- NEXUS local Codex remains final reviewer for repo mutation.

Rules:

- Require source links, file paths, timestamps, and exact failing checks.
- Never call something merge-ready from cached state.
- Never expose secrets, `.env`, raw DoppelGround, model weights, or raw research dumps.

### Research Librarian

Use for HF links, papers, model cards, benchmarks, Zo chats, and dataset notes.

Preferred:

- Long-context cheap model for classification.
- Premium model only for synthesis after classification.

Rules:

- Output proposed routing only: `research`, `datasets`, `benchmarks`, `docs/handoff`, or `MIXED`.
- No file moves from Zo.
- Anything uncertain goes to `MIXED`.

## Secure 24/7 Claw Swarm Layout

Enable only read-only or proposal-bound roles until 48 hours of clean behavior.

| Role | Cadence | Provider Tier | Allowed Actions | Blocked Actions |
|---|---:|---|---|---|
| State Scribe | daily | Tier 1 | summarize digest/docs/git status | edit files, run commands through local NEXUS |
| Provider Sentinel | every 6h | Tier 1 | classify provider health and fallback availability | add keys, rotate secrets |
| PR Sentinel | incident/manual | Tier 2 | summarize PR/check deltas | merge, force-push, resolve checks |
| Research Librarian | daily/manual | Tier 1 -> Tier 2 | classify links/files into proposed buckets | move files, publish research |
| Incident Watcher | incident only | Tier 2 | report spam/source/rate evidence | stop services without approval |
| Bridge Auditor | daily | Tier 1 | check digest freshness and data gaps | arbitrary file read, command execution |

## Zo Cloud vs Local NEXUS Boundary

This plan does **not** prohibit using Zo's own cloud computer. Zo's cloud workspace is the right place for 24/7 watchtower work, provider fallback checks, lightweight Claw/swarm coordination, hosted dashboards, and read-only research triage.

The hard boundary is about the Windows/local NEXUS production workstation: Zo should not get routine SSH/control over the local machine where secrets, Docker, GPU/TWAVE workloads, training/evaluation runs, and private raw research live.

Zo cloud may:

- Read sanitized state digest.
- Read approved handoff docs.
- Query GitHub public/private PR metadata when connected.
- Summarize provider-health failures.
- Draft Notion/Slack summaries with dedupe/rate limits.
- Run its own cloud-native services, scripts, workers, and Claw/swarm helpers inside Zo's hosted environment.
- Maintain a Zo-side mirror of sanitized NEXUS coordination artifacts.

Zo cloud must not:

- Read `.env` or secrets.
- SSH into Windows/local NEXUS as a routine path.
- Restart Docker, kill processes, rotate credentials, or change firewall rules.
- Push, merge, force-push, delete branches, or move local files.
- Access raw private research, raw DoppelGround sessions, model weights, or unreviewed dataset dumps.

## Backup and Continuity Plan

1. Keep `docs/handoff/zo-coordination/NEXUS_STATE_DIGEST.json` as the one sanitized bridge payload.
2. Add provider-health fields to the digest: provider name, last success time, last failure class, retry-after if known.
3. Keep one active daily Zo brief only.
4. Keep heartbeat/PR watchers paused until active incidents/PR windows.
5. Use weekly local Codex automations for deeper repo health and official queue handling.
6. Keep Zo outputs proposal-only; local NEXUS/Codex executes and verifies.
7. If Zo provider fails, write a single provider-health note instead of spawning a new long conversation.
8. Use Zo's own cloud computer for 24/7 lightweight services, but require a sanitized input contract and no local-machine control surface.

## Acceptance Criteria

- No more than one routine Zo/NEXUS conversation per day unless there is a new blocker.
- No automation repeats identical old PR/check facts.
- Provider failures are summarized once with class, affected tool/model, timestamp, and fallback used.
- Zo can state current NEXUS branch/HEAD/test baseline only from a fresh digest or explicit data-gap note.
- No public transcript contains secrets, `.env`, raw logs, raw research dumps, or internal model-weight paths.
- 48 hours without spam, duplicate runs, or unapproved side effects before enabling any broader swarm execution.
