# NEXUS OS — Sakana + Papers10 Upgrade Blueprint
**Date:** 2026-06-22
**Author:** NEXUS planning synthesis
**Status:** PROPOSAL — for review and prioritization

## Context

We grounded 6 papers from `papers10` plus the Sakana Fugu technical report and LLM-PeerReview (LLM Ensemble via peer-review). These describe a coherent architectural family:

- **Sakana lineage**: Fugu (orchestrator LLM with lightweight head), Trinity (SLM + 3-role coordination), Conductor (natural-language workflow generator), Darwin Gödel Machine (open-ended self-improvement)
- **External**: LLM-PeerReview (peer-review ensemble with Dawid-Skene EM), FlowSearch (DAG-of-knowledge with incremental refinement)

All align with NEXUS OS's governance-first architecture and our persistent memory + ModelRelay system. This blueprint lists concrete implementation steps.

## Architecture Family (Sakana lineage + NEXUS)

```
                 NEXUS PersistentRouter (Fugu-style soft-target SFT)
                              ↓
            Trinity-style 3-role coordinator
              ├── Thinker (SLM 0.6B or GLM-5.1)
              │     ↓ proposes workflow
              ├── Worker (LongCat / InternAI / GLM / Nemotron / M3)
              │     ↓ executes subtask
              └── Verifier (Nemotron Ultra safety layer / Intern AI)
                    ↓ ACCEPT/REVISE → terminate or re-iterate
                              ↓
            FlowSearch DAG (typed nodes: search/solve/answer)
              ↓ Refiner mutates with 6 ops
                              ↓
            LLM-PeerReview ensemble (Dawid-Skene EM)
              ↓ final answer selection
                              ↓
            Persistent Memory Handoff + KAIJU gate
```

## Implementation Phases

### Phase A — Trinity-style 3-role coordinator (PRIORITY 1)

**File:** `nexus_os/nexusclaw/trinity_coordinator.py`

**Design:**
- Thin orchestrator on top of existing Brain API
- 3 roles: Thinker (proposer), Worker (executor), Verifier (gate)
- Existing NEXUS pieces map cleanly:
  - Thinker = `nexus_os/engine/hermes.py` (planner)
  - Worker = `nexus_os/nexusclaw/agent_pool.py` (executor)
  - Verifier = `nexus_os/governor/trust_kernel_v2.py` (gate)
- Termination: `τ = min{k ≤ K : verifier_says = ACCEPT}`
- Max 5 workflow steps (same as Fugu-Ultra Conductor)
- Worker pool initially: GLM 5.1 (NVIDIA NIM) + LongCat + InternAI + Nemotron Ultra

**Implementation:**
```python
@dataclass
class TrinityDecision:
    role: str  # thinker | worker | verifier
    model: str
    prompt: str
    confidence: float
    terminated: bool = False

class TrinityCoordinator:
    def __init__(self, brain_api_url, kaiju_url, max_steps=5):
        self.brain = brain_api_url
        self.kaiju = kaiju_url
        self.max_steps = max_steps

    def decide(self, task_context: TaskContext, history: List[TrinityDecision]) -> TrinityDecision:
        """Run one Trinity step. Returns next role+model or termination."""
        # Call lightweight orchestrator (initially rule-based, later trained SLM)
        if not history:
            return TrinityDecision(role="thinker", model="nim/z-ai/glm-5.1",
                                    prompt="Decompose task into subtasks", confidence=1.0)
        # Look at verifier feedback
        if history[-1].role == "verifier" and history[-1].terminated:
            return TrinityDecision(role="worker", model=history[-1].model, ...)  # final
        # Run verifier to accept/revise
        ...
```

**Tests:** 5 tests covering basic 3-role flow, termination conditions, gate rejection.

### Phase B — Fugu-style soft-target SFT (PRIORITY 2)

**File:** `nexus_os/model_relay/persistent_router.py` (extend existing)

**Design:**
- Soft target: `p_i(j) = softmax(r̄_ij / τ)` from worker performance averages (not hard ranking)
- Two-stage training: (1) SFT with soft KL target over worker reward distributions, (2) sep-CMA-ES on end-to-end task trajectories
- Worker reward scorer: `nexus_os/eval/worker_reward_scorer.py`

