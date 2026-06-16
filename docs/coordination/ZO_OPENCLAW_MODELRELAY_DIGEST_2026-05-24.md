---
id: NODE-MIG-ZO_OPENCLAW_MODELRELAY_DIGEST_2026_05_24
authority_scope: experimental
origin_sha256: e6c30e5109f913ba4bfcaf2838651284f4c80d1002fd952545275569a9c121e0
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-FACA57
---
# Zo OpenClaw / ModelRelay Digest - 2026-05-24

<!-- CANARY: 0ce02d7c2521f2752dbab2bfc2a12de8 -->
Source: `https://www.zo.computer/chats/pub_7Ln55LCVcOuqGM6y`

This digest intentionally omits raw provider keys, gateway bearer tokens, and Telegram bot tokens that appeared in the public transcript.

## What Zo Investigated

Zo investigated Slack spam in `#nexus-autoclaw`.

Findings:

- Slack spam came from `autoclaw-local` forwarding repeated `check` messages.
- The forwarding service was `telegram-claw-gateway`.
- The gateway polled Telegram roughly every 2 seconds.
- The gateway had no dedupe or rate-limit layer.
- OpenClaw gateway itself was not the original spam source.
- `telegram-claw-gateway` was disabled by changing the service entrypoint to sleep.

Secondary issues reported by Zo:

- KiloClaw Telegram token returned `401 Unauthorized`.
- `forward_to_kafka` ordering/definition caused runtime errors after posts.
- AutoClaw message source still needs root-cause analysis; disabling the bridge only stopped the symptom.

## OpenClaw State From Zo

Zo found:

- `openclaw-gateway` service was running separately from `telegram-claw-gateway`.
- OpenClaw gateway health responded on localhost port `18789`.
- OpenClaw default model routing was intended to use OpenRouter.
- CLAW-01 failures were caused by provider/key/model-routing problems, not by the Telegram spam fix.
- AutoClaw likely has its own config folder/state separate from `/root/.openclaw/openclaw.json`; this was not fully resolved in the Zo run.

Zo created or modified an OpenClaw workspace:

- `OpenClaw/workspace/SOUL.md`
- `OpenClaw/workspace/AGENTS.md`
- `OpenClaw/workspace/HEARTBEAT.md`
- `OpenClaw/workspace/USER.md`
- `OpenClaw/workspace/TOOLS.md`
- `OpenClaw/workspace/IDENTITY.md`
- `OpenClaw/workspace/memory/`
- `OpenClaw/workspace/governance/`

Risk note:

Zo also moved or removed nested Git state under `OpenClaw/workspace/.git` while trying to commit the workspace into the main repo. This must be reviewed carefully before copying any pattern into local NEXUS.

## ModelRelay Findings

Zo found a ModelRelay implementation under:

- `/home/workspace/src/nexus_os/modelrelay/`

Zo reported these routes on Zo Space:

- `https://specimba.zo.space/api/modelrelay/health`
- `https://specimba.zo.space/api/modelrelay/models`
- `https://specimba.zo.space/api/modelrelay/chat`

The intended chain became:

```text
CLAW-01 / OpenClaw
  -> Zo Space ModelRelay
  -> provider pool through OpenRouter first
  -> future fallback providers
```

Provider conclusions from the run:

- Zo cloud computer has about 4 GB RAM and no GPU, so it is not a real local LLM host.
- Zo should use ModelRelay/provider routing, not local Ollama/vLLM, for LLM execution.
- Windows/local NEXUS remains the correct place for GPU/local model execution.
- OpenRouter can be a working provider, but free-model availability must be live-tested because listed models and callable models diverged.
- Zo edited ModelRelay routes and registry to only advertise verified working models.

## Architecture Decision

Use Zo as:

- Watchtower
- Proposal agent
- Hosted bridge for lightweight ModelRelay calls
- OpenClaw lane coordinator

Do not use Zo as:

- Primary model host
- Secret authority
- Public source of truth
- Unrestricted execution agent
- Force-push authority

## Immediate Follow-Up Tasks

