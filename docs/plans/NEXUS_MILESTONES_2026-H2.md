# NEXUS Milestones — 2026-H2 Roadmap (research-grounded)

**Status:** operator-directed next-steps synthesis, 2026-07-08 (Fable5 composer lane).
**Method:** four parallel web deep-research passes (local SLM SOTA; trace-to-training;
bench credibility; orchestration/governance frontier) fused with the grounded internal
fit-map from three days of full-log mining + repo audits. Extends
NEXUS_UPGRADED_PLAN_2026-07-08.md and the FI plan; supersedes neither.

## The flywheel (north star)

DISCOVER models first -> ROUTE to the cheapest capable lane -> CAPTURE every trace ->
EVALUATE on real work -> TRAIN our own sub-12B models on the legal partition ->
GOVERN with evidence/guards/trust -> trained models re-enter routing. Every subsystem
now exists; the milestones below build the missing ARROWS between them.

## Field validation (what the research confirmed about NEXUS's bets)

1. **Evidence gate = the winning family.** A joint OpenAI/Anthropic/DeepMind red-team
   study (arXiv 2606.26479) defeated 100% of detection-based prompt-injection
   defenses; only architectural/capability controls (CaMeL-class) survive. NEXUS's
   no-proof-no-cycle gate is architecturally correct — extend it, never dilute it.
2. **License partition = reputationally load-bearing.** All three closed providers
   prohibit output-training (verified primary ToS); Anthropic's 2026-02-24 disclosure
   of industrial distillation attacks (DeepSeek/Moonshot/MiniMax, 16M+ exchanges)
   means partition hygiene is now enforcement-visible, not just contractual.
3. **Production-trace bench = open space.** No public incumbent runs an arena on real
   production traffic; SWE-bench Verified is effectively retired (contamination);
   the gap to citability is documentation-weight, not engineering-weight.
4. **Trust-gated memory = ahead of published designs** on the security axis (OWASP
   ASI06 prescribes what the vault already does); gaps are temporal decay + drift
   monitoring + a temporal fact-lifecycle layer.

## Corrections the research forces (do these FIRST — M0)

- **MiniMax license changed with M2.7**: commercial use now requires written
  authorization (M2 was MIT). Registry v3 marks MiniMaxAI permissive -> re-audit to
  version-conditional outputLicense; re-partition any affected trainable traces.
- **DPO negatives rule**: Claude/GPT/Gemini outputs may not be used even as REJECTED
  sides of preference pairs — both sides of every pair must be permissive-partition.
  Encode in trace_source + the SLM plan.
- **Llama naming obligation**: any fine-tune improved by Llama outputs must carry the
  Llama name prefix if distributed (license S1.b.i) — tag at ingestion.
- **Guard tier design**: evidence says guard DIVERSITY beats count, and size does not
  correlate with recall (r=0.21) — replace the planned 3x-similar-0.5B voters with a
  diverse cascade (injection-guard + streaming content-guard + heterogeneous second
  opinion, ANY-vote escalation).
- **Bench**: drop length from probe scoring — length is a covariate in the BT fit,
  never a score component (documented reward-hacking vector).
- **Skip list confirmed**: NVFP4 on the 4070 (Blackwell-only acceleration), vLLM-on-
  WSL2, DFlash (no llama.cpp path), spec-dec on MoE (measured 0.89-1.06x — no gain).
  Spec-dec class stays DEFERRED, now with evidence.

---

## M0 — Corrections & hygiene sprint (days; no blockers)

1. Registry: MiniMax outputLicense -> version-conditional (M2 MIT / M2.7+ restricted-
   commercial); regenerate; re-audit trainable partition for MiniMax (+Llama) traces.
2. trace_source: enforce permissive-only for BOTH sides of preference pairs.
3. dedup_cluster_id population pass over prompt_hash groups (FI-T3 opener).
4. Bench: length -> covariate; record harness/config/cost per probe run.
5. Verify the :7352 weak-auth claim against P1-3 (56bf8a94); if real, fix now.

## M1 — Serving substrate + local stack v0 (week 1-2; REPLACES the Ollama-reinstall blocker)

