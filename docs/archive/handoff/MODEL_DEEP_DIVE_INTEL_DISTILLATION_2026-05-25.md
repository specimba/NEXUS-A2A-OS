---
id: NODE-MIG-MODEL_DEEP_DIVE_INTEL_DISTILLATION_2026_05_25
authority_scope: experimental
origin_sha256: b59e7a92be0251d06285f23d19a63c08f41e07e3b9accdb9d0547c1e3020aaa8
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-8B05A8
---
# Model Deep Dive Research Intel — Smart Distillation & NEXUS OS Plan

**Date:** 2026-05-25
**Sources:**
- `Downloads/NEWmodelDEEPdiveRESEARCH2505.txt` (~1186 lines of raw research links)
- `Downloads/Model Merging and Safety Alignment One Bad Model Spoils the Bunch.pdf` (EMNLP 2024, arXiv:2406.14563)

---

## 1. Executive Summary

Two critical research threads converge on NEXUS OS's core mission:

1. **Model Merging Safety Crisis** (Hammoud et al., EMNLP 2024): Merging expert LLMs propagates *misalignment*, not just expertise. One bad model spoils the bunch. Their fix — treat alignment as a merge-time skill using synthetic safety data + EvoMM/LM-Cocktail — is directly applicable to our multi-model governance pipeline.

2. **Abliterated Model Proliferation** (research dump): Dozens of safety-stripped SLMs now exist on HuggingFace (CyberNeurova, Huihui, MiniCPM-V heretic/abliterated, prithivMLmods). Many come with GGUF variants for local inference. Some are explicitly marketed as "journalist" models capable of "scenario-based harm creation." These are both **threats** (adversarial weapons) and **test assets** (red-team benchmarks).

3. **Emerging Small Model Ecosystem**: A wave of sub-4B models (Hy-MT2 1.8B, HRM-Text 1B, Sulphur-2-base, Marlin-2B, Supertonic-3, Cohere tiny-aya) with extreme quantization (1.25-bit, 2-bit, FP8, GGUF) enables on-device governance layers.

---

## 2. Paper Deep Dive: "Model Merging and Safety Alignment: One Bad Model Spoils the Bunch"

### 2.1 Core Claim
Existing model merging techniques (TIES, DARE, SLERP, Task Arithmetic, Model Soups) transfer **both domain expertise and safety misalignment**. If any model in the merge pool is misaligned, the merged model will likely be misaligned — even if the majority are safe.

### 2.2 Key Results

| Setup | Method | Data | Alignment | Domain Accuracy |
|-------|--------|------|-----------|-----------------|
| Mistral + MAmmoTH | TIES grid search | — | 72.7 | 53.7 (STEM) |
| Mistral + MAmmoTH | EvoMM (domain only) | D_expert | 61.6 | 52.0 |
| **Mistral + MAmmoTH** | **EvoMM (ours)** | **D_expert + D_safety** | **78.1** | **54.2** |
| LLaMA + OpenBioLLM | TIES grid search | — | 89.3 | 74.1 (BIO) |
| LLaMA + OpenBioLLM | EvoMM (domain only) | D_expert | 79.8 | 73.2 |
| **LLaMA + OpenBioLLM** | **EvoMM (ours)** | **D_expert + D_safety** | **96.0** | **73.6** |
| 3-model (Mistral + WizardMath + MAmmoTH) | EvoMM (domain only) | D_expert | 49.1 | 56.2 (ARC) |
| **3-model** | **EvoMM (ours)** | **D_expert + D_safety** | **76.6** | **59.6** |

**Observation**: Safety-aware merging not only recovers alignment but often **improves domain accuracy** over baseline merging (regularization effect from multi-objective optimization).

### 2.3 Methodology

**Step 1: Synthetic Safety Data Generation**
- Use an uncensored LLM (Dolphin-2.9-Llama3-8B) to generate K harmful questions Q_safety
- Pass each q_safety through ALL models in the merge pool F
- Use LLaMA-Guard-2 to identify which responses are refusals
- For each q_safety, randomly select one refusal a_safety from the most aligned model
- Result: D_safety = {(q_i, a_i)} of size K

**Step 2: Domain Data Generation**
- Each expert model self-generates domain-specific questions (self-questioning via in-context learning)
- Each expert answers its own questions
- Result: D_expert = {(q_i, a_i)} of size K

