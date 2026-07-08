# Phase 1 — nexus_pi → nexusctl Migration Plan (planning-only)

> Status: PLANNING-ONLY. No code changes proposed in this document.
> Companion: `00-phase-0-substrate-inventory.md` (committed earlier as the substrate map).
> Goal of this document: hand off a precise migration contract so the next session (or another
> agent) can implement without re-doing the survey.

## 0. Operator-confirmed constraints (do not violate)

1. **No touching of**: API keys, raw logs in `C:\Users\speci.000\Downloads\NEXUSlogs\`,
   artifacts/reports in `C:\Users\speci.000\Downloads\ARCHIVIST\`, datasets, the
   encrypted `~/.nexus_pi/vault\test_*.json`, the May-2026 subagent test artifacts.
2. **Add new, don't replace**: every artifact currently under `~/.nexus_pi\` must be
   mapped to a *new* `nexusctl` subcommand location; original files are left in place
   until the operator explicitly approves deletion.
3. **No blind imitation**: any Fable5 / Antigravity / Hermes / OpenClaw / Codex pattern
   adapted into a `nexusctl` command must be *transformed* through NEXUS, not pasted.
4. **Branch**: `opencodeCLIagents/continuity-substrate-2026-07-08`. Never edit on
   `codex/specimba/nexus-core-solidify` (that is Codex's PR #52 territory).
5. **Pace per session**: anything from 10-minute active to 4-12-hour AFK long-run is
   supported. Continuity is preserved either way; this plan encodes that property.
6. **Git hygiene**: explicit file lists per commit. Never `git add .`. Pre-flight
   `git diff --cached` empty of unintended paths. Pre-commit secret-grep on added lines.

## 1. nexus_pi artifact inventory (already-known, restated from Phase 0)

`%USERPROFILE%\.nexus_pi\`

| Path | Bytes | LastWrite | Migration target |
|---|---|---|---|
| state\.state_token | 64 | 2026-07-02 | dropped — runtime token, regenerated on demand |
| state\handoff_handoff-b055e16f.md | 953 | 2026-06-22 | archive → `docs/handoff/opencodeCLIagents-archive\` |
| state\intro_task-1431efac.md | 645 | 2026-06-22 | archive → same dir; the `intro/outro` shape becomes `nexusctl handoff --task-id` |
| state\intro_task-244ee722.md | 610 | 2026-06-23 | archive |
| state\intro_task-3d4e22f6.md | 595 | 2026-06-23 | archive |
| state\intro_task-8159e31f.md | 625 | 2026-06-22 | archive |
| state\model_memory.json | 4269 | 2026-06-23 | migrate → `nexusctl memory list-agent` (intent) |
| state\outro_task-1431efac.md | 905 | 2026-06-22 | archive |
| state\quota_tracker.json | 218 | 2026-06-23 | supersede by `nexusctl quota status` (already exists; this file holds legacy stale data) |
| state\trinity_fugu_log.jsonl | 4208 | 2026-07-08 11:33 | live copy → `nexusctl continuity log-trinity` (intent) |
| state\handoff\handoff_20260616_064312\manifest.json | 253 | 2026-06-16 | archive |
| state\handoff\handoff_20260616_075650\manifest.json | 253 | 2026-06-16 | archive |
| audit\mcp_test-agent_1777728425.json | 166 | 2026-05-02 | archive (test artifact, never load) |
| audit\mcp_test-agent-001_1777728338.json | 185 | 2026-05-02 | archive |
| vault\test_test_key.json | 109 | 2026-05-02 | archive (test vault entry, never load) |
| vault\test_test_mcp.json | 104 | 2026-05-02 | archive |

## 2. Existing `nexusctl` surface (1209-line main, replay of Phase 0 scope)

Current subcommands:

- `cycle-check`, `doctor`, `status`, `handoff`
- `wiki check`
- `disk-rescue level6`, `disk-rescue kilo-forensics`
- `nexusclaw status`, `nexusclaw dispatch-dry-run`
- `pipeline` (import → compile → fit)
- `models verify|reconcile|status|list`
- `quota status|verify|plan`
- `model-sync`
- `a2a-channels --list|--publish|--subscribe|--consolidate|--stats`
- `dream-cycle`, `hallucination`, `adrf`, `monitor`
- `grok-lane doctor`
- `grounding doctor|status|scan|watch|promote`

Missing for continuity substrate (Phase 2 design set):

1. `nexusctl memory <sub>` — read/write access to the 8 vault channels
2. `nexusctl continuity <sub>` — session compass, period coverage, recency-coverage algo
3. `nexusctl intel <sub>` — DoppelGround bridge drivers + wiki dossier pipeline controls
4. `nexusctl wiki refresh` (optional) — re-derive intel from a raw-curation source

## 3. The 5 new `nexusctl` subcommands — proposed spec (PLANNING-ONLY)

### 3.1 `nexusctl memory`

Pipes straight through to `nexus_os/vault/memory_channels.py::MemoryChannelManager`.

- `nexusctl memory show <channel> [--agent <id>] [--since <iso>] [--limit <n>]`
  — list records in a channel (defaults to current agent id, last 7 days, 50)
- `nexusctl memory append <channel> --content <text> [--topic …] [--tags …]`
  — append a single record (needed for `intel` runs)
- `nexusctl memory trust [agent_id]`
  — print `TrustKernel.get_snapshot(...)` for one agent (or current)
- `nexusctl memory channels`
  — list the 8 channels with their write-gate min-trust thresholds

Implementation: thin wrapper at `nexusctl/memory_cli.py` + argparse entries in
`nexusctl/cli.py`.

### 3.2 `nexusctl continuity`

- `nexusctl continuity compass [--session-id <id>] [--output <json|markdown>]`
  — produce a session compass (interrupted-session resume snapshot)
- `nexusctl continuity coverage [--window 2h|8h|24h|4d|7d|15d|30d] [--mode full|delta|hash]`
  — the operator's recency-coverage algorithm. Default window = 24h.
- `nexusctl continuity check [--since <iso>] [--report-only]`
  — the "session_open vs session_close" test: gather intel refs at
  `since` and now, ask the LLM-on-LLMWiki (or DoppelGround classifier) whether the
  delta is net-positive. Hard-fail if empty/dropped.
- `nexusctl continuity log [--source trinity|fugu|both] [--last <n>]`
  — read the live `~/.nexus_pi/state\trinity_fugu_log.jsonl` (operator already uses it)

The coverage algorithm — operator's novel shape, recap:

| Window | Coverage target mode |
|---|---|
| last 2 h | full |
| last 8 h | full + most-recent delta |
| last 24 h | full + delta + edge commits |
| last 4 d | delta + edge + selected-summary |
| last 7 d | selected-summary + hash-only for unselected |
| last 15 d | hash-only + per-channel counts |
| last 30 d | hash-only + per-channel counts + drift indicator |
| > 30 d | hash-only + per-channel counts only (heavy-load min 3.5–5%) |

This is the **system's continuity algorithm**: it doesn't *need* a re-read of
old material because the algorithm already summarises and hashes by time. New
sessions read what they need off the recent end; older material is referenced
by hash + summary when triggered.

### 3.3 `nexusctl intel`

- `nexusctl intel bridge <record.json>`
  — load a CompiledRecord from JSON and `bridge.bridge_compiled(...)` it
- `nexusctl intel dossier <topic> <file.md>`
  — synthesise a WikiDossier via `WikiIntelPipeline.ingest_evidence_claims(...)`
  (or `ingest_research_synthesis`) and `write_dossiers(...)`
- `nexusctl intel lint`
  — `WikiIntelPipeline.lint()` over `docs/wiki/wiki_output/dossiers/`
- `nexusctl intel stats`
  — dossier count, missing-vap, missing-canonical-ref counts

### 3.4 `nexusctl wiki refresh` (optional, Phase 2+)

Daily-pull-from-kb routes. Not in Phase 2 minimum.

### 3.5 reserved expansion slot

Future: `nexusctl watchdog doom-loop-check <model-id>` — periodic anti-doom probe
(`slop-forensics`-style) over a held-out probe set. Not in Phase 2 minimum.

## 4. Migration mechanics — old-file policy

1. **Add a new top-level `docs/handoff/opencodeCLIagents-archive/`** for the
   archive-only artifacts (handoff manifests, intro/outro, the May-02 test
   artifacts). Move via `git mv` so history follows. Single commit.
2. **Do not** delete `~/.nexus_pi\state\.state_token` (regenerated, harmless).
3. **Do not** delete `~/.nexus_pi\state\trinity_fugu_log.jsonl` (live). `nexusctl
   continuity log` will keep reading from it; nothing changes for the writer side
   until/unless the legacy writer is replaced.
4. **Do not** delete `~/.nexus_pi\state\quota_tracker.json` immediately. It is
   superseded by `nexusctl quota status` but deprecate gracefully (mark in
   `01_PROJECT_STATE.md`).
5. **Do not** delete `~/.nexus_pi\state\model_memory.json`. Migrate content into
   the META channel via `intel bridge` (since META is the right home for
   "memory about memory"); keep the raw file as a backup.
6. **Encrypted test vault**: never load. Just archive and leave in place.

## 5. Phase-sequence for migration execution

The recommended sequence for the next session (or for another agent implementing
this plan). Each step is a tight scope, single commit, ≤500 LOC.

| Step | Action | Files | Verification |
|---|---|---|---|
| 1 | Archive the 8 test/archive files into `docs/handoff/opencodeCLIagents-archive/` | `docs/handoff/opencodeCLIagents-archive/{mcp_test,old_handoffs,intro_outro}/` | `git status`, secret-grep, full pytest |
| 2 | Add `nexusctl memory` (Section 3.1) | `nexusctl/memory_cli.py`, `nexusctl/cli.py` | `nexusctl memory channels` prints 8; `nexusctl memory trust` returns snapshot |
| 3 | Add `nexusctl continuity` (Section 3.2) | `nexusctl/continuity_cli.py`, `nexusctl/cli.py`, new `nexus_os/continuity/` (340-line budget) | `nexusctl continuity coverage --window 24h` returns json; pytest unit-tests the algorithm |
| 4 | Add `nexusctl intel` (Section 3.3) | `nexusctl/intel_cli.py`, `nexusctl/cli.py` (deepening the existing `pipeline` command) | `nexusctl intel lint` returns dossier counts; same shape as wiki lint |
| 5 | Deprecate `model_memory.json`, write 01_PROJECT_STATE.md forward-pointer + a release note at `docs/handoff/opencodeCLIagents-2026-07-08/01-continuity-substrate-release-notes.md` | `docs/handoff/opencodeCLIagents-2026-07-08/0*.md`, `01_PROJECT_STATE.md` | `nexusctl status` prints continuity fields |

Each step independently committable and recoverable via `git revert`. The plan
itself is recoverable at this file's commit hash.

## 6. Operator-facing test gate per step

Before each commit, run:

```sh
python -m pytest -q tests/nexusctl/ tests/vault/ tests/nexusclaw/ \
    tests/governor/ tests/archivist/ tests/registry/ tests/models/ \
    tests/tracing/ tests/security/ -k "not perf and not stress" \
    --tb=short
