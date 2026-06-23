# PAPERS10 Integration Proposals — 2026-06-23

**Version:** 1.0.0
**Status:** Actionable implementation proposals based on PAPERS10 deep synthesis
**Priority:** P0-P2 with specific code paths and test strategies

---

## Proposal 1: TRINITY-Style CogER Router (P0)

### What
Replace the current GMR/CogER routing logic with a TRINITY-inspired lightweight coordinator that dynamically assigns Thinker/Worker/Verifier roles across the model pool.

### Source Paper
TRINITY: An Evolved LLM Coordinator (`arxiv:2512.04695`, ICLR 2026)

### Current State
`nexus_os/gmr/coger.py` — CogER currently routes requests to models based on static scoring. No multi-turn coordination, no role assignment.

### Implementation Plan

**Phase 1 — Coordinator Head (1 day)**
- File: `nexus_os/gmr/trinity_coordinator.py`
- Implement lightweight routing head (linear layer, ~10K params) over hidden states from a small SLM (e.g., Qwen2.5-0.5B or a frozen SLM)
- `class CoordinatorHead(nn.Module)` with `hidden_dim → (n_models * n_roles)` output
- Three roles: `THINKER`, `WORKER`, `VERIFIER` as enum
- Multi-turn loop: `def route(query: str, transcript: list) -> (model_id, role)`

**Phase 2 — Evolutionary Optimizer (1 day)**
- File: `nexus_os/gmr/sep_cma_es.py`
- Implement separable CMA-ES optimizer
- `class SepCMAES`: population-based, diagonal covariance (block-epsilon-separable assumption)
- Reward: binary correctness signal from verifier
- Budget: ~1.5K-40K evaluations feasible for ~10K params

**Phase 3 — Integration with existing CogER**
- Modify `nexus_os/gmr/gmr_router.py` to accept CoordinatorHead as routing strategy option
- Wire into GMR's `select_model()` pipeline
- Add `--coordinator` flag to GMR service startup

### Test Strategy
- `tests/gmr/test_trinity_coordinator.py`:
  - Test three-role loop: single turn, multi-turn (2-5), max turn limit
  - Test coordinator head output dimensions match pool size
  - Test sep-CMA-ES convergence on toy 2D problem
  - Test integration: route(query) returns valid (model_id, role) tuple
  - Test Verifier triggers stop when solution accepted
  - Test edge case: empty model pool
  - Test edge case: all roles assigned to same model (degenerate but valid)

### Risk
- sep-CMA-ES requires each eval to run full multi-turn LLM rollout — expensive
- Mitigation: cache evaluations, use smaller proxy model during training phase

---

## Proposal 2: Conductor-Style RL Orchestration for NEXUSCLAW (P0)

### What
Replace NEXUSCLAW's hand-coded agent workflow logic with an RL-trained Conductor model that learns optimal coordination strategies end-to-end.

### Source Paper
Learning to Orchestrate Agents in Natural Language with the Conductor (`arxiv:2512.04388`, ICLR 2026)

### Current State
`nexus_os/claw/` — NEXUSCLAW uses hardcoded agent pipelines (plan → search → verify → execute). Each new task type requires manual workflow engineering.

### Implementation Plan

**Phase 1 — Conductor Training Pipeline (2 days)**
- File: `nexus_os/claw/rl_conductor.py`
- Define workflow grammar: natural-language steps with `(instruction, agent_id, visibility_mask)` tuples
- Implement RL environment: task dataset → Conductor generates workflow → worker agents execute → reward based on correctness + cost
- Use GRPO (Group Relative Policy Optimization) as in Conductor paper
- **Model choice:** Fine-tune Qwen2.5-7B or VibeThinker-3B as Conductor

**Phase 2 — Recursive Test-Time Scaling (1 day)**
- Allow Conductor to select itself as worker → re-evaluate output → assemble corrective workflow
- `class RecursiveConductor(Conductor)`: adds self-selection logic and iteration budget
- Dynamic test-time scaling: more iterations for hard problems, fewer for easy

**Phase 3 — Plug into NEXUSCLAW (1 day)**
- Replace `ClawPipeline.run()` with `Conductor.generate_workflow(task) -> [steps]`
- Keep existing `ClawExecutor` for step execution (reuse tool-use, sandbox code)
- Add randomized agent pool during training for generalization (Conductor paper §4.1)

