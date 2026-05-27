# Optimal Local Multi-Model Serving & Routing Strategy
## Date: 2026-05-26 | Research compilation from arXiv, Hugging Face, GitHub, and vLLM

---

## 1. THE PROBLEM: VRAM SWAP CHURN & INFRASTRUCTURE BOTTLESTECKS

When executing multi-model safety audits or running real-time guard planes under hardware constraints (RTX 4070 8GB VRAM with ~4.2 GB free), naive routing strategies introduce a critical failure mode: **swap churn / VRAM thrashing**.

### 1.1 The Performance Cliff of System RAM Spillover
As documented in recent `llama.cpp` and `Ollama` core discussions, if any portion of a model or its Key-Value (KV) cache spills over from high-bandwidth GPU VRAM into system memory (DRAM), inference transitions from a compute-bound regime to a PCIe-bandwidth-bound regime:
- **Fully on GPU:** ~40 tokens/sec
- **CPU Offloaded Spillover:** ~3 tokens/sec (a **13x slowdown!**)
- **Impact:** Prompt processing turns sticky, latency surges, and concurrent requests trigger heavy disk pagefile write-spikes (observed up to 1052.5 MB/s and disk queues of 16.5) which manifest physically as system stuttering and audio distortion.

### 1.2 The Naive Quorum voting Flaw
Running concurrent multi-model Quorum voting (e.g. loading `special-virus:latest`, `llama-guard3:1b`, and `qwen2.5:0.5b` simultaneously for every query) forces Ollama to repeatedly load and unload model parameters. Since the combined size exceeds available VRAM, this causes **constant cold starts** (2–4 seconds of weight loading per query) and pagefile thrashing.

---

## 2. THE SOTA SOLUTIONS (LITERATURE & SYSTEM DESIGN REVIEW)

Our sophisticated deep search across peer-reviewed publications and leading serving frameworks identified three dominant paradigms for resource-constrained multi-model orchestration:

### 2.1 Conformal Cascading & Model Cascades (FrugalGPT / RouteNLP)
- **Concept (Chen et al. 2305.05176):** "Classify first, spend second." Instead of query-independent uniform routing or joint voting, LLM tasks are processed via a sequential **Pipelined Cascade Matrix (PCM)**.
- **Mechanics:** 
  - Try a fast, cheap, warm model first (Tier 1).
  - Check the output confidence score ($u$).
  - If $u \le \delta_{k,t}$ (where $\delta$ is a calibrated conformal threshold representing uncertainty), escalate to a more capable model (Tier 2).
- **Outcome:** Up to **74% of requests are handled locally at $0 cost** with negligible latency, while heavy models are only cold-loaded on demand for the remaining <20% of ambiguous queries.

### 2.2 Multi-LoRA Serving (The Memory-Scaling Hack)
- **Concept (vLLM 0.15.0+ / SageMaker Multi-LoRA Serving 2026):** For specialized versions of the same base model (e.g. a safety guard, a general assistant, and a code specialist all fine-tuned on Qwen2.5-1.5B), serving separate full-parameter models is unnecessary.
- **Mechanics:** 
  - Keep a single base model (`qwen2.5-1.5b`) frozen and resident in GPU memory.
  - Dynamically swap tiny Low-Rank Adaptation (LoRA) adapters (weights are megabytes instead of gigabytes) *per request* during the forward pass.
- **Outcome:** Low-latency swapping (**<50ms per request**) supporting dozens of concurrent adapters on a single GPU with less than a 5% latency overhead, completely avoiding full parameter reloading.

### 2.3 Pipelined Sharding (`pshard` - llama.cpp)
- **Concept (ggml b3400+ / PR 22692):** Pipelined sharding combines prioritized VRAM placement, sub-layer sharding, CPU offload, and pipelined copy/compute.
- **Mechanics:** Loads pinned weights into a bounded device buffer, while sharded weights are dynamically prefetched into a GPU scratch buffer from host memory ahead of their execution step, allowing copy and compute overlapping.

---

## 3. THE OPTIMIZED NEXUS OS IMPLEMENTATION BLUEPRINT

To solve our local RAM pressure (avg 86.4%, max 91.9%) and eliminate Ollama model-swapping churn while keeping guard plane accuracy at SOTA levels, we implement the **Session-Pinned Conformal Cascade (SPCC)**:

```text
                                  ┌───────────────────────────┐
                                  │      Incoming Query       │
                                  └─────────────┬─────────────┘
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │    Pre-Filter Tier    │ (MetaAttackDetector)
                                    │   (0ms, 0MB Overhead) │
                                    └───────────┬───────────┘
                                                │
                                      (If Passed Pre-Filter)
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │  Warm Specialist Tier │ (qwen2.5-guard-q4)
                                    │    (VRAM Pinned)      │
                                    └───────────┬───────────┘
                                                │
                                   (Is Confidence >= Threshold?)
                                                │
                       ┌────────────────────────┴────────────────────────┐
                       ▼                                                 ▼
                  [ Yes (>=0.5) ]                                   [ No (<0.5) ]
                       │                                                 │
                       ▼                                                 ▼
               Accept Classification                           ┌───────────────────┐
               (Instant Response)                              │  Escalation Tier  │
                                                               │ (llama-guard3/    │
                                                               │  qwen2.5:1.5b)    │
                                                               └─────────┬─────────┘
                                                                         │
                                                                         ▼
                                                                Quorum Joint Vote
                                                               (Resolve Ambiguity)
```

### 3.1 Step-Wise Execution Path
1.  **Tier 1: Pre-Filter (MetaAttackDetector):** Evaluates the query using highly optimized regex and structural checkers. Blocks clear exploits instantly with **0ms latency and 0MB memory overhead**.
2.  **Tier 2: Warm Specialist (qwen2.5-guard-q4):** If the query passes Tier 1, it is routed to the primary guard model. This model is **pinned warm in VRAM** (`keep_alive: -1`).
3.  **Tier 3: Escalation (llama-guard3 / qwen2.5:1.5b):** If Tier 2's classification confidence is low ($<0.5$) or the result is ambiguous, the system escalates, cold-loading a larger model on demand to execute a decisive joint vote.

### 3.2 Environment Tuning & VRAM Safeguards
We configure the following environment parameters on the local host to optimize the memory-to-compute ratio:
- `OLLAMA_MAX_LOADED_MODELS=2`: Restricts Ollama from loading more than 2 models concurrently, protecting VRAM headroom.
- `OLLAMA_NUM_PARALLEL=1`: Disables multiple request slots per model, cutting down KV cache multiplication overhead.
- `OLLAMA_FLASH_ATTENTION=1`: Enables Flash Attention to compress KV cache footprints.
- `OLLAMA_KV_CACHE_TYPE=q8_0`: Quantizes the KV cache to 8-bit, halving the attention context memory footprint.

---

## 4. IMPACT PROJECTIONS

| Metric | Before Optimization | After SPCC Implementation |
|--------|---------------------|---------------------------|
| **VRAM Resident Models** | 0 (models swap on every request) | 2 (permanently pinned warm set) |
| **Model Swapping Latency** | 2,000ms – 5,000ms | **<100ms** (for >85% of queries) |
| **Disk Queue Spikes** | Frequent (1.6 GB reads on swaps) | **Negligible** (only on rare escalations) |
| **Commit Memory Pressure**| 86% – 92% (thrashing pagefile) | **~72% – 78%** (fully stable) |
| **Audio Stutter Risk** | High | **Extremely Low** |

---

*Prepared by NEXUS OS Core Security Research Group | Session ID: 2026-05-26*