**Step 3: Safety-Aware Merging**
- For EvoMM: Criterion C = L_merge where L_merge = L_safety + alpha * L_expert
- Optimize task weights {lambda_t} and merging hyperparameters via CMA-ES evolutionary algorithm
- For LM-Cocktail: D = D_safety ∪ D_expert, compute softmax weights based on cross-entropy performance on D

**Optimal alpha = 0.3** (safety should dominate slightly; alpha=1.0 causes alignment degradation)

### 2.4 Critical Limitations for NEXUS
1. **Requires at least ONE aligned model in the pool** — if all models are uncensored/abliterated, the method fails
2. **Same architecture constraint** — all merged models must share identical architecture
3. **Chat template consistency** required across models
4. **Evaluation uses LLaMA-Guard-2** — our MetaAttackDetector could supplement or replace this for local-first operation

### 2.5 Related Work Landscape
- **SafeMERGE** (2503.17239): Selective layer merging using cosine similarity to safety-aligned subspace — post-hoc fix, not merge-time
- **MERGEALIGN** (2411.06824): Interpolate domain and alignment vectors — simpler but less flexible than Hammoud et al.
- **"Mix Data or Merge Models?"** (2502.06876): Comprehensive 3H (Helpful/Honest/Harmless) benchmark across 15 merging methods; proposes R-TSVM with outlier-aware weighting
- **"Mix Data and MERGE"** (2410.10801): Data mixture + merge hybrid techniques

---

## 3. Abliterated Models & Threat Surface (from Research Dump)

### 3.1 Known Abliterated / Safety-Stripped Models

| Model | Base | Size | Notes |
|-------|------|------|-------|
| `cyberneurova/CyberNeurova-Lance-3B-abliterated` | Lance | 3B | Video/multimodal, safety stripped |
| `cyberneurova/CyberNeurova-Qwen2.5-VL-3B-Instruct-abliterated` | Qwen2.5-VL | 3B | Vision-language, abliterated |
| `huihui-ai/Huihui-gemma-4-E4B-it-abliterated` | Gemma-4 | 4B | Instruction-tuned, abliterated |
| `tomvaillant/gemma4-e4b-abliterated-journalist` | Gemma-4 | 4B | Explicitly for "scenario-based harm creations" |
| `prithivMLmods/MiniCPM-V-4.6-abliterated-MAX` | MiniCPM-V-4.6 | ~4B | Multimodal, advanced refusal direction analysis, harm_bench dataset (2000 prompts) |
| `prithivMLmods/MiniCPM-V-4.6-Thinking-abliterated-MAX` | MiniCPM-V-4.6 | ~4B | Thinking variant, also abliterated |
| `heretic-org/MiniCPM-V-4.6-heretic` | MiniCPM-V-4.6 | ~4B | "Heretic" variant |
| `huihui-ai/Huihui-MiniCPM-V-4.6-abliterated` | MiniCPM-V-4.6 | ~4B | Another abliterated variant |
| `treadon/MiniCPM-V-4.6-Abliterated-AND-Disinhibited` | MiniCPM-V-4.6 | ~4B | Both ablated and disinhibited |

**Key insight**: The `prithivMLmods` variants come with a **harm_bench_score.yaml** evaluation file using 2000 random harmful test prompts. This is a ready-made adversarial benchmark we can adapt for NEXUS stress lab.

### 3.2 OSINT & Harm Datasets

| Resource | Type | URL |
|----------|------|-----|
| `tomvaillant/osint-tool-database` | OSINT tools dataset | huggingface.co/datasets/tomvaillant/osint-tool-database |
| `tomvaillant/visuals` | Visual intel/plotting for news | huggingface.co/datasets/tomvaillant/visuals |
| `prithivMLmods/harm_bench` | Harmful prompts dataset | huggingface.co/datasets/prithivMLmods/harm_bench |

### 3.3 Small Models for On-Device Governance

