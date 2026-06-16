---
id: NODE-MIG-COMPRESSION_MERGE_FT_APPROACHES
authority_scope: experimental
origin_sha256: 9ac87be4d1bccff0ad79b39654be7dc46ed5e4c85f4f7c4b15d61a806f51433f
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-5B48C7
---
# Compression, Model Merging & Fine-Tuning Approaches

Synthesis of 742-link paper dump + ~208 PDFs across PAPERS/papers01-03 + 423 papers across 9 alphaxiv folders (MODELrelatedPAPERlibraryBASE.txt) = ~1,360+ references, cross-referenced to guard pipeline and benchmark suite (stres7-12, calibrate_twave_v2).

## Hardware Baseline

| Spec | Value |
|------|-------|
| GPU | NVIDIA RTX 4070 Laptop |
| VRAM | 8188 MiB total, ~6600 MiB usable |
| RAM | 64 GB |
| Ollama KEEP_ALIVE | 15m, MAX_LOADED_MODELS = 2 |
| Guard models | special-virus (1.2B) + qwen2.5-guard-q4 (1.5B) + llama-guard3:1b (~3.4 GB total) |

## 1. Compression

### 1.1 Pruning via Merging — MKA (Manifold Knowledge Alignment)

**Paper**: Pruning via Merging: Compressing LLMs via Manifold Alignment Based Layer Merging (EMNLP 2024, papers01)

**Core method**: Two-stage layer fusion within a single model. (1) Extract hidden states on calibration data → Diffusion Kernel manifold for dimensionality reduction → NPIB similarity matrix. (2) Iteratively merge the most similar adjacent layer pair from back to front with adaptive ratio.

```

S_ij = NPIB(L_i, L_j)        # similarity via normalized pairwise info bottleneck
lambda_m = e^{S_ij} / (e^{S_ij} + e^{S_ji})
theta_m = lambda_m * theta_i + (1 - lambda_m) * theta_j
```

**Results**: Llama3-8B 43.75% compression, 2.82% MMLU drop. Outperforms SparseGPT and ShortGPT at all ratios. Composable with SmoothQuant/GPTQ/AWQ.

**VRAM**: Needs full model load + one forward pass. With 4-bit GGUF, 7B model ~4-5 GB.

**RTX 4070**: YES with 4-bit. The Diffusion Kernel and NPIB are compute-bound, not memory-bound.

**Integration path**: Calibrate on stres7-12 datasets. Use as pre-processing before guard pipeline to shrink the model.

### 1.2 PolarQuant

**References**: megaLink lines 353-361. GGUF-level quantization (Q5, EOQ) developed by caiovicentino1. Applied to Qwen3.5-9B, Nemotron-30B, diffusion models.

**Method**: Symmetric per-channel quantization with learned scale factors calibrated on a small held-out set. EOQ variant applies evolutionary optimization to find optimal scale/zero-point per channel.

**RTX 4070**: YES. GGUF format is already used by our Ollama setup. PolarQuant is a drop-in GGUF replacement.

### 1.3 CompactifAI — Tensor Network Compression

**Reference**: Line 452. Uses quantum-inspired tensor networks (matrix product states, tensor trains) to decompose weight matrices.

**Method**: Replace each weight matrix W ∈ R^{m×n} with a tensor train: W(i,j) = sum_{k1,...,kd} A1(i,k1) A2(k1,k2) ... Ad(kd,j). Compression ratio = mn / sum(ranks * sizes).

**VRAM**: Needs the base model plus the tensor train factors (~10-30% of original). Training the TT decomposition requires gradient descent.

**RTX 4070**: MARGINAL. Tensor network fine-tuning is compute-intensive. Only for small models (<3B).

### 1.4 Fast Byte Latent Transformer

**Paper**: papers01. BlockBERT-style sparse attention (local windows + global tokens) + 8-bit quantization + distillation from 12L teacher to 6L student.

**VRAM**: ~3.5 GB (student int8). Fits RTX 4070.

**Integration**: The 6L student could run as a fast pre-filter before the guard pipeline, doing cheap classification to decide whether to route to guard models.

### 1.5 EvolKV — Evolutionary KV Cache Compression

**Paper**: alphaxiv #3 KVV — arxiv 2509.08315

