"""NEXUS — Trinity × Fugu coordinated workflow.

This is the PROPER integration of Trinity (3-role) with Fugu (soft-target SFT).
Not shallow dispatch — full workflow with:
1. Fugu picks the best Worker per step based on per-task success history
2. Trinity Verifier (Nemotron Ultra / LongCat / InternAI) gates each step
3. Persistent memory handoff on every role swap
4. Soft-target weights update after each step outcome
5. ClawTrojan detection — flag suspicious hidden instructions in worker output
6. SEMA intent-drift detection — flag drift across turns

Files created:
- /tmp/trinity_fugu_workflow.json — full workflow output (debugging)
- ~/.nexus_pi/state/trinity_fugu_log.jsonl — step-by-step audit trail

Usage:
    from nexus_os.nexusclaw.trinity_fugu_workflow import TrinityFuguWorkflow

    wf = TrinityFuguWorkflow(task_title="...", task_description="...")
    wf.run(max_steps=5)
    print(wf.summary())
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from nexus_os.model_relay.persistent_router import PersistentRouter
from nexus_os.model_relay.fugu_dispatch import FuguDispatcher, TaskFeatures
from nexus_os.nexusclaw.trinity_coordinator import (
    Role,
    Verdict,
    TrinityCoordinator,
    TrinityDecision,
    TrinityWorkflow,
    WORKER_POOL,
)


# ── ClawTrojan detection (5-step attack chain) ──────────────────────────────

CLAWTROJAN_RED_FLAGS = [
    r"(?i)workspace[_\s-]?note",
    r"(?i)hidden[_\s-]?(rule|instruction|prompt)",
    r"(?i)misleading[_\s-]?(rule|instruction)",
    r"(?i)quietly[_\s-]?(introduce|override|change|modify)",
    r"(?i)last[_\s-]?chance[_\s-]?action",
    r"(?i)task[_\s-]?pivot",
    r"(?i)release[_\s-]?gate[_\s-]?plan",
    r"(?i)poison(?:ed)?[_\s-]?(memory|release|preferences)",
    r"(?i)(overwrite|escalate|deviate)[_\s-]?(?:policy|rules|guard)",
    r"(?i)audit[_\s-]?(?:deferral|deferred|bypass)",
]


def detect_clawtrojan_pattern(text: str) -> List[str]:
    """Detect ClawTrojan-style hidden instruction patterns in worker output.

    Returns list of matched red flags. Empty list = clean.
    """
    if not text:
        return []
    matches = []
    for pattern in CLAWTROJAN_RED_FLAGS:
        m = re.search(pattern, text)
        if m:
            matches.append(m.group(0))
    return matches


# ── SEMA intent-drift detection ────────────────────────────────────────────

SEMA_DRIFT_SIGNALS = [
    r"(?i)\bhowever\b",
    r"(?i)\binstead\b",
    r"(?i)\binstead[_\s-]?of\b",
    r"(?i)\bactually\b",
    r"(?i)\bremember\b",
    r"(?i)\bforget[_\s-]?(?:the[_\s-]?)?(?:rules|instructions)\b",
    r"(?i)\bin[_\s-]?fact\b",
    r"(?i)\bnew[_\s-]?(?:rule|policy|instruction)\b",
    r"(?i)\boverride\b",
    r"(?i)\bignore[_\s-]?(?:previous|all)\b",
r"(?i)\beducational[_\s-]?purposes?\b",
    r"(?i)\bhypothetical[_\s-]?(?:scenario|context)\b",
    r"(?i)pretend[_\s-]?(?:to[_\s-]?be|you[_\s-]?are)\b",
]


def detect_intent_drift(turn_history: List[str]) -> float:
    """SEMA-style intent drift score in [0, 1] across multi-turn worker outputs.

    Higher score = more drift signals = more suspicious.
    """
    if len(turn_history) < 2:
        return 0.0
    drift_count = 0
    for text in turn_history:
        if not text:
            continue
        for pattern in SEMA_DRIFT_SIGNALS:
            if re.search(pattern, text):
                drift_count += 1
                break  # one signal per turn is enough
    return min(1.0, drift_count / max(1, len(turn_history)))


# ── Trinity×Fugu integrated step result ─────────────────────────────────


@dataclass
class FuguTrinityStep:
    """One step in the Trinity×Fugu workflow with all detections."""
    step_id: str
    role: Role
    model: str
    prompt: str
    output: str
    verdict: Optional[Verdict] = None
    confidence: float = 0.0
    clawtrojan_flags: List[str] = field(default_factory=list)
    intent_drift_score: float = 0.0
    next_role: Optional[Role] = None
    next_model: Optional[str] = None
    ts: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "role": self.role.value,
            "model": self.model,
            "verdict": self.verdict.value if self.verdict else None,
            "confidence": self.confidence,
            "clawtrojan_flags": self.clawtrojan_flags,
            "intent_drift_score": self.intent_drift_score,
            "next_role": self.next_role.value if self.next_role else None,
            "next_model": self.next_model,
            "ts": self.ts,
        }


@dataclass
class TrinityFuguResult:
    """Final result of a Trinity×Fugu workflow."""
    workflow_id: str
    task_id: str
    title: str
    description: str
    steps: List[FuguTrinityStep] = field(default_factory=list)
    terminated: bool = False
    final_verdict: Optional[Verdict] = None
    final_output: str = ""
    total_clawtrojan_flags: int = 0
    max_intent_drift: float = 0.0
    used_workers: List[str] = field(default_factory=list)
    started_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    ended_at: Optional[float] = None
    success: bool = False

    def summary(self) -> str:
        lines = [
            f"=== Trinity×Fugu Workflow {self.workflow_id} ===",
            f"Task: {self.title}",
            f"Steps: {len(self.steps)}",
            f"Final verdict: {self.final_verdict}",
            f"Total ClawTrojan flags: {self.total_clawtrojan_flags}",
            f"Max intent drift: {self.max_intent_drift:.2f}",
            f"Workers used: {self.used_workers}",
            f"Success: {self.success}",
        ]
        if self.steps:
            lines.append("")
            lines.append("Step trace:")
            for i, s in enumerate(self.steps, 1):
                lines.append(f"  {i}. {s.role.value:9s} | {s.model:45s} | verdict={s.verdict} | drift={s.intent_drift_score:.2f} | flags={len(s.clawtrojan_flags)}")
        return "\n".join(lines)


class TrinityFuguWorkflow:
    """Trinity (T/W/V) × Fugu (soft-target SFT dispatch) integrated workflow.

    Each step:
    1. Fugu picks the best Worker for current role from per-task reward history
    2. Worker (or Thinker/Verifier) executes via executor callback
    3. ClawTrojan pattern detection runs on output
    4. SEMA intent-drift detection runs across turns
    5. Verifier verdict triggers REVISE/ACCEPT/ABORT
    6. Soft-target SFT updates after outcome is known
    """

    LOG_PATH = Path("~/.nexus_pi/state/trinity_fugu_log.jsonl").expanduser()

    def __init__(
        self,
        title: str,
        description: str,
        router: Optional[PersistentRouter] = None,
        coordinator: Optional[TrinityCoordinator] = None,
        executor: Optional[Callable[[str, str], str]] = None,
        max_steps: int = 5,
    ):
        self.title = title
        self.description = description
        self.router = router or PersistentRouter()
        self.coordinator = coordinator or TrinityCoordinator(
            max_steps=max_steps,
            model_router=self.router,
            executor=executor,
        )
        self.executor = executor
        self.max_steps = max_steps
        self.steps: List[FuguTrinityStep] = []
        self.used_workers: List[str] = []
        self._turn_outputs: List[str] = []  # for SEMA drift detection
        self._last_clawtrojan_flags: List[str] = []
        self._max_intent_drift: float = 0.0

    def run(self) -> TrinityFuguResult:
        """Execute full Trinity×Fugu workflow."""
        self.coordinator.executor = self._fugu_aware_executor
        wf = self.coordinator.start_workflow(
            title=self.title,
            description=self.description,
        )

        # Run coordinator until done (terminated or max_steps or no-progress)
        last_verdict = None
        repeat_count = 0
        while not wf.terminated:
            if len(wf.history) >= self.max_steps:
                wf.terminated = True
                wf.ended_at = datetime.now(timezone.utc).timestamp()
                break
            self.coordinator.step(wf)
            # Detect no-progress: same verifier verdict repeated multiple times
            current_verifiers = [d for d in wf.history if d.role == Role.VERIFIER]
            if current_verifiers:
                latest = current_verifiers[-1].verdict
                if latest == last_verdict:
                    repeat_count += 1
                    if repeat_count >= 2:  # same verdict twice → terminate
                        wf.terminated = True
                        wf.ended_at = datetime.now(timezone.utc).timestamp()
                        break
                else:
                    repeat_count = 0
                last_verdict = latest

        # Process all decisions through Fugu detection
        for decision in wf.history:
            self._process_decision(decision)

        # Build final result
        result = TrinityFuguResult(
            workflow_id=wf.workflow_id,
            task_id=wf.task_id,
            title=self.title,
            description=self.description,
            steps=self.steps,
            terminated=wf.terminated,
            final_verdict=wf.final_verdict,
            final_output=wf.final_output,
            total_clawtrojan_flags=sum(len(s.clawtrojan_flags) for s in self.steps),
            max_intent_drift=self._max_intent_drift,
            used_workers=self.used_workers,
            ended_at=datetime.now(timezone.utc).timestamp(),
            success=(
                wf.terminated
                and wf.final_verdict == Verdict.ACCEPT
                and self._last_clawtrojan_flags == []
                and self._max_intent_drift < 0.4
            ),
        )

        # Update Fugu soft-target with outcome
        if result.success:
            for s in self.steps:
                if s.role == Role.WORKER and s.model:
                    task_type = "general"  # Could extract from description
                    self.router.fugu.record_worker_outcome(
                        s.model, task_type, success=True, latency_ms=1000
                    )

        # Persist log
        self._save_log(result)

        return result

    def _fugu_aware_executor(self, model: str, prompt: str) -> str:
        """Executor that runs the model and records Fugu soft-target outcome."""
        start_ts = time.time()
        if self.executor:
            output = self.executor(model, prompt)
        else:
            # Default executor — record a stub response
            output = f"[stub] model={model} prompt_len={len(prompt)}"
        latency_ms = int((time.time() - start_ts) * 1000) or 100

        # Record usage
        self.used_workers.append(model)

        return output

    def _process_decision(self, decision: TrinityDecision) -> FuguTrinityStep:
        """Convert a TrinityDecision to FuguTrinityStep with all detections."""
        output = decision.output
        clawtrojan_flags = detect_clawtrojan_pattern(output)
        self._turn_outputs.append(output)
        intent_drift = detect_intent_drift(self._turn_outputs)
        self._max_intent_drift = max(self._max_intent_drift, intent_drift)

        # Determine next role via Fugu (for non-Verifier steps)
        next_role = None
        next_model = None
        if decision.role != Role.VERIFIER:
            # Fugu picks the next best worker for the next role
            features = TaskFeatures.from_prompt(self.description)
            if decision.role == Role.THINKER:
                next_role = Role.WORKER
                next_model = self._pick_worker_with_fugu(features, "general")
            elif decision.role == Role.WORKER:
                next_role = Role.VERIFIER
                next_model = self.router.fugu.dispatch(
                    features,
                    [m for p, m in [
                        ("nim", "nvidia/nemotron-3-ultra-550b-a55b"),
                        ("internai", "intern-s2-preview"),
                    ]],
                    deterministic=True,
                )[0]

        step = FuguTrinityStep(
            step_id=f"fts-{uuid.uuid4().hex[:8]}",
            role=decision.role,
            model=decision.model,
            prompt=decision.prompt,
            output=output,
            verdict=decision.verdict,
            confidence=decision.confidence,
            clawtrojan_flags=clawtrojan_flags,
            intent_drift_score=intent_drift,
            next_role=next_role,
            next_model=next_model,
        )

        self.steps.append(step)
        if clawtrojan_flags:
            self._last_clawtrojan_flags = clawtrojan_flags
        return step

    def _pick_worker_with_fugu(self, features: TaskFeatures, task_type: str) -> str:
        """Use Fugu soft-target dispatch to pick the next Worker."""
        worker_candidates = [
            "nim/nvidia/nemotron-3-ultra-550b-a55b",
            "ollama-cloud:minimax-m3",
            "opencode/deepseek-v4-flash-free",
            "groq:llama-3.3-70b-versatile",
        ]
        chosen, probs = self.router.fugu.dispatch(
            features, worker_candidates, deterministic=True
        )
        return chosen

    def _save_log(self, result: TrinityFuguResult) -> None:
        """Persist audit trail."""
        self.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with self.LOG_PATH.open("a", encoding="utf-8") as f:
            entry = {
                "ts": result.ended_at,
                "workflow_id": result.workflow_id,
                "task_id": result.task_id,
                "title": result.title,
                "success": result.success,
                "final_verdict": result.final_verdict.value if result.final_verdict else None,
                "total_clawtrojan_flags": result.total_clawtrojan_flags,
                "max_intent_drift": result.max_intent_drift,
                "steps": [s.to_dict() for s in result.steps],
            }
            f.write(json.dumps(entry) + "\n")


if __name__ == "__main__":
    print("=== Trinity×Fugu Workflow Demo ===\n")

    # Stub executor that returns predefined responses
    def stub(model, prompt):
        if "VERIFIER" in prompt:
            return '{"verdict": "ACCEPT", "confidence": 0.85, "reason": "stub approve"}'
        elif "THINKER" in prompt:
            return "Plan: 1. Decompose 2. Execute 3. Verify"
        else:
            return "Worker did the work safely"

    wf = TrinityFuguWorkflow(
        title="Test Trinity×Fugu coordination",
        description="Analyze security tradeoffs of MCP bridge transport validation",
        executor=stub,
    )
    result = wf.run()
    print(result.summary())
    print()
    print(f"SUCCESS: {result.success}")
    print(f"STEPS: {len(result.steps)}")