### Test Strategy
- `tests/claw/test_rl_conductor.py`:
  - Test workflow grammar: valid step generation, agent visibility masking
  - Test RL environment: task → workflow → reward loop
  - Test with fixed dummy agents: verify Conductor learns to delegate correctly
  - Test recursive topology: self-selection produces different workflow on retry
  - Test out-of-distribution: train on Math, test on Code (generalization)
  - Test cost-awareness: verify Conductor uses fewer steps for simple tasks
  - Test edge case: empty agent pool → fallback to single-model direct answer

### Risk
- RL training with multi-turn LLM rollouts is expensive (~$500-$2000 per training run)
- Conductor may learn spurious correlations in task→workflow mapping
- Mitigation: start with small task dataset (100-200 problems), verify on held-out set

---

## Proposal 3: VibeThinker-3B as TWAVE Primary SLM (P0)

### What
Integrate VibeThinker-3B as the default local reasoning model in TWAVE's low-VRAM execution layer. Replace any existing SLM for reasoning tasks.

### Source Paper
VibeThinker-3B: Exploring the Frontier of Verifiable Reasoning in Small Language Models (`arxiv:2606.16140`)

### Current State
`nexus_os/twave/` — TWAVE currently supports multiple model formats. The default SLM for reasoning may not be optimized for verifiable reasoning.

### Implementation Plan

**Phase 1 — Model Import (0.5 day)**
- Download `WeiboAI/VibeThinker-3B` from HuggingFace
- Add to TWAVE's model registry: `nexus_os/twave/models/vibethinker_3b/`
- Register in `nexus_os/twave/model_registry.py`
- MIT license — no legal restrictions

**Phase 2 — CLR Test-Time Scaling (0.5 day)**
- File: `nexus_os/twave/clr_scaling.py`
- Implement Claim-Level Reliability Assessment:
  - Extract claims from model output
  - Verify each claim via 5 independent rollouts
  - Aggregate: reliability = mean(5 verdicts)^5
  - Select answer with highest combined reliability score
- This is NEXUS's existing verification loop — integrate, not reimplement

**Phase 3 — vLLM Serving Config (0.5 day)**
- Add `twave serve --model vibethinker-3b --speculative-eagle3` config preset
- Enable EAGLE-3 speculative decoding for 2-4x speedup (see Proposal 5)
- Memory target: ~6.7GB VRAM fits consumer GPU (single RTX 3090/4090)

### Test Strategy
- `tests/twave/test_vibethinker.py`:
  - Test model loads at correct size (3.09B params)
  - Test AIME25 subset: verify Pass@1 ≥ 85% (reproduced from alphaXiv replication)
  - Test CLR: compare accuracy with/without claim-level scaling
  - Test VRAM usage: confirm ≤ 7GB with kv_cache quantization
  - Test EAGLE-3 integration: 2x+ throughput improvement
  - Test edge case: < 6GB VRAM → fallback to 4-bit quantization
  - Test edge case: non-verifiable task (free-form text) → skip CLR, use direct output

---

## Proposal 4: Tandem SLM-LLM Collaboration (P0)

### What
Implement the ACL 2025 Tandem pattern: LLM generates compact reasoning guidance → SLM executes full reasoning → cost-aware termination.

### Source Paper
Tandem: Riding Together with Large and Small Language Models for Efficient Reasoning (ACL 2025 Findings)

### Current State
No explicit LLM-SLM collaboration pattern exists in NEXUS. Models are selected independently per task.

### Implementation Plan

**Phase 1 — Tandem Router (1 day)**
- File: `nexus_os/gmr/tandem_router.py`
- `class TandemRouter`:
  - LLM (e.g., GPT-4o, Claude, or external API) generates critical reasoning insights only (compact, 50-200 tokens)
  - SLM (VibeThinker-3B or local SLM) receives insights + problem statement → generates full solution
  - Cost-aware termination: LLM stops generating insights once sufficiency threshold reached
- Sufficiency classifier: trained model that outputs `p(sufficient | insight_so_far, task_difficulty)`

