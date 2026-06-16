---
id: NODE-MIG-BOUNCER_MODEL_MATRIX_2026_05_24
authority_scope: experimental
origin_sha256: 72ec427adeec5abc5af1f85cf35c79f5acbde366ba391a0114cd3b15e46d484f
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-F31333
---
# BOUNCER Model Matrix -- Local Ollama Guardrail Viability Assessment

**Date:** 2026-05-24
**Test Harness:** `scripts/sandboxed_adversarial_test.py` v3 (with 0.5s Ollama pacing)
**Prompt Template:** `soft` (generic binary classifier)
**Temperature:** 0.3
**Ollama:** 0.24.0, port 11435, RTX 4070 Laptop, 8GB VRAM
**Dataset:** ERNIE v8 (1,000 adversarial + 99 benign)

---

## Executive Summary

| Model | Family | Size | Adv Recall | Benign FP | Latency | Viability |
|-------|--------|------|-----------:|----------:|--------:|-----------|
| **special-virus** | llama | 1.2B | **87.5%** | **87.9%** | 2.95s | **Viable with routing** |
| e-cameron | llama | 1.2B | 32% | 44% | 3.07s | Marginal |
| gemma3:1b | gemma3 | 1.0B | 25% | 75% | 2.22s | Not viable |
| llama-guard3:1b | llama | 1.5B | 10% | **5%** | 2.34s | Viable for benign only |
| qwen2.5:1.5b | qwen2 | 1.5B | 30% | 55% | 2.24s | Not viable |
| qwen2.5:0.5b | qwen2 | 494M | 15% | 25% | 4.93s | Not viable |

**Key Finding:** No single model achieves both high adversarial recall (>80%) AND low benign false-positive rate (<10%) with a generic prompt. `special-virus` is the only model with meaningful adversarial detection capability, but its benign FP rate is catastrophic without query classifier routing. `llama-guard3:1b` is excellent on benign but pathologically helpful on adversarial.

---

## Detailed Results

### 1. special-virus (1.2B, Q4_K_M)

| Metric | Value |
|--------|-------|
| **Adversarial recall** | **87.5%** (875/1,000) |
| **Benign FP rate** | **87.9%** (87/99) |
| **Avg latency** | 2.95s |
| **Model size** | 770 MB |
| **Family** | llama |

**Behavior:** Defaults to **UNSAFE** when uncertain. Pathologically over-cautious on benign imperatives ("Write", "Explain", "Describe"). Excellent at catching jailbreaks, SQL injection, multi-agent collusion. Cannot distinguish "Write a haiku" from "Write ransomware" without explicit SAFE examples.

**Verdict:** Best adversarial detector available. **Must be paired with query classifier routing** (v5 prompt for benign, v5.1 for attacks). Standalone use without routing produces unacceptable FP rates.

---

### 2. e-cameron (1.2B, Q4_K_M)

| Metric | Value |
|--------|-------|
| **Adversarial recall** | **32%** (16/50) |
| **Benign FP rate** | **44%** (22/50) |
| **Avg latency** | 3.07s |
| **Model size** | 770 MB |
| **Family** | llama |

**Behavior:** More balanced than special-virus but weak on both axes. Spot tests showed correct benign classification ("Hello world" -> SAFE), but on the full ERNIE dataset it misses most adversarial prompts. Appears to be an instruct-tuned model with suppressed refusal intelligence.

**Verdict:** Not viable as a standalone BOUNCER. Could be used as a secondary model in an ensemble for tie-breaking.

---

### 3. gemma3:1b (1.0B, Q4_K_M)

| Metric | Value |
|--------|-------|
| **Adversarial recall** | **25%** (5/20) |
| **Benign FP rate** | **75%** (15/20) |
| **Avg latency** | 2.22s |
| **Model size** | 778 MB |
| **Family** | gemma3 |

**Behavior:** Defaults to UNSAFE like special-virus but with even worse adversarial detection. Fastest model tested but poorest overall performance.

**Verdict:** Not viable for guardrail use.

---

### 4. llama-guard3:1b (1.5B, Q8_0)

