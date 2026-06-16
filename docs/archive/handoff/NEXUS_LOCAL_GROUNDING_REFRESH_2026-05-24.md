---
id: NODE-MIG-NEXUS_LOCAL_GROUNDING_REFRESH_2026_05_24
authority_scope: experimental
origin_sha256: 38af614cee772ddb1820c893d58b26ea4c934eb17c4764a15a0e64f251495f47
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-89E667
---
# NEXUS Local Grounding Refresh - 2026-05-24

<!-- CANARY: 738c85878ad263e4941da01ae9d5dfb9 -->
Scope: live local repo, high-priority NEXUS folders, and high-priority Downloads inputs.

## Live Repo Coordinates

- Branch: `codex/specimba/1805mainSpeci`
- HEAD: `61df031` - `agent/task @ opt: lower ERNIE benign false positive rate below 10%`
- Recent commit chain includes BOUNCER / ERNIE / MetaAttackDetector work:
  - `61df031` guard-plane optimization
  - `a0d2e37` MetaAttackDetector gap handoff
  - `172d69c` MetaAttackDetector implementation
  - `d948226` BOUNCER Model Matrix report
  - `520fb24` Tier 2.5 and safety cascade restructure

## Canonical Drift

- `01_PROJECT_STATE.md` is stale: dated `2026-04-21`, still claims `617 passed`.
- `knowledge.md` is missing from current root, although `AGENTS.md` still names it as required source of truth.
- Git history shows `knowledge.md` existed and was updated in `d33bbab`, but it is absent at current HEAD.
- `nexusctl doctor version --report-only` confirms `status=degraded` because project-state date/head/test claims are stale.
- `nexusctl cycle-check` is halted by `.nexus_pi/state/halt_report.json`.

## Operational Health Checks

- `nexusctl doctor memory --report-only`: `status=ok`.
- `nexusctl cycle-check`: `status=halted`, reason `INFRASTRUCTURE_STARTUP`.
- Halt report says Ollama startup / port binding remains the blocker, with recovery hint to restart Ollama or use llama.cpp as fallback.

## Import Layout Risk

Both package layouts exist:

- Root package: `nexus_os/`
- Src package: `src/nexus_os/`

Actual import test with `PYTHONPATH=src;bin;.` loaded:

- `nexus_os`: `C:\Users\speci.000\Documents\NEXUS\nexus_os\__init__.py`
- `nexus_os.governor.trust_kernel`: root package path
- `src.nexus_os.governor.trust_kernel`: separately importable from `src`

Conclusion: current checkout still has import-shadowing risk. Claims that the tree is fully consolidated under `src/nexus_os` are not true for this live HEAD.

## Queue State

Filesystem queue directories exist but are empty:

- `tasks/pending`: 0 files
- `tasks/done`: 0 files
- `tasks/failed`: 0 files

Root-level `.task.md` files exist separately and are not in the official queue folders.

## Current Untracked / Local Artifact Surface

The worktree is mostly untracked local research/runtime surface:

- Top untracked groups after ignore patch:
  - `benchmarks`: 208
  - `datasets`: 157
  - `nexus_os_backup_untracked`: 82
  - `nexus_os_untracked_backup`: 82
  - `nexus_os_shadow_backup`: 82
  - `wl-commons`: 67
  - `docs`: 41
  - `.agents`: 39
  - `models`: 36

Size inventory:

- `benchmarks`: about 2848.85 MB
- `models`: about 2526.89 MB
- `datasets`: about 990.53 MB
- `research`: about 983.08 MB
- `docs`: about 16.68 MB
- `backups`: about 12.97 MB

## Safety Patch Applied

`.gitignore` was updated to keep local runtime/research artifacts off Git:

- `/backups/`
- `/models/**/*.gguf`
- `/models/**/.cache/`
- `/models/guards/**/checkpoint-*/`
- `/datasets/**/venv/`
- `/datasets/**/.venv/`
- `/benchmarks/**/*.parquet`
- `/benchmarks/**/1M-*.parquet`
- runtime `__pycache__` under benchmarks/datasets/models

Reason: local Streamlabs backup scene JSONs include widget URLs with token-like query parameters, and model/data artifacts are runtime assets, not source.

## Latest Handoff / Agent Work Themes

High-priority repo-local handoffs indicate:

- BOUNCER / ERNIE guard-plane work is the active technical center.
- `MetaAttackDetector` was introduced to catch Pattern Mirror, Ontological, and Entanglement bypass classes; report claims 16/16 tests pass.
- BOUNCER model matrix recommends a dual-model / routed ensemble rather than a single model.
- ERNIE Session02 analysis recommends ingesting 1000 adversarial JSONL and 100 benign queries into benchmark pipeline.
- Streamlabs OBS stabilization is documented and a local clean baseline was saved under ignored backups.
- Zo 24/7 provider plan now separates Zo cloud workload from local NEXUS execution authority.

## Latest Downloads Inputs

High-priority new Downloads files:

- `NEXUS_OS_NEXT_MOVEMENT_ADVICE.md`: claims ERNIE benchmark pass with 98.2% block rate and 9.1% benign FPR; proposes Grok custom MCP tunnel, OpenClaw/SwarmClaw integration, and MCP pre-integration sandbox.
- `implementation_plan03.md`: proposes classifier v3 retraining, ERNIE benchmark rerun, git rebase, Gas Town / Zo operations.
- `NEXUS_OS_OBSERVABILITY_MANIFEST_V3.md`: proposes Amplitude-backed agent telemetry, trace propagation, funnels, and drift/entropy monitoring.
- `HF-mlintern-NEXUS-RnDlog-01.txt`: captures HF ml-intern dataset/session trace context.
- `ZoCompCLOUDsolutionslog-01.txt`: records Telegram/Slack gateway spam root cause and Zo cloud remediation notes.
- `devinKIMIworklog5.txt`: records trust scoring, TaskClassifier, MCP mock-only, BOUNCER, PR #34, sync checkpoint work.
- `opencodeMAINbackendCODEdeepseekV4flashlog-01.txt`: records guard-plane benign set / classifier work.

Downloads folder also contains the ERNIE research pack:

- `Downloads\ERNIEsupramacyRESEARCHpaper01\session04\scenarios_001-1000_EN.jsonl`
- `Downloads\ERNIEsupramacyRESEARCHpaper01\session04\benign_corpus_100.jsonl`
- validation reports and delivery docs

## Priority Reconciliation Tasks

1. Rebuild or restore `knowledge.md` from the latest valid source, but update it for current HEAD `61df031` and current import-layout reality.
2. Update `01_PROJECT_STATE.md` from stale `617 passed` / `2026-04-21` to a verified current snapshot.
3. Resolve package layout truth: either fully consolidate under `src/nexus_os` or explicitly document dual-layout import precedence.
4. Resolve `cycle-check` halt by addressing Ollama startup / port binding or updating halt state if the port-11435 route is now the real working path.
5. Classify untracked benchmark/dataset/model artifacts into tracked-source, ignored-runtime, or `MIXED` before any staging.
6. Treat Downloads reports as evidence only until reconciled into tracked handoff docs with live-file verification.

