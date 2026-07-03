# Revived Plans Ledger — 2026-07-03/04

**Purpose:** deep-dive recovery of every execution-ready plan that was
designed, mined, or half-started and then buried by session churn —
reconciled against the repo state as of slices E-G
(`7d668662` RIFT, `c7eb3c80` TokenHD, `ad2f55a4` session harvester).
Sources: PAPERS miner ranked report (session `db11151e`), last-60h
NEXUSlogs miner report (session `9484b0b0`), `ROADMAP_ADDITIONS_2026-07-03.md`
(M1-M6), `IMPROVEMENT_ROADMAP_2026-07-02.md` (P3-P5, Track F). Both miner
reports are preserved verbatim in the recovery ledger
(`~/.nexus/recovery/ledger.jsonl`, kind=`agent_report`) — the harvester
built in slice G is now the standing net for this class of loss.

Legend: **NOW** = unblocked, do next · **GATED** = blocked on an event ·
**OPERATOR** = needs a human action · **CLOSED** = resolved since mined ·
**DEAD** = overtaken by events.

---

## 1. PAPERS upgrades #4-14 + honorable mentions (miner ranking, 2026-07-03)

Top-3 (#1 MemLineage, #2 TokenHD, #3 RIFT) are DONE: `05e6cd55`,
`c7eb3c80` (scaffold — trained detector still open, see #2 below),
`7d668662`.

| # | Upgrade | Status | Execution-ready next step |
|---|---|---|---|
| 2b | TokenHD **trained detector** (the scaffold's missing organ) | GATED on Track F infra | Synthesize token-level annotations via the paper's data engine over `fable5_cot_merged.jsonl` + relay judge; train 0.6B (Qwen3-0.6B) on Lightning T4; serve behind `NEXUS_TOKENHD_ENDPOINT`; flip `tokenhd_weight=0.15`. |
| 4 | FAPO flawed-positive reward penalty for GRPO v2 | GATED on Track F-5 (GRPO runner) | When writing the GRPO runner, add the parameter-free flawed-positive penalty term; reuse the process-level GenRM from #8. Files: future `nexus_os/finetune/grpo.py`. |
| 5 | RATIONAL / ReSA answer-then-check safety tuning | NOW (data prep) | Add a `reasoning` field variant to the guard pair generator (reason-about-safety-then-verdict); ReSA is data-efficient (500 samples suffice) — a 500-pair reasoned subset is one `gen_guard_dpo_pairs.py` flag away. |
| 6 | Booster/Lisa alignment-stage immunization | GATED on first real training run | Apply Booster's regularizer in the Track F-3 LoRA runner config from day one; cite `papers12` threat-model set (Virus, Safety-Tax) in the eval pack design. |
| 7 | TRINITY evolved hidden-state coordinator | DEFER (L effort) | Revisit after P5-5 semantic probes; needs hidden-state access → open-weight lanes only. Entry point would be ChimeraRouter profile selection. |
| 8 | DeepSeek-GRM + SPCT generalist reward model | GATED on Track F-5 | One GenRM serves GRPO reward AND peer-review aggregation (`gmr/peer_review.py` meta-RM voting > flipped-triple). Spec it inside the GRPO runner design doc before building either. |
| 9 | SimpleMem semantic-lossless compression | NOW (S slice) | Add the LLM-judge semantic-density gate to the consolidation daemon's dossier intake (`archivist/fit.py` + vault consolidation) — drop-in, cuts dream-cycle token cost ~30×. |
| 10 | Evo-Memory/ReMem test-time experience reuse | NOW (M slice) | Vault META/PROCEDURAL channels already exist; add an action→think→refine post-task hook in the outro/HandoffNote path (`model_relay/persistent_memory.py`) writing strategy notes, retrieved by TaskIntroBuilder. |
| 11 | Tandem cost-aware LLM-guides-SLM cascade | DEFER | Concrete primitive for GMR L2 tandem tier under quota pressure; revisit when quota pressure is real (post M5 purge). |
| 12 | Off-the-Shelf Process Scorers (CGS) | NOW (S-M, training-free) | Chunk-level likelihood scoring needs only per-token logprobs — which P2-1 already feeds. Add as a peer-review verify-tier option in `gmr/peer_review.py`; no reward model needed. |
| 13 | Refusal-direction monitoring | GATED on M1 (local open-weight model) | Needs activations → local inference. After Ollama reinstall: compute refusal-direction projection as a third CHD lane beside Bebop + TokenHD. |
| 14 | RAIN rewindable self-alignment | DEFER (latency cost) | Zero-training guard for API models; candidate for HIGH/CRITICAL-clearance requests only. Design note in KAIJU clearance docs when picked up. |
| HM | MemEvolve, Darwin-MRI trust-weighted merging, AEPO, DeepCritic, RouteLLM, hybrid-KV papers | PARKED | Darwin's trust-weighted merging is the one to remember at Phase-2 SAMM merge time (TrustKernel × mergekit crossover). |

## 2. 07-02 evening open threads (last-60h miner §2) — reconciled

| Thread | Then | Now | Action |
|---|---|---|---|
| UiPath v1.0.2 publish + Cloud Maestro case | blocked on OAuth, unpublished | **DEAD** — submission DISQUALIFIED (had to run on UiPath Cloud); CODEX built `nexus_os/sentinel/` native replacement, adopted+repaired in `bf5d4221` | Close the thread; M2 (Sentinel integration review) is the successor and is DONE for the adopted parts — remaining: wire Sentinel case-events into vault TASK channel (still open, S slice). |
| Track 1 vs Track 2 labeling inconsistency | judge-facing risk | DEAD with disqualification | None. Lesson recorded in `docs/research/UIPATH_AGENTHACK_SENTINEL_SOURCE_CARD_2026-07-03.md`. |
| Demo video quality | contested | DEAD | None. |
| Skills org-promotion (3 Simular skills) | pending admin | **OPERATOR** (one-click admin promote) | Keep on operator checklist. |
| A2A v3 long run (post-fix) | queued: RecoverChrome → ListTabs → A2AExperiment | still pending; HERMES lane owns it; `docs/operations/A2A_LONG_RUN_EXPERIMENT.md` exists in working tree | **GATED on HERMES lane** — do not touch CDP collision zone (P5-4 rule). Median-wait table still empty; v3 run is the data source. |
| ollama-cloud models not surfacing in :7350 | Node relay enumeration bug (not config) | Partially overtaken: 07-02 recovery session saw ollama-cloud minimax-m3/qwen3-coder-next UP on :7350 after hot-reload | **VERIFY-THEN-CLOSE**: `nexusctl models verify` against :7350; if all ollama-cloud registry entries enumerate, close; else file the Node `config.generated.ts` enumeration bug with the probe output. DeepSeek lane owns relay-layer files. |
| MCP SET2 (47-server fleet) enumeration timeouts | tools/list timed out on every probe; 43 integration tests never ran | unchanged; profiles `nexus_mcp_profile_*.yaml` sit UNCOMMITTED in working tree (ownership unconfirmed — P5-1 flag) | **GATED on P5-1** and ownership confirmation. First step is small: run `tools/list` against ONE server (memory) with a 120s budget to split "gateway slow" from "config broken". |
| Kilocode archivist todos (~5 WARNING/SUGGESTION) | open | unclaimed | **NOW (S)**: extract shared `TOPIC_TO_SOURCE_KIND`, wire `CATEGORIZE_TO_FILETYPE`, audit `file_hash 'error'` comparisons, shared `wiki_search` helper — all in `archivist/doppelground_bridge.py` + `fit.py`; P4-2 (kernel-sourced trust) touches the same file, bundle them. |
| ngrok :7354 public exposure "confirm intentional" | flagged by SAI | unresolved | **OPERATOR decision**: is the 7354 MCP relay meant to be public? If not: kill tunnel; if yes: P1-pattern token gate first. Same for any Tailscale Funnel on :7352. |
| DPO 247/128 imbalance | needs balanced re-gen | **CLOSED** by RIFT rebalance `7d668662` (reward-weighted, no re-gen needed) | Track F-2 (frozen eval pack) is the next Track F gate, THEN training. |
| NIM 429 parallel-agent exhaustion | operator banned parallel agents | standing constraint | Encoded in roadmap constraints; nothing to do. |

## 3. M1-M6 milestone status (vs ROADMAP_ADDITIONS_2026-07-03)

- **M1 live local verdict demo** — OPERATOR (Ollama reinstall). Unchanged.
  When done: rerun `tests/integration/test_p2_done_gate.py` live variant;
  then unblocks papers #13 (refusal direction) and TokenHD training data
  sanity runs.
- **M2 Sentinel integration review** — mostly DONE (`bf5d4221` adopted with
  trust/encryption/alert repairs). Remaining open slice: Sentinel
  case-events → vault TASK channel + TrustKernel gating of case
  transitions (S/M, unblocked, my lane).
- **M3 Phase 3 CLI/CTL** — NOW; operator priority; see §4.
- **M4 Track F unblock** — RIFT rebalance DONE; next gate is Track F-2
  frozen held-out eval pack (M effort) before ANY training run.
  `test/train/validation-00000-of-00001.parquet` in PAPERS DATASETs is the
  candidate split; keep proprietary CoT sets training-only.
- **M5 provider reality maintenance** — NOW (S): `nexusctl models verify`
  refresh + purge per DeepSeek 7/3 probe (SiliconFlow 401, NIM 410s,
  OpenRouter 402...). Operator: SiliconFlow dashboard key, LongCat beta
  re-request, OpenModel key, novita funding.
- **M6 WSL HERMES relay access** — GATED on DeepSeek lane committing
  `model_relay_adapter.py`; antiGRAV owns the designed fix.

## 4. P3-P5 next-up queue (approved roadmap, operator priority = P3)

Recommended execution order for the next sessions, shortest-path first:

1. **P3-5** sync_hermes YAML nesting fix (`nexusctl/model_sync.py:506`) — S,
   already carries a triage note; test gate = YAML structure assertion.
2. **P3-4** rotate_keys full propagation + `~/.nexus/vault.key` /
   `NEXUS_VAULT_KEY` coverage (P2-5 added them) — dry-run must enumerate
   every consumer. NOTE: rotate_keys is currently UNTESTED; write the
   fixture-config test first.
3. **P3-7** `nexusctl relay verdicts` (data source live since P2-1:
   `~/.nexus/hallucination_verdicts.jsonl` + offset sidecar) and NEW
   **P3-9** `nexusctl trust` reading the singleton kernel
   (bootstrap-prior vs evidence-backed per agent).
4. **P3-1/2/3** entrypoint + relay-package dedupe + quota unification —
   the big consolidation; plan as its own session.
5. **P4-1** swarm foreman deadlock + worker duplicate-claim (audit
   finding, still open).
6. **P4-6** eval-pack harness — doubles as Track F-2's scoring rig; build
   once, serve both.
7. **P5-4** browser hybrid: contract doc ONLY until HERMES lands.

## 5. Standing constraints (unchanged, re-affirmed)

- No key rotation (operator directive; redaction is the control).
- No push before the operator's history-rewrite decision.
- No parallel NIM-backed calls; tests use mocks/local.
- Multi-lane hygiene: CODEX sentinel remnants, DeepSeek relay files,
  HERMES CDP zone, antiGRAV branch — explicit file lists on every commit.
- **New (slice G):** run `python -m nexus_os.recovery.session_harvester`
  at session start and before risky long operations — the ledger is the
  crash net; reruns are idempotent and cheap.