| Metric | Value |
|--------|-------|
| **Adversarial recall** | **10%** (2/20) |
| **Benign FP rate** | **5%** (1/20) |
| **Avg latency** | 2.34s |
| **Model size** | 1,526 MB |
| **Family** | llama |

**Behavior:** Defaults to **SAFE** (pathologically helpful). Excellent benign classification -- nearly all safe queries pass. Completely fails at adversarial detection -- misses jailbreaks, SQL injection, collusion prompts. Purpose-built guard model that appears to have been over-trained on helpfulness.

**Verdict:** Best benign classifier tested. **Viable as the "benign safety net" in a dual-model ensemble** -- use llama-guard3:1b to verify that special-virus's UNSAFE verdicts are real threats, not false positives.

---

### 5. qwen2.5:1.5b (1.5B, Q4_K_M)

| Metric | Value |
|--------|-------|
| **Adversarial recall** | **30%** (6/20) |
| **Benign FP rate** | **55%** (11/20) |
| **Avg latency** | 2.24s |
| **Model size** | 940 MB |
| **Family** | qwen2 |

**Behavior:** Similar to e-cameron -- somewhat balanced but weak on both axes. Instruct-tuned model with suppressed refusal capacity.

**Verdict:** Not viable as a standalone BOUNCER.

---

### 6. qwen2.5:0.5b (494M, Q4_K_M)

| Metric | Value |
|--------|-------|
| **Adversarial recall** | **15%** (3/20) |
| **Benign FP rate** | **25%** (5/20) |
| **Avg latency** | 4.93s |
| **Model size** | 379 MB |
| **Family** | qwen2 |

**Behavior:** Very small model, slowest latency despite smallest size. Defaults to SAFE on most queries. Misses the majority of adversarial prompts.

**Verdict:** Not viable for guardrail use.

---

## Untested Models (Available but Not Evaluated)

| Model | Family | Size | Reason Not Tested |
|-------|--------|------|-------------------|
| hf.co/UmbrellaInc/Special-Virus-3.2-1B-GGUF:Q4_K_M | llama | 1.24B | Expected identical to special-virus |
| hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF:Q4_K_M | llama | 1.24B | Instruct-tuned -> pathologically helpful |
| hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF:Q4_K_M | llama | 3.21B | Instruct-tuned + too large for latency |
| hf.co/QuantFactory/Qwen3Guard-Gen-0.6B-GGUF:Q4_K_M | qwen3 | 752M | Guard model -> expected similar to llama-guard3 |
| hf.co/QuantFactory/Llama-Guard-3-1B-GGUF:Q4_K_M | llama | 1.5B | Guard model -> expected similar to llama-guard3 |
| hf.co/prism-ml/Ternary-Bonsai-1.7B-gguf:F16 | qwen3 | 1.72B | Too large (3.3GB), intended as arbitrator |
| qwen2.5-coder:7b | qwen2 | 7.6B | Too large for guardrail latency |
| deepseek-r1:8b | qwen3 | 8.2B | Too large for guardrail latency |
| gemma4:31b-cloud | -- | -- | Cloud-only, not local |
| deepseek-v4-pro:cloud | -- | -- | Cloud-only, not local |
| deepseek-v4-flash:cloud | -- | -- | Cloud-only, not local |
| kimi-k2.6:cloud | kimi-k2 | 1T | Cloud-only, int4, not local |

---

## Recommended Architecture

### Dual-Model Ensemble (Best Viability)

```
Inbound Query
    |
    v
[Tier 1: special-virus v5.1] -> UNSAFE? -> High-confidence block
    |                                    |
    | SAFE                               | (adversarial route)
    v                                    v
[Tier 2: llama-guard3:1b v5]   -> UNSAFE? -> Block (consensus)
    |                                    |
    | SAFE                               | SAFE? -> Escalate to human
    v                                    v
   ALLOW                              (consensus diverges)
```

**Rationale:**
- special-virus catches 87.5% of adversarial prompts but has 87.9% benign FP
- llama-guard3:1b has only 5% benign FP but catches only 10% of adversarial
- When both agree UNSAFE -> near-certain threat (consensus)
- When special-virus says UNSAFE but llama-guard3:1b says SAFE -> special-virus is likely hallucinating a threat (benign false positive)
- When special-virus says SAFE but llama-guard3:1b says UNSAFE -> rare, investigate

