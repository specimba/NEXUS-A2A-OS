# NEXUS Fine-Tune & Merge Roadmap — Safety-Anchored Model Pipeline

**Status:** Phase 1 executing (2026-07-02). **Framing:** a publishable,
reproducible safety-anchored merge/tune pipeline for an open agentic OS —
every artifact in this repo, weights and raw data external.

## Why

NEXUS's SLM teams (intent/guard/math/code/reasoning residents escalating
to free-provider frontier LLMs — see `config/models.registry.json` roles)
need purpose-built small models. The operator's curations (ARCHIVIST)
supply the method: SAMM safety-aware merging (naive SLERP/TIES drops
safety to ~53%; SAMM's `L_safety + 0.3·L_expert` restores ~96%), heretic
ARA abliteration benchmarks (α=1.3), hemlock QLoRA, EAGLE3/DFlash
speculative drafts, and Intern Discovery multi-GPU fine-tune workspaces.

## Phases

### Phase 1 — Guard DPO dataset (free, now) ✅ executing
- `scripts/finetune/gen_guard_dpo_pairs.py`: dataset_forge
  GuardSafeGenerator + unsafe-prompt bank → guard-classification prompts;
  **intern-s2-preview as Oracle Judge** (90M tok/mo quota, 30 RPM paced by
  the relay's SlidingWindowRPMTracker) authors gold "chosen" verdicts with
  reasoning; "rejected" = opposite-verdict adversarial templates.
- Output: `datasets/finetune/guard_dpo_v1.jsonl` (untracked; smoke sample
  committed at `jobs/finetune/samples/guard_dpo_smoke.jsonl`).
- Job card: `jobs/finetune/phase1_guard_dpo.yaml`. Offline mode
  (`--offline`) produces template-authored pairs for CI/tests.

### Phase 2 — SAMM guard merge (local RTX 4070 / Lightning T4)
- TIES-merge `qwen2.5-1.5b` guard candidate with SAMM loss
  (`L_safety + 0.3·L_expert`, α=0.3) via mergekit; phase-1 DPO pairs are
  the safety anchor set.
- Eval: guard accuracy on dataset_forge held-out split + refusal-retention
  suite; target ≥96% safety retention per SAMM.
- Candidate vision guard: MiniCPM-V-4.6 (SigLIP2-400M) for
  guard_plane_service — separate job card when phase 2 opens.

### Phase 3 — Nexus-OS-7B (Lightning T4 / Intern Discovery GPUs)
- Operator's plan (MODELLSSSSSS.txt): base `qwen2.5-coder:7b` → heretic
  ARA abliteration (LoRA adapters 3-5 MB) → hemlock QLoRA on sanitized
  `doppelground_sessions.jsonl` derivatives → mergekit SLERP stack.
- Speculative decoding: EAGLE3/DFlash draft heads for Kimi-K2.7-Code-class
  serving (SpecForge on Nemotron-Post-Training-Dataset-v2 precedent).
- Compute: Lightning.ai free T4 (loads two 7B simultaneously) for merges;
  Intern Discovery multi-GPU workspaces (CUDA 11.2-12.4 images, dataset/
  job/model-service tooling) for the QLoRA runs.

## In-repo vs external

| In-repo | External |
|---|---|
| job cards (`jobs/finetune/*.yaml`) | model weights / checkpoints |
| dataset generators + smoke samples | full generated datasets |
| eval harness + SAMM/mergekit configs | raw session logs (sanitized derivatives only) |
| this roadmap | GPU execution environments |

## Operator checklist
- [x] Phase-1 smoke (20 pairs) reviewed, then 1000-pair batch
- [ ] Lightning.ai T4 session for phase 2 merge
- [ ] Intern Discovery workspace provisioned for phase 3
- [ ] doppelground_sessions.jsonl sanitization pass before any phase-3 use