**Method**: Treats KV cache eviction as an evolutionary optimization problem. Each "individual" is a set of KV positions to keep. Fitness is downstream task perplexity. After evolution, learns a fixed eviction mask per attention head.

**Result**: 4x compression with 0.3% perplexity loss. Evolved masks transfer across inputs from the same distribution.

**RTX 4070**: YES. Post-training step (CPU-bound evolution, ~1 hour). Once mask is learned, inference is standard with reduced KV cache.

### 1.6 Cortex — Semantic-Aware Knowledge Caching

**Paper**: alphaxiv #3 KVV — arxiv 2509.17360

**Method**: Groups KV cache entries into semantic clusters (via embedding similarity), then caches at cluster level. Novel inputs find nearest centroid rather than full recomputation. Uses hierarchical clustering with online update.

**Result**: 3-5x generation speedup on long-context tasks with <1% accuracy loss.

**RTX 4070**: YES. The embedding model for clustering is ~100 MB. Can be applied to any transformer model.

### 1.7 Cross-Layer KV Cache Sharing

**Paper**: alphaxiv #3 KVV — arxiv 2405.12981

**Method**: Adjacent layers share key-value projections. Reduces KV cache memory proportionally (2x sharing = 50% reduction). Finetune with LoRA to recover quality.

**Result**: 1.8x compression with 1.2% perplexity loss after LoRA recovery.

**RTX 4070**: YES. LoRA fine-tuning for recovery fits in ~4 GB.

## 2. Model Merging

### 2.1 TIES-MERGING

**Paper**: Resolving Interference When Merging Models (NeurIPS 2023)

**Algorithm**:
1. **TRIM**: Keep only top-k% of task vector params by magnitude (k=20 default)
2. **ELECT SIGN**: Per-parameter, choose sign with greater total magnitude across all task vectors
3. **DISJOINT MERGE**: Average only the models whose sign matches the elected sign

```
tau_t = theta_ft^t - theta_init          # task vector
tau_t = top_k(tau_t, k=20%)             # trim
gamma_m = sgn(sum(sgn(tau_t)))           # elect sign
theta_m = theta_init + 1/|A| * sum_A tau_t  # disjoint merge
```

**Implementation**: `pip install mergekit` handles this. CLI: `mergekit-yaml config.yaml ./output`.

**VRAM**: Merge operation is CPU-bound (just weight arithmetic). Loading source models needs VRAM but can load one at a time.

**RTX 4070**: YES. Can merge 7B models by loading them sequentially.

### 2.2 Task Arithmetic

**Paper**: Editing Models with Task Arithmetic (ICLR 2023)

**Algorithm**: Three operations on task vectors:
- **ADD**: `theta_new = theta_pre + lambda * sum(tau_t)` — multi-task capability
- **NEGATE**: `theta_new = theta_pre - lambda * tau_t` — removes behavior
- **ANALOGY**: `tau_D = tau_C + tau_B - tau_A` — zero-shot task transfer

**Key insight**: Task vectors are nearly orthogonal, enabling additive combination with minimal interference. Optimal lambda ∈ [0.3, 0.8].

**Implementation**: `mergekit` with `--method linear`.

**RTX 4070**: YES. Trivial to execute.

### 2.3 L-LoRA (Linearized LoRA for Merging)

**Paper**: Parameter Efficient Multi-Task Model Fusion with Partial Linearization (ICLR 2024)

**Problem**: Standard LoRA task vectors have high cosine similarity (poor orthogonality) → destructive interference when merged.

**Method**: Apply first-order Taylor expansion ONLY to LoRA modules (not the full model):

```
f_theta0_lin(x; phi) = f_theta0(x; 0) + nabla_phi f_theta0(x; 0)^T * phi
```

Fine-tune in tangent space → task vectors are more orthogonal → better merging.

**VRAM**: Same as LoRA. On RTX 4070, QLoRA for 7B fits.

**RTX 4070**: YES. Practical with `peft` library + mergekit.

### 2.4 DARE (Drop And REscale)

**Reference**: Referenced in MergeAlign paper. Also built into mergekit.

**Method**: Randomly drop a fraction p of task vector parameters (set to 0), rescale the rest by 1/(1-p). Pre-processing step before TIES or Task Arithmetic.

