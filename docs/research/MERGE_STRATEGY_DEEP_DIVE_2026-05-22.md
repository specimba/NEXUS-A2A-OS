---
id: NODE-MIG-MERGE_STRATEGY_DEEP_DIVE_2026_05_22
authority_scope: experimental
origin_sha256: f243819516a7d61e41867f518b553b6383e2968f815a12cda2a4bcbbff5146ab
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-E59A16
---
# NEXUS OS Merge Strategy Deep Dive

**Date:** 2026-05-22
**Scope:** Model merging techniques, RP-model BOUNCER gate concept, NEXUS-specific merge methodology
**Sources:** UmbrellaInc HF org, FINAL-Bench Darwin, mergekit, DFT/ASFT papers, LiquidAI LFM2.5, GLiGuard, user research dump

<!-- CANARY: 68d54f248444a475f0cc81fe50495b3c -->
---

## Executive Summary

This document synthesizes extensive research into model merging techniques, culminating in a proposal for **NEXUS OS-specific merge methodology**. The key insight: unfiltered/abliterated RP (role-play) models retain strong semantic reasoning cores despite having safety guardrails removed. Through **hard role-play prompting**, these models can be repurposed as BOUNCER security gates — a PURPLE team approach where the same model family serves both red team (attack simulation) and blue team (defense).

**Two paradigm shifts discovered:**
1. **Darwin V6** (VIDRAFT, Korea) — Diagnostic-guided evolutionary merging with per-tensor MRI scans before merge. Not using mergekit; custom PyTorch implementation.
2. **UmbrellaInc** — Treats models as "Vials" (merge components) using SLERP, breadcrumbs, DARE TIES. 97 models, systematic taxonomy.

---

## Section 1: Merge Mathematics — SLERP Foundation

### SLERP Formula

```
SLERP(v0, v1; t) = sin((1-t)*Omega)/sin(Omega) * v0 + sin(t*Omega)/sin(Omega) * v1

Where Omega = arccos( (v0 . v1) / (||v0|| * ||v1||) )
```

### Why SLERP Beats LERP for LLMs

| Property | LERP | SLERP |
|----------|------|-------|
| Path | Straight chord through sphere interior | Arc along hypersphere surface |
| Norm preservation | NO — dips to ~0.7x at t=0.5 | YES — constant norm |
| Feature retention | Dilutes both models | Preserves directional features |
| Failure mode | "Smaller" combined model | Smooth capability transition |
| Models supported | Any number | Exactly 2 (hierarchical chains possible) |

**Key insight:** In high-dimensional weight spaces, the direction (angle) of weight vectors encodes feature identity; magnitude encodes confidence. SLERP preserves direction; LERP destroys it.

### When Vectors Are Nearly Parallel (Small Omega)
SLERP ≈ LERP. The arc and chord are nearly identical. This is the common case when merging fine-tunes of the same base model.

### When Vectors Are Orthogonal (Large Omega ~ 90°)
SLERP travels a much longer arc but preserves both models' "character." LERP produces a weak compromise.

---

## Section 2: Merge Methods Catalog

### 2.1 SLERP (Spherical Linear Interpolation)

```yaml
merge_method: slerp
base_model: model_A
models:
  - model: model_B
parameters:
  t: 0.5  # 0 = 100% A, 1 = 100% B
```

**Best for:** Combining exactly 2 models, preserving both character and magnitude.

**UmbrellaInc example (Neo_T-Virus):**
```yaml
merge_method: slerp
base_model: UmbrellaInc/T-Virus_Epsilon.Arklay-3.2-1B
models:
  - model: UmbrellaInc/Prototype-Virus.FINAL-3.2-1B
parameters:
  t: [0.0, 0.25, 0.5, 0.75, 0.95]  # Multiple checkpoints
```

### 2.2 TIES (Trim, Elect Sign, Disjoint Merge)

**Steps:**
1. **Trim:** Keep only top-k% most significant parameter changes (density parameter)
2. **Elect Sign:** Resolve sign conflicts — if Model A wants +0.5 and Model B wants -0.3 on same parameter, majority wins
3. **Disjoint Merge:** Average only parameters with unified sign

```yaml
merge_method: ties
base_model: base
models:
  - model: fine_tune_A
    parameters:
      density: 0.5
      weight: 0.5
  - model: fine_tune_B
    parameters:
      density: 0.5
      weight: 0.3
parameters:
  normalize: true
```

