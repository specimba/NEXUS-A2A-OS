# NEXUS Advisory Direction Sync

Date: 2026-06-19
Status: Draft automation foundation
Authority: advisory intake only; local NEXUS verification remains source of truth

## Purpose

Coordinate external AI work surfaces without letting them become uncontrolled executors. Z.ai, Grok, Zo, Qwen, and similar browser/cloud agents are treated as advisory design/research/implementation accelerators. NEXUS converts their outputs into verified local task envelopes, route plans, or UI prompts.

## Sources

| ID | Source | Primary Use | Access Mode | Failure Mode |
|---|---|---|---|---|
| S1 | Z.ai dashboard GLM-5.2 chat `https://chat.z.ai/c/1e041cbd-354e-45ed-9fa2-3c186325ce3f` | Dashboard/backend/UI direction | Authenticated Chrome tab if visible | `BLOCKED_CONTROLLER` if tab title/URL visible but content claim times out |
| S2 | Z.ai Imagine Labs chat `https://chat.z.ai/c/0c84cee3-d9e8-4913-97c4-9e3d20797abd` | Imagine Labs design/product direction | Authenticated Chrome tab if visible | Same as S1 |
| S3 | Grok 4.3 NEXUS sources | Burst worker, MCP/tool-control ideas, paid browser agent | Existing Grok control extension or visible tab | Treat output as proposal only |
| S4 | Zo canonical NEXUS integration share | Cloud-computer command routing and long-running infrastructure advice | Public share or authenticated tab if already open | `BLOCKED_ZO_ACCESS` if content unreadable |
| S5 | Qwen NEXUS Imagine source | HTML/UI variants and comparison prompt source | Visible tab/public share | Advisory only |

## Current Discovery Notes

- Z.ai dashboard tab is open and visible in Chrome, but direct tab claiming timed out twice. Lightweight tab listing works. Routine automation must not call this `DONT_NOTIFY`; it should report `BLOCKED_CONTROLLER` when only URL/title fingerprint is available.
- Visible Z.ai dashboard advice from the current stage: build/wire FastAPI backend on port `7352`, fix `ZAI_API_KEY` settings visibility, and remove sandbox stub backups after verification.
- Agent-log reconciliation confirms the canonical target: `7350 = Node ModelRelay`, `7352 = Brain API`, `7355 = Python ModelRelay fallback`, `7356 = static dashboard`, `3001 = Next dashboard`. Any Node process on `7352` is runtime drift, not the architecture.
- A bounded fix was applied: `nexus_cli_ctl/daemon/master_daemon.py` now imports `brain_app` instead of nonexistent `app`. Runtime still needs stale Node-on-7352 relocation before Brain API can bind.

## GLM-5.2 Capability Implications

Use GLM-5.2 as a high-context design and engineering reviewer, not as an unchecked executor.

Relevant verified capabilities from public sources:

- 1M-token context and 128K max output window make it suitable for project-scale dashboard architecture review and long-horizon refactor planning.
- It supports thinking mode, function calling, context caching, structured output, MCP integration, and streaming.
- It is strong on coding/agentic benchmarks, but public discussions show early runtime friction: benchmark reproduction questions, H200 FP8/vLLM issue reports, crash reports, and requests for smaller Air/Flash variants.

NEXUS mapping:

- Bridge: use GLM-5.2 outputs through advisory source records, not direct shell/tool execution.
- Governor/KAIJU: every instruction from GLM becomes a dry-run task envelope before local execution.
- Vault/S-P-E-W: store only fingerprints, source cards, and verified summaries; do not copy private chat dumps wholesale.
- Engine/GMR: use GLM-5.2 as teacher/designer/reviewer through API/Modal/provider lane, not local 8GB VRAM default.

## Dashboard Prompt Packet For Z.ai

Use this when asking the Z.ai dashboard agent for high-quality UI/backend movement. Do not ask it to execute local commands unless a cloud sandbox is explicitly isolated.

```text
You are acting as NEXUS Dashboard Architect, not a generic app builder.

Goal: turn the NEXUS OS dashboard into a real governed control surface, not a mock demo.

Grounding constraints:
- Treat your environment as advisory unless you can prove a file exists in your sandbox.
- Do not claim local NEXUS runtime facts unless I give logs or endpoint responses.
- Output implementation plans as small routeable slices, each with risk level, files likely touched, API contract, UI state, and verification.
- Prefer dashboard/backend contract clarity over visual decoration.

Current verified local facts from Codex:
- Python Brain API exists at `nexus_os/api/brain_api.py` as `brain_app`.
- Brain API routes include `/health`, `/api/stats`, `/api/providers`, `/api/relay/*`, `/api/dashboard/sync`, `/api/wiki/*`, `/api/messaging/*`, `/ws`.
- Canonical port map from the latest agent logs: `7350 = Node ModelRelay`, `7352 = Brain API`, `7355 = Python ModelRelay fallback`, `7356 = static dashboard`, `3001 = Next dashboard`.
- Static dashboard on `7356` serves successfully.
- Next dashboard on `3001` and Python ModelRelay on `7355` were not listening during the last check.
- `nexus_cli_ctl/daemon/master_daemon.py` was patched to import `brain_app` correctly.
- Next route `/api/governance` was patched to probe Brain API `/api/stats` via `NEXUS_BRAIN_API_URL` defaulting to `http://127.0.0.1:7352`. Its POST action mapping remains provisional and should be reconciled against real `brain_app` routes before deeper rewrites. `nexusctl dashboard --doctor --json` now detects this runtime drift read-only.
- Settings should report Z.ai key presence using encrypted `ApiKey(provider='z-ai')` plus env presence, not plaintext `SystemConfig` secrets.

Task:
Produce a dashboard/backend implementation map for the next 3 slices:
1. Runtime port ownership and Brain API startup verification.
2. Dashboard API contract unification for Overview, Governor, Vault/Wiki, ModelRelay/GMR, Tasks/NexusClaw.
3. UI/UX polish plan for a serious operator cockpit: state hierarchy, source badges, degraded/offline states, evidence-first panels, and no fake green health.

Output format:
- Start with a one-screen executive diagnosis.
- Then a table: Slice, objective, files, API contracts, UI state, tests, risk.
- Then give exact prompt for the next agent if another model must continue.
- Mark all assumptions explicitly.
- Do not say complete; say what local Codex must verify.
```

## Routine Automation Contract

Status outputs:

- `BASELINE_CREATED`: first successful fingerprint for at least one source.
- `DONT_NOTIFY`: only after successful baseline exists and all accessible fingerprints are unchanged.
- `BLOCKED_CONTROLLER`: tab is visible by title/URL, but controller cannot claim or read visible content.
- `NOTIFY_SETUP_REQUIRED`: three or more sources are blocked/auth-inaccessible.
- `DEGRADED`: only old public/share sources are readable.

Read rules:

- For Z.ai/private dashboard chats, prefer a separate controller-owned Chrome window/tab opened directly to the chat URL, then close it after the run. Avoid claiming the operator active tab/window.
- Otherwise make one bounded navigation attempt per public/share source.
- Do not inspect cookies, local storage, passwords, tokens, API keys, session stores, or private files.
- Do not click Send, submit forms, upload/download, approve, delete, install, or execute commands.
- Capture only newest visible heading/turn marker, app status, timestamp, or short fingerprint.

Output rules:

- Max 10 bullets grouped by source.
- Mark every external item `ADVISORY`.
- Include lane mapping, required local verification, and exact next prompt/direction.
- Convert commands into `NexusClawTaskEnvelope` dry-run proposals.
- No duplicated recap and no follow-up question.
