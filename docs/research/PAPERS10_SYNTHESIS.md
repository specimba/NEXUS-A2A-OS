# PAPERS10 Deep Synthesis — 2026-06-23

**Version:** 1.0.0
**Status:** Deep-dive completion after strategic assessment (PAPERS10_STRATEGIC_ASSESSMENT_2026-06-23.md)
**Scope:** Web-researched deep analysis of priority topics with NEXUS architecture mapping

---

## 1. Sakana AI Fugu Architecture (HIGH)

### Key Findings

**Fugu** (released June 22, 2026) is Sakana AI's commercial multi-agent orchestration product. It is not a single model — it is an LLM trained to call other LLMs. Behind a single OpenAI-compatible API endpoint, Fugu dynamically orchestrates a pool of frontier models (GPT-5.5, Claude Opus 4.8, Gemini 3.1 Pro) plus itself recursively.

**Architecture pillars:**
1. **TRINITY** (`arxiv:2512.04695`, ICLR 2026) — Lightweight coordinator (~0.6B SLM + ~10K parameter routing head) optimized via evolutionary strategy (sep-CMA-ES). Assigns Thinker/Worker/Verifier roles across multi-turn LLM calls. Total learnable parameters < 20K.
2. **Conductor** (`arxiv:2512.04388`, ICLR 2026) — 7B model trained with RL to discover natural-language coordination strategies. Learns communication topologies and prompt engineering for worker agents. Supports recursive topologies (Conductor calls itself as worker → dynamic test-time scaling).
3. **Fugu product** wraps both into two tiers: Fugu (latency-balanced) and Fugu Ultra (max quality with deeper orchestration).

**Benchmarks:** Fugu Ultra scores 73.7 SWE-Bench Pro, 82.1 TerminalBench, 93.2 LiveCodeBench — surpassing GPT-5.5 and Opus 4.8.

**Key insight for NEXUS:** The evolutionary coordinator (< 20K params) is lighter than any agent in the NEXUS stack. The Conductor's RL-discovered coordination strategies eliminate hand-coded LangChain-style pipelines.

### Relevance to NEXUS

| Component | Relevance | How |
|-----------|-----------|-----|
| GMR/CogER | HIGH | TRINITY's role assignment (Thinker/Worker/Verifier) is a direct template for CogER routing decisions |
| NEXUSCLAW | HIGH | Conductor's RL coordination can replace hand-coded agent pipeline logic in CLAW |
| Governor | MEDIUM | Fugu's model pool compliance filtering maps to Governor's provider governance |
| TWAVE | LOW | Fugu is API-based orchestration, not local execution |

### Evidence
- https://sakana.ai/fugu/ — product page
- https://arxiv.org/abs/2512.04695 — TRINITY paper
- https://arxiv.org/abs/2512.04388 — Conductor paper
- https://github.com/SakanaAI/fugu — open-source shell installer
- https://news.ycombinator.com/item?id=47923668 — HN discussion with architectural detail

---

## 2. VibeThinker-3B / 1.5B (HIGH)

### Key Findings

**VibeThinker-3B** (Weibo AI, June 16 2026) is a 3.1B parameter dense reasoning model achieving 94.3 on AIME26 and 80.2 Pass@1 on LiveCodeBench v6. It matches DeepSeek V3.2 (671B) on math — a 223x parameter efficiency ratio.

**Architecture:**
- Base model: Qwen2.5-Coder-3B (MIT license)
- **Spectrum-to-Signal Principle (SSP)** — 4-stage post-training pipeline:
  1. Two-stage SFT with curriculum learning (broader mix → long/difficult only)
  2. Multi-domain reinforcement learning (Math, Code, STEM) using MGPO (MaxEnt-Guided Policy Optimization)
  3. Offline self-distillation (using self-generated trajectories with score-based prioritization)
  4. Instruct RL (rule-based + rubric-based rewards for instruction following)