**Implementation:**
```python
def compute_soft_targets(worker_scores: Dict[str, float], temperature: float = 1.0) -> Dict[str, float]:
    """Convert worker performance scores to soft selection probabilities."""
    import numpy as np
    models = list(worker_scores.keys())
    rewards = np.array([worker_scores[m] for m in models])
    probs = np.exp(rewards / temperature) / np.sum(np.exp(rewards / temperature))
    return {m: float(p) for m, p in zip(models, probs)}

def fugu_dispatch(task_embedding, worker_pool, soft_targets) -> str:
    """Pick worker based on soft target weighted by orchestrator's prediction."""
    # Toy version: weighted random pick. Real version: train lightweight head.
    candidates = list(worker_pool.keys())
    weights = [soft_targets[c] for c in candidates]
    return np.random.choice(candidates, p=weights)
```

**Tests:** 3 tests for softmax correctness, dispatch determinism.

### Phase C — LLM-PeerReview ensemble (PRIORITY 3)

**File:** `nexus_os/governor/peer_review.py`

**Design:**
- Dawid-Skene EM for per-judge confusion matrix
- Flipped-triple scoring trick to mitigate position bias
- Used for HIGH-STAKES tasks (Brain API proposals, NEXUSCLAW critical decisions)

**Implementation:**
```python
@dataclass
class PeerReviewResult:
    winner: str
    confidence: float
    judge_scores: Dict[str, float]
    judge_agreement: float

def dawid_skene_em(judgments: List[Tuple[str, int]], n_classes: int, n_iter: int = 10) -> Dict[int, float]:
    """Dawid-Skene EM: returns posterior over true labels for each item."""
    # Implement the EM loop. Initial: uniform prior.
    n_items = len(judgments)
    priors = [1.0 / n_classes] * n_classes
    # ... EM iterations ...
    return posteriors
```

**Tests:** 5 tests covering basic EM, single judge, multi-judge agreement.

### Phase D — FlowSearch DAG (PRIORITY 4)

**File:** `nexus_os/research/knowledge_flow.py`

**Design:**
- Typed nodes: `search` / `solve` / `answer`
- 6 graph operations for refiner: AddNode, DelNode, ModNode, AddEdge, DelEdge, ModEdge
- Persistent in 8-channel memory: search → EPISODIC, solve → TASK, answer → META
- Parallel execution when dependencies resolve

**Implementation:**
```python
class KnowledgeNode:
    id: str
    type: str  # search | solve | answer
    query: str
    result: str = ""
    parents: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    status: str = "pending"  # pending | running | complete | failed

class FlowSearchDAG:
    def __init__(self):
        self.nodes = {}
        self.graph_ops = ["AddNode", "DelNode", "ModNode", "AddEdge", "DelEdge", "ModEdge"]

    def plan_next_step(self, current_dag: Dict) -> List[str]:
        """Returns list of next operations to apply."""
        # Identify decomposable nodes
        pending = [n for n in self.nodes.values() if n.status == "pending"]
        return [f"AddNode:{self.generate_child(p)}" for p in pending[:3]]

    def execute_ready(self, executor_fn) -> List[KnowledgeNode]:
        """Execute all ready nodes in parallel."""
        ready = [n for n in self.nodes.values() if n.status == "pending" and self._deps_met(n)]
        for n in ready:
            n.status = "running"
        # Parallel call (concurrent.futures or asyncio)
        results = executor_fn(ready)
        return results
```

**Tests:** 4 tests for DAG mutation, parallel execution, cycle detection.

### Phase E — Darwin Gödel Machine (PRIORITY 5, dry-run only)

**File:** `nexus_os/nexusclaw/dgm_archive.py`

**Design:**
- Open-ended archive of agent variants
- Parent selection: `p ∝ score / (1 + num_children_with_edit_capability)`
- Staged evaluation: 10 → 60 → 200 task cascade
- **MUST run in dry-run mode initially per AGENTS.md Phase 0**
- Every self-modification passes `nexusctl cycle-check` + 631 tests before promotion

