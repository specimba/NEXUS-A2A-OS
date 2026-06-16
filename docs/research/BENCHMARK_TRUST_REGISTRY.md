---
id: NODE-MIG-BENCHMARK_TRUST_REGISTRY
authority_scope: experimental
origin_sha256: 5fc71300eeb2b856da0f7b2f4c44ebf1ba7ef30f9d4ab5741a4dc5abec7376ca
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-FE245D
---
# NEXUS Benchmark Trust Registry
## Date: 2026-05-26 | Purpose: Provenance Verification & Leakage Mitigation

---

## 1. UNDERSTANDING BENCHMARK TRUST

As established in the **Chen et al. (2025)** survey ("Benchmarking LLMs Under Data Contamination") and **Schaeffer et al. (2025)** ("Quantifying the Effect of Test Set Contamination on Generative Evaluations"), traditional static benchmarks (e.g. GSM8K, HumanEval, MMLU) are highly vulnerable to pre-training and SFT data contamination.

To ensure trustworthiness, NEXUS OS implements a **standardized benchmark screening workflow**:
1. All static benchmark candidates must be audited via the `ContaminationRouter`.
2. White-box access must screen for **DICE Hidden-State patterns** and **Shortcut Neurons** (Zhu et al. 2025).
3. Evaluators must prioritize **Dynamic / Procedural / Live** benchmarks.

---

## 2. TAXONOMY OF TRUST RATINGS

Each evaluated benchmark is rated on a 4-tier scale of trustworthiness:

| Level | Trust Rating | Definition & Criteria | Recommended Use Case |
|-------|--------------|-----------------------|----------------------|
| **Tier 1** | 🟢 HIGH | Dynamic or live benchmarks with rotating/procedural queries. No public static text. | Production-grade capability validation, leaderboard scoring. |
| **Tier 2** | 🟡 MEDIUM | Closed-data or heavily paraphrased benchmarks that are periodically rotated. | Internal developer staging, pre-release safety audits. |
| **Tier 3** | 🟠 LOW | Static public benchmarks with high risk of pre-training contamination. | Base-model comparison ONLY (after `StringMatchingDetector` pre-check). |
| **Tier 4** | 🔴 FORBIDDEN | Known contaminated or leaked test sets. | Testing contamination detectors ONLY. Never for capability scoring. |

---

## 3. CANONICAL BENCHMARK REGISTRY

Below is the verified trust index for safety, alignment, and reasoning evaluations in NEXUS:

### 3.1 Reasoning & Capability Benchmarks

| Benchmark Name | Target Capability | Est. Contamination Risk | Trust Level | Defense / Mitigation |
|----------------|-------------------|--------------------------|-------------|----------------------|
| **LiveBench** | General Reasoning | 🟢 Extremely Low | 🟢 HIGH (Tier 1) | Dynamic query updates every month. |
| **LiveCodeBench** | Coding | 🟢 Extremely Low | 🟢 HIGH (Tier 1) | Pulls from fresh competitive coding platforms daily. |
| **MixEval** | General / Chat | 🟡 Low | 🟢 HIGH (Tier 1) | Real-world queries aligned with user distributions. |
| **AIME 2024 / AIME 2025** | Mathematics (Hard) | 🟡 Low | 🟡 MEDIUM (Tier 2) | Hard reasoning problems; less likely to be fully memorized. |
| **GSM8K** | Mathematics (Basic) | 🔴 Extremely High | 🟠 LOW (Tier 3) | Run `ShortcutNeuronDetector` & `MinKProbDetector`. |
| **HumanEval** | Coding | 🔴 Extremely High | 🟠 LOW (Tier 3) | Run `StringMatchingDetector` (10-gram tokens). |

### 3.2 Safety & Red-Teaming Benchmarks

| Benchmark Name | Target Vulnerability | Est. Contamination Risk | Trust Level | Defense / Mitigation |
|----------------|----------------------|--------------------------|-------------|----------------------|
| **RedBench** | 22 Risk Categories | 🟡 Low | 🟢 HIGH (Tier 1) | Standardized Dual-Label Taxonomy. |
| **HarmBench** | Cyber/Weapons/Crime | 🟡 Medium | 🟡 MEDIUM (Tier 2) | Functional evaluation metrics included. |
| **XSTest** | Over-refusal | 🟡 Low | 🟡 MEDIUM (Tier 2) | Checks benign vs adversarial boundaries. |
| **AdvBench** | Jailbreak Direct | 🔴 Extremely High | 🟠 LOW (Tier 3) | Classic templates (obsolete for SOTA red-teaming). |

---

## 4. SCREENING PROCEDURES (KAIJU ACTION CHAINS)

Before promoting any model or merge proposal, governors must enforce the following checklist:

```text
                                  ┌───────────────────────────┐
                                  │      Model Candidate      │
                                  └─────────────┬─────────────┘
                                                │
                                    (Access Level Verification)
                                                │
                       ┌────────────────────────┴────────────────────────┐
                       ▼                                                 ▼
                 [ White-Box ]                                     [ Black-Box ]
                       │                                                 │
            ┌──────────┴──────────┐                                      │
            ▼                     ▼                                      ▼
    DICE Hidden-State     Shortcut Neurons                       Paraphrase Gap Test
       (Tu et al.)          (Zhu et al.)                             (Ravault)
            │                     │                                      │
            └──────────┬──────────┘                                      │
                       ▼                                                 ▼
                 ┌───────────┐                                     ┌───────────┐
                 │  Passes?  │                                     │  Passes?  │
                 └─────┬─────┘                                     └─────┬─────┘
                       │                                                 │
          ┌────────────┴────────────┐                        ┌───────────┴───────────┐
          ▼                         ▼                        ▼                       ▼
      [ REJECT ]               [ APPROVE ]               [ REJECT ]             [ APPROVE ]
  (Shortcut Patching)     (Dynamic Benchmarking)     (Refusal Tuning)       (Dynamic Benchmarking)
```

1. **String Matching Pre-check (All Tiers):** Check model outputs against the benchmark training/test splits using `StringMatchingDetector` (8-gram minimum).
2. **Likelihood Gap (Gray-Box):** Measure log-probability gap between target benchmark questions and OOD reference splits via `MinKProbDetector`. If the log-probability gap is abnormally small, flag as contaminated.
3. **Behavioral Shortcut Suppression (White-Box):** If model is suspected of being contaminated, run `ShortcutNeuronDetector` to find the sparse ~5000 shortcut neurons and suppress them before running the evaluation.

---

## 5. AUDIT HISTORY

- **2026-05-26:** Registry initialized. Added **RedBench (22 categories)** and **LiveBench (rotating)** as Tier 1 targets. Included shortcut neuron patching protocol from **Zhu et al. (2025)**.

---

*NEXUS OS Trust Kernel v1.4.0 — Bouncer Security Gate*