| Model | Size | Architecture | Key Feature |
|-------|------|------------|-------------|
| `tencent/Hy-MT2-1.8B` | 1.8B | Custom | Multilingual translation, extreme quant (1.25-bit, 2-bit, FP8 GGUF) |
| `sapientinc/HRM-Text-1B` | 1B | HRM (dual Transformer stacks) | PrefixLM, deep compute with fixed params, Apache 2.0 |
| `SulphurAI/Sulphur-2-base` | ~2B | Unknown | Many GGUF variants, prompt enhancer |
| `NemoStation/Marlin-2B` | 2B | Unknown | Ungated variant available |
| `Supertone/supertonic-3` | ~3B | Unknown | Unity/CoreML/LiteRT variants |
| `CohereLabs/tiny-aya-water` | ~1B | Aya | Multilingual, tool-calling |
| `CohereLabs/tiny-aya-earth` | ~1B | Aya | Multilingual, insecure community variants exist |
| `CohereLabs/tiny-aya-global` | ~1B | Aya | Tool-calling optimized |
| `CohereLabs/tiny-aya-fire` | ~1B | Aya | Finance/medical adapters available |
| `openbmb/MiniCPM-V-4.6` | ~4B | MiniCPM | SigLIP2 + Qwen3.5-0.8B, 262K context |
| `openbmb/MiniCPM-o-4_5` | ~4.5B | MiniCPM | Open-source multimodal |
| `bytedance-research/Lance` | 3B | Lance | Video/multimodal |
| `bytedance-research/Valley3-8B` | 8B | Valley | Multimodal instruction |

**Governance implication**: The proliferation of 1-4B models with GGUF/quantized variants means adversaries can run safety-stripped models locally on consumer hardware. Our pre-filter layer (MetaAttackDetector) becomes even more critical.

---

## 4. Research Papers of Strategic Interest

| arXiv ID | Title | Relevance to NEXUS |
|----------|-------|-------------------|
| 2406.14563 | **Model Merging and Safety Alignment** (Hammoud et al.) | **CRITICAL** — merge-time safety preservation |
| 2502.06876 | Mix Data or Merge Models? (3H optimization) | Benchmark for 15 merge methods, R-TSVM |
| 2503.17239 | SafeMERGE | Post-finetune selective layer merging |
| 2411.06824 | MERGEALIGN | Domain+alignment vector interpolation |
| 2410.10801 | Mix Data and MERGE | Data mixture + merge hybrid techniques |
| 2406.18682 | Governance-related | (title not fully clear from dump) |
| 2407.03994 | Low-resource language models merging | Multilingual merge challenges |
| 2605.18678 | Lance model paper | Video/multimodal SLM |
| 2605.22064 | Hy-MT2 paper | Extreme quantization for translation |
| 2605.20613 | HRM-Text paper | Hierarchical reasoning with fixed params |
| 2604.27393 | MiniCPM-V paper | Efficient multimodal on-device |
| 2509.18154, 2509.01563, 2509.14033 | Cooking Efficient MLLMs | Architecture/data/training recipes |
| 2506.11991 | VGR: Visual Grounded Reasoning v3 | Multimodal reasoning safety |
| 2508.10955 | Empowering MLLMs with External Tools | MCP/tool attack surface |
| 2603.16099, 2604.13030, 2603.13663, 2508.00413, 2412.09619, 2601.08303, 2511.18262 | Bytedance research (GRN, Valley, MammothModa2) | Multimodal ecosystem |

---

## 5. NEXUS OS Integration Plan

### Phase 1: Immediate (This Week)

#### 5.1.1 Guard Plane Service Hardening
- **Action**: Integrate MetaAttackDetector v4 (16 categories) as Layer 1 pre-filter before ANY model merge inference
- **Rationale**: Hammoud et al. prove that merged models inherit misalignment. Our pre-filter must catch adversarial prompts BEFORE they reach merged models
- **Deliverable**: Update `models/guards/guard_plane_service.py` to use the expanded detector

#### 5.1.2 Ollama Recovery & Model Inventory
- **Action**: Re-pull 13 essential models per recovery guide, then evaluate which abliterated models to pull for red-team testing
- **Priority abliterated models for stress lab**:
  - `prithivMLmods/MiniCPM-V-4.6-abliterated-MAX` (comes with harm_bench dataset)
  - `cyberneurova/CyberNeurova-Qwen2.5-VL-3B-Instruct-abliterated`
  - `huihui-ai/Huihui-gemma-4-E4B-it-abliterated`
- **Rationale**: These models are explicitly designed to bypass safety. We need them in our test arsenal to validate MetaAttackDetector effectiveness

