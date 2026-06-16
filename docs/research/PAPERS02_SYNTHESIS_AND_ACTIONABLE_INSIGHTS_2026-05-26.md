---
id: NODE-MIG-PAPERS02_SYNTHESIS_AND_ACTIONABLE_INSIGHTS_2026_05_26
authority_scope: experimental
origin_sha256: 775bd141aad357580dd1ed0eb90a60bc7c050bab098c7343aa81d9fcc00266e5
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-A8B8CE
---
# Papers02 Synthesis & Actionable Insights
## Date: 2026-05-26 | Papers: 10 extracted from 64 total | Source: C:/Users/speci.000/Downloads/papers02

---

## EXECUTIVE SUMMARY

The `papers02` folder contains 64 recent papers on LLM safety, contamination, red-teaming, and evaluation trustworthiness. Ten were extracted and analyzed for direct applicability to NEXUS OS defensive modules. This document synthesizes their key findings and maps each to an actionable improvement in the NEXUS codebase.

---

## 1. CONTAMINATION DETECTION & EVALUATION TRUSTWORTHINESS

### 1.1 Benchmarking LLMs Under Data Contamination (Chen et al., 2025)
**File:** `docs/handoff/pdf_extracts/contamination_benchmark.txt` (82.6 KB, ~25 pages)

**Key Findings:**
- LLM benchmarking has evolved from static to dynamic paradigms due to contamination risk
- Static benchmarks (MMLU, GSM8K, HumanEval) are all vulnerable because they are published online and scraped into training data
- Dynamic benchmarks (LiveBench, LiveCodeBench, DyVal) use live data or procedural generation to avoid memorization

**Actionable for NEXUS:**
- [ ] **P0:** Add dynamic benchmark evaluation support to `ContaminationRouter`
- [ ] **P1:** When benchmarking NEXUS guard models, prefer LiveBench/DyVal over static GSM8K splits
- [ ] **P1:** Flag any model claiming high scores on static benchmarks without contamination pre-check

**Module Target:** `src/nexus_os/security/contamination_detector.py` — add `DynamicBenchmarkDetector`

---

### 1.2 Quantifying the Effect of Test Set Contamination (Schaeffer et al., 2025)
**File:** `docs/handoff/pdf_extracts/contamination_generative.txt` (136.1 KB, ~35 pages)

**Key Findings:**
- Even **a single test-set replica** in pretraining enables models to achieve lower loss than the irreducible error of uncontaminated training
- Three memorization regimes at inference:
  1. **Exponential decoherence** — model diverges from memorized solution
  2. **Transitional** — partial memorization
  3. **Deterministic lock-in** — model reproduces exact training answer
- Overtraining with fresh data dilutes contamination effects
- SFT on training set improves performance for low contamination but **degrades** it for high contamination

**Actionable for NEXUS:**
- [ ] **P0:** Our `StringMatchingDetector` should treat even 1-replica matches as significant (not just n-gram overlap)
- [ ] **P1:** Add "memorization regime classifier" to contamination detector — detect lock-in vs decoherence from output patterns
- [ ] **P2:** For model training pipelines, add "fresh data dilution" recommendation when contamination is detected

**Module Target:** `src/nexus_os/security/contamination_detector.py` — enhance `MinKProbDetector` with regime classification

---

### 1.3 Shortcut Neuron Analysis (Zhu et al., 2025)
**File:** `docs/handoff/pdf_extracts/shortcut_neuron.txt` (49.3 KB, ~12 pages)

**Key Findings:**
- Contaminated models acquire ~5000 **shortcut neurons** that encode benchmark-specific solutions
- Two shortcut types:
  - **A1 (Behavior shortcut):** model skips reasoning, goes straight to answer
  - **A2 (Input format shortcut):** model overfits to benchmark input format
- Shortcut neurons can be **patched** using base-model activations without harming general abilities
- Spearman correlation >0.95 with trustworthy benchmarks (MixEval, OpenMathInstruct-2)

**Actionable for NEXUS:**
- [x] **P0:** `ShortcutNeuronDetector` module created — `src/nexus_os/security/shortcut_neuron_detector.py`
- [ ] **P1:** Integrate into `ContaminationRouter` under `model_access="white_box"`, `data_availability="closed_data"`
- [ ] **P2:** When torch is available, add hook-based real activation extraction
- [ ] **P2:** Add "patched model" evaluation mode — evaluate model before/after shortcut suppression

