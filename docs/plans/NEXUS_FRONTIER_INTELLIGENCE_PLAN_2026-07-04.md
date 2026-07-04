# NEXUS Frontier Intelligence Plan — 2026-07-04

**Status:** operator-directed master plan (plan-first session; execution
follows approval of sequencing in §6). Extends
`IMPROVEMENT_ROADMAP_2026-07-02.md` + `ROADMAP_ADDITIONS_2026-07-03.md` +
`REVIVED_PLANS_2026-07-03.md`; does NOT replace them.

**Provenance.** Operator mission (2026-07-04) originally tasked to the
opencode MiniMax-M3 lane: dynamic model/provider discovery with
first-access reach, exact per-window quota knowledge, provider
special-tariff optimization — plus three doors opened in conversation:
NEXUS Bench from the operator's curation ordering, and a reasoning-trace
database feeding purpose-specific fine-tunes. Grounded by a 4-expert
deep-search team (repo/logs miner, provider-frontier scout, bench
methodologist, trace strategist; full reports preserved in
`~/.nexus/recovery/ledger.jsonl`). The MiniMax-M3 lane's proposals are
adopted and credited in FI-Q3/Q5 — it diagnosed correctly but could not
edit files; this plan lands its ideas.

**Reference data:** `docs/research/PROVIDER_TARIFF_INTEL_2026-07-04.md`
(discovery endpoints, quota tables, Owl Alpha case study).

---

## 0. The thesis, validated

The operator's first-access thesis is now evidence-backed: Meituan's
LongCat-2.0 ran as stealth alias **"Owl Alpha"** on OpenRouter for ~9
weeks before being unmasked, reaching #1 by token volume while unbranded.
A 15-minute `/models` diff with an unknown-prefix rule would have caught
it on day one. Meanwhile the repo audit found the mirror-image gap:
`provider_refresher.probe_provider` computes only attrition
(`registered − listed`) and **never** `new = listed − registered` — NEXUS
is structurally blind to new models today. The distance between "blind"
and "first-access" is small and cheap; that is workstream FI-D.

---

## 1. Workstream FI-D — Discovery & First-Access

Foundation: extend `nexus_os/relay/provider_refresher.py` + the
registry/sidecar pattern. Never auto-commit the registry; discovery
proposes, operator adopts.

- **FI-D1 — the new-model diff (S, do first).**
  In `probe_provider`: compute `new = listed − registered`; write
  candidates into `~/.nexus/registry_health.json` under
  `providers.<name>.candidates` with `{model_id, first_seen, context_len,
  pricing}`; emit an A2A `provider-news` event per genuinely-new ID.
  Noise rules from the scout: ignore price/metadata-only diffs; removed
  row → check alias page before declaring dead. Fix the stale-sidecar bug
  en route (dead NIM models still `active` because aging only runs on
  probe — age on read too). Tests: fixture listings with new/renamed/
  removed models.
- **FI-D2 — external watchlist pollers (M).**
  New `nexus_os/relay/frontier_watch.py`: poll the scout's ranked no-auth
  sources — OpenRouter `/models` (+ **unknown-prefix stealth rule**),
  OpenRouter rankings-daily, HF org watcher (8 tracked labs), GitHub
  releases, Cloudflare models JSON, Ollama library `-cloud` tags.
  Normalized snapshot store `~/.nexus/frontier_watch.json`, diff-based
  events, per-source cadence config, single-threaded + jittered (politeness
  and NIM-style 429 hygiene). NOTE: OpenRouter POLLING needs no credits —
  our dead OpenRouter routing lane does not block discovery. Tests:
  snapshot-diff unit tests with recorded fixtures.
- **FI-D3 — adopt pipeline (S).**
  `nexusctl models candidates` (list, with provenance + first_seen age)
  and `nexusctl models adopt <provider> <model_id>` → writes a
  `status: pending_operator` registry entry + regenerates artifacts
  (`gen_model_registry.py --check` gate). Registry stays hand-landed; the
  command just removes the friction. Tests: adopt round-trip on a temp
  registry.