- **Claim-Level Reliability (CLR)** — test-time scaling: evaluates claim-by-claim reliability to boost AIME26 from 94.3 → 97.1
- **Parametric Compression-Coverage Hypothesis** — verifiable reasoning is highly compressible into small models; knowledge tasks still need scale

**VibeThinker-1.5B** — precursor with same SSP pipeline. Training cost: $7,800. Beats DeepSeek R1 on AIME24 (80.3 vs 79.8) and AIME25 (74.4 vs 70.0).

### Relevance to NEXUS

| Component | Relevance | How |
|-----------|-----------|-----|
| TWAVE | HIGH | Primary candidate for local SLM — 3B fits 6.7GB VRAM, MIT license, runs on consumer GPU |
| Tandem Routing | HIGH | SLM role in LLM-SLM pair: VibeThinker handles reasoning while larger models handle knowledge |
| GMR | HIGH | SSP training pipeline is template for fine-tuning strategy |
| NEXUSCLAW | MEDIUM | CLR test-time scaling integrates with CLAW's verification loop |
| Vault | MEDIUM | Parametric Compression-Coverage Hypothesis informs memory architecture design |

### Evidence
- https://arxiv.org/abs/2606.16140 — VibeThinker-3B paper
- https://arxiv.org/abs/2511.06221 — VibeThinker-1.5B paper (original SSP)
- https://github.com/WeiboAI/VibeThinker — MIT-licensed code and weights
- https://huggingface.co/WeiboAI/VibeThinker-3B — 3B weights
- https://sebastianraschka.com/blog/2026/vibethinker-3b-post-training.html — Sebastian Raschka post-training analysis

---

## 3. Sakana Tandem / LLM-SLM Collaboration (HIGH)

### Key Findings

Two distinct "Tandem" concepts exist:

**Tandem (ACL 2025 Findings)** — `arxiv:xxxx.xxxxx`, GitHub: `Applied-Machine-Learning-Lab/ACL2026_Tandem`
- LLM (32B) generates compact critical reasoning insights
- SLM (7B) executes full reasoning using those insights as guide
- Cost-aware termination: LLM stops early once sufficient guidance accumulated
- **Results:** 40.7% cost reduction vs standalone LLM, +2.56% accuracy improvement
- Sufficiency classifier transfers across domains without retraining (MATH → HumanEval)

**KAME (Sakana AI, ICASSP 2026)** — `arxiv:2510.02327`
- Real-time speech-to-speech: fast S2S model handles immediate response loop
- Backend LLM runs asynchronously, injects "oracle" signals in real-time
- "Speak while thinking" paradigm — not just "think, then speak"
- Backend LLM is fully swappable (GPT-4.1, Claude Opus, Gemini 2.5 Flash)

### Relevance to NEXUS

| Component | Relevance | How |
|-----------|-----------|-----|
| Tandem Routing (papers09) | HIGH | ACL Tandem paper is the EXACT technique papers09 hypothesized as "Tandem Riding" |
| TWAVE | HIGH | KAME's async oracle injection pattern for low-latency NEXUSCLAW responses |
| GMR | HIGH | Cost-aware termination strategy for budget-limited model selection |
| NEXUSCLAW | MEDIUM | SLM+LLM collaboration pattern for agentic tool use with cost control |
| Bridge | LOW | LLM-swappable pattern for Bridge's provider abstraction |

### Evidence
- https://github.com/Applied-Machine-Learning-Lab/ACL2026_Tandem — Tandem code + paper
- https://sakana.ai/kame-icassp-2026/ — KAME: Tandem Architecture (ICASSP 2026)
- https://arxiv.org/abs/2510.02327 — KAME paper
- https://arxiv.org/abs/2507.16731 — Survey on Edge SLM / Cloud LLM collaboration

---

## 4. EAGLE-3 / Speculative Decoding Advances (HIGH)

### Key Findings