**Strategic unlock:** llama.cpp llama-server router mode (official) serves multiple
models with preset pinning (--models-preset INI, --models-max), dynamic load/unload,
and --sleep-idle-seconds — the pinned-anchors + rotatable-slot design in ONE Windows-
native CUDA process. Adopting it converts blocker B2 from operator-reinstalls-Ollama
to download-one-binary (operator still approves; Ollama coexists for :cloud lanes).

1. llama-server CUDA build + presets encoding the stack.
2. Stack v0 (research-updated picks, all registered in registry v3 under a new
   provider slug, e.g. llamacpp): gate = Qwen3.5-0.8B (Apache 2.0); guards =
   PromptGuard2-86M + Qwen3Guard-Stream-0.6B (moderates DURING generation — ideal for
   uncensored task models) + ANY-vote escalation to Qwen3Guard-Gen-4B / cloud Granite
   Guardian 4.1; embeddings = EmbeddingGemma-300M on CPU (+ Qwen3-Reranker-0.6B);
   task slots = Qwen3.5-4B Q4 default coder, Gemma-4-E2B QAT generalist (~2.9GB, best
   2026 quality-per-GB), VibeThinker-3B ONLY inside a Best-of-N + automated-tests
   harness (independent bench: ~38% standalone pass@1 despite contest headlines).
   Trial Needle-26M (MIT) as intent anchor (frees ~250MB of pinned budget).
3. chimera_rotator increment against llama-server preset/props API; mocked tests.
4. Own imatrix quant pipeline (BF16 source, activation-storing GGUF output,
   NEXUS-domain calibration text) for every slot below Q6.
5. MTP only on the task slot when headroom exists (Unsloth Qwen3.5 MTP GGUFs,
   1.4-2.2x dense); never on MoE.

## M2 — Frozen eval pack F-2 (week 2-3; THE gate for all training)

CursorBench pattern: 100-300 tasks sampled from real ARCHIVIST/trace production work;
four frozen sets (task holdout / capability-drift / refusal-safety / paired arena vs
base); prompt-hash decontamination between eval and training splits; hash-pinned and
versioned. Nothing trains until this exists. Doubles as bench capsule seed.

## M3 — First training loop on the A800 (week 3-5; gated on M2)

1. RFT baseline (the 2026 workhorse): permissive traces filtered by verdict-pass AND
   trust>=threshold AND outcome ok -> QLoRA SFT (Unsloth, r=16, lr 2e-4, 1-2 epochs)
   on a Qwen3.5-7/8B-class per lane (coding first). Gate on F-2.
2. TokenHD v1: LettuceDetect-mmBERT-base (307M, MIT, trained for code/tool-output
   spans, released 2026-07-01) continue-trained on NEXUS traces weak-labeled by our
   logprob verdicts; deploy behind a HaluGate-style sentinel; un-darkens the CHD
   tokenhd lane (tokenhd_weight > 0 after eval).
3. RIFT guard set 750 -> 2-3k via reward-weighted rejection sampling WITH dynamic
   filtering (drop all-pass/all-fail items — measured ~+5pt effect).
4. Organic DPO pairs from identical-task multi-model traces (both sides permissive),
   ranked by trust-score delta.
5. LATER: Trust-GRPO — binary verifiable core + trust posterior as bounded shaping
   term, tight KL, forward-correction using the detector's measured FN rate
   (calibrate FIRST); KL-spike monitoring as the hacking alarm.
6. Merging (TIES/task-arithmetic) is eval-gated optimization, never default.

## M4 — Bench credibility v1: Shadow Arena MVP + the five documents (week 4-6)

Engineering: shadow-route real tasks to challenger models; blinded pairwise judging
with position randomization + no-own-family judges; style-controlled Bradley-Terry
(length/markdown covariates — the LMArena recipe); bootstrap CIs (>=1000 resamples);
tie-reporting below ~150-200 battles per pair; a dimension covariate in one global BT
fit instead of 12 independent small-n boards (P2L direction).