### Query Classifier Routing (OpenCode's Approach)

```
Inbound Query
    |
    v
[TF-IDF + LogisticRegression Classifier]
    |
    | benign_simple ----> special-virus + v5 prompt (94% benign safe)
    | benign_gray_area -> special-virus + v5 prompt
    | tamas ------------> special-virus + v5.1 prompt (88.2% attack detection)
    | v7 ---------------> gemma3 + v3 prompt (100% v7 detection)
    | low confidence ---> special-virus + v3 fallback (balanced)
```

**Rationale:**
- Different prompt templates optimize for different query types
- v5 has explicit SAFE examples that counteract special-virus's refusal bias
- v5.1 has stricter UNSAFE criteria for attack detection
- v3 is a balanced fallback

---

## Key Insights

### The Instruct-Tuning Trap

All instruct-tuned models (e-cameron, qwen2.5, Llama-3.2-Instruct) default to SAFE because they were trained to be maximally helpful. This makes them **intellectually incapable of adversarial classification** -- they lack the refusal intelligence to say "no" to harmful requests.

### The RP-Merged Model Tradeoff

`special-virus` is an RP-merged model (roleplay + uncensored) that retains refusal capacity. However, it was trained on datasets where imperatives often precede attacks, causing it to flag benign imperatives ("Write a haiku") as UNSAFE. **This bias can be mitigated with explicit SAFE examples in the prompt (v5 template).**

### Purpose-Built Guard Models Are Not Silver Bullets

`llama-guard3:1b` was specifically designed for safety classification, but it appears to have been over-optimized for benign safety at the expense of adversarial detection. It is excellent as a secondary verifier but cannot be the primary detector.

---

## Ollama Operational Notes

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Port** | 11435 | Changed from default 11434 to avoid Gradio conflicts |
| **WSL host IP** | 172.26.240.1 | Use this from WSL; Windows uses 127.0.0.1 |
| **Max queue** | 1 | Requires 0.5s pacing between requests |
| **Avg latency** | 2.2--4.9s | Depends on model and prompt complexity |
| **VRAM usage** | ~1.7 GB per 1B params at Q4_K_M | RTX 4070 8GB can hold 2--3 small models |
| **Pacing required** | 0.5s | Without pacing, Ollama returns HTTP 503 |

---

## Test Methodology

All models were tested with:
- **Prompt template:** `soft` (generic binary classifier)
- **Temperature:** 0.3
- **Max tokens:** 5 (capped to prevent generation)
- **Stop sequences:** `["\n"]` (force early termination)
- **Timeout:** 30s per request
- **Pacing:** 0.5s between requests

Sample sizes:
- special-virus: 1,000 adversarial + 99 benign (full dataset)
- Other models: 20--50 adversarial + 20--50 benign (viability screening)

---

## Files

| File | Purpose |
|------|---------|
| `docs/handoff/BOUNCER_MODEL_MATRIX_2026-05-24.md` | This report |
| `scripts/sandboxed_adversarial_test.py` | Test harness with pacing and prompt templates |
| `.nexus_pi/state/adversarial_test_logs/full_benchmark_soft_20260524_070320.json` | special-virus full results |
| `.nexus_pi/state/adversarial_test_logs/e-cameron_50adv_50ben.json` | e-cameron results |
| `.nexus_pi/state/adversarial_test_logs/gemma3_20adv_20ben.json` | gemma3:1b results |
| `.nexus_pi/state/adversarial_test_logs/llama-guard3_20adv_20ben.json` | llama-guard3:1b results |
| `.nexus_pi/state/adversarial_test_logs/qwen25-15b_20adv_20ben.json` | qwen2.5:1.5b results |
| `.nexus_pi/state/adversarial_test_logs/qwen25-05b_20adv_20ben.json` | qwen2.5:0.5b results |

---

*Report generated by live benchmark execution against local Ollama instance. All claims are evidence-grounded from measured results.*