- **FI-D4 — scheduling + alert surfacing (S).**
  Fold `models verify` + frontier_watch into the existing
  `NexusModelSync4h` task (roadmap P3-6 hook); monitor_daemon consumes
  `provider-news` A2A events → surfaced in `nexusctl status` ("N new
  candidates, oldest 3d") and the :7356 dashboard. Gate: last-verify age
  visible; candidate count nonzero triggers a visible line, never a
  silent log.

## 2. Workstream FI-Q — Quota/Tariff Intelligence

Foundation: `provider_budget.py` ledger (the strongest existing engine)
becomes the single quota authority; registry schema carries the knowledge.

- **FI-Q1 — tariff schema v3 (M, prerequisite for the rest).**
  Registry `quota` block becomes structured: `windows {rps, rpm, rph,
  rpd}`, `tokens {tpm, tph, tpd, monthly}`, `concurrent`, `burst`,
  `metering (requests|tokens|neurons|gpu_time)`, `credit {trial_usd,
  min_recharge_usd, permanent_tier_rule}`, `confidence (official|
  community|conflicted)`, `degradation (hard_fail|silent|dynamic_throttle
  |opaque)`, `notes`. Seed every provider from
  `PROVIDER_TARIFF_INTEL_2026-07-04.md` (keep the confidence tags —
  Cerebras is CONFLICTED, NIM is community-only). Schema bump v2→v3 with
  migration + `gen_model_registry.py` regeneration. Tests: schema
  validation + generated-artifact drift gate.
- **FI-Q2 — quota unification into the ledger (M-L; IS roadmap P3-3).**
  `provider_budget.py` grows per-second and per-hour windows (today only
  60s RPM + daily-derived targets); `SlidingWindowRPMTracker`'s
  header-ingestion (`X-RateLimit-Remaining/Reset`) moves INTO the ledger
  path so live headers correct static config; `quota_tracker.KNOWN_QUOTAS`
  and `DEFAULT_POLICIES` hard-codes become registry-generated. One
  authority, three consumers deleted/shimmed (P3-2/P3-3 in one motion).
  Tests: window math per class, header-override precedence, migration
  parity vs old trackers.
- **FI-Q3 — provider quirks knowledge base (S-M; adopts MiniMax-M3 lane).**
  New registry section `providerQuirks` (machine-readable): NIM
  `thinking.type` defaults + per-model `chat_template_kwargs`
  (`NIM_THINKING_DEFAULTS` — MiniMax proposal, never applied), **Kimi 2.6
  NIM tool-calling bug** (first time recorded in-repo: route tool-call
  requests for that model elsewhere), NIM dual failure modes (429-RPM vs
  context-limit — router currently conflates), OpenRouter negative-balance
  402, Moonshot no-$0-tier fact. Relay consults quirks at dispatch
  (`nim_precheck` context check + max-2-NIM concurrency limiter + 3s
  stagger — all MiniMax proposals). Tests: quirk-gated dispatch fixtures.
- **FI-Q4 — soak/endurance harness (M).**
  New `nexus_os/relay/soak_probe.py` + `nexusctl providers soak`:
  scheduled LONG-usage consistency tests against the silent-degradation
  watchlist (NIM, Baseten, Moonshot, Ollama Cloud) — token-metered daily
  drip (e.g. 20 spaced requests over 6h), tracking degradation onset vs
  cumulative spend; encodes the operator's "OK-but-dead-after-$1" failure
  class as `degradation_events` in the health sidecar. Cheap by design
  (bounded tokens/day, free lanes only). Tests: simulated degradation
  detection.
- **FI-Q5 — `/health/providers` + status surface (S; MiniMax proposal).**
  Node relay `:7350` and Python relay `:7355` expose breaker + ledger +
  quirk state; `nexusctl status` shows per-provider budget/cooldown/
  degradation at a glance. Tests: endpoint contract.

## 3. Workstream FI-B — NEXUS Bench ("nexus bench routes")

Design chosen by the methodologist after surveying BT/Elo arena math,
the Leaderboard-Illusion critique, style-control, P2L, and
shadow/interleave deployment patterns. Three stages, each independently
valuable. The operator's curation ordering (Mythos ≥ Fable 5 > GLM 5.2 >
GPT 5.5 > Opus 4.8 > DeepSeek V4 Pro > Kimi 2.7 > Qwen 3.7 Max >
Sonnet 5 > Gemini 3.5 > MiniMax M3 > MiMo V2.5 Pro > LongCat 2.0 > …)
becomes the Bayesian prior and the first validation target.