Documentation (the actual credibility gap — all cheap): (1) contamination-policy
one-pager (private-by-construction + battle date-stamps vs model release dates);
(2) frozen hash-pinned monthly Decathlon capsule spec; (3) operator-prior transparency
+ prior-sensitivity (data-only board published alongside); (4) pre-committed
anti-gaming governance (all-runs-count, no retraction, symmetric deprecation);
(5) public scorer + trace schema + synthetic V1 probes for third-party rerunnability.
First capsule ships when battle counts separate ANY pair.

## M5 — Governance hardening (week 5-8; parallel-friendly)

1. CaMeL-style tool-call firewall increment: taint/provenance tracking (extend
   MemLineage) + capability policies gating tool calls — extends the evidence-gate
   principle from cycles to tool calls.
2. MCP mesh: gateway in front of all MCP servers; OAuth 2.1 + PKCE; audience-bound
   tokens; input allow-listing; SSRF egress blocks (exposed weak-auth MCP servers =
   the top 2026 incident vector).
3. A2A bus: adopt the A2A v1.0 ENVELOPE (signed agent cards, task-state lifecycle,
   Message/Part/Artifact typing) over the existing file transport — files stay as
   local transport, the schema standardizes. SPIFFE-class workload identities when
   cross-machine lanes appear.
4. Vault ASI06 completion: temporal decay + belief-drift monitoring + per-entry
   provenance checksums (layers 4-5 on the existing trust gates). EVALUATE (not
   adopt blind) a Graphiti-style bi-temporal fact layer fused with the vault.
5. CDP stability: port the browser-use raw-CDP watchdog pattern (event-driven crash/
   page-state watchdogs; target/frame/backend-node ID tracking) — their migration doc
   describes our exact window-hang failure; persistent profiles per lane.

## M6 — Discovery completion + ops (continuous)

1. FI-D2 public pollers: OpenRouter /models + HF org watchers (keyless — the actual
   Owl-Alpha catcher; the refresher covers only REGISTERED providers today).
2. FI-D3 nexusctl models adopt: candidate -> registry-entry pipeline.
3. FI-Q2 quota consolidation (three trackers -> one ledger-fed); FI-Q4 soak harness
   for the silent-degrader watchlist (NIM, Baseten, Moonshot, Ollama-Cloud).
4. Evidence-gate lab runs: produce the first REAL VERIFIED browser cycles; verify
   EPISODES/a2a -> ARCHIVIST -> vault ingestion end-to-end.
5. Vision guard weights (B5) when operator lands them; SenBen voter-3 next.
6. Operator queue unchanged: push/history-rewrite, FI-T2 legal review, keys, token
   rotation flags.

## Sequencing logic

M0 -> (M1 and M2 in parallel) -> M3 (needs M2; benefits from M1 local serving) ->
M4 overlaps M3 (its documents are independent) -> M5 parallel after M1 -> M6
continuous. Respects operator priority 1-3-2: M2+M3 (trace/training) lead; M1 serves
them; the fancyMODELS curation reading debt slots before M3 model picks freeze.

## Research provenance

Four agent reports (2026-07-08, fully cited inline in the recovery ledger):
local-SLM SOTA (llama-server router mode, Qwen3.5 small series, guard-diversity
evidence, Gemma-4 QAT, MTP/EAGLE-3 practicality, NVFP4/DFlash skip list);
trace-to-training (RFT-first consensus, verifier-noise forward correction, verified
ToS matrix + Feb-2026 distillation enforcement, MiniMax M2.7 license change,
LettuceDetect line, Unsloth/QLoRA recipe, eval-pack methodology); bench credibility
(SWE-bench-Verified retirement, Leaderboard-Illusion lessons, style-control recipe,
small-n statistics, the 10-point citability checklist); orchestration/governance
(100% red-team defeat of detection defenses, CaMeL family, MCP OAuth 2.1 practice,
A2A v1.0 under Linux Foundation, SPIFFE identity baseline, OWASP ASI06 memory
defense, browser-use raw-CDP watchdogs, LongMemEval-over-LoCoMo eval hygiene).
