# NEXUS Long-Run Integration Control Plan - 2026-06-20

Status: operator-facing control plan  
Scope: NEXUS main repo, NEO evidence intake, GLM-5.2 dashboard collaboration, Grok/Zo advisory lanes  
Rule: NEXUS remains canonical; external agents and side workspaces are evidence inputs only.

## 1. Grounded State

### Verified local artifacts

- `docs/coordination/NEO_EVIDENCE_MATRIX_2026-06-20.md` exists in main NEXUS.
- `docs/planning/NEO_TO_NEXUS_IMPORT_PLAN_2026-06-20.md` exists in main NEXUS.
- The created file counts are currently:
  - Evidence matrix: 61 lines.
  - Import plan: 174 lines.
- Both files are untracked and should remain review-only until accepted.
- NEO evidence now confirms useful but bounded facts:
  - NEO git status fails with `fatal: bad object HEAD`.
  - NEO contains token-efficiency candidate modules.
  - NEO contains Azure references and an Azure key marker in `.env`.
  - NEO memory hierarchy claims conflict with NEXUS 8-channel memory.

### Verified browser/control state

- Isolated browser can open `https://chat.z.ai/c/47e59a42-06cb-442e-9b35-3e3d8d2b078f`, but Z.ai returns signed-out home plus API error: `failed to get chat: chat not found`.
- Firefox is running locally and appears to hold the intended auth account, but Codex cannot currently attach to Firefox.
- Computer Use bootstrap is broken in this Codex runtime with an `@oai/sky` package export error before window listing.
- Therefore direct Firefox/Z.ai interaction is blocked from this Codex turn. Manual prompt handoff or a fixed Computer Use runtime is required.

### Automation state risk

- Recent logs show repeated automation churn around GLM/Zo/Grok.
- The old high-frequency GLM loop burned tokens and was paused earlier.
- The useful automation design is not "keep checking every 30 minutes"; it is "cheap fingerprint first, act only if source is authenticated, readable, waiting, and has a concrete artifact delta."
- Any automation that cannot read a source must return `NOTIFY_SETUP_REQUIRED` or `BLOCKED`, not `DONT_NOTIFY`.

## 2. Decisions

### Keep

- Keep the NEO evidence matrix and import plan as review artifacts.
- Keep Grok as the most useful live advisory lane for now, because shared/public access is more reliable.
- Keep GLM-5.2 as a controlled collaboration lane, but require manual or authenticated-browser handoff until Firefox control is fixed.
- Keep Zo as advisory command-routing only; no execution through Zo.

### Pause or reduce

- Do not run a 30-minute GLM loop unless it can actually read the authenticated GLM chat and observe artifact deltas.
- Reduce private-browser advisory sources to 6-hour cadence unless an operator is actively supervising.
- Do not create new duplicate automations until stale ones are removed or conclusively paused.

### Reject

- Reject NEO "approved for execution" language.
- Reject Cline/Gemini false-completion claims that created files in a different workspace.
- Reject claims such as "7352 = ModelRelay", "blockchain memory", "Gemini as NEXUS standard", "all Johns", or "21 working lines".
- Reject importing NEO `vault/manager.py` or S-P-E-W memory hierarchy into NEXUS.

## 3. Long-Run Session Goals

### Goal A - Clean Knowledge State

1. Review the two new NEO files.
2. Mark accepted facts directly in a coordination ledger.
3. Do not stage them yet.
4. Add only one canonical follow-up task list:
   - NEO git read-only fsck.
   - token-efficiency module diff.
   - Azure reference remediation plan.
   - 8-channel memory compatibility check.

Done condition:

- NEO is classified as `evidence-input`, not `migration-source`.
- Every proposed import item has `accept/revise/reject/defer`.

### Goal B - Local Runtime Truth

1. Verify port ownership live:
   - `7350` Node ModelRelay.
   - `7352` Brain API only.
   - `7355` Python fallback.
   - `7356` static dashboard.
   - `7357` god_mode_proxy.
2. Verify Brain API route count from source and import.
3. Verify `/api/stress/report` route registration.
4. Do not claim durable Vault/Archivist writeback until a safe local test proves output.

Done condition:

- Local port and route truth is in one small report.
- No stale `7352 = ModelRelay` claim is treated as current.

### Goal C - GLM-5.2 Dashboard Collaboration