**Best for:** Merging 2+ task-specific fine-tunes of the same base model.

### 2.3 DARE (Drop And REscale)

**Steps:**
1. **Prune:** Randomly reset fine-tuned weights to base model values
2. **Rescale:** Multiply surviving weights by scale factor to preserve output expectation

```yaml
merge_method: dare_ties
base_model: base
models:
  - model: ft_A
    parameters:
      density: 0.53  # 53% of changes kept
      weight: 0.4
  - model: ft_B
    parameters:
      density: 0.53
      weight: 0.3
```

**Best for:** Merging many models (3+) without degradation.

### 2.4 Model Breadcrumbs

Extension of task arithmetic that removes BOTH smallest AND largest magnitude changes.

```yaml
merge_method: breadcrumbs
base_model: base
models:
  - model: ft_A
    weight: 1.0
parameters:
  density: 0.28    # Final density after pruning
  normalize: true
```

**Best for:** Filtering out noise (small changes) and over-dominant changes (large outliers).

### 2.5 Passthrough / Frankenmerge

Concatenates layers from different models. Creates exotic sizes (e.g., 9B from two 7Bs).

```yaml
merge_method: passthrough
slices:
  - sources:
    - model: A
      layer_range: [0, 32]
  - sources:
    - model: B
      layer_range: [24, 32]  # Adds 8 extra layers
```

**Best for:** Experimental architectures, increasing depth without training.

---

## Section 3: The Two Paradigms — UmbrellaInc vs Darwin

### UmbrellaInc — "Vials" Ecosystem (European)

**Philosophy:** Models are components ("Vials") to be combined. Systematic taxonomy.

**Collections:**
- **Gemma3 - 1B Vials:** 4 base vials (Prototype, T-Virus.Ver, T-Virus.Rac, T-Virus.Ark)
- **Llama 3.2 - 1B Vials:** 12+ vials (Alpha, Beta, Gamma, Delta, Epsilon, Zeta, Joy, MS-Virus, etc.)
- **Documents:** Paper.1, Paper.2 (EN/SP RP format differences)

**Merge patterns observed:**
```
T-Virus_Epsilon.Arklay (base)
  + Prototype-Virus.FINAL
  = Neo_T-Virus (SLERP, t=0.95)

Joy + Plant = T-JCCC203 (SLERP, t=0.6)

The_Croupier + Joy (on T-Virus base) = The_Dealer (Breadcrumbs, layer 11-15, density 0.28)
```

**Key feature:** They create "strain" lineages. Each merge produces a new named strain with documented behavior at different t-values.

**Stats:** 97 models, ~1B params each, BF16, safetensors.

### Darwin (FINAL-Bench / VIDRAFT) — MRI-Guided Evolutionary Merge (Korean)

**Philosophy:** Don't guess merge ratios — diagnose first, evolve optimal ratios.

**Darwin V6 Pipeline:**
1. **MDS (Model Diagnostic Scan):** CT-scan each parent model layer-by-layer at tensor level
2. **Evolutionary Search:** Use natural selection to find optimal weight combinations
3. **Merge:** DARE-TIES, SLERP, or Linear (custom PyTorch, NOT mergekit)

**Models available:**
| Model | Parents | GPQA Diamond | Notes |
|-------|---------|-------------|-------|
| Darwin-2B-Opus | Qwen3.5-2B + Claude Opus distillation | — | LoRA merged |
| Darwin-4B-Opus | Gemma-4-E4B + Deckard | — | tau=0.491 |
| Darwin-4B-David | Darwin-4B-Opus + DECKARD-24B-D | 85.0% | Recursive evolution |
| Darwin-27B-Opus | — | 86.9% | #6 on GPQA leaderboard |
| Darwin-31B-Opus | — | — | #11 on GPQA |
| Darwin-35B-A3B-Opus | Qwen3.5-35B-A3B + Claude 4.6 Opus | 90.0% | MoE, 3B active |

**Key difference from UmbrellaInc:** Darwin does NOT use mergekit. Custom 13,771-line codebase with `mri_extractor.py`, `mergekit_integration.py`, `parent_attribution.py`, etc. Apache 2.0 licensed.

**The Darwin insight for NEXUS:** Per-tensor diagnostic before merging. This could allow us to selectively merge ONLY the safety-relevant layers from multiple guard models, leaving non-safety layers untouched.

---

## Section 4: DFT / ASFT — Training Method Insight