**Implementation:**
```python
class DGMArchive:
    def __init__(self, dry_run: bool = True):
        self.archive = {}  # id -> AgentVariant
        self.dry_run = dry_run

    def select_parent(self) -> str:
        """Score-weighted, child-count-penalized parent selection."""
        scores = {aid: v.score for aid, v in self.archive.items()}
        children_count = {aid: len([c for c in v.children if self.archive[c].can_edit]) for aid, v in self.archive.items()}
        probs = {aid: s / (1 + children_count[aid]) for aid, s in scores.items()}
        total = sum(probs.values())
        probs = {k: v/total for k, v in probs.items()}
        return max(probs, key=probs.get)

    def evolve_step(self, parent_id: str) -> str:
        """Generate child variant, evaluate, add to archive if better."""
        # 1. Analyze parent's eval logs
        # 2. Propose next improvement
        # 3. Implement (in dry-run, just record what WOULD happen)
        # 4. Benchmark
        # 5. Add to archive if score > parent
        ...
```

**Tests:** 3 tests covering archive operations, parent selection, dry-run mode.

## Worker Pool (initial)

| Role | Model | Provider | Why |
|------|-------|----------|-----|
| Thinker | GLM 5.1 | NVIDIA NIM | Best frontier for planning (91% intell) |
| Worker (complex) | GLM 5.1 / Nemotron Ultra | NVIDIA NIM | High-difficulty subtasks |
| Worker (specialist) | LongCat / Intern AI / DeepSeek V4 Flash | OpenCode/InternAI/NIM | Domain-specific |
| Worker (fast) | groq/llama-3.3-70b-versatile | Groq | 236ms latency |
| Verifier | Nemotron Ultra + LLM-PeerReview | NVIDIA NIM + ensemble | Safety gate |
| Logger (memory) | LongCat / Intern AI | OpenAI + Anthropic compatible | Persistent consistency |

## Success Metrics

| Metric | Baseline (current) | Target (after Phase A-E) |
|--------|---------------------|---------------------------|
| NEXUS test count | 2,265+ | 2,500+ (with new Trinity/Conductor/FlowSearch tests) |
| MCP guard recall | 100% (post-papers09 fix) | 99%+ with Trinity verification |
| NEXUSCLAW Brain API tasks | static routing | Trinity-coordinated with persistent memory |
| Model selection explainability | opaque | "Verifier ACCEPT, score 0.91, GLM 5.1, Trinity step 3" |
| Fallback latency (LongCat) | "rotate randomly" | "Verifier REVISE → LongCat log → continue" |
| Memory continuity | per-call | persistent across Trinity cycles |

## Risks

1. **Trinity 3-role overhead** — 3 LLM calls per task instead of 1. Mitigation: Thinker is 0.6B SLM (fast); Worker cache; Verifier can short-circuit on tool-call approvals.
2. **DGM risk** — self-modifying NEXUS code can break governance. Mitigation: dry-run only; `nexusctl cycle-check` + 631 tests gate every promotion; KAIJU wraps every change.
3. **Conductor emergence** — RL-trained workflows can drift. Mitigation: format reward + LLM-PeerReview ensemble sanity check.
4. **Soft-target SFT data** — need N>=50 worker reward measurements per task type. Mitigation: start with rule-based fallbacks; collect data during Phase A operation.

## Next Steps (proposed order)

1. **Build TrinityCoordinator skeleton** (`nexus_os/nexusclaw/trinity_coordinator.py`) — 200 lines, 5 tests
2. **Wire into existing Brain API proposals** — extend `/governance/proposals` to use Trinity for any decision affecting >1 layer
3. **Add Fugu-style soft-target scoring** — track worker success/failure per task type in `quota_tracker.py`, use as soft targets
4. **Add LLM-PeerReview for CRITICAL flag in Brain API** — proposals marked `critical=true` get ensemble review
5. **Build FlowSearch DAG prototype** — for `nexusctl deep-research` command (new CLI surface)
6. **DGM dry-run archive** — collect agent variants without auto-promotion

## References

- Sakana Fugu Technical Report (papers10)
- LLM-PeerReview (Scoring, Reasoning, and Selecting the Best!) — papers10
- TRINITY (papers10, arXiv 2512.04695v3)
- Conductor (papers10, arXiv 2512.04388v5)
- Darwin Gödel Machine (papers10, arXiv 2505.22954v3)
- FlowSearch (papers10, arXiv 2510.08521v2)
- Sakana API docs: https://console.sakana.ai/get-started
- Intern AI Discovery: https://discovery.intern-ai.org.cn/org/ailab/
- papers09 batch (89 papers, 80 grounded) — foundation for papers10 work