**VRAM**: Negligible.

**RTX 4070**: YES. Built into mergekit.

### 2.5 SLERP (Spherical Linear Interpolation)

**Reference**: megaLink line 31, `github.com/Digitous/LLM-SLERP-Merge`.

**Method**: Interpolate between two models on the hypersphere: `theta = sin((1-t)*omega)/sin(omega) * theta_1 + sin(t*omega)/sin(omega) * theta_2`, where cos(omega) = dot(theta_1, theta_2) / (||theta_1|| * ||theta_2||).

**VRAM**: Negligible.

**RTX 4070**: YES.

### 2.6 MergeAlign — Safety-Aware Merging

**Paper**: Model Merging and Safety Alignment: One Bad Model Spoils the Bunch (EMNLP 2024 Findings)

**Method**: Treat safety as a separate task alongside domain tasks. (1) Generate synthetic safety data (harmful prompts + refusals) filtered by LLaMA-Guard-2. (2) Generate domain expert data. (3) Optimize merging weights that minimize loss on BOTH safety and domain data: `L_merge = L_safety + alpha * L_expert`.

**Key finding**: Naive merging (TIES, DARE, Task Arithmetic) drops alignment from ~93% to 53% when one bad model is in the pool.

**Implementation**: MergeAlign uses EvoMM (evolutionary merge) or LM-Cocktail for weight optimization. Compatible with mergekit.

**RTX 4070**: YES for <7B models. Needs LLaMA-Guard-2 running during evaluation (adds ~2 GB).

### 2.7 MaTS (Merging by Matching in Task Subspaces)

**Paper**: TMLR 2024

**Method**: Unified view of merging as solving `(sum C_m) * theta = sum(C_m * theta_m)` where C_m is a task-specific covariance. Uses conjugate gradient instead of direct inversion to avoid numerical instability. Supports block-diagonal Fisher (K-FAC) for better conditioning.

**VRAM**: HIGH — stores gradient statistics for each layer.

**RTX 4070**: NO for 7B+. Only for <300M param models.

### 2.8 Darwin Family — MRI-Trust-Weighted Evolutionary Merging

**Paper**: alphaxiv #3 KVV, #5 SLM — arxiv 2605.14386. Darwin-35B-A3B-Opus-GGUF.

**Method**: Training-free scaling via evolutionary model merging with "MRI-trust-weighted" crossover. Treats model parameters as chromosomes in a genetic algorithm:
1. **Population**: Seed with base models initialized from different checkpoints (e.g., Qwen2.5-7B variants).
2. **Fitness**: Evaluate on held-out calibration set (safety + domain tasks for guard models).
3. **Crossover**: MRI-trust-weighted: `theta_child = W_mri * theta_parent1 + (1 - W_mri) * theta_parent2` where W_mri is a per-layer trust weight derived from mutual information between layer activations and task performance.
4. **Mutation**: Sparse Gaussian noise (sigma=0.01, p=0.001) with conditional computation islands.
5. **Selection**: Tournament selection with elitism (keep top 2).

Generates multiple merged candidates per generation. The Darwin-35B-A3B model uses conditional computation (only 3B active parameters) — critical for 8 GB VRAM.

**Key insight**: MRI-trust-weights naturally handle conflicting parameters (like safety vs. helpfulness). The mutual information metric identifies which layer in which parent is most "trustworthy" for each parameter region. This is more principled than TIES sign-election because it's continuous, not binary.

**RTX 4070**: YES. The active-parameter model (3B) fits comfortably. Evolutionary process is CPU-bound for weight arithmetic; only forward passes for fitness eval need GPU.

**Integration**: Ideal for merging guard models (special-virus + qwen2.5-guard + llama-guard3) into a single model. The MRI-trust mechanism naturally resolves their safety classification conflicts.

### 2.9 Mix Data or Merge Models?

**Paper**: alphaxiv #5 SLM — arxiv 2410.10801

**Key Question**: Given limited compute, should you train on more diverse data or train separate models and merge?

**Findings**:
- **Merge wins** when task-specific data is abundant per-task but scarce overall (the guard model scenario — each model has specialized safety knowledge from different training distributions).
- **Mix wins** when you have large uniform datasets (pretraining).
- **Cross-entropy gap**: Merging recovers ~70-80% of the multi-task gap. Mixing recovers ~90%. But merging is ~10x cheaper.
- **Scaling**: Merge advantage grows with model size. At 7B+, merging matches or exceeds mixing.