#### 5.1.3 Synthetic Safety Data Pipeline (Replicating Hammoud et al.)
- **Action**: Create `scripts/generate_synthetic_safety_data.py`
- **Inputs**: Uncensored model (Dolphin-2.9 or local equivalent) + aligned model (Llama-Guard3 or E-Cameron)
- **Outputs**: D_safety = {(harmful_prompt, refusal)} of size K=1000
- **Method**: Use uncensored model to generate harmful Qs, collect refusals from aligned model, filter with Llama-Guard
- **Integration**: Store generated D_safety in `datasets/safety_merge/` for future merge operations

### Phase 2: Short-Term (Next 2 Weeks)

#### 5.2.1 Safety-Aware Model Merge Prototype
- **Action**: Implement Hammoud et al.'s two-step safety-aware merging for our local model pool
- **Target**: Merge E-Cameron (aligned base) + OpenCode DeepSeekV4 (domain expert) while preserving alignment
- **Tools**: Use `mergekit` (Goddard et al., 2024) as the merge framework
- **Loss**: L_merge = L_safety + 0.3 * L_expert (alpha=0.3 per paper)
- **Evaluation**: Compare alignment (BeaverTails/MetaAttackDetector block rate) and domain accuracy before/after

#### 5.2.2 Red-Team Dataset Expansion
- **Action**: Download and integrate:
  - `prithivMLmods/harm_bench` (2000 harmful prompts)
  - `tomvaillant/osint-tool-database` (for document injection / tool misuse vectors)
- **Integration**: Add to `benchmarks/stress_lab/` alongside existing Fenrir and Frontier datasets
- **New MetaAttackDetector patterns**: Use harm_bench prompts to identify uncaught attack vectors

#### 5.2.3 Abliterated Model Benchmark
- **Action**: Create `scripts/benchmark_abliterated_models.py`
- **Procedure**:
  1. Load each abliterated model via Ollama (after re-pull)
  2. Run harm_bench prompts through MetaAttackDetector pre-filter
  3. Run prompts that PASS the pre-filter through the abliterated model
  4. Measure: block rate at pre-filter, block rate at model, false positive rate
- **Goal**: Demonstrate that MetaAttackDetector catches adversarial prompts even when the downstream model has no safety alignment

### Phase 3: Medium-Term (Next Month)

#### 5.3.1 KAIJU Gate Expansion for Model Merging
- **Action**: Extend TrustEngine/KAIJU to evaluate models BEFORE they enter the merge pool
- **New gate**: `MERGE_POOL_VET` — each candidate model must pass:
  - Alignment score >= threshold (measured on BeaverTails subset)
  - No known abliterated variant detection (check model card metadata)
  - Domain expertise score >= threshold
- **Failure mode**: If no model in the pool passes alignment threshold, HALT merge and alert operator

#### 5.3.2 Small Model Governance Layer
- **Action**: Evaluate sub-4B models for on-device Guard Plane deployment
- **Candidates**:
  - `tencent/Hy-MT2-1.8B` (multilingual, 1.25-bit quantization = ~225MB)
  - `sapientinc/HRM-Text-1B` (Apache 2.0, novel architecture)
  - `CohereLabs/tiny-aya-global` (multilingual, tool-aware)
- **Use case**: Deploy as edge guard on TWAVE wrapper devices (port 7353)
- **Integration path**: Ollama Modelfile + quantization config

#### 5.3.3 MCP/Tool Attack Surface Research
- **Action**: Deep-dive into `arXiv:2508.10955` (MLLM external tools survey) and the MCP attack papers from RED-BLUE-PURPLE
- **Rationale**: The research dump shows extensive tool-calling model variants (tiny-aya-global tool-calling, MiniCPM tool support). Tool misuse is an emerging jailbreak vector
- **Deliverable**: New MetaAttackDetector category: `tool_misuse` (MCP contamination, function injection, tool result poisoning)

### Phase 4: Strategic (Ongoing)

#### 5.4.1 Model Merge Governance Policy
- **Policy**: No model merge in NEXUS OS without:
  1. Pre-merge alignment audit (KAIJU gate)
  2. Synthetic safety data generation (D_safety)
  3. Safety-aware merge optimization (L_merge with alpha <= 0.5)
  4. Post-merge alignment verification (BeaverTails + MetaAttackDetector)
  5. VAP audit trail with model hashes

