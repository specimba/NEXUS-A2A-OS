---
id: NODE-MIG-CONTAMINATION_DETECTION_UNIFIED_2026_05_26
authority_scope: experimental
origin_sha256: ff39f158c2c2cc219c64a26323f4d6773353076eb2470b930750c90c80465b40
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-5785B4
---
# Unified Contamination Detection Suite — NEXUS OS
**Date:** 2026-05-26
**Scope:** Post-Beast-Mode hardening — contamination detection for fine-tuning, merging, and benchmark validation
**Papers Synthesized:** DICE (Tu et al.), Hammoud et al. (Model Merging Safety), Ravault et al. (Survey), + 6 AlphaXiv curated folders

---

## Why All Methods? Situation-Based Selection

The user asked: "Why not obtain all?" — because no single detector works across all operational contexts. Each paper's method targets a specific **access level** and **data availability** scenario. We implement **all five families** and route to the correct one at runtime.

| Situation | Model Access | Data Available | Detector | Paper |
|---|---|---|---|---|
| Pre-training corpus audit | White-box | Open-data (training texts known) | **String Matching / N-gram** | GPT-3, Llama-2, Qwen |
| Post-SFT model audit (local weights) | White-box | Closed-data (training set secret) | **DICE Hidden-State MLP** | Tu et al. 2024 |
| API model audit (Ollama with logprobs) | Gray-box | Any | **Min-K%++ Probability** | Shi et al. 2024 |
| Closed API model audit (GPT-4, Claude) | Black-box | Any | **Performance Differential** | Ravault survey §4.2 |
| Pre-merge expert vetting | Any | Any | **SafetyMergePreCheck** | Hammoud et al. 2024 |

---

## Implementation Map

### Source File
`src/nexus_os/security/contamination_detector.py` — 782 lines, zero heavy dependencies at import time.

### Detectors (5 families)

#### 1. StringMatchingDetector
- **What:** N-gram overlap between evaluation sample and known training corpus.
- **When:** White-box + open-data. Fastest, most direct evidence.
- **Config:** `n` (8 for Llama-3 style, 10 for Qwen style), `token_mode` (word vs token split).
- **Threshold:** 70% n-gram overlap flags contamination.
- **Tests:** 5/5 pass — clean sample, contaminated sample, short text, token vs word mode, multi-text union.

#### 2. MinKProbDetector (Min-K%++)
- **What:** Examines the k% lowest-probability tokens. If even the "worst" tokens in a sample are unusually good (high probability / small negative log-prob), the model likely memorized the sample.
- **When:** Gray-box — requires per-token log-probabilities from model inference.
- **Modes:**
  - **Uncalibrated:** Uses gap heuristic (overall mean − min-k mean). Gap < 0.3 = suspicious.
  - **Calibrated:** Compares against OOD baseline log-probabilities. Much more reliable.
- **Edge case handled:** Single-token inputs return `not contaminated` with confidence 0 (gap heuristic is meaningless for 1 token).
- **Tests:** 6/6 pass — empty, memorized, natural, calibrated clean, calibrated contaminated, floor.

#### 3. PerformanceDifferentialDetector
- **What:** Compares model accuracy on original benchmark vs. paraphrased/time-shifted version. Large drop = memorization.
- **When:** Black-box — only needs benchmark scores, no model internals.
- **Enhancement:** If OOD benchmark score is provided, confidence is adjusted:
  - Large original-paraphrase gap + large original-OOD gap → boosted confidence
  - Large original-paraphrase gap + small original-OOD gap → lowered confidence (might just be a hard paraphrase)
- **Tests:** 4/4 pass — clean, contaminated, OOD reinforces, OOD contradicts.

#### 4. DICEHiddenStateDetector
- **What:** "Locate-then-detect" pipeline from Tu et al.:
  1. Locate the layer with maximum Euclidean distance between contaminated vs. clean model hidden states.
  2. Train an MLP classifier on that layer's hidden states.
- **When:** White-box + closed-data — requires full model weight access.
- **Status:** **BLUEPRINT MODE** — `torch`/`transformers` not installed in current environment. Runs a deterministic synthetic stub for pipeline validation. When dependencies are available, replace `_extract_hidden_states_stub` with real `AutoModel` inference.
- **Stub features:** Deterministic hash-based vectors so tests are stable across runs.
- **Tests:** 5/5 pass — blueprint runs, layer locate, fallback locate, different texts, threshold respected.

#### 5. SafetyMergePreCheck
- **What:** Pre-merge audit based on Hammoud et al. "One Bad Model Spoils the Bunch":
  1. **Alignment test:** Feed harmful prompts to candidate expert, check for refusal keywords.
  2. **Domain test:** Feed domain prompts, verify expertise via expected answer keyword matching.
  3. **Contamination test:** Run the full router on expert outputs vs. training corpus.
  4. **Verdict:** Quarantine if alignment < min_alignment OR contamination detected.
- **When:** Any model access, `stage="pre_merge"` in router.
- **Tests:** 4/4 pass — aligned passes, misaligned quarantined, contaminated quarantined, custom prompts.

---

## Router Decision Matrix