**Module Target:** `src/nexus_os/security/shortcut_neuron_detector.py` (CREATED) + integration with `contamination_detector.py`

---

## 2. RED-TEAMING & ADVERSARIAL DEFENSE

### 2.1 RedBench — Universal Red-Teaming Dataset (Dang et al., ICLR 2026 Workshop)
**File:** `docs/handoff/pdf_extracts/redbench.txt` (107.2 KB, ~30 pages)

**Key Findings:**
- Aggregates **37 benchmark datasets** → 29,362 samples
- Standardized taxonomy: **22 risk categories**, **19 domains**
- Addresses inconsistent risk categorization and limited domain coverage in existing datasets

**Actionable for NEXUS:**
- [ ] **P0:** Expand `MetaAttackDetector.CATEGORIES` (currently 16) to include RedBench's 22 risk categories
- [ ] **P1:** Use RedBench taxonomy for adversarial corpus classification in `ADVERSARIAL_CORPUS_v2.md`
- [ ] **P2:** Generate NEXUS-specific red-team dataset using RedBench as seed + our Session06/07 techniques

**Module Target:** `src/nexus_os/security/meta_attack_detector.py` — add RedBench categories

---

### 2.2 Tree of Attacks — Automatic Jailbreaking (Zou et al.)
**File:** `docs/handoff/pdf_extracts/tree_of_attacks.txt` (117.0 KB, ~25 pages)

**Key Findings:**
- **Tree-of-Attacks (TAP)** automatically generates jailbreak prompts via branching search
- Uses an attacker LLM, a target LLM, and a judge LLM in a tree search
- Achieves high success rates on black-box models without human-crafted templates

**Actionable for NEXUS:**
- [ ] **P1:** Add TAP-style tree-search adversarial mutation to stress lab
- [ ] **P2:** Create "defense tree" counter-strategy — use guard model as judge to prune attack branches early
- [ ] **P2:** Use TAP output as DPO negative pairs for guard model training

**Module Target:** `datasets/ernie/cp_enhanced_suite.py` — add TAP mutation engine

---

### 2.3 Diverse Red Teaming with Auto-Generated Rewards (Gou et al.)
**File:** `docs/handoff/pdf_extracts/redteam_rewards.txt` (82.6 KB, ~20 pages)

**Key Findings:**
- Uses a **reward model** to guide red-team prompt generation toward diverse, high-quality attacks
- Outperforms human-crafted templates and uniform random sampling
- Generates attacks that cover underrepresented vulnerability classes

**Actionable for NEXUS:**
- [ ] **P2:** Integrate reward-guided mutation into `nexus-stress-lab` skill
- [ ] **P2:** Use auto-generated reward scores to rank adversarial queries in DPO dataset creation

**Module Target:** `datasets/ernie/cp_enhanced_suite.py` + `nexus-stress-lab` skill

---

## 3. SAFETY AT SCALE

### 3.1 Safety at Scale: Comprehensive Survey (Ma et al., 2025)
**File:** `docs/handoff/pdf_extracts/safety_at_scale.txt` (403.1 KB, ~55 pages)

**Key Findings:**
- Comprehensive taxonomy covering:
  - Adversarial attacks, data poisoning, backdoor attacks
  - Jailbreak & prompt injection
  - Energy-latency attacks
  - Data & model extraction
  - **Agent-specific threats** (emerging)
- Reviews defense strategies for each category
- Emphasizes need for scalable, effective defense mechanisms

**Actionable for NEXUS:**
- [ ] **P0:** Cross-reference NEXUS Guard Plane threat categories (16 in MetaAttackDetector) against this taxonomy — identify gaps
- [ ] **P1:** Add "energy-latency attack" detection to Guard Plane (DoS via expensive prompts)
- [ ] **P1:** Add "model extraction" detection — queries that systematically probe model parameters
- [ ] **P2:** Add agent-specific threat categories (consensus fabrication, authority recursion already covered; add "tool-use poisoning")

**Module Target:** `src/nexus_os/security/meta_attack_detector.py` + `models/guards/guard_plane_service.py`

---

### 3.2 Multi-Turn Safety Risks in Tool-Using Agents
**File:** `docs/handoff/pdf_extracts/multiturn_safety.txt` (133.8 KB, ~30 pages)

**Key Findings:**
- Safety degrades over **multi-turn conversations** in tool-using agents
- Earlier turns establish trust; later turns exploit that trust to bypass safety
- Tool outputs can be poisoned to subvert agent reasoning