1. Work only with GLM-5.2. Do not accept GLM-4.7, GLM-5, turbo, flash, or substitutes.
2. If using authenticated Firefox, operator or fixed Computer Use must expose the actual chat.
3. Ask GLM for concrete artifacts only:
   - patch file,
   - SHA256,
   - byte count,
   - changed-file list,
   - tests run,
   - local verification commands,
   - explicit blockers.
4. Treat GLM output as advisory until local `git apply --check` and focused tests pass.

Done condition:

- Either a patch artifact is locally available, or GLM is marked `BLOCKED_ARTIFACT_MISSING`.

### Goal D - Automation Hygiene

1. Inventory active automations.
2. Keep only:
   - one Grok progression lane,
   - one Zo advisory lane,
   - one GLM lane if authenticated access is working,
   - low-frequency health/queue jobs only when they produce useful deltas.
3. Convert noisy private-chat loops to 6-hour cadence.
4. Require first-run `BASELINE_CREATED`, not `DONT_NOTIFY`.

Done condition:

- No duplicate high-frequency loops remain.
- Every automation has an explicit blocked/degraded/no-delta contract.

## 4. Firefox/Z.ai Prompt For Manual Handoff

Use this in the authenticated Firefox Z.ai chat if Codex cannot control Firefox:

```text
You are GLM-5.2 only. Do not downgrade to GLM-4.7, GLM-5, GLM-5-Turbo, turbo, flash, or any substitute.

NEXUS current state:
- NEXUS main root: C:\Users\speci.000\Documents\NEXUS
- 7352 is Brain API / governance only.
- 7350 is Node ModelRelay primary.
- 7355 is Python/internal ModelRelay fallback.
- 7356 is static dashboard.
- 7357 is god_mode_proxy.
- NEXUS uses 8-channel memory, VAP/audit, TrustKernel, KAIJU gates.
- NEO is evidence input only, not canonical.

Task:
Create the next concrete NEXUS dashboard/backend integration artifact. Focus on one bounded patch only:
1. Port Doctor and Brain API status correctness.
2. Stress/report writeback verification surface.
3. ModelRelay provider/runtime risk status display.
4. GLM-5.2 canonical route with provider echo diagnostic.

Output contract:
- Produce an exportable patch file.
- Produce `.sha256` with SHA256 and byte count.
- List changed files.
- List tests run.
- List exact local verification commands.
- If blocked, state blocker precisely.
- Do not publish, upload, delete, install, expose secrets, or modify unrelated source.
- Do not claim production readiness without local tests.
```

## 5. Grok/Zo Prompt For Advisory Agents

```text
Treat this as advisory only. Do not execute commands against local NEXUS.

Read the latest NEXUS coordination state and produce a bounded task proposal:
- What changed?
- What evidence supports it?
- Which NEXUS lane does it affect: Brain API, ModelRelay/GMR, NEXUSCLAW, ARCHIVIST, Modal Lab, GROSS bridge, Imagine Labs?
- What local verification is required before adoption?
- What must not be trusted yet?

Return a NexusClawTaskEnvelope-style proposal only. Do not ask to run shell commands, upload files, rotate keys, delete data, or modify remote state.
```

## 6. Next Local Commands, In Order

These are safe candidates for a later execution pass, not executed by this plan:

```powershell
git status --short -- docs\coordination\NEO_EVIDENCE_MATRIX_2026-06-20.md docs\planning\NEO_TO_NEXUS_IMPORT_PLAN_2026-06-20.md
python -c "from nexus_os.bridge.port_registry import PortRegistry; print(PortRegistry.CANONICAL_PORTS)"
python -c "from nexus_os.api.brain_api import brain_app; print(len(brain_app.routes)); print(any('/api/stress/report' in getattr(r, 'path', '') for r in brain_app.routes))"
rg -n "7352.*ModelRelay|ModelRelay.*7352|glm-4\.7|glm-4-7" docs nexus_os src --glob "!node_modules" --glob "!.next"
```

## 7. Approval Gates

Requires explicit operator approval:

- Any NEO git repair beyond read-only `git fsck`.
- Any `.env` edit or Azure key deletion.
- Any NEO-to-NEXUS code import.
- Any provider endpoint rewrite.
- Any automation deletion if the automation API cannot clearly identify the target.
- Any upload/download through GLM/Z.ai/Zo/Grok browser UI.