- **FI-B1 — Trust Ledger (1-2 wk, near-zero operator time; ships first).**
  Hierarchical Beta-Binomial over verified outcomes NEXUS already
  produces (TrustKernel verdicts, per-token hallucination scores,
  harness-compliance events): per model-category posterior with
  empirical-Bayes shrinkage + Rasch-style task-difficulty offsets;
  Thompson sampling over the same posteriors doubles as the router
  (evaluation and routing become one system). Categories: coding /
  debugging / harness-following / research / creative / assistance,
  auto-tagged by the relay's existing complexity classifier. Output:
  `nexusctl bench trust` leaderboard with credible intervals.
- **FI-B2 — Shadow Arena (2-3 wk; the flagship).**
  Relay shadow-routes 10-20% of real tasks to a second model chosen by an
  active sampler (max information gain); primary answers the user, shadow
  is logged. Nightly blinded adjudication queue (~10 min/day): both
  outputs position-randomized; operator votes win/tie/loss AND logs an
  identity guess pre-reveal (the N=1-bias audit). 3-judge jury from three
  different providers (never a compared model, position-swapped) votes in
  parallel; jury calibrated against operator agreement (Kendall τ
  published). Scoring: Bradley-Terry MLE, ties half-win, style-control
  covariates (length, markdown density) PLUS two NEXUS-unique covariates
  (mean hallucination score, verified-outcome flag); bootstrap 95% CIs;
  provisional tier under 200 battles. Credibility artifacts: hash-chained
  battle ledger, jury-vs-operator correlation, identity-guess ablation
  board, Clio-style anonymized workload distribution, open scoring code.
  Contamination structurally impossible: prompts are tomorrow's real work.
- **FI-B3 — Decathlon capsule (phase 3; publication vehicle).**
  Monthly ~150-task stratified frozen capsule (sanitized), replayed
  across the full roster, Plackett-Luce over overlapping 8-model jury
  panels, one-month embargo then published. Only stage with real API
  replay cost — gate on FI-B2 proving the workload is worth it.
- **FI-B4 — validation experiment (first week of FI-B1 data).**
  Correlate Trust-Ledger posteriors against the operator's ordering:
  where they agree, the formalization holds; where they diverge, either a
  bench bug or a genuine insight — both valuable. Report committed to
  docs/research/.

## 4. Workstream FI-T — Reasoning-Trace DB → fine-tune portfolio

Strategist verdict: the asset is real and rare (multi-model traces on
IDENTICAL production tasks = organic preference data), but **ToS is the
#1 risk and partitioning must exist from write #1**.

- **FI-T1 — capture sink (S-M; "start capturing tomorrow").**
  Hook beside `_assess_logprobs` in the relay (the one place every
  response transits, already redaction-wired). Schema per trace:
  `trace_id, ts, provider, model_id, license_class, task_type,
  prompt_hash, redacted_prompt, reasoning_text, final_answer,
  hallucination_verdict, downstream_outcome, tokens, latency,
  dedup_cluster_id, redaction_flags[], generation_lineage`.
  `license_class {permissive|restricted|unknown}` set at ingestion from a
  new registry field, hard-gating corpus membership. Redact at WRITE time.
  Retention/sampling policy per provider tier set BEFORE enabling.
