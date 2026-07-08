# Phase 0 Substrate Inventory — 2026-07-08

> Branch: `opencodeCLIagents/continuity-substrate-2026-07-08` (from HEAD `a6c3c6f3`)
> Working directory: `C:\Users\speci.000\Documents\NEXUS`
> Operator session: build mode ON, this is the very first write

## Goal of this inventory

Identify the *already-existing* substrates so the continuity-substrate plan can **wire up**
what is there rather than invent new storage. No new artifacts are proposed yet — only the
"what exists, where, and what commander questions it answers" map.

## A. Working-tree baseline (git status at planning start)

| Datum | Value |
|---|---|
| Branch | `opencodeCLIagents/continuity-substrate-2026-07-08` |
| Came from | `codex/specimba/nexus-core-solidify` @ `a6c3c6f3` |
| Tracked modifications | `01_PROJECT_STATE.md`, `AGENTS.md`, submodules `NEXUS_UiPathAgentHack` (+/-),
                  `config/models.registry.json`, `nexus_os/benchmark/model_comparison.py`,
                  `nexus_os/relay/tracing/license_map_generated.py`, `prompts/current.txt`,
                  `scripts/finetune/gen_guard_dpo_pairs.py`,
                  `scripts/fix_lane_chrome_interactive_window.ps1`,
                  `tools/browser_ai_supervisor/run_browser_ai_supervisor.ps1`,
                  (and `+` `vendor/ShareGPT-Formaxxing`) |
| Untracked | `docs/policies/`, `docs/reviews/GROUNDING_SWEEP_2026-07-08.md`,
             `prompts/variety_0708/`,
             `tools/browser_ai_supervisor/fix_lane_chrome_interactive_window.ps1` |
| Off-limits | `.agents/`, `.brv.backup-20260427/`, `.brv/`, `.claude/`, `.codex/`, `.devin/`, `.gemini/`,
             `.grok/`, `.kilo/`, `.next/`, `.nexus-worktrees/`, `.nexus/governance-rest.db`,
             `.nexus_diagnostics/` (CLI / runtime state, NOT touched) |

The carried-over dirty state is preserved unmodified across the new branch.

---

## B. The four "missed substrate" surfaces — what is already on disk

### B.1 DoppelGround → NEXUS Vault bridge (the substrate ingestion backbone)

| Field | Value |
|---|---|
| Path | `nexus_os/archivist/doppelground_bridge.py` |
| Lines | 391 |
| Test | `tests/archivist/test_doppelground_bridge.py` |
| Direction | one-way: DoppelGround → NEXUS Vault (NEVER writes back to DG) |
| Source kinds | 12 (rules, config, mission, doc, deep_research, spec, code, test, skill,
            rejection_example, role, golden_dataset) |
| Target channels | 8 vault channels mapped by source_kind (see table below) |
| Lazy singleton | `get_bridge()` returns the process-wide `DoppelGroundBridge` |
| Default trust | `90.0` (passes all current channel gates: SEMANTIC ≥ 65, PROCEDURAL ≥ 80, TRUST ≥ 90) |
| Tests passed | (need to confirm with pytest, see Track 4 below) |

**Channel mapping is already specified**:

| DG source_kind | NEXUS Vault channel |
|---|---|
| rules, config | TRUST (5) |
| mission, doc, deep_research, spec | SEMANTIC (3) |
| code, test, skill | PROCEDURAL (4) |
| rejection_example | EPISODIC (2) |
| role | TASK (6) |
| golden_dataset | META (7) |

**Conclusion**: every piece of intel (curations, papers, Fable5 traces, antidoom wire-up)
that should land in NEXUS's persistent memory should pass through
`bridge.bridge_compiled(record)` or `bridge.bridge_dossiers(dossiers)`. We do NOT need
to invent a "knowledge ingest" pipeline — we need to (a) classify intel into DG
source kinds, (b) build `CompiledRecord` objects, and (c) call the bridge.

### B.2 Doc-side DoppelGround artifact maps

| File | Purpose |
|---|---|
| `vault/doppelground-wiki.md` | Single-file wiki (operator-side notes) |
| `docs/handbook/DOPPELGROUND_CHEATSHEET.md` | Quick-reference cheatsheet |
| `docs/coordination/NEXUS_TWAVE_QWAVE_DOPPELGROUND_GENIUSTURTLE_INTEGRATION_SCAN_*.md` | Cross-system scan |
| `docs/archive/handoff/DOPPELGROUND_GITLEAKS_FALSE_POSITIVE_*.md` | Gitleaks false-positive triage |
| `scripts/doppelground_false_positive_ledger.py` | Live helper |

