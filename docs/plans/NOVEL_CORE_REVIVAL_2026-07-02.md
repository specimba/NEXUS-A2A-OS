# Novel Core Revival — Design & Wiring Plan (2026-07-02)

> **STATUS 2026-07-02 (later same day): ABSORBED into `docs/plans/IMPROVEMENT_ROADMAP_2026-07-02.md`.**
> Slice status at absorption: trust equation RESTORED (51603dba); rotation handoff (entry/outro via persistent_memory) DONE (6eeb5164); LG relay logprobs feed → roadmap P2-1; TrustKernel unification + agent_pool read-through → P2-2; COGER trust budget → P2-3; gmr breaker sync → P2-4; Obsidian wikilinks DONE (0f987684). Execute remaining items from the roadmap, not from here.

Branch: `codex/specimba/nexus-core-solidify`. Grounded by four read-only
explorations (trust forensics, GMR scoping, LG feed design, Archivist map)
against repo + ARCHIVIST canon. Operator directives: no key rotation
(env/vault plumbing instead); GMR revived as auto-mode routing inside
ModelRelay with Chimera coordinated; memory entry/outro (dropoff-handoff)
for zero-knowledge model rotation; trust equation restored to the novel
11-element math; LG detection given a real runtime plan; Archivist→wiki→
doppelground→dossier/card chain connected, Obsidian-browsable.

## 1. Trust equation — RESTORED (commit 51603dba)

Forensic verdict: `trust_scoring.compute_score` (the 11-element tanh
scorer: Qeff experience gating, P polarity, hard-fail → −1.0, R>Rcrit →
ESCALATED) was intact and live. The downgrade was in the DURABLE update:
`TrustKernel.record_event` used a plain Beta posterior mean
(`alpha/(alpha+beta)`) — monotonic in success volume, i.e. the exact
grinding attack framework §1.1 forbids. TrustEngineV2 (which HAS the
anti-grinding ΔT law) is wired only to benchmarks.

Restored in record_event: inverted-logistic throttle on positive evidence
(`trust_formulas.logistic_scale`, was orphaned), −20-display-point
non-compensatory floor on hard_fail/ESCALATED, 0.995 cap, posterior mass
rebalanced only when a clamp fires. `non_compensatory_penalty` direction
bug fixed (max→min). Pinned by tests/governor/test_trust_kernel_antigrinding.py.

Still open (next slices):
- Unify or quarantine TrustEngineV2 so benchmarks exercise the live path.
- `agent_pool.update_trust` accepts arbitrary caller values and internal
  seeds (95/90/85/80) never refresh from the kernel → needs a TrustKernel
  singleton + read-through. `gmr/trust_adapter.py` is a Bayesian-only stub.

## 2. GMR auto-mode inside ModelRelay + entry/outro handoff

Key discoveries:
- GMR is complete but orphaned: `coger.py` L1(direct SLM)/L2(tandem)/
  L3(peer-review)/L4(tool-delegate) all functional with tests; only
  `engine/hermes.py` + `nexusclaw/brainstorm.py` consume gmr today.
- **The entry/outro system already exists**: `nexus_os/model_relay/
  persistent_memory.py` — `TaskContext`, `HandoffNote` (rate_limit/
  quota_exhausted/better_model/user_request), `TaskIntroBuilder.build()`
  (≤1500-token entry briefing), `OutroBuilder.build()` (done/decisions/
  next-steps/resume), `MemoryBus` persisting `~/.nexus_pi/state/
  model_memory.json`; orchestrated by `persistent_router.py`. Two thinner
  shapes overlap: gmr `ContextPacket.to_prompt_prefix()` and vault
  `GovernedMemoryBroker.build_context()`.
- "auto-fastest" does NOT exist anywhere (Node side aspirational); the
  only live auto resolution is Python relay `model_relay.py:322` →
  ChimeraRouterV2.

Wiring plan (behind new alias `auto-gmr`; plain `auto` stays Chimera-only,
no regression):
1. `model_relay.py:322` pre-stage: COGER classifies L1–L4 (outer strategy);
   Chimera remains the intra-level tier/temperature selector via the shared
   `self.router` instance. L2/L3 use rotator's `execute_with_fallback(execute_fn=...)`
   pattern with a local Ollama-call closure so relay health/fallback
   (`_select_healthy_fallback`) is reused, never bypassed.
2. Rotation handoff: on model swap, `persistent_memory.handoff_to(task_id,
   from, to, reason)` emits the outro; the next model's first system message
   is `TaskIntroBuilder.build(task, persistent_summary=broker.build_context(...)
   .context_text)`. Merge ContextPacket into TaskContext (≈80% overlap).
