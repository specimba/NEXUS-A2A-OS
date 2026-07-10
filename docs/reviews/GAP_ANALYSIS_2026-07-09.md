# Gap Analysis & Improvement Plan — 2026-07-09

| Field | Value |
|-------|-------|
| **Date** | 2026-07-09 |
| **Scope** | Review last developments across codex + opencode lanes, identify gaps, plan improvements |
| **Branches reviewed** | `codex/specimba/nexus-core-solidify` (118 commits ahead, PR #52) + `opencodeCLIagents/continuity-substrate-2026-07-08` (2 handoff commits) |
| **Logs reviewed** | NEXUSopencodeMAINbackendMINIMAXm3NIMlog-30.txt (4,031 lines), NEXUSv4planningCODEXlog-22.txt (18,189 lines) |

## 1. Current Lane Activity Summary

### Codex Lane (CODEXlog-22, 18,189 lines)
- **Branch**: `codex/specimba/nexus-core-solidify` → pushed to `specimba/nexusalpha`, PR #52 "Before Codex Grounding PR" (118 commits ahead of main)
- **Work done**: 
  - Sentinel native implementation (18 files, +2,418 lines) — UiPath→NEXUS-native conversion
  - Provider quota hardening commit `a6c3c6f3` — NIM RPM 40→8, LongCat Preview→2.0 migration, intern-latest context fix, suspended-status override
  - Continuity substrate implementation (unstaged, +643/−49 over 7 files) — `nexus_os/continuity/records.py`, `nexusctl/continuity_cli.py`, `nexusctl/model_team_cli.py`
  - Browser-AI director continuity mirror — `progress_class_for_outro()`, `append_continuity_mirror()`
  - Papers12/13 intake — 93 files discovered + ingested, generalized `intake_papers.py`
  - Model-team role templates — Planner→LongCat, Researcher→intern-s2, Executor→LongCat, Verifier→intern-latest, Archivist→intern-s2
- **Test results**: 3901 passed / 98 failed / 181 errors (environmental — SQLite readonly + WinError 5 permission blocks)

### OpenCode Lane (MINIMAXm3NIMlog-30, 4,031 lines)
- **Branch**: `opencodeCLIagents/continuity-substrate-2026-07-08` (from `a6c3c6f3`, 2 planning-only commits)
- **Work done**:
  - Phase 0 substrate inventory (207 lines) — found existing DoppelGround bridge, 8-channel vault, trust kernel all already functional
  - Phase 1 migration plan (242 lines) — 5 new `nexusctl` subcommands: `memory`, `continuity`, `intel`, `wiki refresh`, `watchdog`
  - Operator's recency-coverage algorithm defined: 2h=FULL, 8h=80%, 24h=65%, 4d=45%, 7d=25%, 15d=15%, 30d=7%, heavy-load min 3.5-5%
- **Status**: PLANNING-ONLY, no code committed yet

## 2. Critical GAPS Identified

### Gap 1: Two agents building the same thing independently (COLLISION RISK)
**Severity**: HIGH
**Evidence**: 
- OpenCode drafted a Phase 1 migration plan for `nexusctl memory`, `nexusctl continuity`, `nexusctl intel` (log-30:3888-3894)
- Codex ACTUALLY IMPLEMENTED these: `nexus_os/continuity/records.py` (+222 lines), `nexusctl/continuity_cli.py` (+129 lines), `nexusctl/model_team_cli.py` (+186 lines) (CODEXlog-22:18176-18181)
- Both agents reference the same branch `opencodeCLIagents/continuity-substrate-2026-07-08`
- **Risk**: If both teams merge independently, there will be duplicate/conflicting implementations
**Fix needed**: Reconcile the codex implementation against the opencode spec. The codex implementation is closer to working; the opencode plan has the recency-coverage algorithm spec. Merge the algorithm spec into the codex implementation.

### Gap 2: GroundingDoctor SQLite readonly BLOCKER
**Severity**: CRITICAL
**Evidence**: `nexusctl grounding doctor --json` fails with `sqlite3.OperationalError: attempt to write a readonly database` (CODEXlog-22:729, 18081-18123)
**Impact**: GND-001 policy verification is impossible — the grounding doctor command is the verification mechanism per the policy
**Fix needed**: Fix `GroundingStore.__init__()` to handle read-only DB gracefully, or create the DB in a writable location (`~/.nexus/grounding.db` instead of repo-tracked location)

### Gap 3: 98 pytest failures from environment debt
**Severity**: HIGH
**Evidence**: Full suite = 98 failed, 3901 passed, 181 errors (CODEXlog-22:17963)
**Root cause**: `sqlite3.OperationalError: attempt to write a readonly database` + `PermissionError: [WinError 5] Access is denied` on `~/.nexus/trust_memory.json` and `.tmp/pytest_runtime`
**Impact**: Test gate is non-functional — cannot verify "4100 passed" baseline from FABLE5-03
**Fix needed**: Set `NEXUS_TEST_DB_PATH` to a writable temp dir for CI; fix the ACL on `~/.nexus/`; ensure `trust_memory.json` is created with correct permissions

### Gap 4: M0 corrections sprint not applied
**Severity**: HIGH
**Evidence**: 
- MiniMax license ✅ FIXED (registry v3)
- DPO judge replacement ⚠️ NOT YET APPLIED — `gen_guard_dpo_pairs.py` still references `intern-s2-preview` (needs → `deepseek-v4-pro`)
- Bench length→covariate ⚠️ NOT YET APPLIED
- Guard tier redesign ⚠️ NOT YET STARTED
**Fix needed**: Apply DPO judge fix, bench covariate fix, start guard diversity cascade design before M3

### Gap 5: Brain API (port 7352) still DOWN
**Severity**: CRITICAL
**Evidence**: Connection refused (grounding sweep report, CODEXlog-22)
**Impact**: Entire governance layer unreachable — KAIJU gates, governor, trust kernel cannot function at runtime
**Fix needed**: Diagnose startup failure — likely pip install -e . blocked or Python venv issue. The :7352 weak-auth fix from FABLE5-02 may have introduced a startup regression.

### Gap 6: Uncommitted working tree across two branches
**Severity**: MEDIUM
**Evidence**: 
- Codex: continuity implementation (7 files, +643/−49) + browser-AI director changes + papers intake — all UNSTAGED
- OpenCode: 10 tracked modifications carried through branch switch
- Combined: ~50+ files in a dirty state across both branches
**Fix needed**: Each lane must stage and commit their work separately before any merge attempt

### Gap 7: Operator's recency-coverage algorithm NOT implemented
**Severity**: HIGH
**Evidence**: The operator defined a novel time-based priority algorithm (log-30:2554):
```
2h = FULL     8h = 80%    24h = 65%   4d = 45%
7d = 25%     15d = 15%   30d = 7%    heavy-load min 3.5-5%
```
The opencode Phase 1 plan specifies it in `nexusctl continuity coverage --window 24h`, but the codex implementation has `ProgressClass` enum (`NOOP_RECAP, ADVISORY_ONLY, EVIDENCE_DELTA, IMPLEMENTED_DELTA, VERIFIED_DELTA`) which is a different model.
**Fix needed**: Reconcile — the codex `ProgressClass` is agent-output classification; the operator's coverage % is time-window-based content selection. Both are needed but they are different layers.

### Gap 8: Sentinel implementation unreconciled with hackathon disqualification
**Severity**: MEDIUM
**Evidence**: UiPath AgentHack was disqualified (CODEXlog-22:11-13 — platform eligibility failure). But:
- Codex created `nexus_os/sentinel/` (18 files) — adapting the disqualified code into NEXUS-native
- The code exists but is NOT committed (in the unstaged working tree)
- The hackathon repo `NEXUS_UiPathAgentHack` is a submodule with pending submod changes
**Fix needed**: Decide — either (a) commit the sentinel implementation as NEXUS-native code (porting the governance patterns), or (b) archive it. The UiPath disqualification does NOT make the governance patterns worthless.

### Gap 9: NIM free-tier capacity cascading
**Severity**: HIGH
**Evidence**:
- GLM-5.1: 410 Gone (removed from catalog)
- Kimi K2: 410 EOL
- MiniMax M3: DEGRADED (function lockout, transient)
- GLM-5.2: DEGRADED (cannot invoke functions)
- Only 3 of 11 NIM models alive: Nemotron Ultra, MiniMax M3 (transient), Qwen3.5-122B
- Codex updated the primary rotation: Nemotron Ultra → MiniMax M3 → Qwen3.5 122B (CODEXlog-22:1451-1462)
**Fix needed**: Register Alibaba Qwen3 (confirmed alive) in all config layers; promote InternAI as primary frontier (90M tokens/month); complete LongCat 2.0 migration

## 3. Improvement Plan (Prioritized)

### P0 — Immediate (Blocks Everything)

| # | Action | Owner Lane | Files | Status |
|---|--------|------------|-------|--------|
| 1 | Fix GroundingDoctor SQLite readonly blocker | Codex | `nexus_os/grounding/*.py` | BLOCKER — GND-001 verification impossible without it |
| 2 | Fix pytest environment debt (98 failures → 0) | Codex | `conftest.py`, `pyproject.toml` ACL fixes | BLOCKER — test gate non-functional |
| 3 | Diagnose Brain API :7352 startup failure | Codex | `nexus_os/bridge/server.py`, `master_daemon.py` | BLOCKER — governance runtime down |
| 4 | Reconcile codex implementation vs opencode plan for continuity | Both | `nexus_os/continuity/`, `nexusctl/continuity_cli.py` | COLLISION — both are building the same thing |
| 5 | Commit codex continuity implementation (7 files, +643) | Codex | `nexus_os/continuity/records.py`, `nexusctl/continuity_cli.py`, `nexusctl/model_team_cli.py` | UNSTAGED — needs explicit file list commit |

### P1 — Core (This Week)

| # | Action | Owner Lane | Files | Status |
|---|--------|------------|-------|--------|
| 6 | Apply M0 DPO judge fix | Either | `scripts/finetune/gen_guard_dpo_pairs.py` | NOT YET APPLIED |
| 7 | Register Alibaba Qwen3 + promote InternAI | Codex | `config/models.registry.json`, `model_sync.py` | NIM collapse mitigation |
| 8 | Implement recency-coverage algorithm | OpenCode | `nexus_os/continuity/coverage.py` (new) | Operator's novel spec needs implementation |
| 9 | Archive sentinel implementation (decision required) | Codex | `nexus_os/sentinel/` | Commit or archive |
| 10 | Bench length→covariate fix | Either | `nexus_os/benchmark/runner.py` | M0 item, NOT YET DONE |

### P2 — Infrastructure (Parallel)

| # | Action | Owner Lane | Files | Status |
|---|--------|------------|-------|--------|
| 11 | Hermes config apply (`hermes config set model.base_url http://127.0.0.1:7350/v1`) | Operator | CLI command | Proposed 4 times, never executed |
| 12 | Start M1 — llama-server router mode adoption | OpenCode | `nexus_os/relay/llama_server_router.py` (new) | Replaces Ollama reinstall blocker |
| 13 | Track F-2 frozen eval pack (M2 gate) | Either | `nexus_os/bench/frozen_eval_pack.py` (new) | Hard gate for any training |
| 14 | Fix UnifiedStateManage 0.0.0.0 bind | Either | `unified_state/state_manager.py` | Unauthenticated :8765/:8766 |
| 15 | Fix AdaptiveCircuitBreaker signature regression | Either | `nexus_os/gmr/circuit_breaker.py` | Crashes production callers |

## 4. Coordination Protocol (For Simultaneous Work)

### Lane boundaries (collision prevention)
- **Codex lane** owns: `codex/specimba/nexus-core-solidify` branch, `nexus_os/sentinel/`, provider/quota config, `config/models.registry.json`, `tests/relay/`, `nexusctl/models_cli.py`
- **OpenCode lane** owns: `opencodeCLIagents/continuity-substrate-2026-07-08` branch, `nexus_os/continuity/` (algorithm spec), `nexusctl/continuity_cli.py`, `nexus_os/grounding/` (fixes)
- **Shared files** (require coordination): `01_PROJECT_STATE.md`, `AGENTS.md`, `nexusctl/cli.py`, `docs/plans/*`

### Merge order when both branches complete
1. Merge codex PR #52 into main first (it has the provider/quota fixes + sentinel)
2. Cherry-pick opencode's `nexus_os/continuity/` additions into main
3. Reconcile any conflicts in `nexusctl/cli.py` (both added subcommands)
4. Verify full suite passes before pushing

### Communication protocol
- Each lane MUST read the other's latest commits before starting work
- Each lane MUST `git fetch` to see if the other has pushed new commits
- No changes to `01_PROJECT_STATE.md` without coordination (both lanes edit it)

## 5. Grok 4.5 Lane Review (Added 2026-07-10)

### Logs reviewed
- `NEXUSbuildubuntuGROK45logs-01.txt` (1,401 lines) — Grounding fixes, port plane, GMR/Chimera/LG pipeline
- `NEXUSbuildubuntuGROK45logs-02.txt` (849 lines) — Browser AI supervisor, A2A multi-lane collaboration

### What the Grok 4.5 lane resolved (from my original gap list)
| # | Original Gap Status | New Status | Evidence |
|---|---------------------|-----------|----------|
| Gap 2 | GroundingDoctor SQLite readonly BLOCKER | ✅ FIXED | `nexus_os/grounding/reliable_store.py` — writable-root candidates + RO degrade (commit `50382c01`) |
| Gap 3 | 98 pytest environment debt failures | ✅ FIXED | `tests/conftest.py` — session temp isolation for NEXUS_HOME, NEXUS_GROUNDING_ROOT, NEXUS_TRUST_MEMORY_PATH (commit `50382c01`) |
| Gap 5 | Brain API :7352 DOWN | ⚠️ STALE FINDING | Grok 4.5 verified :7352 is UP via live probe — my grounding sweep used unreliable WSL curl evidence |
| My "Port 7350 health broken" | 7350 /health returns 404 | ⚠️ FALSE NEGATIVE | ModelRelay npm serves `/` and `/v1/models`, not `/health` — port is UP, probe path was wrong |
| My "Hermes config never applied" | Proposed 4×, never executed | ✅ APPLIED | `hermes config set model.base_url http://127.0.0.1:7350/v1` — executed by Grok 4.5 lane (log-01:896-944) |

### New work from Grok 4.5 lane (not in original gaps)
| # | Deliverable | Commit | Files |
|---|-------------|--------|-------|
| G1 | Port plane 7350-7360 + `nexusctl ports doctor` | `50382c01` | `nexus_os/bridge/port_plane.py`, `nexusctl/cli.py`, `tests/bridge/test_port_plane.py` |
| G2 | GMR/Chimera/LG pipeline + telemetry | `f9ad5170` | `nexus_os/gmr/chimera_lg_pipeline.py`, `nexus_os/gmr/telemetry.py`, `nexusctl/cli.py` |
| G3 | CDP lane hardening (dedupe, preflight, restore) | `818406e5` | `tools/browser_ai_supervisor/dedupe_lane_tabs_cdp.mjs`, `lane_stack_preflight.mjs`, `grok_cdp_context_probe.mjs` |
| G4 | A2A Cycle 1 multi-lane collaboration | `754ccde3` | `multi_lane_a2a_cycle.mjs`, `prompts/a2a_cycle1/*`, `docs/reviews/NEXUS_A2A_C1_MULTI_LANE_COLLAB_2026-07-09.md` |
| G5 | Continuity ledger `NEXUScontinuity_runs.jsonl` | unstaged | `docs/operations/NEXUS_CONTINUITY_LEDGER.md`, `run_browser_ai_supervisor.ps1` |
| G6 | fix_lane_chrome parse fix (em-dash → ASCII) | `818406e5` | `scripts/fix_lane_chrome_interactive_window.ps1` |

### Revised P0 priority (after Grok 4.5 work)
| # | Action | Status | Owner |
|---|--------|--------|-------|
| 1 | ~~Fix GroundingDoctor SQLite readonly~~ | ✅ DONE (Grok 4.5) | — |
| 2 | ~~Fix pytest env debt (98 failures)~~ | ✅ DONE (Grok 4.5) | — |
| 3 | Diagnose Brain API :7352 startup | ✅ VERIFIED UP (Grok 4.5) | — |
| 4 | Reconcile codex + opencode continuity implementations | ⚠️ COLLISION GROWS — Grok 4.5 also on same branch | All 3 lanes |
| 5 | Commit unstaged work across all 3 lanes | ⚠️ ~60+ files unstaged | All lanes |

### Live A2A cycle evidence
- Grok: REPLY_COLLECTED (`NEXUS_PROOF_OK` verified in DOM)
- ChatGPT: message landed in thread (Pro upsell friction)
- DeepSeek: send mapped, evidence gap (body.innerText shell-only)
- Gemini, Qwen, Meta, Z.ai: lanes READY (preflight pass) but send not yet attempted
- A2A protocol: 8 steps (Preflight → Role-send → Wait evidence → Aggregate → Ledger → Synth → Verify Zo → Handoff Hermes)

### Key corrections to my grounding sweep report
1. "Brain API :7352 DOWN" was based on WSL curl which cannot see Windows localhost listeners — **should have probed from Windows PowerShell**
2. "Port 7350 health broken" was a false negative — ModelRelay npm doesn't serve `/health`, serves `/` and `/v1/models`
3. "Hermes config never applied" was accurate at the time but now resolved by Grok 4.5 lane

## 6. antiGRAV-11 Gap Closed (Added 2026-07-10)

### Previous gap
- **antiGRAVnexlog-11.txt** (~12,478 lines) — never fully read in initial grounding sweep (agent returned project state instead of log content)
- Marked as "contain whole set of model related structure of nexus system"

### What was found in full coverage
File: `NEXUSantiGRAVnexlog-11.txt` (12,478 lines, 6 chunks, 100% coverage per GND-001)

**Key discoveries**:
1. **Operator-defined canonical workflow (L2442)** — 3-tier VRAM budget with 1GB guard + 2.5GB rotatable = 3.5GB MAX local, then cloud elevation
2. **TIER_PRIMARY cloud rotation (8 models)** — kilocode/z-ai/glm-5.2, baseten/GLM-5.2, kilocode/nemotron-3-ultra, opencode/deepseek-v4-flash, kilocode/minimax-m3, nim/minimax-m3, nim/qwen3.5-122b
3. **TIER_FALLBACK** — longcat/LongCat-2.0, internai/intern-s2-preview
4. **TIER_SPECIALIST (code/SWE)** — opencode/deepseek-v4-flash, opencode/north-mini-code, ollama-cloud/qwen3-coder:480b, baseten/kimi-k2.7-code
5. **Local rotatable SLM stack (3B class, uncensored)** — `usermma/Mythos-nano-OBLITERATED`, `refinedneuro/refinedtoolcallv5-3b`, `mradermacher/VibeThinker-3B-Agentic-GGUF`
6. **Heavy coding (12B if full VRAM)** — `yuxinlu1/gemma-4-12B-coder-fable5-composer2.5-v1-GGUF`
7. **Guard cascade L1-L3** — `walledai/walledguard-edge` (0.6B), `meta-llama/Llama-Guard-3-1B` (1.5B), `ibm-granite/granite-guardian-3.2-3b-a800m` (3.3B)
8. **GMR Security Stack (model_rotator.py)** — L0 BashGemma-270M, L1 FunctionGemma-270M, L2 GLiGuard-300M, L3 arch-guard-300m, L4 meta-attack regex

### Critical corrections in the log
1. **35B local is WRONG** — 35B at Q4_K_M = ~20GB, forces 12GB weights to system RAM, PCIe bottleneck <1 tok/s. **Decision**: 35B models = Cloud-Only A2A lane
2. **Mythos-nano base has refusal overhead** — **Decision**: Use OBLITERATED variant (heretic via OBLITERATUS)
3. **VibeThinker-3B is NOT for tool-calling** — **Decision**: Use `refinedtoolcallv5-3b` for multi-turn
4. **GMR = ChimeraRouter (strategy) + ModelRelay (execution)** — separation of concerns

### Output deliverable
- **File written**: `C:\Users\speci.000\Documents\NEXUS\docs\plans\NEXUS_MODEL_USAGE_PLAN_2026-07-10.md` (232 lines)
- Contains: full model pools, tier rotation, guard cascade, embeddings, action items, file reference

### Other gaps closed by antiGRAV-11
- **NIM rate limit cascade** (P0, my gap 9) — AntiGRAV already FIXED: `NIM_HEAVY_COOLDOWN = 70s`, serial-only
- **GLM-5.2 invisibility in arena** — AntiGRAV FIXED: baseUrl injection + dynamic `ALL_ACTIVE_CLOUD_MODELS`
- **Provider discovery** — AntiGRAV wired ProviderRefresher daemon thread (3600s, chat_probe=False)
- **My "Ollama reinstall" blocker** — AntiGRAV shows llama-server router mode is the replacement strategy