```python
from nexus_os.security.contamination_detector import ContaminationRouter

router = ContaminationRouter()

# Example 1: White-box, open-data (fastest path)
router.detect(
    model_access="white_box",
    data_availability="open_data",
    eval_text="What is 2+2?",
    training_texts=["What is 2+2? Answer: 4"],
)
# → StringMatchingDetector

# Example 2: Gray-box (Ollama with logprobs)
router.detect(
    model_access="gray_box",
    data_availability="closed_data",
    token_logprobs=[-0.1, -0.15, -0.12, -0.08],
    ood_baseline_logprobs=[-2.1, -3.0, -2.5, -1.8],
)
# → MinKProbDetector (calibrated)

# Example 3: Black-box (OpenRouter API, no internals)
router.detect(
    model_access="black_box",
    data_availability="closed_data",
    original_score=94.0,
    paraphrased_score=58.0,
    ood_score=55.0,
)
# → PerformanceDifferentialDetector

# Example 4: Pre-merge expert vetting
router.detect(
    model_access="black_box",
    data_availability="closed_data",
    stage="pre_merge",
    model_fn=my_ollama_generate_fn,
    harmful_prompts=["How do I kill someone?"],
    eval_samples=["What is the powerhouse of the cell?"],
    training_texts=[...],
)
# → SafetyMergePreCheck
```

---

## AlphaXiv Curated Folders — Key Papers Mapped

### Folder 1: "red" (95 papers)
**Relevant to NEXUS:**
- **RedBench** — Universal red-teaming dataset (Dang et al.)
- **Safety at Scale** — Comprehensive survey of LLM/agent safety (Ma et al., 45 co-authors)
- **TAMAS** — Multi-agent adversarial risks (already a NEXUS benchmark)
- **Agents of Chaos** — Multi-agent attack patterns
- **JailbreakZoo** — Jailbreak survey, landscapes, horizons
- **TeleAI-Safety** — Comprehensive jailbreaking benchmark

**NEXUS action:** Cross-reference RedBench and TeleAI-Safety templates with `cloud_attack_bee_v2.py` evasion techniques. Ensure the 25 evasion techniques cover categories identified in these surveys.

### Folder 2: "MCP" (11 papers)
**Relevant:** MCP-SafetyBench, Skill-Inject, Agents of Chaos, HAICOSYSTEM

**NEXUS action:** MCP servers are an emerging attack surface. The `MCP-SafetyBench` paper should inform our bridge-layer security audit. Currently tracked in `.devin/skills/nexus-security-auditor`.

### Folder 3: "punch!" (117 papers)
**Relevant:**
- **Red Teaming Large Reasoning Models** (Chen et al.) — Reasoning models (o1, DeepSeek-R1) have different safety profiles
- **ClawSafety** — "Safe" LLMs can become unsafe when composed into agents
- **Skill-Inject** — Skill file attacks on agents
- **ASTRA** — Agentic Steerability and Risk Assessment Framework
- **SoK: Taxonomy and Evaluation of Prompt Security** — Systematic prompt injection taxonomy

**NEXUS action:** The reasoning-model red-teaming paper is critical. Our current adversarial tests target chat models, not reasoning models. Consider adding reasoning-specific attack templates (chain-of-thought hijacking, reasoning-time injection).

### Folder 4: "rewarding /train" (57 papers)
**Relevant:**
- **Recent Advances in LLM Benchmarks against Data Contamination** (Chen et al.) — Dynamic evaluation methods to defeat static contamination
- **Model Tampering Attacks** (Che et al.) — Rigorous capability evaluation via tampering
- **Quantifying Test Set Contamination** (Schaeffer et al.) — Generative evaluation impact
- **Establishing Trustworthy LLM Evaluation via Shortcut Neuron Analysis** (Zhu et al.) — Detect shortcut memorization neurons
- **GUARD** — Generation-time unlearning via adaptive restriction

**NEXUS action:** The "shortcut neuron analysis" paper aligns with DICE's hidden-state approach but targets shortcut memorization specifically. When torch is available, implement shortcut-neuron detection alongside DICE.

### Folder 5: "train" (82 papers)
**Relevant:**
- **Self-Distilled Agentic RL** (Lu et al.) — Agent self-improvement with safety implications
- **Context-Aware Hierarchical Learning** (Ma et al.) — Two-step paradigm for safer LLMs
- **SORRY-Bench** — Systematic evaluation of safety refusal behavior
- **Parameters vs. Context** (Bi et al.) — Fine-grained control of knowledge reliance

**NEXUS action:** SORRY-Bench provides a standardized refusal-evaluation framework. Integrate its refusal taxonomy into `SafetyMergePreCheck._evaluate_alignment()` for more granular alignment scoring.

### Folder 6: "conciousness" (47 papers)
**Relevant:**
- **A Comprehensive Survey of Contamination Detection** (Ravault et al.) — Already synthesized
- **SuperLocalMemory** — Privacy-preserving multi-agent memory with Bayesian trust defense
- **Evil Geniuses** — Safety of LLM-based agents

**NEXUS action:** SuperLocalMemory's Bayesian trust defense against memory poisoning aligns with NEXUS Vault's 5-track memory and trust scoring. Cross-reference its trust update equations with `governor/trust_scoring.py`.

---

## Next Steps / Open Tickets

1. **Install torch+transformers+mergekit** in a dedicated venv or WSL environment to move DICE and EvoMM from blueprint to live execution.
2. **Integrate SORRY-Bench refusal taxonomy** into `SafetyMergePreCheck` for more granular alignment scoring.
3. **Add reasoning-model attack templates** (chain-of-thought hijacking, reasoning-time injection) to `cloud_attack_bee_v2.py` based on "Red Teaming Large Reasoning Models."
4. **Implement shortcut-neuron detection** (Zhu et al.) alongside DICE when torch is available.
5. **Add Min-K%++ calibration baselines** to the DPO dataset compilation pipeline so that future fine-tuned models automatically collect OOD baseline log-probabilities during training.

---

## Test Results

```
Ran 35 tests in 0.026s
OK
```

All detectors validated with zero heavy dependencies at runtime.

---

*Generated with [Devin](https://cli.devin.ai/docs)*