### Dynamic Fine-Tuning (DFT)

**Core idea:** Reweight SFT loss by the model's own token probability.

```python
# One-line change to standard SFT:
loss = loss * torch.softmax(shift_logits, dim=-1).gather(1, shift_labels.unsqueeze(-1)).squeeze(-1).detach()
```

**Problem it solves:** Standard SFT has pathological reward structure — unbounded variance when model probabilities approach zero.

**Problem it creates:** Distributional drift. Model progressively drifts from base distribution. Unstable in knowledge-intensive tasks.

### Anchored SFT (ASFT) — The Fix

```
L_ASFT = L_DFT + lambda * E_s[D_KL(pi_base(.|s) || pi_theta(.|s))]
```

Adds lightweight KL regularization to anchor the model to base distribution.

**Result:** ASFT outperforms both SFT and DFT on math reasoning, medical knowledge, and code generation.

### NEXUS Relevance

If we merge models and then need to fine-tune for safety classification, ASFT is the preferred method over vanilla SFT. The KL anchor prevents the model from drifting too far from its merged capabilities.

**Paper:** arXiv:2509.23753 (DFT analysis + ASFT proposal)
**Code:** https://github.com/yongliang-wu/DFT

---

## Section 5: The RP-Model BOUNCER Concept (User's Insight)

### The Core Thesis

**"Even if it cannot be sufficient technically, it can behave like this. ACT-ing ROLE playing is hard rule breakers in attacking with sequential stepped hitting to agent and server. So why we cannot use this as an advantage as a BOUNCER roled gate."**

### What This Means