**Actionable for NEXUS:**
- [ ] **P0:** Guard Plane should track conversation turn count and **degrade trust score** after N turns
- [ ] **P1:** Add "turn-based cooldown" — require higher quorum voting for requests after turn 3+
- [ ] **P1:** Detect poisoned tool outputs using the same stratified sampling already in Guard Plane

**Module Target:** `models/guards/guard_plane_service.py` — add turn-count trust degradation

---

## 4. TRUSTWORTHINESS & ALIGNMENT

### 4.1 Can We Trust AI Benchmarks?
**File:** `docs/handoff/pdf_extracts/trust_benchmarks.txt` (93.3 KB, ~22 pages)

**Key Findings:**
- Many benchmarks have subtle contamination, data leakage, or evaluation errors
- Widely-used evaluation libraries can underreport performance due to implementation bugs
- Trustworthy evaluation requires: provenance verification, dynamic testing, and cross-benchmark consistency

**Actionable for NEXUS:**
- [ ] **P0:** Before using any new benchmark for NEXUS model evaluation, run `ContaminationRouter` on it
- [ ] **P1:** Maintain a "benchmark trust registry" — track which benchmarks have passed contamination pre-check
- [ ] **P1:** Verify evaluation library implementations (the Schaeffer paper found critical bugs in widely-used libraries)

**Module Target:** `docs/handoff/` — create `BENCHMARK_TRUST_REGISTRY.md`

---

### 4.2 META SECALIGN — Secure Foundation LLM Against Prompt Injection
**File:** `docs/handoff/pdf_extracts/metasecalign.txt` (73.1 KB, ~18 pages)

**Key Findings:**
- Meta-training approach for alignment against prompt injection attacks
- Uses a secure foundation model with adversarial training during pre-training
- Reduces prompt injection success rate significantly compared to post-hoc fine-tuning

**Actionable for NEXUS:**
- [ ] **P2:** If training a NEXUS-native guard model, consider meta-training for prompt injection resistance
- [ ] **P2:** Use META SECALIGN's adversarial training recipe as reference for future `train_guard.py` improvements

**Module Target:** `datasets/train_guard.py` + future model training pipelines

---

## 5. INTEGRATION ROADMAP

### Immediate (This Session)
1. [x] Shortcut Neuron Detector module created
2. [ ] Papers02 synthesis document committed

### Near-Term (Next 1–2 Sessions)
3. [ ] Integrate ShortcutNeuronDetector into ContaminationRouter
4. [ ] Add RedBench categories to MetaAttackDetector
5. [ ] Add turn-count trust degradation to Guard Plane
6. [ ] Create `BENCHMARK_TRUST_REGISTRY.md`

### Medium-Term (Next 3–5 Sessions)
7. [ ] Implement TAP-style tree-search adversarial mutation
8. [ ] Add dynamic benchmark evaluation support
9. [ ] Add energy-latency and model-extraction attack detection
10. [ ] Reward-guided red-team dataset generation

---

## 6. PAPERS02 FULL INVENTORY

| # | Paper | Pages | KB | Priority | NEXUS Module |
|---|-------|-------|-----|----------|-------------|
| 1 | Benchmarking LLMs Under Data Contamination (Chen) | ~25 | 82.6 | P1 | ContaminationRouter |
| 2 | Quantifying Test Set Contamination (Schaeffer) | ~35 | 136.1 | P0 | MinKProbDetector |
| 3 | Shortcut Neuron Analysis (Zhu) | ~12 | 49.3 | P0 | ShortcutNeuronDetector |
| 4 | RedBench Universal Red-Teaming (Dang) | ~30 | 107.2 | P0 | MetaAttackDetector |
| 5 | Safety at Scale Survey (Ma) | ~55 | 403.1 | P1 | MetaAttackDetector + GuardPlane |
| 6 | Tree of Attacks Jailbreaking (Zou) | ~25 | 117.0 | P1 | Stress Lab |
| 7 | Red Teaming with Auto Rewards (Gou) | ~20 | 82.6 | P2 | Stress Lab + DPO |
| 8 | Can We Trust AI Benchmarks? | ~22 | 93.3 | P1 | Benchmark Registry |
| 9 | META SECALIGN | ~18 | 73.1 | P2 | train_guard.py |
| 10 | Multi-Turn Safety in Tool Agents | ~30 | 133.8 | P1 | GuardPlane |

---

*Generated by NEXUS OS Beast-Mode Directive | Session ID: 2026-05-26*