1. Verify current Zo Space ModelRelay health from an external client.
2. Export or copy the actual ModelRelay code from Zo to local NEXUS only after redacting secrets.
3. Compare Zo ModelRelay with local `scripts/zo_nexus_state_bridge.py` and `nexus_os/mcp/` before adopting code.
4. Add rate limiting, dedupe, and circuit-breaker logic before re-enabling Telegram/Slack bridges.
5. Add a Slack anti-spam guard:
   - suppress identical messages
   - minimum 5-minute routine polling
   - maximum one routine summary per channel per 30 minutes
   - sleep-mode on repeated duplicate output
6. Treat OpenClaw workspace commits from Zo as candidate artifacts until reviewed locally.
7. Do not copy Zo browser/public transcript snapshots into the repo because they can contain keys.

## Backend Team Answer

If backend agents ask:

> Once the Zo gateway is reachable, should OpenClaw route API calls to OpenRouter or deeply integrated local endpoints?

Answer:

Use ModelRelay as the abstraction. On Zo, ModelRelay should route to OpenRouter/provider APIs because Zo has no GPU and limited RAM. Local NEXUS/Windows can later expose approved local endpoints as a ModelRelay provider, but only through a narrow authenticated bridge. Do not wire OpenClaw directly to local private endpoints or raw provider keys.

## Acceptance Criteria For Re-Enablement

- Gateway has dedupe and rate limiting.
- Gateway does not forward repeated `check` messages.
- Provider routing is tested with real models and redacted logs.
- No raw keys in repo, public chats, or handoff docs.
- Zo summaries are delta-only and not faster than the agreed routine cadence.
- OpenClaw workspace state is reviewed before being treated as canonical NEXUS architecture.

## Later Zo/OpenClaw Dashboard Update

Reported by Zo after the initial digest:

- Local OpenClaw dashboard: `http://127.0.0.1:18789/`
- Tailscale dashboard candidate: `https://modal.tail5788b3.ts.net`
- Local gateway: `ws://127.0.0.1:18789`, reported live at roughly 159 ms.
- Tailscale exposure requires explicit approval via `openclaw devices approve --latest`.
- Pending Tailscale scope approval request was reported, but should not be approved until the hardening gate below passes.
- Four registered agents were reported:
  - `main` with heartbeat active
  - `glm5-worker-1` disabled
  - `glm5-worker-2` disabled
  - `opusman` disabled
- Provider pool was reported as OpenRouter-backed with a funded key and six configured models. Raw key values are intentionally omitted here.
- `auth-profiles.json` permissions were reported fixed to mode `600`.
- Security warning remained: host-header origin fallback enabled.

Useful OpenClaw commands from Zo:

```bash
openclaw status --deep
openclaw gateway probe
openclaw agent list
openclaw security audit --deep
openclaw logs --follow
openclaw update
```

Decision:

Do not approve the Tailscale public control surface yet. Keep OpenClaw local-only until:

1. `openclaw security audit --deep` is saved with redacted output.
2. Host-header origin fallback is disabled:
   `openclaw config set gateway.controlUi.dangerouslyAllowHostHeaderOriginFallback false`
3. Dashboard/API auth is confirmed for all non-local routes.
4. Logs confirm no `autoclaw-local: check` flood for at least 48 hours.
5. ModelRelay/provider calls have per-provider rate limiting and circuit breakers.
6. OpenClaw workspace files are exported in redacted form and reviewed locally before being treated as canonical.

Public URL rule:

The Tailscale URL is acceptable as a private mesh endpoint after approval, but not as an unauthenticated public dashboard. It should be considered a remote admin surface.

## Zo-Reported Security Gate Update

Later Zo report, not independently verified from local Windows:

- Host-header origin fallback disabled.
- `auth-profiles.json` mode `600`.
- Security audit reported clean: `0 critical`, `0 warning`.
- Local gateway reported clean.
- OpenRouter key funded.
- ModelRelay on Zo Space reported operational.
- Anti-spam bridge still disabled.
- Tailscale URL remains pending explicit device approval.

Updated decision:

The Tailscale approval can be considered only after a redacted copy of `openclaw security audit --deep` and `openclaw gateway probe` is saved or pasted without provider keys. If approved, treat `https://modal.tail5788b3.ts.net` as a private Tailscale admin surface, not public internet infrastructure.