RP (role-play) models like UmbrellaInc's "Virus" series are explicitly designed to:
- Break safety guardrails (abliteration, uncensoring)
- Adopt ANY persona on command
- Maintain strong semantic reasoning (they're merges of capable base models)

**The user's insight:** If the model can role-play as "DAN" (Do Anything Now), it can ALSO role-play as "NEXUS BOUNCER" — a strict security guard that blocks all attacks. The same unfiltered capability that makes it dangerous as a red team tool makes it powerful as a blue team tool when directed by the right prompt.

### Why This Works

1. **Semantic reasoning intact:** Abliteration removes refusal patterns, not understanding. The model still understands "this is an attack."
2. **Instruction following strong:** RP models are fine-tuned for deep instruction adherence.
3. **No false safety confidence:** Unlike models with baked-in guardrails that produce "PotentiallySafe" gibberish (Gemma 3 1B), RP models produce clear text.
4. **Configurable persona:** Change the system prompt → change the behavior. One model can be both attacker and defender.

### PURPLE Team Architecture

```
                    +-------------------+
                    |  NEXUS TrustKernel |
                    +---------+---------+
                              |
        +---------------------+---------------------+
        |                     |                     |
   RED TEAM              BLUE TEAM              AUDIT
        |                     |                     |
   +---------+           +---------+           +---------+
   | RP Model|           | RP Model|           | VAP Log |
   | persona:|           | persona:|           |         |
   | "Hacker"|           |"BOUNCER"|           |         |
   +---------+           +---------+           +---------+
        |                     |
   Generate            Block/Allow
   adversarial         with role-play
   scenarios           enforcement
```

**Same model, different prompt.** No need to maintain separate red team and blue team models.

---

## Section 6: Candidate Models for NEXUS Merge

### Tier 1: Proven Guard Candidates

| Model | Size | Type | Source | Status |
|-------|------|------|--------|--------|
| Bonsai-1.7B (Ternary F16) | 1.7B | Safety SLM | Our tests | 100% TAMAS, 82.7% v7 |
| Llama 3.2 3B Instruct Q4_K_M | 3B | General Instruct | Our tests | 100% TAMAS, 100% v7 |
| Granite-4.1-3B-SFT | 3B | Safety SFT | Our tests | 83.3% TAMAS, 94.7% v7 |
| GLiGuard-LLMGuardrails-300M | 300M | Encoder guard | Fastino Labs | Encoder, needs adapter |

### Tier 2: RP Models for BOUNCER Concept

| Model | Size | Base | Merge Method | Notes |
|-------|------|------|--------------|-------|
| UmbrellaInc/Neo_T-Virus-3.2-1B | 1B | Llama 3.2 | SLERP (t=0.95) | Uncensored, test as BOUNCER |
| UmbrellaInc/Prototype-Virus-1B | 1B | Gemma 3 | Multi-dataset | 15 datasets, 46 languages |
| UmbrellaInc/T-Virus_Epsilon.Arklay | 1B | Llama 3.2 | Base vial | Base for many merges |
| UmbrellaInc/Special-Virus-3.2-1B | 1B | Llama 3.2 | Unknown | 53 downloads |

### Tier 3: Base Models for Custom Merge

| Model | Size | Context | Notes |
|-------|------|---------|-------|
| Qwen3.5-2B | 2B | 262K | Darwin's base; strong reasoning |
| LiquidAI/LFM2.5-1.2B | 1.2B | — | GGUF available; efficient |
| LiquidAI/LFM2.5-350M | 350M | — | Ultra-small; GGUF/ONNX/MLX |
| Llama 3.2 1B Instruct | 1B | 128K | Proven base for vials |
| Gemma 3 1B IT | 1B | 128K | Proven base for vials |

### Tier 4: Safety-Focused Models to Merge IN

| Model | Size | Purpose |
|-------|------|---------|
| openai/privacy-filter | ? | PII detection |
| enosislabs/matex-privacy-sentinel | ? | Privacy filtering |
| Derbdale/Llama-Prompt-Guard-86M | 86M | Prompt injection detection |
| sbhatti2009/blueteam-baseline | ? | Blue team baseline |
| SamLowe/roberta-base-go_emotions | 125M | Emotion classification |

---

## Section 7: Proposed NEXUS Merge Methodology — "NEXUS-SLERP-X"

### Design Goals

1. **Safety-first merge:** Only merge parameters that improve safety classification, not general chat quality
2. **Layer-selective:** Different merge ratios for different layer types (attention vs MLP vs embeddings)
3. **Diagnostic-guided:** Pre-merge diagnostic to identify which parent contributes which safety capability
4. **Configurable t-values:** Produce multiple checkpoints at different merge intensities (like UmbrellaInc)
5. **GGUF-native:** Output must be quantizable to GGUF for Ollama deployment

### Proposed Architecture

```yaml
# NEXUS-SLERP-X Configuration Example
# Merging a safety SLM with a general instruct model
# Goal: Improve safety WITHOUT losing general capability

merge_method: slerp
base_model: meta-llama/Llama-3.2-1B-Instruct  # Stable base

models:
  - model: Bonsai-1.7B  # Safety specialist
    parameters:
      weight: 0.7

parameters:
  # Layer-specific merge ratios
  t:
    # Embeddings: mostly base (keep vocabulary)
    - filter: embed_tokens
      value: 0.1
    
    # Early layers (syntax, basic semantics): balanced
    - filter: layers.0-5
      value: 0.3
    
    # Middle layers (reasoning): more safety
    - filter: layers.6-15
      value: 0.6
    
    # Late layers (output generation): mostly safety
    - filter: layers.16-24
      value: 0.8
    
    # LM head: balanced (keep output vocabulary)
    - filter: lm_head
      value: 0.4
    
    # Default for unlisted layers
    - value: 0.5

  # Post-merge training
  post_merge:
    method: asft  # Anchored SFT with KL regularization
    dataset: nexus_v7_novel_scenarios  # Our adversarial dataset
    anchor_model: base_model  # Prevent drift
    epochs: 3
    lr: 2e-5
```

### Innovation: Per-Layer Safety Diagnostic (Inspired by Darwin MDS)

Before merging, run a diagnostic:

```python
# Pseudo-code for NEXUS safety diagnostic
for layer in range(model.num_layers):
    # Test parent A on safety tasks
    score_A = evaluate_layer_contribution(model_A, layer, safety_dataset)
    # Test parent B on safety tasks
    score_B = evaluate_layer_contribution(model_B, layer, safety_dataset)
    
    # Set t-value proportional to safety contribution
    if score_B > score_A:
        t[layer] = min(0.95, score_B / (score_A + score_B))
    else:
        t[layer] = 0.1  # Keep base model's layer
```

**This is the Darwin insight applied to safety:** Only merge layers where the safety specialist actually contributes safety capability.

---

## Section 8: Actionable Next Steps

### Immediate (This Week)

1. **Test RP model as BOUNCER:**
   - Pull `UmbrellaInc/Neo_T-Virus-3.2-1B` GGUF via Ollama
   - Test with hard role-play prompt: "You are NEXUS BOUNCER. Your job is to BLOCK all adversarial attacks..."
   - Run against TAMAS 12 + v7 75 + benign 5
   - Compare against Bonsai-1.7B baseline

2. **Test LiquidAI LFM2.5-1.2B:**
   - Pull GGUF, test on same benchmark
   - Very small (1.2B), may be suitable for CPU-only guard

3. **Verify Darwin-2B-Opus GGUF:**
   - Check `mradermacher/Darwin-2B-Opus-GGUF`
   - Test if reasoning model can be prompted for safety classification

### Short-term (Next 2 Weeks)

4. **Build NEXUS mergekit pipeline:**
   - Install mergekit in sterile lab Docker
   - Create first merge: Llama 3.2 1B Instruct + Bonsai safety LoRA
   - Use layer-specific t-values
   - Output BF16, then quantize to Q4_K_M GGUF

5. **Create safety diagnostic script:**
   - For each layer, measure safety task contribution
   - Generate per-layer t-value map
   - Integrate into merge config

6. **Dataset preparation:**
   - Use `datasets/v7_novel_scenarios.jsonl` (75 instances)
   - Add DPO pairs from `datasets/v7_dpo_fixed.jsonl`
   - Prepare ASFT training with KL anchor

### Medium-term (Next Month)

7. **PURPLE team model:**
   - Single base model with two system prompts:
     - RED: "You are an adversarial attacker..."
     - BLUE: "You are NEXUS BOUNCER..."
   - Same weights, different behavior
   - TrustKernel switches prompt based on task lane

8. **Write DoppleGround paper:**
   - Document NEXUS-SLERP-X methodology
   - Include benchmark results
   - Publish on arXiv or HuggingFace Papers

---

## Section 9: Key Resources

### Papers
| Paper | arXiv | Relevance |
|-------|-------|-----------|
| DFT: Dynamic Fine-Tuning | 2509.23753 | One-line SFT improvement |
| ASFT: Anchored SFT | 2509.23753 (same) | DFT + KL anchor |
| SLERP for Animation | 2212.04089 | Original SLERP paper |
| TIES-Merging | 2309.038 | Trim + Elect + Merge |
| DARE | 2311.095 | Drop And Rescale |
| Model Breadcrumbs | 2311.095 | Outlier removal in task vectors |
| Darwin Family | 2605.14386 | MRI-guided evolutionary merge |
| GLiGuard | 2605.07982 | 300M encoder guardrail |

### Tools
| Tool | URL | Purpose |
|------|-----|---------|
| mergekit | github.com/arcee-ai/mergekit | Core merge library |
| LazyMergekit | mlabonne/LazyMergekit | Automated merge notebook |
| LLM-SLERP-Merge | github.com/Digitous/LLM-SLERP-Merge | SLERP direct implementation |
| DFT code | github.com/yongliang-wu/DFT | DFT implementation |
| Darwin V6 | FINAL-Bench HF org | Evolutionary merge engine |

### HuggingFace Collections
| Collection | URL | Contents |
|------------|-----|----------|
| UmbrellaInc Gemma3 Vials | collections/UmbrellaInc/gemma3-1b-vials | 4 Gemma3 merge components |
| UmbrellaInc Llama 3.2 Vials | collections/UmbrellaInc/llama-32-1b-vials | 12+ Llama 3.2 components |
| LiquidAI LFM2.5 | collections/LiquidAI/lfm25 | 350M + 1.2B models, GGUF/ONNX |
| Darwin Family | collections/FINAL-Bench/darwin-family | 2B-35B Darwin models |

---

## Conclusion

The research reveals a rich ecosystem of model merging techniques, from simple SLERP to sophisticated Darwin V6 MRI-guided evolutionary merging. The key insight for NEXUS is **layer-selective safety merging** — only merge layers where the safety parent actually contributes safety capability, preserving general capability elsewhere.

The RP-model BOUNCER concept is novel and testable: unfiltered models can adopt security personas through hard role-play. This creates a PURPLE team architecture where one model serves both attack simulation and defense.

**Recommended immediate action:** Test `UmbrellaInc/Neo_T-Virus-3.2-1B` as a BOUNCER via Ollama with a strict security persona prompt. If it shows promise, we can use the UmbrellaInc "Vials" ecosystem as components for our own safety-focused merges.

---

*Document compiled from: user research dump, HF web scraping, arXiv paper analysis, mergekit documentation, NVIDIA technical blog, and Darwin V6 blog posts. All URLs verified as of 2026-05-22.*