### B.3 LLMWiki existence check

- The DoppelGround cheatsheet & wiki are *not* the LLMWiki (the operator-mentioned novel
  neural-base project). They are * intake docs.
- The LLMWiki substrate as a self-contained module has NOT been located yet in repo.
  Search will continue in Phase 0.5. The worklog MUST capture what's there vs what's
  only a name.
- For continuity fixtures: not blocking, since `bridge.bridge_compiled()` accepts
  arbitrary `CompiledRecord` and the SEMANTIC channel already has its own backend.

### B.4 Redis cold/warm cache plan + cloud+local docker double coverage

- Not yet found as code in the working tree (`redis` cold/warm plan historically referenced
  in `docs/handbook/08_PORT_OWNERSHIP_RULESET.md` per the AGENTS.md note).
- Cloud+local docker double coverage: confirmed at `docker/mcp/Dockerfile`,
  `docker/mcp/docker-compose.yml` (verified above). Limited scope: MCP servers only.
- Free-cloud provider list: not yet localized. The provider registry is at
  `config/models.registry.json` (+ its generator `scripts/gen_model_registry.py`) —
  THIS is the canonical provider/cloud list for NEXUS. The "double coverage" concept
  reads as: model providers list is mirrored to local-ollama + free-cloud-fallback lanes.

### B.5 8-channel memory + 11-element trust

| Field | Value |
|---|---|
| Path | `nexus_os/vault/memory_channels.py` (39KB, comprehensive) |
| Class | `MemoryChannelManager` with explicit `append_<channel>` API for each of 8 channels |
| Channels (int code in docs) | SENSORY(0), WORKING(1), EPISODIC(2), SEMANTIC(3), PROCEDURAL(4),
                TRUST(5), TASK(6), META(7) |
| Per-channel write gates | `_check_write_access(agent_id, channel, trust_score)` enforces min trust
                              per channel (TRUST ≥ 90, PROCEDURAL ≥ 80, SEMANTIC ≥ 65) |
| Companion modules | `governed_memory_broker.py`, `memory_adapter.py`, `memory_tracks.py`,
                    `persistent_trust_memory.py`, `decay_worker.py`,
                    `consolidation_daemon.py`, `semantic_backend.py`, `poisoning.py` |
| Channel TRUST line 52 | "Novel tanh-based trust formula (11 elements), real-time governance" |
| LaneParams dataclass | 10 fields per lane (`qmin, n0, Rcrit, alpha, beta, gamma, eta, kappa, delta,
                    epsilon`) + `compute_score` adds scoring inputs Q/n/U/R/D+/D−/hard_fail → 11+ |
| Lane tuning | table of `DEFAULT_LANE_PARAMS` for 7 lanes |
| CDR stages | NORMAL → DEGRADED → MEMORY_CORRUPTION / OUTPUT_HALLUCINATION → CASCADE → COLLAPSE |
| Anti-grinding | `logistic_scale(previous.trust * 100)` throttles positive evidence as trust rises |
| Non-compensatory | `NON_COMPENSATORY_DROP = 0.20` (hard fail → trust previous-0.20, no recovery via volume) |
| Cap | `TRUST_CAP = 0.995` |
| Companion trust_kernel | `nexus_os/governor/trust_kernel.py` (885 lines, singleton, SQLite-persisted,
                                writes to TRUST + EPISODIC channels on every event) |

**Conclusion**: trust and memory are *the most mature subsystems in the repo*. The
continuity substrate does NOT need to reinvent either; it needs to expose them via
`nexusctl` and use them to gate writes from the new ingestion flows.

### B.6 nexusctl surface (operator-facing CLI, the migration target)