**EAGLE-3** (`arxiv:2503.01840`) — state-of-the-art speculative decoding technique:
- Lightweight autoregressive draft head attached to target model's internal layers
- **No separate draft model** — reuses target model's features (embeddings + LM head)
- Training-time test: simulates inference conditions during training, preventing distribution mismatch
- Fuses features from multiple layers (low, middle, high) instead of only top layer
- Tree attention for efficient parallel verification
- **Results:** 3-6.5x speedup (up to 7.5 tokens accepted), 70-90% acceptance rates
- EAGLE-3.1 ships as vLLM plugin — 3 lines of config to enable

**Medusa-2:** Non-autoregressive multiple heads (2.2-2.8 accept length) — simpler, less overhead

**Production state (2026):** vLLM, SGLang, TensorRT-LLM all default-recommend speculative decoding. EAGLE-3 is market leader.

### Relevance to NEXUS

| Component | Relevance | How |
|-----------|-----------|-----|
| TWAVE | CRITICAL | Primary latency optimization for local SLM inference — 2-4x speedup on consumer GPU |
| NEXUSCLAW | HIGH | Faster response enables more complex agent loops within same latency budget |
| GMR | LOW | Speculative decoding is inference-layer, not routing-layer |
| Governor | LOW | No direct impact |

### Evidence
- https://arxiv.org/abs/2503.01840 — EAGLE-3 paper
- https://developer.nvidia.com/blog/an-introduction-to-speculative-decoding-for-reducing-latency-in-ai-inference — NVIDIA technical blog
- https://kga-it.com/en/blog/ml-inference-speculative-decoding-production-guide — Production benchmarks 2026

---

## 5. TRINITY: An Evolved LLM Coordinator (HIGH)

Already covered under Fugu (Section 1). Standalone key details:

- **20K learnable parameters total** (0.6B frozen SLM + 10K trained head)
- **sep-CMA-ES** training: evolutionary strategy beats RL, SFT, random search for this problem
- **86.2% LiveCodeBench** pass@1 (state-of-the-art at publication)
- Generalizes to out-of-distribution tasks
- **Limitation:** cannot act on tools/APIs — abstract reasoning only (future work includes code interpreters)
- **Multi-turn loop:** coordinator reads full transcript each turn → assigns role + LLM → repeat until Verifier accepts

---

## 6. Conductor: RL-Trained Orchestration (HIGH)

Already covered under Fugu (Section 1). Standalone key details:

- **7B Conductor** trained end-to-end with RL
- Learns: (a) communication topologies, (b) targeted prompt engineering for each worker
- **Recursive test-time scaling:** Conductor selects itself as worker → re-evaluates output → assembles corrective workflow
- **Randomized agent pools during training** → generalizes to unseen agents at inference
- **83.9% LiveCodeBench, 87.5% GPQA-Diamond** (state-of-the-art)

---

## 7. TAID: Knowledge Distillation (HIGH)

### Key Findings

**TAID** (`arxiv:2501.16937`, ICLR 2025 Spotlight) — Sakana AI's novel distillation method:
- Dynamically interpolates between student and teacher distributions over time
- Adaptive intermediate distribution gradually shifts from student→teacher
- **Solves three problems:** capacity gap (teacher too smart), mode averaging, mode collapse
- Theoretical guarantee: TAID prevents mode collapse (proven with regression model proxy)
- **Results:** TinySwallow-1.5B (Japanese SLM from 32B teacher) — state-of-the-art among 1.5B Japanese models
- TAID-VLM-2B: vision-language model distilled from larger VLM

### Relevance to NEXUS

| Component | Relevance | How |
|-----------|-----------|-----|
| TWAVE | HIGH | Directly applicable: distill from NEXUS's best models → edge-deployable SLMs |
| Vault | MEDIUM | Mode averaging/collapse analysis applies to memory consolidation |
| Governor | LOW | No direct application |

---

## 8. Agentic Frameworks & Tool Use (MEDIUM)

### Key Findings