**Implication for guard models**: Merging the 3 guard models is likely superior to training a single model on combined safety data, given limited compute and specialized training distributions.

### 2.10 No Task Left Behind — Isotropic Model Merging

**Paper**: alphaxiv #2 — arxiv 2502.04959

**Method**: Preserve both common and task-specific subspaces during merging by:
1. SVD decomposition of task vectors into shared (top-k singular vectors) and task-specific components.
2. Shared components averaged across all tasks; task-specific components projected onto orthogonal complement of shared subspace.
3. Reconstruct: `theta_merged = theta_init + theta_shared + sum(theta_task_specific)`.

**Key result**: Outperforms TIES+DARE on multi-task benchmarks by 2-4% while maintaining better per-task performance.

**RTX 4070**: YES. SVD of task vectors (O(n^2) in param count) is feasible for 3B models (<10 minutes on CPU).

## 3. Fine-Tuning Approaches

### 3.1 LQF (Linear Quadratic Fine-Tuning)

**Paper**: papers03

**Method**: Replace linear classifier head with quadratic form: `f(x) = W * phi(x) + (phi(x) - mu)^T * Q * (phi(x) - mu)` where Q = V^T V (low-rank, r=64). Regularized with `lambda * ||Q - I||_F^2`.

**VRAM**: ~0.1 GB added to backbone. Total depends on backbone size.

**RTX 4070**: YES. Minimal overhead.

**Integration**: Train a safety classifier head on top of frozen guard model features. The quadratic form captures non-linear decision boundaries that linear probes miss.

### 3.2 LINES (Layer Scaling Interpolation)

**Paper**: Post-Training Layer Scaling Prevents Forgetting (papers03)

**Method**: After fine-tuning, learn one scalar alpha_l per layer to interpolate back toward pre-trained:

```
W_final = alpha_l * W_ft + (1 - alpha_l) * W_pre
```

Train alpha_l (L parameters total, ~12-48 for most models) for 1 epoch on a small calibration set (200-500 samples). Prevents catastrophic forgetting.

**VRAM**: Negligible (only L scalars).

**RTX 4070**: YES. Extremely practical.

**Integration**: After any fine-tuning step (including guard model FT), apply LINES to retain general safety knowledge.

### 3.3 PET/iPET (Pattern-Exploiting Training)

**Paper**: It's Not Just Size That Matters — Small Language Models Are Also Few-Shot Learners

**Method**: Convert every task into a cloze question via Pattern-Verbalizer Pairs (PVP). Ensemble of 3 MLMs across multiple patterns → annotate unlabeled data → distill into single classifier. iPET iterates: each generation labels more data for next.

**Key result**: ALBERT + PET/iPET outperforms GPT-3 on SuperGLUE with 0.1% of params, using 32 training examples.

**VRAM**: ~2-4 GB for ALBERT-xxlarge.

**RTX 4070**: YES.

**Integration**: Use PET/iPET to train guard classifiers with minimal labeled data (32 examples of harmful/safe pairs) instead of 3 separate guard models.

### 3.4 Edge AI Fine-Tuning (Layer Freezing + QAT)

**Paper**: Fine-Tuning Small Language Models for Domain-Specific AI: An Edge AI Perspective (papers01)

**Method**: Freeze bottom 70% of layers, fine-tune top 30% + task head. Simulate INT8 quantization during training (FakeQuant). Extend vocabulary with domain-specific tokens.

**VRAM**: ~1.5 GB for 4-layer student, ~3 GB for teacher.

**RTX 4070**: YES.

## 4. Training Approaches

### 4.1 rStar-Math (MCTS + DPO Self-Play)

**Paper**: Small LLMs Can Master Math Reasoning (papers01)

**Method**: Four-step cycle: (1) Self-play MCTS rollouts from the LLM itself. (2) Self-critique of intermediate steps. (3) DPO training on correct vs. incorrect trajectories. (4) Iterate.