- **FI-T2 — physical partition + license map (S).**
  Two stores, not one flagged store: `traces/trainable/` (MIT/Apache
  teachers: DeepSeek, Qwen, GLM; Kimi pending per-model license check)
  and `traces/reference/` (Claude/GPT/Gemini + existing
  `fable5_cot_merged.jsonl` → **reference/eval-only pending legal
  review**; never enters a training loader). Registry gains
  `outputLicense` per model.
- **FI-T3 — quality pipeline (M).**
  Continuous gates in order: semantic dedup (guard-DPO's 62% duplicate
  rate is the expected BASELINE), verified-outcome filter, hallucination-
  verdict threshold (reuse P2-1 scores), difficulty scoring/balancing,
  redaction-clean hard gate. Nightly stats into the health surface.
- **FI-T4 — first LoRA (gated on Track F-2 frozen eval pack).**
  Domain: debugging-refactoring (best signal density). Trainable corpus
  only; QLoRA on T4 per FINETUNE_MERGE_ROADMAP Phase 3; held-out
  hand-verified eval (~1K, s1-style) BEFORE any SAMM merge. LoRA-portfolio
  shape: per-domain adapter bank served via multi-adapter routing;
  sign-consensus merging only if consolidation needed later.
- **DO-NOT (standing):** no training on restricted-provider outputs
  without legal sign-off; no merged undifferentiated corpus; no raw
  prompt persistence; no skipping dedup; no self-generated traces as
  teachers (lineage-track N+1); no LoRA ship without held-out eval; no
  unbounded capture.

## 5. Open item

Original mission question #4 could not be identified (operator: "not sure
exactly got it what it is") — needs restating in a future session before
anything is built against it.

## 6. Sequencing (interleaved with the standing P3 queue)

The P3 queue and FI workstreams are not rivals — two FI items literally
ARE roadmap items (FI-Q2 = P3-3; FI-D4 = P3-6).

| Order | Slice | Why here |
|---|---|---|
| 1 | P3-5 sync_hermes YAML fix | S, already triaged, clears model_sync for FI-D4 |
| 2 | FI-D1 new-model diff + sidecar aging fix | the structural blindness; smallest high-value cut |
| 3 | FI-Q1 tariff schema v3 + seed | knowledge base everything else consults |
| 4 | FI-B1 Trust Ledger | near-free, starts accumulating bench data immediately |
| 5 | FI-T1+T2 capture sink + partition | every day not capturing is data lost; cheap |
| 6 | P3-4 rotate_keys tests + vault.key propagation | security debt, unchanged |
| 7 | FI-D2 frontier_watch pollers | first-access goes live |
| 8 | FI-Q3 quirks KB + NIM governed path | adopts MiniMax lane work |
| 9 | FI-Q2 quota unification (P3-3) + FI-Q5 health endpoint | the big consolidation |
| 10 | FI-D3 adopt pipeline + FI-D4 scheduling (P3-6) | closes the discovery loop |
| 11 | FI-B2 Shadow Arena | after Trust Ledger proves the categories |
| 12 | FI-Q4 soak harness | needs Q1 schema + a few weeks of ledger baselines |
| 13 | P3-7/P3-9 verdicts + trust CLIs, then P3-1/2 consolidation | per standing roadmap |
| 14 | FI-T3 quality pipeline → FI-T4 first LoRA | gated on Track F-2 eval pack |
| 15 | FI-B3 Decathlon | publication phase |

**Operator checklist (unchanged + new):** Ollama reinstall (M1);
history-rewrite decision (blocks push); ngrok :7354 intentionality;
SiliconFlow key, LongCat beta, OpenModel key; NEW: legal review decision
on restricted-provider trace usage (FI-T2); NEW: confirm Cerebras real
limits at build time (docs conflict).

**Standing constraints:** no key rotation; no push pre-decision; NIM
serial-only; multi-lane commit hygiene; plan-first calm execution —
progression guaranteed over finish-fast.
