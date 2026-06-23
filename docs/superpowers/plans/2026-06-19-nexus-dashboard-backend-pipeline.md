# NEXUS Dashboard Backend Pipeline Plan - 2026-06-19

## Verified Advisory Input

Z.ai dashboard chat `1e041cbd-354e-45ed-9fa2-3c186325ce3f` is advisory only. Visible latest guidance recommended:

1. Wire dashboard tabs to a Python FastAPI backend on port `7352`.
2. Fix settings/config visibility for `ZAI_API_KEY`.
3. Remove sandbox stub backups after canonical files are verified.

## Live Verification Findings

- `nexus_os/api/brain_api.py` already defines the FastAPI Brain API as `brain_app` with `/health`, `/api/stats`, `/api/providers`, `/api/relay/*`, `/api/dashboard/sync`, `/api/wiki/*`, `/api/messaging/*`, and `/ws`.
- Agent-log reconciliation confirms canonical ownership: `7350 = Node ModelRelay`, `7352 = Brain API`, `7355 = Python ModelRelay fallback`, `7356 = static dashboard`, `3001 = Next dashboard`. Current runtime still drifts: `7352` is occupied by a `node` HTML app, not Brain API; `/health` returns 404.
- `7356` serves the static dashboard successfully.
- `7355` Python ModelRelay is not listening during this check.
- `3001` Next dashboard is not listening during this check.
- `nexus_cli_ctl/daemon/master_daemon.py` imported nonexistent `app` from `brain_api`; this was patched to import `brain_app`.
- Existing focused tests pass: `tests/nexus_cli_ctl/test_brain_api_extensions.py` + `tests/nexus_cli_ctl/test_dashboard_sync.py` = `33 passed`.

## Backend Route

### P0 - Runtime Port Ownership

- Enforce canonical ownership: `7352 = Brain API`, `7350 = Node ModelRelay`, `7355 = Python ModelRelay`, `7356 = static dashboard`, `3001 = Next dashboard`.
- Add and use the read-only `nexusctl dashboard --doctor --json` check. It fails when `7352` is not Brain API JSON and reports expected versus detected owners.
- Move the Node HTML app currently on `7352` to `3001` or stop it before starting the master daemon.

### P1 - Contract Unification

- Freeze `Brain API Contract v1` around the existing `brain_app` routes.
- Keep Next routes on the Brain API contract. `/api/governance` GET was patched from stale `/dashboard/stats` to `/api/stats` through `NEXUS_BRAIN_API_URL`; POST action routes still need a separate contract reconciliation.
- Create a single frontend client layer for Brain API access so dashboard tabs do not independently guess ports and paths.

### P2 - Settings And Provider Keys

- Do not store raw provider secrets in `SystemConfig` as a quick fix.
- Use `ApiKey` encrypted records for stored keys and an env-presence facade for runtime-only keys.
- Update `/api/settings` so `z-ai` checks encrypted `ApiKey(provider='z-ai')` and `process.env.ZAI_API_KEY` / `ZAI_SDK_KEY`, returning only boolean/masked status.

### P3 - Dashboard Tab Wiring

- Overview/System: consume `/api/stats`, `/api/dashboard/sync`, and `/api/state`.
- Governor/Trust Engine: consume `/api/trust`, `/api/trust/agent/:id`, and local Prisma-backed routes only when Brain API is offline.
- Vault/ARCHIVIST/Wiki: consume `/api/wiki`, `/api/wiki/pages`, `/api/wiki/search`, `/api/wiki/sources` first; keep raw Downloads/GROSS out of canonical UI.
- ModelRelay/GMR/Providers: consume `/api/relay/health`, `/api/relay/models`, `/api/providers`, `/model/health`; checks must be lazy and must not load local Ollama runners.
- Tasks/NEXUSCLAW: consume `/api/tasks`, `/api/agents`, and `NexusClawTaskEnvelope` dry-run proposal endpoints when present.

### P4 - Advisory Source Pipeline

- Convert Z.ai/Grok/Zo/Qwen advisory chats into `AdvisorySourceRecord` inputs: source id, URL, visible marker, short fingerprint, lane mapping, proposed action, required local verification, and risk.
- Never execute cloud-chat advice directly. Convert commands into dry-run `NexusClawTaskEnvelope` proposals.
- Preserve cloud UI screenshots/markers as evidence fingerprints, not as canonical truth.

## Immediate Next Slice

1. Stop or relocate the Node service on `7352` only after operator approval.
2. Start Brain API through the fixed master daemon or a direct `uvicorn nexus_os.api.brain_api:brain_app --host 127.0.0.1 --port 7352` dev command.
3. Run `python -m nexus_os.cli.nexusctl dashboard --doctor --json`; then verify `/health`, `/api/stats`, `/api/dashboard/sync`, `/api/providers`, `/api/relay/health` return expected JSON after Brain API owns `7352`.
4. Add a focused route test for `/api/governance` GET using `NEXUS_BRAIN_API_URL` and `/api/stats`; then separately reconcile POST action routes.
5. Patch `/api/settings` provider-key status to use encrypted `ApiKey` plus env presence, not plaintext `SystemConfig` secrets.