```
UCT = Q(s,a) + C * sqrt(ln N_parent / N_child)    # C = 1.4
L_DPO = -E[log sigma(beta * (log pi_theta(y_w|x) - log pi_ref(y_w|x)
         - log pi_theta(y_l|x) + log pi_ref(y_l|x)))]
```

**VRAM**: ~6 GB for 1.5B model fp16. Use QLoRA for 7B.

**RTX 4070**: YES for 1.5-3B models. MARGINAL for 7B (needs 4-bit).

### 4.2 DP-SGD (Differentially Private SGD)

**Paper**: Deep Learning with Differential Privacy (Abadi et al., 2016)

**Method**: Per-example gradient clipping (L2 bound C) + Gaussian noise calibrated to (epsilon, delta) privacy budget. Moments Accountant for tight composition tracking.

```
g_i = clip(nabla L_i, C)
g_bar = 1/N * sum g_i + N(0, sigma^2 * C^2 * I)
```

**VRAM**: High — needs per-example gradients (not per-batch). Memory scales with batch size.

**RTX 4070**: MARGINAL. Use small batch sizes (2-4) + gradient accumulation.

**Integration**: Apply DP-SGD when fine-tuning guard models on sensitive data (user chats, red-team traces).

### 4.3 Knowledge Distillation

**Multiple papers**: Fast BLT, Edge AI FT, L-LoRA all use distillation.

**Method**: `L = CE(y_true, y_student) + alpha * KL(p_teacher || p_student)`. Alpha = 0.5 typically.

**VRAM**: Needs both teacher and student in memory simultaneously. ~2x base.

**RTX 4070**: YES for student <3B with teacher <7B.

### 4.4 Autoregressive DPO (AR-DPO)

**Paper**: alphaxiv #2, #7 — arxiv 2602.09533

**Method**: Extends standard DPO by conditioning on the diffusion/reasoning trajectory, not just the final answer. Uses a classifier-free guidance style objective:

```
L_AR-DPO = -E[log sigma(beta * (R(y_w, x) - R(y_l, x)))]
```

Where `R(y, x)` is the reward-adjusted log-probability over the full autoregressive trajectory, not just final tokens.

**Key advantage**: Captures partial credit — a trajectory with 9/10 correct steps before a wrong final answer isn't treated identically to a fully incorrect trajectory. This matters for guard model reasoning chains.

**RTX 4070**: YES for 1.5-3B. Uses standard DPO training loop with modified loss. Can be implemented as a `Trainer` subclass in HF transformers.

### 4.5 GUARD — Generation-Time LLM Unlearning

**Paper**: alphaxiv #2 — arxiv 2505.13312

**Method**: Alternative to pre-filtering guard models. Operates at generation time by:
1. Computing a "forget vector" via gradient ascent on harmful outputs.
2. During generation, projecting hidden states away from the forget direction at each layer.
3. No retraining, no additional model.

**Result**: 95% rejection rate on harmful prompts with <2% utility loss. Compatible with existing guard pipelines as a second-stage filter.

**RTX 4070**: YES. The projection is a single matrix multiply per token. Negligible overhead (~2% latency).

**Integration**: Add as a post-processing stage after the consensus guard vote. If the majority votes safe but GUARD detects harmful trajectory, escalate.

## 5. Evaluation Methods

### 5.1 Shortcut Neuron Analysis

**Paper**: Establishing Trustworthy LLM Evaluation via Shortcut Neuron Analysis (papers02)

**Method**: Compute shortcut score for each neuron: `S_i = |E[a_i | correct] - E[a_i | incorrect]| / sigma_i`. Mask top-k (1-5%) and re-evaluate. Score drop indicates shortcut reliance.

**VRAM**: Negligible (activations only, no gradients).

**RTX 4070**: YES.

**Integration**: Apply to guard models to identify if classification relies on spurious patterns (e.g., keyword matching) vs. genuine understanding.

### 5.2 CapBencher

**Paper**: How Can I Publish My LLM Benchmark (papers02)

**Method**: Inject randomness into benchmark answers (e.g., shift by +1 or -1). Models that exceed Bayes accuracy ceiling are contaminated. Affine mapping preserves ranking: `s_capped = 1/L * s_orig + (L-1)/(L*(K-1))`.

**Integration**: Apply to stres7-12 suite to make benchmarks contamination-resistant before public release.

### 5.3 Multi-Axis Robustness Framework

