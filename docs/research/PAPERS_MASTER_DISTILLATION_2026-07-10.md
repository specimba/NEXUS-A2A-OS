# PAPERS Master Distillation — Full Scientific-Base Sweep Mapped to M0-M6
**Date:** 2026-07-10 · **Composer:** Fable5 (8 parallel distillation agents) · **Status:** CANONICAL research synthesis
**Corpus:** `Downloads/ARCHIVIST/PAPERS` — papers01-13 + DATASETs + Workflows; 1,192 files / 3.2GB / ~826 PDFs.
**Method:** every batch triaged by title, high+maybe abstracts scanned, ~90 top papers deep-read (PyMuPDF extraction);
batches 02/09/10 processed as DELTA against their existing syntheses. Milestone hooks refer to
`docs/plans/NEXUS_MILESTONES_2026-H2.md` (M0-M6). Evidence grade: E1 (bodies read this sweep) unless noted.

---

## 0. Corrections to prior art (read first)

1. **The two papers09 docs were filename-only** (`PAPERS09_STRATEGIC_ASSESSMENT_2026-06-20.md`,
   `PAPERS09_AND_MODEL_CURATION_BRIEF_2026-06-21.md` — self-graded E0, zero PDF bodies parsed). Their rankings are
   superseded by §2/§3 below: RIFT promotes to P0 training input; the ~30-paper single-turn jailbreak cluster demotes
   to a bulk red-team corpus (threat moved to agent-state attacks — see papers11).
2. **DATASETs dir is mislabeled.** It is not 290 dataset cards; it is two Web-Bench frontend eval-run archives
   (deepseek-r1 pass@1 14.5%, gemini-2.5-pro 26.4%) plus ~7 real assets. License partition rulings:
   - `fable5_cot_merged.jsonl` (70MB, 4,665 recs) — Anthropic model output + **third-party user sessions (PII-bearing,
     home paths/session UIDs of user "lane")** → **reference partition ONLY, never train, never share**.
   - `Claude-Opus-4.7-4.8-DeepReason-462x-105M.jsonl` (146MB) — Anthropic outputs → **no-train partition**.
   - Gemini eval outputs in the Web-Bench runs → non-permissive (no-train); DeepSeek-R1 outputs → permissive-OK.
   - `ADVERSARIAL DÉJÀ VU JAILBREAK DICTIONARYmethods.txt` (397 jailbreak skills, JSON) — best guard asset in the
     vault; guard-DPO feed + guard eval probes. Verify release license before the trainable partition; eval use fine.
   - HellaSwag parquet trio (MIT): validation split is drop-in for the M2 eval pack today.
3. **papers13 is not abliteration** — it is a decoding/sampling & anti-degeneration batch (§5, mostly free-lunch).
4. **AI-generated meta-reports in papers11** (Sycophantic Cascade, Great Unpacking, Defensive Canvas, ERNIE x2,
   "Engineering Proactive Defense" written about NEXUS itself) → tag SIMULATED; useful only as hallucination case
   studies for the evidence gate, never as scientific citations.
5. **Dedupe on disk:** VibeThinker-3B (papers09=papers11 byte-identical), `gpt-5-6-preview (1)`,
   `Engineering Proactive Defense (1)`, `ERNIE Agent (1)`, leaderboard-manipulation paper (papers05=papers06),
   4x "Advancing Trustworthy AI Robustness Toolboxes" (papers01).

---

## 1. Convergent findings (independently confirmed by ≥2 batches)

**F1 — Harness beats weights.** LIFE-HARNESS (+88.5% avg relative improvement across 126 model×env settings, harness
evolved on Qwen3-4B transfers to 17 backbones), Meta-Harness (searched harness beats human-written), NVIDIA Workspace
Optimization, Apodex scaffolding, Harness-1 ("move bookkeeping out of the policy"). The frontier engineers the frozen-
model interface. NEXUS's trust ledger + A2A evidence gate are exactly the substrate these methods assume.

**F2 — The training pipeline is the attack surface, and input filtering alone cannot close it.** Malice in Agentland
(poisoning a few finetuning demos → >80% data-leak backdoor; 4 guardrail models + 1 weight defense all fail), Virus
(guardrail-FILTERED data still carries the attack), FCV (code that passes all tests but ships CWEs — 40.7% ASR),
Hidden Ads (semantic-trigger backdoors survive clean finetuning). Consequence: the M3 loop needs (a) provenance vetting
of source lanes, (b) trajectory purification, (c) a **post-training safety+refusal regression gate** in the frozen eval
pack — verdict filtering is necessary but not sufficient.