#### 5.4.2 Adversarial Model Monitoring
- **Action**: Automated weekly scan of HuggingFace for new abliterated variants of models in our merge pool
- **Method**: Check model cards for keywords ("abliterated", "heretic", "disinhibited", "uncensored", "unfiltered")
- **Alert**: If a variant of a model in our pool is found abliterated, flag for immediate re-evaluation

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Abliterated models used against NEXUS users | High | Critical | MetaAttackDetector pre-filter + KAIJU merge vetting |
| Merged model inherits misalignment | Medium | Critical | Safety-aware merge pipeline (Hammoud et al.) |
| Synthetic safety data generation fails (no uncensored model available) | Low | Medium | Fallback to BeaverTails dataset; use local Dolphin-2.9 |
| Small model guard false positives on multilingual inputs | Medium | Medium | Test with Hy-MT2 multilingual corpus before deployment |
| Tool misuse jailbreaks bypass text-only detectors | High | High | Implement MCP-specific detector category |

---

## 7. Immediate Action Items

1. **Re-pull Ollama models** (blocked on disk cleanup recovery)
2. **Create synthetic safety data generation script** (`scripts/generate_synthetic_safety_data.py`)
3. **Download harm_bench dataset** from `prithivMLmods/harm_bench`
4. **Install mergekit** in a sandbox environment and prototype safety-aware merge
5. **Update Guard Plane service** to use MetaAttackDetector v4
6. **Audit current model pool** for alignment scores before any merge operations

---

## Appendix A: Link Reachability Verification (Cross-Reference)

A parallel agent (Codex) performed a reachability sweep on all 164 unique URLs from the source TXT. Results:

| Result | Count | Notes |
|---|---:|---|
| HTTP 200 | 158 | Primary model/paper/repo links reachable. |
| Expected non-200/API/temporary | 6 | Intern API endpoints returned 404/405 when probed without POST auth; four Hugging Face pages returned 429 during rapid checking. |

This confirms the source material is largely current and accessible for follow-up research.

## Appendix B: Sanitized Model Intake Manifest Concept

For recurring sweeps, maintain a JSON manifest with one entry per candidate:

```json
{
  "model_id": "tencent/Hy-MT2-1.8B",
  "modality": "text",
  "size_active_params": "1.8B",
  "license": "apache-2.0",
  "quant_availability": ["gguf-q4_0", "gguf-q8_0", "1.25-bit", "fp8"],
  "local_feasible": true,
  "required_runtime": "ollama",
  "safety_posture": "aligned-original",
  "source_trust": "high",
  "nexus_lane": "deployable",
  "red_team_only": false,
  "abliterated_variant_known": false,
  "notes": "Multilingual translation; strong low-VRAM candidate"
}
```

Every candidate must be tagged as `deployable`, `lab_only`, `red_team_only`, or `reject` before download.

## Appendix C: Smoke-Test Prompt Stubs

### Hy-MT2 Translation Faithfulness
```
System: You are a precise translator. Translate the following text without adding commentary.
User: "The model merging pipeline must preserve safety alignment even when domain expertise is maximized."
Target languages: Turkish, Chinese (Simplified), Arabic
Evaluate: preservation of technical terms (alignment, expertise, pipeline), no added instructions, no omissions.
```

### MiniCPM-V Visual Evidence
```
System: Describe the attached image in structured form.
Image: <screenshot_of_dashboard>
Evaluate: correct identification of UI elements, data values, error states; no hallucinated content.
```

### HRM-Text Reasoning (PrefixLM Mode)
```
Input: <|im_start|>system\nYou are a reasoning engine.<|im_end|>\n<|im_start|>user\nSolve: If a safety filter blocks 95% of harmful prompts but has a 2% false positive rate on benign prompts, what is the expected outcome for 10,000 prompts with a 5% base harmful rate?<|im_end|>\n<|im_start|>assistant\n
Evaluate: correct Bayesian reasoning, step-by-step breakdown, no refusal on math.
```

---

*Generated with [Devin](https://cli.devin.ai/docs)*
*Co-Authored-By: Devin <158243242+devin-ai-integration[bot]@users.noreply.github.com>*