Candidate approval command, only after reviewing the redacted audit:

```bash
openclaw devices approve 15f8606b-6e47-4ece-aacd-899d6983ecaf
```

Post-approval verification:

```bash
openclaw gateway probe
openclaw security audit --deep
openclaw logs --follow
```

Watch for:

- Any return of `autoclaw-local: check` flood.
- Any host-header/origin fallback warning.
- Any unauthenticated dashboard/API route.
- Any provider key displayed in logs.
- Any provider rate-limit loop or repeated failed model call.

## Zo Audit/Probe Artifact Update

Later Zo report:

- Redacted audit saved in Zo workspace:
  `docs/handoff/zo-coordination/OPENCLAW_AUDIT_REDACTED.txt`
- Redacted probe saved in Zo workspace:
  `docs/handoff/zo-coordination/OPENCLAW_PROBE_REDACTED.txt`
- Commit reported by Zo:
  `docs: add redacted OpenClaw audit and probe output for Tailscale approval gate`
- Remote verification from local Windows:
  - `specimba/NEXUS-A2A-OS` `main` = `68da388`
  - `specimba/NEXUS-A2A-OS` `canonical-617` = `68da388`

Important correction:

The pasted audit output says:

```text
Summary: 0 critical · 1 warn · 2 info
WARN gateway.probe_failed ... scope upgrade pending approval
```

So the correct status is not strictly `0 warning` before approval. It is:

- `0 critical`
- `1 expected warning`, caused by pending Tailscale scope approval
- `2 info`

This is acceptable for approval if and only if the redacted probe confirms local gateway health and no other warnings exist.

Force-push note:

Zo force-pushed `canonical-617` to `main` in `specimba/NEXUS-A2A-OS`. This is verified by matching remote refs at `68da388`, but it remains a process risk. Future Zo pushes should use PR/branch flow unless explicitly approved.

Current approval candidate:

```bash
openclaw devices approve 047af614-d15f-4ce9-8c8b-4624e6416999
```

Use this newer request ID instead of the older `15f8606b-...` request if it is still current in OpenClaw.

## Dashboard Access And Provider Failure - 2026-05-25

Windows access to the Tailscale dashboard was confirmed by the operator:

- Dashboard URL: `https://modal.tail5788b3.ts.net`
- Local NEXUS shortcut: `shortcuts/Zo OpenClaw Dashboard.url`

New live failure from the OpenClaw dashboard:

```text
Agent failed before reply: No API key found for provider "openai".
Auth store: /root/.openclaw/agents/main/agent/auth-profiles.json
agentDir: /root/.openclaw/agents/main/agent
```

Interpretation:

- Tailscale/dashboard access works.
- The active `main` agent is still trying to use provider `openai`.
- This is not a Tailscale problem.
- This is not solved by adding OpenRouter keys unless the active agent model/provider mapping is changed.
- The earlier Zo-side ModelRelay/OpenRouter work has not become the active model path for the `main` OpenClaw agent.

Required Zo-side fix:

```bash
openclaw status --deep
openclaw agent list
openclaw logs --follow
```

Then inspect the active main agent model/auth profile:

```bash
cat /root/.openclaw/agents/main/agent/models.json
cat /root/.openclaw/agents/main/agent/auth-profiles.json
cat /root/.openclaw/openclaw.json
```

Safe target state:

- Main agent default model must not be `openai/*` unless a real OpenAI key is configured.
- Prefer `openrouter/auto` only if OpenRouter is known working.
- Better target: route through Zo ModelRelay as the abstraction, then ModelRelay routes to OpenRouter/backup providers.
- Do not paste raw keys into chat or tracked files.

Minimum working repair options:

1. Configure OpenClaw `main` to use an OpenRouter model and OpenRouter auth profile.
2. Configure OpenClaw `main` to call ModelRelay as an OpenAI-compatible base URL if OpenClaw supports custom base URLs.
3. Add OpenAI auth only as a fallback if the operator explicitly wants OpenAI billing used.

Post-fix acceptance test:

```bash
openclaw gateway probe
openclaw security audit --deep
openclaw logs --follow
```

Then from the dashboard, send a single low-cost test prompt. It must not call provider `openai` unless intentionally configured.