- **MCP (Model Context Protocol)** and **A2A (Agent-to-Agent)** are the dominant 2026 standards for tool use + agent communication
- **ARTIST** framework: couples agentic reasoning + RL + tool integration in unified loop
- **Parallel tool calling** and **dynamic tool discovery** becoming standard in all major frameworks
- LangGraph v1.1.3, CrewAI v1.12, AG2 — all now support MCP, OpenRouter, DeepSeek, Ollama providers

### Relevance to NEXUS

NEXUS already has Bridge (MCP/A2A interface) and Governor (access control). These are confirmations that NEXUS's architecture direction is correct. No immediate code changes needed.

---

## 9. CLIP / Multimodal Advances (LOW)

### Key Findings

- CLIP remains foundational for vision-language alignment (dual encoders, contrastive learning)
- FastCLIP optimization techniques for efficient CLIP training
- CLIP-VAD: voice activity detection using CLIP models
- No breakthrough advances in 2025-2026 that change the landscape for NEXUS

### Relevance to NEXUS

NEXUS does not currently process images or video. Monitor but not actionable.

---

## 10. curriculum learning / "How to Train Your Dragon" (MEDIUM)

### Key Findings

- No paper with this title in ML/LLM context found (search results were children's book/film)
- **Adaptive Difficulty Curriculum Learning (ADCL)** (`arxiv:2505.08364`) — addresses "Difficulty Shift" where model's perception of problem difficulty changes during training. Periodically re-estimates difficulty per data batch.
- **Curriculum learning for LLM pretraining** (survey 2020-2025) shows 3.5% performance gain with difficulty-based data ordering
- VibeThinker's SSP pipeline already uses curriculum-based SFT (Stage 1→2 progression)

### Relevance to NEXUS

The ADCL technique (+10% AIME24, +16.6% AIME25 over Zero-RL baseline) is directly applicable to any RL training in NEXUS — specifically for fine-tuning guard models or NEXUSCLAW agents.

---

## Priority Summary Table

| Topic | NEXUS Priority | Key Action | Effort |
|-------|---------------|------------|--------|
| TRINITY (evolved coordinator) | P0 | Implement CogER routing over model pool | 2-3 days |
| Conductor (RL orchestration) | P0 | Replace hand-coded agent pipelines | 3-5 days |
| VibeThinker-3B | P0 | Integrate as TWAVE primary SLM | 1-2 days |
| EAGLE-3 Speculative Decoding | P0 | Enable in vLLM/TWAVE serving stack | 0.5-1 day |
| Tandem (ACL 2025) | P0 | Wire SLM-LLM collaboration pattern | 2-3 days |
| TAID Distillation | P1 | Distill NEXUS models → edge SLMs | 3-7 days |
| KAME async oracle | P1 | Async injection for NEXUSCLAW loops | 2-4 days |
| ADCL curriculum learning | P2 | Apply to guard model fine-tuning | 1-2 days |
| Agentic frameworks (MCP/A2A) | P2 | Verify Bridge alignment, minor updates | 0.5 day |
| CLIP/Multimodal | P3 | Monitor only | 0 days |

---

## Cross-Cutting Patterns Identified

1. **Evolutionary optimization > gradient methods** for coordination problems (TRINITY's sep-CMA-ES beats RL/SFT)
2. **SLM+LLM collaboration converges** across three independent teams (Tandem, KAME, VibeThinker) — strong signal
3. **Speculative decoding is table stakes** — any local model serving stack must support EAGLE-3 in 2026
4. **Small reasoning models decouple from scaling laws** — VibeThinker proves verifiable reasoning compresses to 3B
5. **Orchestration is the new frontier** — Sakana's entire thesis: managing model pools beats building bigger models

---

**Document Status:** COMPLETE
**Last Updated:** 2026-06-23
**Cross-ref:** PAPERS10_INTEGRATION_PROPOSALS.md for actionable implementation plans
