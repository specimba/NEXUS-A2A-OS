# NEXUS Local SLM Stack Plan — 2026-07-08

**Status: OPERATOR-APPROVAL-PENDING. Hard dependency: B2 (Ollama local reinstall, M1)
— nothing here is buildable until llama-server exists locally.**

**Provenance:** design by the antigravity (Gemini) lane, 07-07/08 — brain-dir
implementation_plan.md + scientific_training_plan.md + the ARCHIVIST dossier wave
(3.5B Core Integration, Inside-the-Club Governance, Scientific Fine-Tuning stacks,
Cascade Routing v1/v2, Curation & Speculative-Decoding dossier, SLM discovery).
Ported into the repo by the Fable5 composer lane WITH the reality corrections below —
the original docs re-plan several subsystems that already exist. Credit: antiGRAV
lane for the stack design; operator for the workflow spine and budget directives.

## The operator's workflow spine (verbatim intent)

User prompt -> pinned CPU/GPU anchors (FunctionGemma-270M intent + BashGemma-270M CLI
+ EmbeddingGemma) -> bouncer/guard team stack (~1GB) -> rotatable task SLM (2-2.5GB)
= 3.5GB active VRAM max -> escalate to cloud free-frontier CLI lanes -> browser CDP
collaboration LAST -> final output re-checked by the local SLM gate. Local-first
always; Fugu-style multi-LLM intel distillation on the collaborative tier.

## Stack design (post-revision, 8GB card / ~3.5GB active budget)

- L0/L1 pinned anchors (~750MB): FunctionGemma-270M (intent), BashGemma-270M-merged
  (CLI). CPU-offload embeddings: nomic-embed-v1.5 or Qwen3-Embedding-0.6B.
- Gate (1B): Neo_T-Virus-3.2-1B / IBM-Grok4-1B rapid gatekeeper (decensored bouncer).
- Guard voters (3 x ~0.5B): DeBERTa-v2 prompt-guard + GLiGuard-300M + Arch-Guard-300M
  consensus; Tier-3 defensive-roleplay bouncer special-virus:latest. Operator: exceed
  2.5B total smartly; multiple chained governance mindset stacks, one gate is never
  enough; uncensored task models + governance concentrated in the guard tiers.
- Task SLM rotation (2-2.5GB): coder = VibeThinker-3B family (operator rejected
  7B/14B coders as VRAM waste); reasoning = Mythos-nano-OBLITERATED; tool-caller =
  refinedtoolcallv5-3b class. Rotator: unload-before-load via
  nexus_os/gmr/model_rotator.py pins + a new chimera_rotator increment.
- Escalation: trust/quality gate -> cloud free tier (upgraded-plan S2 chain) -> CDP
  browser Trinity swarm (Thinker/Worker/Verifier) + Dawid-Skene EM peer review, with
  ClawTrojan + SEMA drift filters; trajectories land in EPISODIC memory.

## REALITY CORRECTIONS (fold-in before building; from the 07-08 mining pass)

1. 11-element trust EXISTS (restored 07-02: anti-grinding law, -20 floor, 99.5 cap;
   TrustKernel singleton P2-2). Remaining work = lane-param binding + verification
   only — do not reimplement compute_score.
2. TRUST SCALE MISMATCH: dossiers use Q<0.3 (0-1 space); TrustEngine v2.2 runs 0-100
   (baseline 25, cap 99.5). Define the escalation trigger explicitly in 0-100 terms
   (e.g. trust<30 or HELD) before wiring the CDP handoff.
3. 8-channel memory EXISTS (memory_channels.py, AES-GCM P2-5, trust write gates).
   Delta = pipeline write-throughs (SENSORY/EPISODIC/META during requests) + the
   CDP-to-EPISODIC hook, which MUST go through the A2A evidence gate episode sink
   (ARCHIVIST/EPISODES/a2a) — only VERIFIED cycles become memory.
4. peer_review.py EXISTS (circular triplets, judge attribution P2-3). Dawid-Skene EM
   is an ENHANCEMENT to it, not greenfield (roadmap slot RP Papers #12).
5. Evo-Memory sleep-time consolidation folds into RP Papers #10 (already NOW-M) —
   fold, do not fork.
6. DPO imbalance is CLOSED (RIFT 7d668662). The real training gate is Track F-2
   frozen eval pack.
7. LICENSE PARTITION IS LAW: HelioAI/Fable-5-Distill and any Fable/Claude/GPT/Gemini-
   derived corpora are reference-only (FI-T #1 risk); the training corpus is the
   permissive partition + operator-owned local outputs. license_class() gates every
   ingestion.
8. Local guard/bouncer models register in registry v3 shape (provider=ollama,
   status=active, quota windows null, outputLicense permissive with basis) — the
   registry stays canonical/deterministic; LIVENESS stays in the
   ~/.nexus/registry_health.json sidecar. No hand-edited live-state in git.
9. Speculative decoding (MTP grafting Q8-heads-on-Q4-trunk, DFlash, DSpark) stays
   DEFERRED per the revived-plans ledger until operator arbitration.
10. UPnP IP-rotator (cascade v1) is REJECTED — governance posture.
11. CDP swarm efficacy claims require VERIFIED evidence-gate cycles; Paranoia-Engine-
    class simulated metrics are invalid (three 07-02 sessions reclassified).
12. Cascade router work targets nexus_os/governor/cascade_router.py +
    gmr/model_rotator.py + nexusclaw/trinity_fugu_workflow.py (all exist); the only
    NEW module is the Tier-2 rotator increment (chimera_rotator).
13. All-local serving assumes B2 (Ollama reinstall). D:-drive GGUF wiring (D4) is
    gated on the same.

## Training methodology (scientific_training_plan.md, corrected)

Task Arithmetic + TIES merging (e.g. Neo_T-Virus safety + VibeThinker reasoning);
SAMM safety-bounded merging (alpha=0.3); Gabliteration (orthogonal projection against
the refusal direction) for task SLMs — safety delegated to the outer guard tiers;
Trust-Driven GRPO with the 11-element compute_score as reward (KL-regularized) — uses
the EXISTING scorer per correction 1; Evo-Memory per correction 5. Venue: Intern A800
notebook (upgraded plan S3). Every dataset passes the license partition (correction
7) and waits on Track F-2 (correction 6).

## Build order (once B2 lands + operator approves)

1. Register anchors/gate/guard/task models in registry v3 (correction 8) + regenerate.
2. model_rotator pins + chimera_rotator increment (unload-before-load; tests with
   mocked Ollama).
3. cascade_router Tier0-Tier4 wiring + explicit trust threshold (correction 2); tests.
4. Pipeline memory write-throughs (correction 3); tests for channel writes.
5. trinity_fugu_workflow local-first rewiring; CDP escalation via evidence gate only.
6. Guard-stack verification against the frozen eval pack; then GRPO/merge experiments
   on the A800 (corrections 6/7).

## Verification plan (requested by the source dossiers)

tests/test_memory_channels.py write-through cases; trust-formula lane-param binding
unit test; tests/test_cascade_router.py with mocked Ollama; chimera_rotator
unload-order test; browser director --dry-run smoke; end-to-end: one prompt routed
local -> escalated -> VERIFIED CDP cycle -> EPISODIC entry present.