**Phase 2 — Sufficiency Classifier (1 day)**
- Train on MATH dataset: for each problem, generate incremental LLM insights → check if SLM can solve with partial info
- Model: small MLP or linear probe over insight embeddings
- Transfer: sufficiency classifier trained on MATH should transfer to HumanEval (per paper)

**Phase 3 — Integration with GMR (1 day)**
- Add Tandem as a routing strategy option in GMR
- `--tandem` flag pairs a large external model with local VibeThinker-3B
- Cost savings: ~40% API cost reduction per paper claim

### Test Strategy
- `tests/gmr/test_tandem_router.py`:
  - Test LLM insight generation: compactness (≤200 tokens), informativeness
  - Test SLM solution: correct answer from LLM insights
  - Test sufficiency classifier: predict threshold for insight sufficiency
  - Test cross-domain transfer: train on MATH, test on HumanEval (code)
  - Test cost: verify API token reduction ≥ 30%
  - Test edge case: LLM generates misleading insights → SLM should still produce reasonable answer
  - Test edge case: simple task → LLM stops after 1 insight (cost-aware)

---

## Proposal 5: EAGLE-3 Speculative Decoding for TWAVE (P0)

### What
Enable EAGLE-3 speculative decoding in TWAVE's vLLM serving stack for 2-4x inference speedup on local models.

### Source Paper
EAGLE-3: Scaling up Inference Acceleration of Large Language Models via Training-Time Test (`arxiv:2503.01840`)

### Current State
TWAVE uses vLLM for serving. Speculative decoding may not be enabled or may use an older technique.

### Implementation Plan

**Phase 1 — EAGLE-3 Head Training or Download (0.5 day)**
- For VibeThinker-3B: check if EAGLE-3 draft head is available on HuggingFace
- If not: train using EAGLE-3 code (requires ~8 H100-hours, ~$80)
- Draft head: lightweight auto-regressive transformer layer (~1% of target model params)
- Fuses low/middle/high layer features (EAGLE-3 innovation)

**Phase 2 — vLLM Integration (0.5 day)**
- Configure vLLM with `--speculative-model eagle3 --num-speculative-tokens 6`
- EAGLE-3.1 ships as native vLLM plugin (vllm ≥ 0.8.0)
- Tree attention depth: 6-8 tokens (per production benchmarks)
- Memory overhead: ~3.8GB for 70B model, proportionally less for 3B

### Test Strategy
- `tests/twave/test_speculative_decoding.py`:
  - Test throughput: tokens/sec with/without EAGLE-3 (target ≥ 2x)
  - Test output equivalence: verify identical output to non-speculative (mathematical guarantee)
  - Test acceptance rate: monitor, target ≥ 70%
  - Test VRAM budget: stay within available GPU memory
  - Test edge case: creative generation (lower acceptance rate) → fallback to standard decoding

---

## Proposal 6: KAME Async Oracle for NEXUSCLAW (P1)

### What
Implement KAME's asynchronous oracle injection pattern: start response immediately with a fast model, inject improved results from a slower backend model in real-time.

### Source Paper
KAME: Tandem Architecture for Enhancing Knowledge in Real-Time Speech-to-Speech Conversational AI (ICASSP 2026, `arxiv:2510.02327`)

### Current State
NEXUSCLAW responses are synchronous — wait for entire pipeline before returning.

### Implementation Plan

**Phase 1 — Async Injection Layer (2 days)**
- File: `nexus_os/claw/kame_oracle.py`
- Fast response loop: VibeThinker-3B generates initial response immediately
- Backend oracle: larger model (external API or local 70B) runs async, generates refined response candidates
- Injection mechanism: replace segments of running output with oracle signals
- `class KAMEAsyncOracle`: manages two concurrent generation loops + merge logic

**Phase 2 — Integration with Bridge/SSE (1 day)**
- Wire into Bridge's streaming response pipeline
- Client sees: fast initial tokens → gradual refinement as oracle injects
- SSE stream carries revision markers

### Test Strategy
- `tests/claw/test_kame_oracle.py`:
  - Test async: both loops complete successfully
  - Test injection quality: oracle-injected answer ≥ fast-only answer
  - Test latency: first-token time improves (target ≤ 500ms)
  - Test edge case: oracle slower than response → no injection (graceful degradation)