**F3 — Teacher-free, trace-native training is the A800 play.** SERA soft-verified generation (26x cheaper than RL,
SFT-only, matches Devstral-Small-2; no unit-test infra needed), Nebius playbook (RFT with execution feedback captures
half the total gain BEFORE any RL; 11→20→39% SWE-bench), OPSD/SDPO self-distillation (the model conditioned on its own
verified traces/error feedback is the teacher; SDPO reaches GRPO accuracy in 4x fewer generations), RIFT (reward-
weighted loss trains on ALL traces incl. failures), TMAX (open terminal-agent RL recipe: taxonomy-generated envs, DPPO
+ FP32 head), CLEANER/SAAR (purified trajectories, SOTA at 1/3 the steps), FAPO (~30-50% of "correct" RLVR rollouts are
flawed positives — add a process-check judge), Does-RLVR (spend RL only where the base model is at ~0%: NEXUS-
idiosyncratic skills like tool discipline and CDP operation, not math/code), FRPO (one-line future-KL fix when GRPO
arrives), Antislop/FTPO (final-token preference pairs: 90% slop suppression <1% quality loss — displaces DPO for style
objectives). REASONS-DB already captures everything these methods eat.

**F4 — The trust ledger is a reward signal, not just a gate.** RIFT's scalar reward weight = our Beta posterior; Fugu
soft-target SFT is unblocked (softmax over per-model trust posteriors); trust-weighted merge coefficients for adapter
fusion; abstention must not damage trust the way wrong answers do (AA-Omniscience Omniscience Index shape).

**F5 — Calibrate the judges before they gate anything.** VerifyBench (all reference-based verifiers degrade sharply on
hard instances), PPE (reward-model benchmark validated against real post-RLHF outcomes), Aletheia (small code-verifier
recipe: on-policy + negatives, drop long thinking traces at low budget), PGED (even frontier judges produce cyclic
preferences — 64% of graphs; ensemble small judges and denoise to a DAG), mode-collapse entropy monitoring (SFT on low-
entropy verdict-filtered corpora collapses diversity — track semantic entropy in M2), leaderboard-manipulation defenses
(voting channels are gameable; add judge/voter anomaly detection before BT aggregation).

**F6 — Memory needs lineage, consolidation, and its own eval.** MemLineage (Merkle-anchored signatures + derivation DAG
+ untrusted-path persistence → 0 ASR on three memory-laundering families, sub-ms overhead) is the vault's P0 upgrade;
LightMem sleep-time consolidation (up to 38x token reduction — run vault consolidation overnight on idle free quota);
SimpleMem multi-view indexing (+26.4% F1, 30x cheaper reads); attention-variance filter kills stealthy RAG poisoning
(white-box only — works on local llama-server models); MINJA/MURMUR/AgentPoison are the concrete threat models for
shared workforce memory (→ per-principal isolation in the CDP workforce); Evo-Memory task-streams give M2 a memory
benchmark so vault policies are measured, not vibed.

**F7 — Browser/OS-agent security is now a mature literature and it maps 1:1 onto the CDP workforce.** WASP (86% partial
injection success — "security by incompetence"), RedTeamCUA (hybrid OS+web injection-at-point), BrowseSafe (open guard
model + realistic HTML payloads), WindowsAgentArena (150+ Windows tasks), ARGUS (span-level influence-provenance on
tool-call arguments: ASR 3.8% at 87.5% utility — a buildable CaMeL alternative), PACT/AuthGraph (both BEAT the CaMeL
baseline our M5 plan assumed), SKILL-INJECT (80% ASR via skill files → authorization frameworks, not filtering),
Trojan's Whisper (narrative-reframing attacks that keyword guards miss), papers08's L0-L5 MCP guard map + MCPTox/
AgentRedBench regression suites, Sponge attacks (token-exhaustion → quota-governor anomaly flag).