**Paper**: A Comprehensive Evaluation Framework for Deep Model Robustness (papers01)

**Components**: Adversarial (PGD, epsilon=4/255), corruption (15 types x 5 severities), OOD detection (Mahalanobis distance), calibration (ECE). Composite: `R = 0.3*adv + 0.3*corr + 0.2*ood + 0.2*(1-ECE)`.

**Integration**: Adapt for guard models — measure PGD attacks on text embeddings, corruption (typos, phrasing variations), OOD (novel attack patterns), calibration (confidence thresholds).

### 5.4 MirrorShield — Universal Defense Against Jailbreaks

**Paper**: alphaxiv #2 — arxiv 2503.12931

**Method**: Entropy-guided universal defense. At each decoding step, compute entropy of the next-token distribution. If entropy drops below threshold theta (indicating high-confidence harmful trajectory), inject noise into logits to force exploration of safer continuations.

```
if H(p_next) < theta:
    logits += N(0, sigma * (theta - H(p_next)) * I)
```

No training required. Works on any autoregressive model. 97.5% jailbreak resistance on AdvBench.

**RTX 4070**: YES. Entropy computation is trivial. Adds <1% latency.

**Integration**: Post-processing layer on any guard model output. If a guard model is highly confident about "safe" (low entropy) but the trajectory is actually harmful, MirrorShield's noise injection can reveal this.

### 5.5 MCP Security Analysis

**Papers**: alphaxiv #9 MCP — First Look at MCP Security (2510.16558), MCP-SafetyBench (2512.15163), SoK: Taxonomy of Prompt Security Attacks (2510.15476), HAICOSYSTEM (2409.16427)

**Key findings**:
- MCP servers are vulnerable to skill-injection attacks (25% of tested servers can be hijacked via crafted prompts).
- MCP-SafetyBench provides a standardized benchmark with 1,100+ test cases across 5 attack categories.
- HAICOSYSTEM provides a sandbox architecture that could isolate guard model execution.

**Integration**: The relay bridge (model_relay.py) uses MCP-like architecture. Apply sandbox isolation to guard model inference.

### 5.6 Skill-Inject Security in Agent Systems

**Paper**: alphaxiv #8 SKILLZ — arxiv 2602.20156

**Method**: Evaluates agent vulnerability to skill injection via crafted tool descriptions. 60% of tested agents follow injected "skills."

**Integration**: Guard pipeline should validate tool descriptions and agent instructions before passing to models.

## 6. Cross-Reference: Guard Pipeline Integration

| Approach | Guard Pipeline Integration | Priority |
|----------|--------------------------|----------|
| TIES-MERGING + DARE | Merge guard-specialized models (different guard families) into one | HIGH |
| MergeAlign | Safety-aware merging of guard + domain expert models | HIGH |
| Darwin Family (MRI-trust) | Evolutionary merge of 3 guard models into 1 with trust-weighted crossover | HIGH |
| Isotropic Merging (No Task Left Behind) | Preserve task-specific safety subspaces during merging | HIGH |
| Mix Data or Merge? | Evidence supports merging over training for guard models | HIGH |
| L-LoRA | Train guard adapters with linearized LoRA for better composability | MEDIUM |
| LINES | Post-guard-FT regularization against forgetting | MEDIUM |
| LQF | Quadratic classification head on guard model features | MEDIUM |
| PET/iPET | Few-shot guard classifier from 32 examples | HIGH |
| EvolKV | Compress KV cache for longer guard reasoning contexts | MEDIUM |
| Cortex | Semantic caching for repeated guard queries | MEDIUM |
| Shortcut Neuron | Benchmark guard models for spurious pattern reliance | MEDIUM |
| CapBencher | Contamination-resistant guard benchmark | LOW |
| PolarQuant | Quantize merged guard model to Q5 for lower VRAM | HIGH |
| MKA (Pruning via Merging) | Compress 3-model guard pipeline to single merged model | HIGH |
| DP-SGD | Privacy-preserving guard training on user data | MEDIUM |
| AR-DPO | Trajectory-aware DPO for guard reasoning chains | MEDIUM |
| GUARD (generation-time unlearning) | Second-stage filter after consensus vote | MEDIUM |
| MirrorShield | Entropy-based noise injection on guard outputs | HIGH |
| rStar-Math (MCTS+DPO) | Self-play improvement of guard reasoning | LOW (research) |
| MCP Security | Sandbox isolation for guard model inference | HIGH |