3. Persist handoffs to the vault TASK channel (trust-gated, durable), not
   just the JSON file.
4. Hazards: gmr breaker must consume the relay's breaker state
   (`AdaptiveCircuitBreaker.sync_from_relay` exists) — one trip-state, not
   two; COGER's `trust_score=100.0` default + magic-90 gate (coger.py:302,
   open by default) must instead take TrustKernel's budget; gmr sub-routers
   default to port 7350 (Node) while the Python relay is 7355 — make
   configurable.

## 3. LG hallucination detection — runtime feed

Input contract: `assess(logits=None, position, temperature, topk_probs=None,
hidden_state=None)`. **`topk_probs` is the viable minimal hot-path input**
(drives EPR entropy + Bebop TV-distance = 2 of 3 score contributors);
without real `logits`, the LG free-energy tracker silently runs on a
synthetic random walk (`_dry_run_entropy`) — production numbers today are
partly simulation.

Plan:
1. FIX FIRST (hazards): `calibrated_hallucination_detector.py:64-66`
   reads `self.bebop_weight` before assignment when `high_sensitivity=True`
   (AttributeError); `assess()` calls `_save_calibration()` on EVERY call
   (JSON disk write per token) — batch or gate persistence for hot path.
2. Primary chokepoint `model_relay.py:348-371` (`proxy_completion`): add
   `logprobs:true, top_logprobs:K` to the payload; parse
   `choices[0].logprobs.content[i].top_logprobs` → `probs=[exp(lp)]` →
   `assess(topk_probs=probs, position=i, temperature=T)` per token. Reuse
   the `exp(logprob)` conversion precedent in `governor/token_confidence.py:76`.
3. True token-level hot path (the ARCHIVIST mandate): the tracker's
   `logits_processor()` (`landau_ginzburg_tracker_v2.py:507`, HF
   LogitsProcessor, currently dead code) for any in-process model.
4. Verdict flow per existing conventions: advisory per-token risk into the
   relay response `relay_info`; high-risk → `hallucination-alert` on the
   A2A "hallucination" channel (`a2a_channels.py:348 wire_to_chd`);
   blocking reserved for confirmed `is_hallucinating`, paralleling the
   guard pipeline's 403 path. Calibration state: `~/.nexus/calibration_state.json`;
   HERMES thresholds are constants (RISK_HIGH 0.60 / MED 0.40 / LOW 0.25).

## 4. Archivist → doppelground → wiki → Obsidian

Every stage exists and is tested; the CHAIN is inert. Breaks, in order:
1. No trigger: `ArchivistDaemon` never started (master_daemon has zero
   archivist refs); pipeline runs only in tests.
2. `nexusctl archivist run` (cli.py:883-963) calls NONEXISTENT
   `ArchivistCompiler.compile_all()` and `compiler.compiled` → always
   errors/0 dossiers. Fix: build records → `compile_batch`;
   `_dossier_candidates`.
3. Fit→SEMANTIC severed: `daemon.run_deep` stops after `fit_batch`, never
   calls `DoppelGroundBridge.bridge_dossiers` — the only SEMANTIC writer
   with `source_dossier_id` has no production caller.
4. Output-dir mismatch: `fit.save_dossier` → `nexus_os/archivist/wiki/dossiers/`
   (EMPTY) while the 8 real dossiers sit in legacy `wiki_output/` (Jun 11),
   only counted (never content-indexed) via `_fallback_dossier_count`.
5. Obsidian: `wiki/` is already vault-shaped (index/concepts/entities/
   sources/dossiers) and `fit.generate_wiki_markdown` already emits
   Obsidian-compatible YAML frontmatter. Only real gap: `[[wikilink]]`
   emission (none exists repo-wide) — emit `[[source-card-slug]]` per
   source_record + `[[topic]]` MOC links in `fit._generate_dossier_markdown`
   (:417), write per-source stubs into `wiki/sources/`, regenerate
   `wiki/index.md` as a topic MOC.
- Cards: no Card class; "source card" = `AdmissionClass.SOURCE_CARD` on
  `ImportRecord` (+ `m0_freeze/*.md` frontmatter cards). Registry/intel
  cards are design-only.

## Sequencing

1. ~~Trust restoration~~ (done, 51603dba).
2. Archivist chain reconnect (small, unlocks the intel vault): CLI method
   fix + daemon bridge call + dir unification + dossier migration.
3. LG hazard fixes (tiny) then relay logprobs feed (medium).
4. GMR `auto-gmr` pre-stage + handoff adapter (largest; TrustKernel
   singleton work rides along).
5. Obsidian wikilink emission + index MOC.
