# Phase 2 Release Notes — Continuity Substrate (2026-07-08 → 07-10)

> Branch: `opencodeCLIagents/continuity-substrate-2026-07-08`
> Base: `a6c3c6f3` (from `codex/specimba/nexus-core-solidify`)
> Head: `6b39c64a`

## Deliverables Committed

| Commit | Scope | Files | LOC |
|---|---|---|---|
| `92dff94a` | Phase 0 inventory | `docs/handoff/opencodeCLIagents-2026-07-08/00-phase-0-substrate-inventory.md` | 207 |
| `d1a518eb` | Phase 1 migration plan | `docs/handoff/opencodeCLIagents-2026-07-08/01-phase-1-migration-plan.md` | 242 |
| `01cc8f79` | `nexusctl memory` subcommand | `nexusctl/memory_cli.py`, `nexusctl/cli.py`, `tests/nexusctl/test_memory_cli.py` | 286+27+138 = 451 |
| `4690e5cf` | `nexusctl continuity` subcommand | `nexus_os/continuity/{__init__,records}.py`, `nexusctl/continuity_cli.py`, `nexusctl/cli.py`, `tests/nexusctl/test_continuity_cli.py` | 228+19+129+35+75 = 486 |
| `5fe6795f` | `nexusctl intel` subcommand | `nexusctl/intel_cli.py`, `nexusctl/cli.py`, `tests/nexusctl/test_intel_cli.py` | 103+22+119 = 244 |
| `6b39c64a` | Archive janitor | `docs/handoff/opencodeCLIagents-archive/{mcp_test,old_handoffs,intro_outro,vault_test}/` (12 files) | 170 |

Total new code: **~1351 LOC**. Total new tests: **17 test functions** (9 memory + 2 continuity + 6 intel).

## What Was Built

### 1. `nexusctl memory` — 8-Channel Vault Access

Read and append to the NEXUS vault memory channels (MemoryChannelManager).

Subcommands:
- `memory channels` — list 8 channels with trust gates
- `memory show <channel> [--agent] [--limit]` — read records
- `memory trust [--agent] [--lane]` — TrustKernel snapshot
- `memory stats` — consolidation stats per channel
- `memory failures [--agent]` — list failure patterns
- `memory append <channel> --content ... [--allow-write]` — gated write

### 2. `nexusctl continuity` — Durable Session Ledger

Append-only JSONL ledger for agent run lifecycle. Survives sessions.

Subcommands:
- `continuity status` — ledger health + summary + legacy state refs
- `continuity coverage --hours N` — records within a time window
- `continuity open --run-id --agent-id --source-lane` — open a run
- `continuity close --run-id ... [--artifact ...] [--test ...] [--blocker ...]` — close with auto progress classification
- `continuity resume-plan` — print resume plan from latest record

Progress classifications: `NOOP_RECAP` → `ADVISORY_ONLY` → `EVIDENCE_DELTA` → `IMPLEMENTED_DELTA` → `VERIFIED_DELTA`.

Ledger path: `$LOCALAPPDATA/NEXUS/continuity/runs.jsonl` (override via `NEXUS_CONTINUITY_LEDGER` env var).

### 3. `nexusctl intel` — LLMWiki Dossier Pipeline

Wrap `WikiIntelPipeline` for evidence-claim and research-synthesis ingestion into canonical dossiers.

Subcommands:
- `intel stats` — known dossier count + lint summary
- `intel lint` — audit dossiers for missing VAP/provenance fields
- `intel ingest-claims <file.json>` — JSON array → dossiers (idempotent via fingerprint dedup)
- `intel ingest-synthesis <file.json>` — research synthesis → dossiers

When `--wiki-output-dir` is specified, memory dir co-locates as sibling to prevent cross-contamination.

### 4. Archive Janitor

Copied 12 legacy test/archive files from `~/.nexus_pi/` into `docs/handoff/opencodeCLIagents-archive/` with category subdirectories. Originals left in place per operator constraint.

## Verification Results

| Gate | Result |
|---|---|
| `pytest tests/nexusctl/ tests/vault/ tests/governor/ tests/archivist/ tests/nexusclaw/` | **1206 passed**, 1 pre-existing relay port failure (`test_modelrelay_defaults_are_lazy_and_node_port` — URL changed from `localhost:7350/api/models` to `127.0.0.1:7350/v1/models` from parallel session) |
| `pytest tests/nexusctl/test_intel_cli.py` | 6/6 passed |
| `pytest tests/nexusctl/test_continuity_cli.py` | 2/2 passed |
| `pytest tests/nexusctl/test_memory_cli.py` | 9/9 passed |
| `python scripts/gen_model_registry.py --check` | "registry artifacts in sync" |
| Secret-grep on all staged lines | 0 matches |
| Pre-commit hygiene hook | passed on every commit |