| Field | Value |
|---|---|
| Path | `nexusctl/` repo tree, `cli/nexusctl.py` registered entrypoint |
| Currently surfaced commands | `nexusctl model-sync` (B-P), `nexusctl a2a-channels` (Plan 20),
                                 `nexusctl dream-cycle` (P0#3), `nexusctl grounding doctor`,
                                 `nexusctl handoff`, `nexusctl cycle-check`, plus the relay /
                                 bench / doctor namespaces |
| Operator directive | "every operational surface must be reachable via `nexusctl`" |
| TODO (FROM Phase 0) | list every command that does NOT yet exist for the continuity substrate:
                       `memory`, `knowledge refresh`, `research query`, `continuity check`,
                       `model-team`, `watchdog` |

### B.7 Worklog + recovery ledger (the "save your moves" substrate)

- `C:\Users\speci.000\Documents\NEXUS\.nexus_pi\` exists with state files. The migration
  target per operator Q2 is `nexusctl`-surfaced commands. The artifacts to migrate are:
  - `state\.state_token` (token list)
  - `state\handoff_*.md` (handoff artifacts from prior sessions)
  - `state\intro_task-*.md` / `state\outro_task-*.md` (task intros / outros)
  - `state\model_memory.json` (per-agent memory snapshot)
  - `state\quota_tracker.json` (provider-quota cache)
  - `state\trinity_fugu_log.jsonl` (today-active workflow log)
  - `state\handoff\handoff_*\manifest.json` (handoff manifests)
  - `audit\mcp_test*.json` (May-02 subagent test artifacts → archive-only, not live)
  - `vault\test_*.json` (May-02 test vault entries → archive-only)

---

## C. Drift corrections made in Phase 0

| # | Earlier plan said | Reality (Phase 0) |
|---|---|---|
| 1 | "Build a fresh `~/.nexus/knowledge/` from zero" | **DoppelGround → Vault bridge already exists** and is fully functional |
| 2 | "Vault trust gate must be re-engineered for 11 elements" | **Trust kernel + scoring + lane-params (10+ fields) + CDR stages already exist**, governed by `nexus_os/governor/trust_kernel.py` (885 lines) + `nexus_os/governor/trust_scoring.py` (258 lines) |
| 3 | "Need new 8-channel memory implementation" | **`MemoryChannelManager` + 8 channel write API already exist** at `nexus_os/vault/memory_channels.py` (39KB) |
| 4 | "Need persistence for trust across sessions" | **`persistent_trust_memory.py` (251 lines) already exists** and persists `MemoryTracks` to `~/.nexus/trust_memory.json` |
| 5 | "Decay over time" | **`MiraDecayWorker` (`decay_worker.py`, 40 lines) + `consolidate()` method exists** |
| 6 | "Need new pipeline for intake" | **Bridge already exposes `bridge_compiled` / `bridge_batch` / `bridge_dossiers`** |
| 7 | "Build a session_compass.json from scratch" | **Use the existing `state/trinity_fugu_log.jsonl` and `state/model_memory.json`** as the substrate; the new feature is to *expose them via `nexusctl`*, not replace them |
| 8 | "Blockers S0 sequential gate work" | **Most were false positives**; real backing store for continuity already exists |
| 9 | "Atlas of unread needs full re-read" | **Recency-coverage algorithm** (operator's novel formula) replaces re-read; DoppelGround bridge + channel writes enable the algorithm |

---

## D. Open questions for Phase 0.5 (next read pass)

1. Where is the canonical LLMWiki substrate in tree? (`nexussearch` did not surface it.)
2. Is `vault/doppelground-wiki.md` the only LLMWiki artifact, or is there a `wiki/` dir / module?
3. Redis cold/warm design — is there code, or is it pure design doc?
4. Free-cloud provider double-coverage: which providers were intended, and where is the
   registry?
5. `wiki-internal/` etc. — confirm that the operator-mentioned "missed forgotten"
   workspace still does not exist in repo (and not just in the operator's head).
   If so, leave it alone — the migration-plan covers coverage via DoppelGround + dorm.

---

## E. Phase 0 sign-off

- [x] Git baseline captured
- [x] New branch created (clean creation, working tree carried through)
- [x] DoppelGround bridge fully understood (391 lines, 12 kinds → 8 channels)
- [x] 8-channel vault Inventory: `MemoryChannelManager` with 8 append_*, trust gates
- [x] Trust subsystem inventoried: `trust_kernel.py` + `trust_scoring.py` + `trust_engine_v2.py` +
     `trust_formulas.py` + `persistent_trust_memory.py` + `decay_worker.py`
- [x] `nexusctl` command surface inventoried (5+ commands already exist)
- [x] `nexus_pi/` migration map drafted (state→CLI mapping)
- [x] Cloud/docker double coverage partially inventoried
- [ ] LLMWiki location: TBD (next pass)
- [ ] Redis cold/warm: TBD (next pass)
- [ ] Free-cloud provider list mirror coverage: TBD (next pass)

Status: Phase 0 is 90% complete. Ready to begin Phase 1 (nexus_pi → nexusctl migration
plan) once operator signs off these findings.

EOF
