"""NEXUS — Trinity-style 3-role coordinator.

Based on Sakana Trinity paper (arXiv:2512.04695v3) — ICLR 2026.
https://github.com/SakanaAI/sakana

Architecture:
    Thinker (T) → proposes workflow / subtask decomposition
    Worker (W) → executes subtask via LLM
    Verifier (V) → ACCEPT / REVISE on Worker output

Termination: τ = min{k ≤ K : V_k = ACCEPT}

Mapping to NEXUS OS:
    Thinker = engine/hermes.py (planner)
    Worker = nexusclaw/agent_pool.py (executor)
    Verifier = governor/trust_kernel_v2.py (gate)

Worker pool (initial):
    Thinker: nim/z-ai/glm-5.1 (best frontier planner)
    Worker complex: nim/z-ai/glm-5.1 or nim/nvidia/nemotron-3-ultra
    Worker specialist: opencode/deepseek-v4-flash-free or longcat/LongCat-2.0-Preview
    Worker fast: groq/llama-3.3-70b-versatile (236ms)
    Verifier: nim/nvidia/nemotron-3-ultra + LLM-PeerReview ensemble

This file: lightweight rule-based Trinity — no SLM training required for
initial deployment. Can be upgraded later with trained lightweight head.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# ── Roles ────────────────────────────────────────────────────────────────


class Role(str, Enum):
    THINKER = "thinker"
    WORKER = "worker"
    VERIFIER = "verifier"


# ── Verdict ──────────────────────────────────────────────────────────────


class Verdict(str, Enum):
    ACCEPT = "ACCEPT"
    REVISE = "REVISE"
    ABORT = "ABORT"


# ── Decision record ──────────────────────────────────────────────────────


@dataclass
class TrinityDecision:
    """One step in a Trinity workflow."""
    decision_id: str
    role: Role
    model: str
    prompt: str
    output: str = ""
    verdict: Optional[Verdict] = None
    confidence: float = 0.0
    next_role: Optional[Role] = None
    next_model: Optional[str] = None
    ts: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "role": self.role.value,
            "model": self.model,
            "prompt": self.prompt[:200] + ("..." if len(self.prompt) > 200 else ""),
            "output": self.output[:500] + ("..." if len(self.output) > 500 else ""),
            "verdict": self.verdict.value if self.verdict else None,
            "confidence": self.confidence,
            "next_role": self.next_role.value if self.next_role else None,
            "next_model": self.next_model,
            "ts": self.ts,
        }


@dataclass
class TrinityWorkflow:
    """Complete Trinity workflow session."""
    workflow_id: str
    task_id: str
    title: str
    description: str
    history: List[TrinityDecision] = field(default_factory=list)
    terminated: bool = False
    final_output: str = ""
    final_verdict: Optional[Verdict] = None
    started_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    ended_at: Optional[float] = None
    model_router: Optional[Any] = None  # Optional persistent_router

    def add_step(self, decision: TrinityDecision) -> None:
        self.history.append(decision)

    def steps_count(self) -> int:
        return len(self.history)

    def steps_by_role(self, role: Role) -> List[TrinityDecision]:
        return [d for d in self.history if d.role == role]


# ── Worker pool registry ──────────────────────────────────────────────────


WORKER_POOL: Dict[str, Dict[str, Any]] = {
    # THINKER candidates — best frontier planners
    "nim/z-ai/glm-5.1": {
        "role_hint": Role.THINKER,
        "intell": 0.91,
        "ctx_k": 202,
        "latency_ms": 2765,
        "lane": "teacher",
    },
    # WORKER complex candidates
    "nim/nvidia/nemotron-3-ultra-550b-a55b": {
        "role_hint": Role.WORKER,
        "intell": 0.45,
        "ctx_k": 1000,
        "latency_ms": 4500,
        "lane": "primary",
    },
    "ollama-cloud:minimax-m3": {
        "role_hint": Role.WORKER,
        "intell": 0.90,
        "ctx_k": 512,
        "latency_ms": 1200,
        "lane": "primary",
    },
    # WORKER specialist candidates
    "opencode/deepseek-v4-flash-free": {
        "role_hint": Role.WORKER,
        "intell": 0.85,
        "ctx_k": 128,
        "latency_ms": 1400,
        "lane": "specialist",
    },
    "longcat:LongCat-2.0-Preview": {
        "role_hint": Role.WORKER,
        "intell": 0.80,
        "ctx_k": 128,
        "latency_ms": 2400,
        "lane": "fallback",
    },
    # WORKER fast
    "groq:llama-3.3-70b-versatile": {
        "role_hint": Role.WORKER,
        "intell": 0.58,
        "ctx_k": 128,
        "latency_ms": 236,
        "lane": "fast",
    },
    # VERIFIER
    "nim/nvidia/nemotron-3-ultra-550b-a55b": {
        "role_hint": Role.VERIFIER,
        "intell": 0.45,
        "ctx_k": 1000,
        "latency_ms": 4500,
        "lane": "verifier",
    },
    "internai:intern-s2-preview": {
        "role_hint": Role.VERIFIER,
        "intell": 0.60,
        "ctx_k": 256,
        "latency_ms": 1500,
        "lane": "verifier",
    },
}


def pick_default_thinker() -> str:
    return "nim/z-ai/glm-5.1"


def pick_default_worker(task_hint: str = "") -> str:
    """Pick worker based on task hint keyword or default."""
    hint = task_hint.lower()
    if any(w in hint for w in ["code", "python", "javascript", "function", "implement"]):
        return "opencode/deepseek-v4-flash-free"
    if any(w in hint for w in ["quick", "fast", "simple"]):
        return "groq:llama-3.3-70b-versatile"
    if any(w in hint for w in ["long", "context", "large"]):
        return "ollama-cloud:minimax-m3"
    return "nim/z-ai/glm-5.1"


def pick_default_verifier() -> str:
    return "nim/nvidia/nemotron-3-ultra-550b-a55b"


# ── Decision policies ────────────────────────────────────────────────────


def should_terminate(history: List[TrinityDecision], max_steps: int) -> bool:
    """Trinity termination: τ = min{k ≤ K : V_k = ACCEPT}.

    Per paper, terminate when verifier returns ACCEPT or after K steps.
    """
    if not history:
        return False
    last = history[-1]
    if last.role == Role.VERIFIER and last.verdict == Verdict.ACCEPT:
        return True
    if last.role == Role.VERIFIER and last.verdict == Verdict.ABORT:
        return True
    if len(history) >= max_steps:
        return True
    return False


def decide_next_role(history: List[TrinityDecision]) -> Role:
    """Decide the next role based on Trinity cycle: T → W → V → W → V → ... → ACCEPT."""
    if not history:
        return Role.THINKER
    last = history[-1]
    if last.role == Role.THINKER:
        return Role.WORKER
    if last.role == Role.WORKER:
        return Role.VERIFIER
    if last.role == Role.VERIFIER:
        if last.verdict == Verdict.ACCEPT:
            return Role.WORKER  # shouldn't reach here (should terminate)
        if last.verdict == Verdict.ABORT:
            return Role.WORKER  # shouldn't reach here
        return Role.WORKER  # REVISE → loop back
    return Role.THINKER


def build_thinker_prompt(task_description: str, history: List[TrinityDecision]) -> str:
    """Build prompt for Thinker role — decompose task into subtask."""
    if not history:
        return (
            "You are the THINKER in a 3-role Trinity workflow.\n"
            "Your job: decompose the task into 1-5 concrete subtasks.\n"
            "For each subtask, specify: model_hint (nim/z-ai/glm-5.1, ollama-cloud:minimax-m3, "
            "opencode/deepseek-v4-flash-free, groq:llama-3.3-70b-versatile, "
            "longcat:LongCat-2.0-Preview, internai:intern-s2-preview), "
            "what the subtask does, what the Verifier should check.\n\n"
            f"Task: {task_description}\n\n"
            "Output as JSON list of subtasks."
        )
    # Revise based on verifier feedback
    last_verifier = next((d for d in reversed(history) if d.role == Role.VERIFIER), None)
    if last_verifier and last_verifier.verdict == Verdict.REVISE:
        return (
            "You are the THINKER. The Verifier requested revisions. "
            "Re-decompose the task with the verifier's feedback in mind.\n\n"
            f"Original task: {task_description}\n\n"
            f"Verifier feedback: {last_verifier.output[:1000]}\n\n"
            f"Previous attempts: {[d.output[:200] for d in history if d.role == Role.WORKER][-2:]}\n\n"
            "Output revised subtasks as JSON."
        )
    return f"Re-decompose: {task_description}"


def build_verifier_prompt(task_description: str, worker_output: str) -> str:
    """Build prompt for Verifier role — ACCEPT/REVISE on Worker output."""
    return (
        "You are the VERIFIER in a 3-role Trinity workflow.\n"
        "Review the Worker's output and return ACCEPT or REVISE.\n"
        "If REVISE, explain what is wrong and what needs to change.\n\n"
        f"Original task: {task_description}\n\n"
        f"Worker output:\n{worker_output[:2000]}\n\n"
        "Output JSON: {\"verdict\": \"ACCEPT\"|\"REVISE\"|\"ABORT\", "
        "\"confidence\": 0.0-1.0, \"reason\": \"...\"}"
    )


def parse_verifier_response(text: str) -> tuple:
    """Parse verifier response into (verdict, confidence, reason)."""
    try:
        data = json.loads(text)
        verdict = data.get("verdict", "REVISE")
        if verdict == "ACCEPT":
            return Verdict.ACCEPT, float(data.get("confidence", 0.5)), data.get("reason", "")
        elif verdict == "ABORT":
            return Verdict.ABORT, 1.0 - float(data.get("confidence", 0.5)), data.get("reason", "")
        else:
            return Verdict.REVISE, 1.0 - float(data.get("confidence", 0.5)), data.get("reason", "")
    except (json.JSONDecodeError, AttributeError):
        return Verdict.REVISE, 0.3, "Verifier output not parseable JSON"


# ── Main coordinator ─────────────────────────────────────────────────────


class TrinityCoordinator:
    """Rule-based Trinity coordinator. Lightweight, no SLM training needed.

    Usage:
        coord = TrinityCoordinator(model_router=persistent_router)
        workflow = coord.start_workflow(
            title="Test Trinity",
            description="...",
        )
        while not workflow.terminated:
            decision = coord.step(workflow)
            print(decision.to_dict())
    """

    def __init__(
        self,
        max_steps: int = 5,
        model_router: Optional[Any] = None,
        executor: Optional[Callable[[str, str], str]] = None,
    ):
        self.max_steps = max_steps
        self.model_router = model_router  # Optional PersistentRouter instance
        self.executor = executor or self._default_executor
        self.workflows: Dict[str, TrinityWorkflow] = {}

    def _default_executor(self, model: str, prompt: str) -> str:
        """Default executor — call the model via persistent_router if available,
        otherwise return a stub."""
        if self.model_router is not None and hasattr(self.model_router, "execute"):
            try:
                return self.model_router.execute(model=model, prompt=prompt)
            except Exception as e:
                return f"[stub] model={model} prompt_len={len(prompt)} error={e}"
        return f"[stub] model={model} prompt_len={len(prompt)}"

    def start_workflow(
        self,
        title: str,
        description: str,
        task_id: Optional[str] = None,
    ) -> TrinityWorkflow:
        """Start a new Trinity workflow."""
        wf = TrinityWorkflow(
            workflow_id=f"trinity-{uuid.uuid4().hex[:8]}",
            task_id=task_id or f"task-{uuid.uuid4().hex[:8]}",
            title=title,
            description=description,
            model_router=self.model_router,
        )
        self.workflows[wf.workflow_id] = wf
        return wf

    def step(self, workflow: TrinityWorkflow) -> TrinityDecision:
        """Execute one Trinity step. Returns the decision that was taken."""
        history = workflow.history
        role = decide_next_role(history)

        if role == Role.THINKER:
            return self._step_thinker(workflow)
        elif role == Role.WORKER:
            return self._step_worker(workflow)
        elif role == Role.VERIFIER:
            return self._step_verifier(workflow)
        else:
            raise ValueError(f"Unknown role: {role}")

    def run_to_completion(
        self,
        workflow: TrinityWorkflow,
    ) -> TrinityWorkflow:
        """Run steps until terminated or max_steps reached."""
        while not workflow.terminated:
            if should_terminate(workflow.history, self.max_steps):
                workflow.terminated = True
                break
            self.step(workflow)
        workflow.ended_at = datetime.now(timezone.utc).timestamp()
        if workflow.history:
            workflow.final_output = workflow.history[-1].output
            last_verifier = next(
                (d for d in reversed(workflow.history) if d.role == Role.VERIFIER),
                None,
            )
            if last_verifier:
                workflow.final_verdict = last_verifier.verdict
        return workflow

    # ── Step implementations ─────────────────────────────────────────

    def _step_thinker(self, workflow: TrinityWorkflow) -> TrinityDecision:
        prompt = build_thinker_prompt(workflow.description, workflow.history)
        model = pick_default_thinker()
        output = self.executor(model, prompt)
        decision = TrinityDecision(
            decision_id=f"d-{uuid.uuid4().hex[:8]}",
            role=Role.THINKER,
            model=model,
            prompt=prompt,
            output=output,
            confidence=1.0,
            next_role=Role.WORKER,
            next_model=pick_default_worker(workflow.description),
        )
        workflow.add_step(decision)
        return decision

    def _step_worker(self, workflow: TrinityWorkflow) -> TrinityDecision:
        # Get task context from latest thinker
        last_thinker = next(
            (d for d in reversed(workflow.history) if d.role == Role.THINKER),
            None,
        )
        if last_thinker is None:
            raise RuntimeError("Worker called without prior Thinker")
        model = pick_default_worker(workflow.description)
        prompt = (
            f"Execute the following task per the Thinker's plan.\n\n"
            f"Task: {workflow.description}\n\n"
            f"Thinker plan: {last_thinker.output[:1500]}\n\n"
            f"Worker output:"
        )
        output = self.executor(model, prompt)
        decision = TrinityDecision(
            decision_id=f"d-{uuid.uuid4().hex[:8]}",
            role=Role.WORKER,
            model=model,
            prompt=prompt,
            output=output,
            confidence=0.8,
            next_role=Role.VERIFIER,
            next_model=pick_default_verifier(),
        )
        workflow.add_step(decision)
        return decision

    def _step_verifier(self, workflow: TrinityWorkflow) -> TrinityDecision:
        last_worker = next(
            (d for d in reversed(workflow.history) if d.role == Role.WORKER),
            None,
        )
        if last_worker is None:
            raise RuntimeError("Verifier called without prior Worker")
        model = pick_default_verifier()
        prompt = build_verifier_prompt(workflow.description, last_worker.output)
        output = self.executor(model, prompt)
        verdict, confidence, reason = parse_verifier_response(output)
        decision = TrinityDecision(
            decision_id=f"d-{uuid.uuid4().hex[:8]}",
            role=Role.VERIFIER,
            model=model,
            prompt=prompt,
            output=output,
            verdict=verdict,
            confidence=confidence,
            metadata={"reason": reason},
            next_role=Role.WORKER if verdict == Verdict.REVISE else None,
        )
        workflow.add_step(decision)

        if verdict == Verdict.ACCEPT:
            workflow.terminated = True
            workflow.final_output = last_worker.output
            workflow.final_verdict = verdict
            workflow.ended_at = datetime.now(timezone.utc).timestamp()
        elif verdict == Verdict.ABORT:
            workflow.terminated = True
            workflow.final_verdict = verdict
            workflow.ended_at = datetime.now(timezone.utc).timestamp()
        # REVISE: loop back — next step will be WORKER (with Thinker revision)

        return decision


# ── Singleton + convenience ────────────────────────────────────────────


_COORDINATOR: Optional[TrinityCoordinator] = None


def get_trinity_coordinator(model_router: Optional[Any] = None) -> TrinityCoordinator:
    global _COORDINATOR
    if _COORDINATOR is None:
        _COORDINATOR = TrinityCoordinator(model_router=model_router)
    return _COORDINATOR


def run_trinity_workflow(
    title: str,
    description: str,
    max_steps: int = 5,
    executor: Optional[Callable[[str, str], str]] = None,
) -> TrinityWorkflow:
    """One-shot Trinity workflow execution. Returns the completed workflow."""
    coord = TrinityCoordinator(max_steps=max_steps, executor=executor)
    wf = coord.start_workflow(title=title, description=description)
    return coord.run_to_completion(wf)


if __name__ == "__main__":
    # Demo
    print("=== Trinity Workflow Demo ===\n")
    wf = run_trinity_workflow(
        title="Test Trinity 3-role coordination",
        description="Analyze the tradeoffs of using GLM 5.1 vs Nemotron Ultra for memory continuity",
        max_steps=5,
    )
    print(f"Workflow: {wf.workflow_id}")
    print(f"Steps: {wf.steps_count()}")
    print(f"Final verdict: {wf.final_verdict}")
    print(f"Final output length: {len(wf.final_output)} chars")
    print()
    for i, d in enumerate(wf.history, 1):
        print(f"Step {i}: {d.role.value} | {d.model} | verdict={d.verdict} | conf={d.confidence:.2f}")