## Drift Corrections from Phase 0

| Claim | Reality | Action |
|---|---|---|
| "nexus_pi/ is continuing" | False — parallel session had already created `nexus_os/continuity/` + `nexusctl/continuity_cli.py` as untracked work | Integrated instead of duplicating; wired subparser + verified tests |
| "Step 3 (intel) needs DoppelGroundBridge.bridge_compiled" | True but bridge_compiled requires CompiledRecord objects (heavy import→compile pipeline objects). WikiIntelPipeline is the practical CLI surface | Built intel_cli.py around WikiIntelPipeline only; bridge_compiled remains for the API layer |
| "12 archive files to move" | 12 files confirmed on disk in ~/.nexus_pi/ | All 12 copied into repo archive |

## Substrate Reference Card

| Component | File | Role |
|---|---|---|
| DoppelGround bridge | `nexus_os/archivist/doppelground_bridge.py` | 12 source kinds → 8 vault channels |
| WikiIntelPipeline | `nexus_os/nexusclaw/wiki_intel_pipeline.py` | canonical LLMWiki dossiers |
| Memory channels | `nexus_os/vault/memory_channels.py` | 8-channel MemoryChannelManager |
| Trust kernel | `nexus_os/governor/trust_kernel.py` | event-sourced canonical trust |
| Trust scoring | `nexus_os/governor/trust_scoring.py` | LaneParams × lanes, scoring, CDR ladder |
| Trust engine v2 | `nexus_os/governor/trust_engine_v2.py` | next-gen engine |
| Persistence | `nexus_os/vault/persistent_trust_memory.py` | `~/.nexus/trust_memory.json` |
| Decay | `nexus_os/vault/decay_worker.py` | Mira earn-or-fade |
| Consolidation | `nexus_os/vault/consolidation_daemon.py` | Dream Cycle |
| Poisons | `nexus_os/vault/poisoning.py` | adversarial / memory-poisoning guards |
| Semantic backend | `nexus_os/vault/semantic_backend.py` | SEMANTIC channel backend |
| Cache | `nexus_os/vault/cache.py` | caching layer |
| Continuity ledger | `nexus_os/continuity/records.py` | append-only JSONL run records |
| nexusctl surface | `nexusctl/cli.py`, `nexusctl/{memory,continuity,intel}_cli.py` | operator-facing CLI |

## What Remains (for the next session)

1. **`nexusctl wiki refresh`** (Phase 2 step 5 / optional) — re-derive intel from raw-curation sources. Low priority; current `intel ingest-*` covers the main use case.

2. **Deprecate `model_memory.json`** — write forward-pointer in `01_PROJECT_STATE.md` noting that `nexusctl memory` supersedes the old `model_memory.json`. Per Phase 1 plan step 5.

3. **Recency-coverage algorithm** — the operator's novel algorithm (2h=full, 8h=full+delta, 24h=full+delta+edges, 4d=delta+edge+summary, 7d=summary+hash, 15d=hash+counts, 30d=hash+counts+drift, >30d=hash+counts) is spec'd in the Phase 1 plan but not yet implemented as a separate `coverage.py` module. The current `continuity coverage --hours N` provides raw time-window filtering; the full algorithm would add mode-aware summarization.

4. **Pre-existing test failure** — `test_modelrelay_defaults_are_lazy_and_node_port` in `tests/nexusclaw/test_coordinator.py` fails because `TelemetryIngest().url` changed. Not related to this work; needs a separate fix from whoever owns the relay URL migration (`localhost:7350/api/models` → `127.0.0.1:7350/v1/models`).

5. **Untracked parallel-session files** — `nexusctl/model_team_cli.py` (8.7KB) and its test file exist as untracked work from a parallel session. Not yet wired into `cli.py`. Validate and integrate when ready.

## Continuity Contract

Next session resume point:
```
Branch: opencodeCLIagents/continuity-substrate-2026-07-08
HEAD:   6b39c64a
Read:   docs/handoff/opencodeCLIagents-2026-07-08/02-phase-2-release-notes.md (this file)
Then:   Pick up from "What Remains" section above
```