## 7. Recommended Implementation Order

### Phase 1 (immediate, 1-2 days)
1. **MKA** — compress the 3-guard pipeline into a single merged guard model
2. **TIES-MERGING + DARE** — merge guard specialists with mergekit
3. **Darwin Family MRI-trust** — evolutionary merge of guard models with trust-weighted crossover (complements TIES)
4. **MirrorShield** — entropy-based noise injection on guard outputs (zero-training defense, instant deploy)
5. **PolarQuant** — quantize merged guard to Q5 for VRAM savings
6. **PET/iPET** — train a 32-example few-shot guard classifier as 4th "fast path" stage

### Phase 2 (short-term, 1 week)
7. **Isotropic Merging (No Task Left Behind)** — preserve safety subspaces during guard model merging
8. **MergeAlign** — safety-aware weights when merging domain experts
9. **L-LoRA** — implement linearized LoRA for guard adapter training
10. **LINES** — apply post-FT regularization to prevent forgetting
11. **Shortcut Neuron** — benchmark guard models; fix spurious patterns
12. **MCP Security** — sandbox isolation for guard model inference in relay

### Phase 3 (medium-term, 2-4 weeks)
13. **AR-DPO** — trajectory-aware DPO for guard reasoning chain improvement
14. **GUARD** — generation-time unlearning as second-stage filter
15. **LQF** — quadratic guard classification head
16. **DP-SGD** — privacy-preserving fine-tuning on traces
17. **EvolKV / Cortex** — KV cache compression for longer guard reasoning
18. **CapBencher** — contamination-hardened benchmark for stres7-12
19. **Multi-axis robustness** — adversarial guard model evaluation
20. **MCP-SafetyBench** — standardized security benchmark for relay/bridge

## Key Tools & Libraries

| Tool | For | Source |
|------|-----|--------|
| mergekit | TIES, DARE, Task Arithmetic, SLERP | `pip install mergekit` |
| peft | LoRA, QLoRA, L-LoRA | `pip install peft` |
| bitsandbytes | 4-bit quantization | `pip install bitsandbytes` |
| llama.cpp / Ollama | GGUF quantization | Built-in via Ollama |
| transformers | Model loading, distillation | `pip install transformers` |
| torch.func | JVP for linearized FT | Built into PyTorch |
| shortcut-neuron | Shortcut analysis | Custom impl ~100 lines |

## References

Paper dump: `C:\Users\speci.000\Downloads\ARCHIVIST\megaLinkModelPaperdump-01.txt` (742 links)
PAPERS dir: `C:\Users\speci.000\Downloads\PAPERS\papers01/` (98 PDFs), `papers02/` (64 PDFs), `papers03/` (46 PDFs)
Alphaxiv library: `C:\Users\speci.000\Downloads\ARCHIVIST\MODELrelatedPAPERlibraryBASE.txt` (9 folders, 423+ papers)
  #1 rewarding/train (75 papers): RLVR, DPO/PPO, reward models, self-distilled RL
  #2 train (104 papers): test-time learning, MirrorShield, GUARD, AR-DPO
  #3 kv VECTORS (24 papers): Darwin Family, EvolKV, Cortex, DFlash, KV quantization
  #4 consciousness (63 papers): attractor models, SuperLocalMemory, LightMem
  #5 SLM_SMOL (20 papers): Mellum2, Darwin Family, Mix Data or Merge?, SWE-Protégé
  #6 MEMM (7 papers): Evo-Memory, LightMem, MemEvolve, LiNeS
  #7 hallucination (65 papers): attractor models, AR-DPO, hallucination detection
  #8 SKILLZ (54 papers): Mellum2, Skill-Inject, Tree Search for RL, ReMA
  #9 MCP (11 papers): MCP-SafetyBench, SoK Prompt Security, HAICOSYSTEM
Guard analysis: `docs/research/model_analysis_and_guarding_strategies.md`
Benchmarks: `benchmarks/calibrate_twave_v2_landau_ginzburg.py`, `benchmarks/stres7_*.py` through `stres12_*.py`