python scripts/gen_model_registry.py --check
nexusctl doctor --report-only
```

Comparison to current baseline: Fable5-03 last full gate = **4100 passed / 61
skipped**. Each step must hold or raise that number. No new failures, no new
skips. (Local pytest under 80s as in the existing test layout.)

## 7. Substrate summary card (deliverable for the next session)

After Step 5 lands, snapshot this table in `01_PROJECT_STATE.md`:

| Substrate | File | Role |
|---|---|---|
| DoppelGround bridge | `nexus_os/archivist/doppelground_bridge.py` | 12 source kinds → 8 vault channels |
| WikiIntelPipeline | `nexus_os/nexusclaw/wiki_intel_pipeline.py` | canonical LLMWiki dossiers |
| Memory channels | `nexus_os/vault/memory_channels.py` | 8-channel MemoryChannelManager |
| Trust kernel | `nexus_os/governor/trust_kernel.py` | event-sourced canonical trust, Bayesian, CDI |
| Trust scoring | `nexus_os/governor/trust_scoring.py` | LaneParams × lanes, scoring, CDR ladder |
| Trust engine v2 | `nexus_os/governor/trust_engine_v2.py` | next-gen engine (read next) |
| Persistence | `nexus_os/vault/persistent_trust_memory.py` | `~/.nexus/trust_memory.json` |
| Decay | `nexus_os/vault/decay_worker.py` | Mira earn-or-fade |
| Consolidation | `nexus_os/vault/consolidation_daemon.py` | Dream Cycle |
| Poisons | `nexus_os/vault/poisoning.py` | adversarial / memory-poisoning guards |
| Semantic backend | `nexus_os/vault/semantic_backend.py` | SEMANTIC channel backend |
| Cache | `nexus_os/vault/cache.py` | caching layer |
| nexusctl surface | `nexusctl/cli.py`, `nexusctl/{memory,continuity,intel}_cli.py` | operator-facing CLI |

## 8. Open questions this plan does NOT solve

Carried to Phase 2+:

1. Redis cold/warm split — design-only today; not implemented. M6 of the milestone
   doc owns this. Need to confirm that the operator wants this implemented in NEXUS
   or borrowed from an upstream (e.g. Cloudflare KV, Upstash).
2. Free-cloud + local-docker double-coverage — design-only. M6.
3. HelioAI organization ownership — operator confirmed; operator-owned material
   is for inspiration only, never SFT-imitation. The `nexusctl intel dossier`
   pipeline handles this through provenance / `disposition=rejection` flags.
4. Knowledge ingest cadence — operator said "daily, not monthly". The cadence of
   `nexusctl wiki refresh` (when implemented) is daily. Codex/PR-#52 push
   decision is not blocking any of these steps.
5. Fable5 raw session log → system-evolution training material — this is the
   worklog as training-raw-material pattern: every `nexusctl continuity log`
   call captures the worklog text; the Fable5 log is *evidence*, the
   worklog is *training row*.

## 9. Sign-off

This document is the planning boundary. Implementation requires:

- Operator approval of the entire plan
- A green pytest baseline (4100 passed / 61 skipped)
- A clean working tree (no unrelated staged changes)

After approval, the next session (any CLI) can resume from this file path and
implement the plan step-by-step without re-reading the archived curations.

— end of Phase 1 plan —