---

## Proposal 7: TAID Distillation for NEXUS Edge SLMs (P1)

### What
Use TAID to distill large NEXUS models into compact edge-deployable SLMs for TWAVE.

### Source Paper
TAID: Temporally Adaptive Interpolated Distillation for Efficient Knowledge Transfer in Language Models (ICLR 2025 Spotlight, `arxiv:2501.16937`)

### Current State
No structured distillation pipeline in NEXUS. Models are trained independently.

### Implementation Plan

**Phase 1 — Distillation Pipeline (3 days)**
- File: `nexus_os/twave/distillation/taid_trainer.py`
- Implement TAID loss: temporally interpolated student-teacher distribution
- Intermediate teacher distribution: `p_intermediate(t) = (1-λ(t)) * p_student + λ(t) * p_teacher`
- λ(t) schedule: starts near 0, ends near 1
- Teacher: NEXUS's best available model (external API or largest local)
- Student: Qwen2.5-1.5B or TinySwallow base

**Phase 2 — Domain-Specific SLMs (2 days)**
- Distill separately for: Math/Code/STEM/Instruction-following
- Use diversity-exploring distillation (VibeThinker SSP technique) for multi-domain models
- Merge domain-specific SLMs via parameter merge (DARE/TIES)

### Test Strategy
- `tests/twave/distillation/test_taid.py`:
  - Test student accuracy improves over baseline (no distillation)
  - Test capacity gap robustness: 70B teacher → 1.5B student
  - Test mode collapse: student output diversity comparable to teacher
  - Test mode averaging: student doesn't converge to uniform distribution

---

## Proposal 8: ADCL Curriculum Learning for Guard Model Training (P2)

### What
Apply Adaptive Difficulty Curriculum Learning (ADCL) to guard model fine-tuning for improved robustness.

### Source Paper
Learning Like Humans: Advancing LLM Reasoning Capabilities via Adaptive Difficulty Curriculum Learning and Expert-Guided Self-Reformulation (`arxiv:2505.08364`)

### Current State
Guard model training (Qwen3Guard, Llama-Guard-3) uses static dataset. No difficulty-adaptive curriculum.

### Implementation Plan

**Phase 1 — ADCL Scheduler (1 day)**
- File: `nexus_os/guard/adcl_scheduler.py`
- Periodically re-estimate difficulty of each training example based on current model loss
- Batch data by re-estimated difficulty → present easy→hard over time
- Addresses "Difficulty Shift" phenomenon

**Phase 2 — Integration with Guard Training (1 day)**
- Modify `nexus_os/guard/train_guard.py` to accept ADCL scheduler
- Expected improvement: 10-16% on guard accuracy (paper results on reasoning)
- Test on ASB/guard benchmark datasets

---

## Implementation Order

```
Week 1 (P0):  Proposal 3 (VibeThinker import) → Proposal 5 (EAGLE-3) → Proposal 1 (TRINITY coordinator)
Week 2 (P0):  Proposal 4 (Tandem router) → Proposal 2 (Conductor RL)
Week 3 (P1):  Proposal 6 (KAME async) → Proposal 7 (TAID distillation)
Week 4 (P2):  Proposal 8 (ADCL curriculum)
```

All P0 proposals have concrete implementation paths with ≤ 3 days each. Total P0 effort: ~8-12 engineering days.

---

## Dependency Graph

```
Proposal 3 (VibeThinker-3B) ──┐
                              ├── Proposal 5 (EAGLE-3) ── faster local inference
                              │
                              ├── Proposal 4 (Tandem) ── LLM+SLM pair
                              │
                              └── Proposal 1 (TRINITY) ── needs model pool, VibeThinker as worker

Proposal 2 (Conductor RL) ─── needs Proposal 1 (TRINITY coordinator as baseline)
Proposal 6 (KAME) ────────── needs Proposal 3 (VibeThinker for fast loop)
Proposal 7 (TAID) ────────── independent, can run in parallel
Proposal 8 (ADCL) ────────── independent, can run in parallel
```

---

**Document Status:** COMPLETE
**Last Updated:** 2026-06-23
**Cross-ref:** PAPERS10_SYNTHESIS.md for detailed research findings