**F8 — Small-model free lunches for the 8GB lane.** min-p (config flag, coherent at temp 1.5-3.0), p-less
(hyperparameter-free, faster than min-p), min-k (temperature-invariant diversity harvesting), TOOLSPEC (tool-call JSON
is 80-96% of agent latency; schema-FSM speculation = 3.5-4.2x speedup, training-free, schema comes from MCP defs),
Token Recycling (~2x speedup, <2MB, no draft model), BashGemma (270M micro-specialist LoRA recipe trainable ON the
4070), MiniCPM4 + Nanbeige4.1-3B (600 tool-call turns at 3B) as M1 serving candidates, SelfCheckGPT (black-box
sampling-consistency hallucination scoring — works on CDP lanes with no logits), LLMRouterBench (most routers fail to
beat best-single-model → curate the registry pool, don't grow it).

---

## 2. P0 adoption queue (ranked; effort in days)

| # | Item | Source | Milestone | Effort | Where |
|---|------|--------|-----------|--------|-------|
| 1 | min-p default + p-less logits processor for all local serving | papers13 | M1 | XS | 8GB |
| 2 | Nanbeige4.1-3B vs VibeThinker-3B bench-off on frozen probes (M1 slot decision input) | papers10/12 | M1 | 1 | 8GB |
| 3 | LIFE-HARNESS failure-mining → 4-layer harness on the CDP director (env contract / skill lib / action validation / trajectory regulation) | papers10 | M1-M2 | 2-4 | 8GB |
| 4 | BenchBuilder-style eval-pack minting from REASONS-DB traces + VerifyBench/PPE judge calibration + AA-Omniscience abstention scoring + EQ-Bench + HellaSwag-val | papers05/06/12/13 | M2 | 3-5 | 8GB+API |
| 5 | Post-merge AND post-training safety/refusal regression gate (frozen probe slice; Virus/one-bad-model rule) | papers01/02/12 | M2/M3 | 2 | 8GB |
| 6 | SERA soft-verified repo-native SFT + Nebius RFT-first playbook as the A800 opening move (permissive teachers only) | papers10 | M3 | 3-5 | A800 |
| 7 | RIFT trust-weighted loss (Beta posterior = reward weight; failures stop being wasted) | papers09 | M3 | 2 | A800 |
| 8 | CLEANER trajectory purification + FAPO flawed-positive process check before traces enter the trainable partition | papers04/10 | M3 | 2-3 | local prep |
| 9 | FTPO (not DPO) for style/slop objectives; guard-DPO fed by the 397-skill jailbreak dictionary, gated by OR-Bench-hard over-refusal slice | papers13/09/06 | M3/M5 | 2-3 | 8GB-A800 |
| 10 | MemLineage crypto lineage + sensitive-action gate on the 8-channel vault | papers11 | M5 | 4-6 | CPU |
| 11 | ARGUS-style span-provenance on browser tool-call arguments (page content = canonical untrusted span); evaluate PACT/AuthGraph vs CaMeL for the firewall design of record | papers10/08 | M5 | 4-6 | 8GB |
| 12 | SenBen 241M explainable scene-graph voter → ImageGuardPlane (machine-readable evidence, violence/substances coverage) | papers12 | M5 | 3-4 | 8GB |
| 13 | Fugu soft-target SFT via trust posteriors (blueprint Phase B — data problem now solved) | papers10 | M3 | 1-2 | A800 |
| 14 | WASP/RedTeamCUA/AgentLure/MCPTox injection regression suites into guard probe replay | papers02/08/10 | M4/M5 | 3 | 8GB |

**P1 shortlist:** SelfCheckGPT lane-consistency scoring (CDP trust signal); TOOLSPEC + Token Recycling (after M1 stack
lands); SimpleMem/LightMem consolidation patterns for the vault; Selective-Sampling linear probe as a TokenHD weak-label
source; PGED judge-cycle denoising; CGS chunk-scoring (local 3B generates, free-API large model scores likelihoods —
the Tandem pattern instantiated); AutoSkill trace→skill mining for lane prompts; REFUTE falsification track in the
evidence gate; adapter-merge toolkit TIES/DARE/LiNeS (CPU) once ≥2 QLoRA specialists exist; SKILL-INJECT static scan +
capability manifest on skill loading; Reflexion channel → organic DPO pairs.

---

## 3. What this changes per milestone

- **M0 (corrections):** add the DATASETs quarantine rulings (§0.2) to the license partition NOW — two large Anthropic
  CoT dumps and Gemini eval outputs must be tagged reference-only before any training tooling can touch the vault.
- **M1 (serving):** sampler defaults (min-p/p-less) are free wins on day one; the model slot decision becomes a
  measured bench-off (Nanbeige-3B agentic generalist vs VibeThinker-3B math specialist vs MiniCPM4 line); TOOLSPEC +
  Token Recycling are the speculation path that does NOT cost draft-model VRAM (EAGLE-3 deferred — vLLM-centric, VRAM-
  hungry at 8GB); LIFE-HARNESS wraps whatever model wins.
- **M2 (frozen evals):** mint from our own traces (BenchBuilder), calibrate every judge before it gates (VerifyBench/
  PPE/PGED), score abstention correctly (AA-Omniscience), add memory task-streams (Evo-Memory), semantic-entropy
  diversity metric, safety/refusal regression slice, EQ-Bench + HellaSwag-val as external anchors.
- **M3 (A800 loop):** order of operations is now evidence-based — SERA SVG-SFT → RFT with execution feedback → (later)
  GRPO/DAPO with FRPO fix; RIFT reward-weighting throughout; CLEANER purification + FAPO process checks on input;
  FTPO for style; spend RL only on skills where base models are near 0% (Does-RLVR); OPSD/SDPO remove the frontier-
  teacher dependency; DPPO + FP32 head (TMAX) is the stability recipe; TDScaling: spend generation budget on trajectory
  DIVERSITY metrics, not volume.
- **M4 (Shadow Arena):** Claw-Eval three-evidence-channel grading + Pass^k consistency; leaderboard-manipulation
  defenses before BT aggregation feeds the trust ledger; CYBENCH subtask partial credit; Qwen-AgentWorld-style
  simulator-in-the-loop for perturbed-state probing without touching live web lanes; slop-fingerprints as a style
  covariate next to length.
- **M5 (governance):** the firewall design of record should be re-decided against PACT/AuthGraph/ARGUS (all now beat or
  concretize CaMeL); MemLineage on the vault; SenBen voter + cross-modal jailbreak probes (Jailbreak-in-Pieces/
  UltraBreak) for the vision guard; SKILL-INJECT + Trojan's Whisper categories in guard training; OR-Bench keeps the
  guards honest; instruction-data separation is architectural (SEP: models provably cannot self-separate).
- **M6 (discovery):** DR-Tulu evolving rubrics for the research agent; MAPE data-flywheel loop (failure traces →
  targeted small-model fine-tune → redeploy; NVIDIA replaced a 70B router with an 8B at 96%); EvoFlow workflow
  evolution with bench replay as fitness; SWE-Protégé selective-escalation economics for the local↔cloud split.

## 4. Sakana blueprint re-rankings (papers10 delta, today's state)

MORE: Fugu soft-target SFT (Phase B — trust ledger solved its data problem, cheapest high-value item);
Tandem router (reinforced by CGS); ADCL curriculum (cheap add-on to the imminent guard-DPO run); LLM-PeerReview
merged with PGED into one bench-judge upgrade. LESS/DEFER: Trinity coordinator (wire-up to the existing evidence
gate, ~150 lines — not a new build); Conductor RL orchestration and TRINITY coordinator head (wait for Shadow Arena
reward data); Darwin Gödel Machine (parked pre-M5); TAID distillation (license partition constrains teachers);
EAGLE-3 (decide after M1; llama.cpp-native drafts or Token Recycling first); KAME (no latency requirement).
Darwin Family preprint remains UNPROVEN — extraordinary claims, thin validation; keep only the trust-weighted-merge
idea.

## 5. Workflows dir salvage (design artifacts, not papers)

Reusable now: file-driven `.task.md` queues with YAML frontmatter (O(n) token-free lane coordination — drop-in for the
CDP workforce); DAG WorkflowEngine with CHECKPOINT nodes + time-travel restore (kilocode orchestration primitive;
human gates before destructive browser actions); Foreman heartbeat/stall/reassign lifecycle (exactly what the multi-
lane Chrome workforce lacks); ExecutionRecord audit schema (already evidence-gate-shaped — unify); S-P-E-W memory
promotion (trust>0.85 AND access_count>10 — implementable as-is now that the trust ledger exists); memory folding
(DeepAgent) for long browser sessions; GPT-5.5 architect note: adopt OpenShell-style sandbox AROUND coding agents
without letting it replace NEXUS governance.

## 6. Deprioritized (evidence-backed skip list, corpus-wide)

Watermarking/model-extraction/AI-text-attribution (papers05 — NEXUS serves nothing publicly); humor/creativity
benches; video/image generation tech reports and diffusion-side safety (we moderate, we don't generate); diffusion-LM
+ speculative-decoding research beyond the three picked methods (revisit only if llama.cpp lands support); federated/
DP training; frontier-scale benches (BBEH) that 0.27-4B models floor; program-synthesis classics; embodied/vision
pretraining; the single-turn jailbreak-prompt long tail (bulk red-team corpus, no per-paper integration); Mellum 2 and
MISRouter to the registry watch-list (MoE-router manipulation becomes relevant only if MoE models are served locally).

## 7. Batch index (one line each)

- **papers01** (May 19): SLM capability thesis + agent supply-chain attacks (Malice in Agentland, SKILL-INJECT) + rStar-Math/SWE-Protégé training economics.
- **papers02** (May 26): browser/OS-agent security cluster (WASP/RedTeamCUA/BrowseSafe/WindowsAgentArena) + merge-safety + SEP instruction-data separation; old synthesis missed the whole first cluster.
- **papers03** (Jun 03): memory systems (LightMem/SimpleMem/Evo-Memory/AutoSkill) + adapter-merging toolkit (TIES/DARE/LiNeS) + unlearning contingency bookmark.
- **papers04** (Jun 07): teacher-free training (SDPO/OPSD/CLEANER/FRPO/DR-Tulu) + multimodal jailbreak red-team corpus + BashGemma micro-specialist recipe.
- **papers05** (Jun 08): provenance/protection (skip-heavy) + SDPO + Synthetic Artifact Auditing (third-party-verifiable license-partition evidence for M4 credibility).
- **papers06** (Jun 09): the evidence layer — VerifyBench/PPE/Aletheia judge calibration, RouteLLM/BenchBuilder/OR-Bench, MiniCPM4, leaderboard-manipulation defenses, DeepSeek-GRM inference-time judging.
- **papers07** (Jun 12): offense→verification — Apodex evidence-graph teams, SelfCheckGPT, REFUTE falsification, FCV "tests aren't enough", CYBENCH, verdict_lever WANDERING probe.
- **papers08** (Jun 13): MCP security canon — own 5-tier index (L0-L5 guard map), poisoning triad (VATS/ITP/TDP), AIRGuard/PACT/AuthGraph/MindGuard, MCPTox/AgentRedBench regression suites.
- **papers09** (Jun 20): RIFT + Does-RLVR + LCPO length control + GAR adversarial curricula; jailbreak cluster demoted; prior docs were E0 filename-only.
- **papers10** (Jun 24): Sakana wave + the uncovered 84 — LIFE-HARNESS/Meta-Harness, SERA/Nebius/FAPO/TTRL, ARGUS, PGED, Claw-Eval, Nanbeige; blueprint re-ranked (§4).
- **papers11** (Jun 29): agent-state security — MemLineage, ARG deterministic proof gates, VulnAgent-R2 evidence calibration, MINJA/MURMUR/AgentPoison, Sponge; AI-generated meta-reports flagged SIMULATED.
- **papers12** (Jul 07): the vision-guard dossier (YOLO26/SenBen/LSPD/on-device cascade) + TMAX/Nanbeige/TOOLSPEC/Token-Recycling/EAGLE-3 + harmful-finetuning cluster (Virus/Safety-Tax/Booster/Lisa) + LLMRouterBench + AA-Omniscience + Qwen-AgentWorld/Agents-A1.
- **papers13** (Jul 09): free-lunch decoding — Antislop/FTPO, min-p/p-less/min-k, Selective Sampling probe, mode-collapse warning, single-neuron loop surgery; EQ-Bench.
- **DATASETs** (Jul 03): Web-Bench eval-run archive + license quarantine rulings (§0.2) + the 397-skill jailbreak dictionary.
- **Workflows** (Jun 23): NEXUS design-artifact salvage (§5) + paper workflow figures.

---
*Full per-batch agent reports preserved in the session recovery ledger. Adoption items require the usual gates:
evidence-grounded, proposal-bound, test-gated, auditable. Nothing here authorizes training on quarantined data.*
