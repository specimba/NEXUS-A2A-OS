"""NEXUS Model Relay — Persistent Memory Handoff System.

When NEXUS swaps models mid-task (e.g., GLM 5.1 → Nemotron Ultra due to rate limit
or quota exhaustion), the new model needs context about:
- What the task IS (intro)
- What's been DONE so far (state)
- Key DECISIONS made (memory)
- What's NEXT (outro/handoff)

This module provides:
1. TaskIntroBuilder — generates a structured intro for a new model when starting a task chunk
2. HandoffNote — captures state + decisions at task boundaries
3. OutroBuilder — generates the handoff summary so the next model can continue
4. MemoryBus — persistent JSON store at ~/.nexus_pi/state/model_memory.json

The system is designed to be:
- Compact (fits in any model context window)
- Deterministic (same inputs → same output)
- Provider-agnostic (works with GLM, Nemotron, DeepSeek, Claude, etc.)
- Persistent (survives model swaps and restarts)
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

MEMORY_BUS_PATH = Path("~/.nexus_pi/state/model_memory.json").expanduser()

MAX_INTRO_TOKENS = 1500  # ~6000 chars — fits comfortably in any model context
MAX_OUTRO_TOKENS = 1500


@dataclass
class TaskContext:
    """Persistent context for a single task or task chunk."""
    task_id: str
    title: str
    description: str
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    working_model: str = ""
    working_provider: str = ""
    files_involved: List[str] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    completed: bool = False
    parent_task_id: Optional[str] = None
    memory_summary: str = ""


@dataclass
class HandoffNote:
    """Snapshot of task state at a model swap boundary."""
    note_id: str
    task_id: str
    from_model: str
    from_provider: str
    to_model: str
    to_provider: str
    reason: str  # "rate_limit" | "quota_exhausted" | "better_model" | "user_request"
    ts: float = field(default_factory=time.time)
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    resume_instructions: str = ""


class MemoryBus:
    """Persistent memory store for model handoffs."""

    def __init__(self, path: Path = MEMORY_BUS_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.tasks: Dict[str, TaskContext] = {}
        self.handoffs: List[HandoffNote] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                for tid, td in data.get("tasks", {}).items():
                    self.tasks[tid] = TaskContext(**td)
                for hd in data.get("handoffs", []):
                    self.handoffs.append(HandoffNote(**hd))
            except Exception:
                pass

    def _save(self) -> None:
        data = {
            "tasks": {tid: asdict(t) for tid, t in self.tasks.items()},
            "handoffs": [asdict(h) for h in self.handoffs[-100:]],
        }
        self.path.write_text(json.dumps(data, indent=2))

    def create_task(
        self,
        title: str,
        description: str,
        working_model: str = "",
        working_provider: str = "",
        parent_task_id: Optional[str] = None,
    ) -> TaskContext:
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        ctx = TaskContext(
            task_id=task_id,
            title=title,
            description=description,
            working_model=working_model,
            working_provider=working_provider,
            parent_task_id=parent_task_id,
        )
        self.tasks[task_id] = ctx
        self._save()
        return ctx

    def update_task(
        self,
        task_id: str,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        add_file: Optional[str] = None,
        add_decision: Optional[Dict[str, Any]] = None,
        add_finding: Optional[str] = None,
        set_next_steps: Optional[List[str]] = None,
        mark_completed: Optional[bool] = None,
        set_summary: Optional[str] = None,
    ) -> None:
        ctx = self.tasks.get(task_id)
        if ctx is None:
            return
        if model:
            ctx.working_model = model
        if provider:
            ctx.working_provider = provider
        if add_file:
            ctx.files_involved.append(add_file)
        if add_decision:
            ctx.decisions.append(add_decision)
        if add_finding:
            ctx.findings.append(add_finding)
        if set_next_steps is not None:
            ctx.next_steps = set_next_steps
        if mark_completed is not None:
            ctx.completed = mark_completed
        if set_summary:
            ctx.memory_summary = set_summary
        ctx.updated_at = time.time()
        self._save()

    def record_handoff(
        self,
        task_id: str,
        from_model: str,
        from_provider: str,
        to_model: str,
        to_provider: str,
        reason: str,
        resume_instructions: str = "",
    ) -> HandoffNote:
        note = HandoffNote(
            note_id=f"handoff-{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            from_model=from_model,
            from_provider=from_provider,
            to_model=to_model,
            to_provider=to_provider,
            reason=reason,
            state_snapshot=asdict(self.tasks.get(task_id)) if task_id in self.tasks else {},
            resume_instructions=resume_instructions,
        )
        self.handoffs.append(note)
        ctx = self.tasks.get(task_id)
        if ctx:
            ctx.working_model = to_model
            ctx.working_provider = to_provider
            ctx.updated_at = time.time()
        self._save()
        return note


class TaskIntroBuilder:
    """Build a compact, deterministic task intro for any new model pickup."""

    @staticmethod
    def build(task: TaskContext, persistent_summary: str = "") -> str:
        lines = [
            f"# Task Intro: {task.title}",
            "",
            f"**Task ID**: `{task.task_id}`",
        ]
        if task.parent_task_id:
            lines.append(f"**Parent Task**: `{task.parent_task_id}`")
        lines += [
            f"**Started**: {datetime.fromtimestamp(task.started_at, tz=timezone.utc).isoformat()}",
            f"**Last Updated**: {datetime.fromtimestamp(task.updated_at, tz=timezone.utc).isoformat()}",
            f"**Active Model**: `{task.working_model}` ({task.working_provider})",
            "",
            "## Goal",
            task.description.strip(),
            "",
        ]

        if persistent_summary:
            lines += [
                "## Persistent Memory (carried across model handoffs)",
                persistent_summary.strip()[:3000],
                "",
            ]

        if task.findings:
            lines += ["## Findings So Far"]
            for f in task.findings[-10:]:
                lines.append(f"- {f}")
            lines.append("")

        if task.decisions:
            lines += ["## Decisions Made"]
            for d in task.decisions[-10:]:
                who = d.get("by_model", "?")
                what = d.get("decision", "")
                why = d.get("reason", "")
                lines.append(f"- **{who}**: {what}" + (f"  \n  _Reason: {why}_" if why else ""))
            lines.append("")

        if task.files_involved:
            lines += ["## Files Touched"]
            for f in task.files_involved[-15:]:
                lines.append(f"- `{f}`")
            lines.append("")

        if task.next_steps:
            lines += ["## Next Steps (planned)"]
            for i, s in enumerate(task.next_steps, 1):
                lines.append(f"{i}. {s}")
            lines.append("")

        lines += [
            "## Operating Constraints (NEXUS OS)",
            "- This is a governed session. Follow prior decisions unless they are provably wrong.",
            "- If you change a prior decision, record it in `findings` and explain why.",
            "- Persist critical context via MemoryBus before responding.",
            "- When done, call `mark_completed=True` and write an outro summary.",
        ]
        return "\n".join(lines)


class OutroBuilder:
    """Build the handoff outro — a compact summary the NEXT model reads first."""

    @staticmethod
    def build(task: TaskContext, handoff: Optional[HandoffNote] = None) -> str:
        lines = [
            f"# Task Outro (Handoff): {task.title}",
            "",
            f"**Task ID**: `{task.task_id}`",
        ]
        if handoff:
            lines += [
                f"**Handoff**: {handoff.from_model} ({handoff.from_provider}) → "
                f"{handoff.to_model} ({handoff.to_provider})",
                f"**Reason**: {handoff.reason}",
                "",
            ]
        lines += [
            "## What Was Done",
            task.memory_summary or "(no summary yet — please write one)",
            "",
        ]

        if task.findings:
            lines += ["## Top Findings"]
            for f in task.findings[-7:]:
                lines.append(f"- {f}")
            lines.append("")

        if task.decisions:
            lines += ["## Decisions Locked In"]
            for d in task.decisions[-7:]:
                who = d.get("by_model", "?")
                what = d.get("decision", "")
                lines.append(f"- **{who}**: {what}")
            lines.append("")

        if task.next_steps:
            lines += ["## Immediate Next Steps"]
            for i, s in enumerate(task.next_steps[:5], 1):
                lines.append(f"{i}. {s}")
            lines.append("")

        if task.files_involved:
            lines += ["## Files Recently Touched"]
            for f in task.files_involved[-10:]:
                lines.append(f"- `{f}`")
            lines.append("")

        if handoff and handoff.resume_instructions:
            lines += ["## Resume Instructions", handoff.resume_instructions, ""]

        lines += [
            "## How To Continue",
            "1. Read the **Goal** and **Findings** sections above.",
            "2. Open any **Files Touched** files to refresh context.",
            "3. Execute the **Immediate Next Steps** in order.",
            "4. After each significant change, call MemoryBus to persist progress.",
            "5. When done, write an outro summary and mark task completed.",
        ]
        return "\n".join(lines)


# ── Singleton + convenience helpers ────────────────────────────────────────────

_BUS: Optional[MemoryBus] = None


def get_memory_bus() -> MemoryBus:
    global _BUS
    if _BUS is None:
        _BUS = MemoryBus()
    return _BUS


def start_task(title: str, description: str, model: str = "", provider: str = "") -> str:
    """Create a new task and return the intro the model should read."""
    bus = get_memory_bus()
    task = bus.create_task(title, description, model, provider)
    intro = TaskIntroBuilder.build(task)
    intro_path = Path(f"~/.nexus_pi/state/intro_{task.task_id}.md").expanduser()
    intro_path.parent.mkdir(parents=True, exist_ok=True)
    intro_path.write_text(intro)
    return task.task_id


def record_progress(task_id: str, **kwargs: Any) -> None:
    """Convenience wrapper for update_task."""
    get_memory_bus().update_task(task_id, **kwargs)


def end_task(task_id: str, summary: str, completed: bool = True) -> str:
    """Write outro, mark completed, return outro text."""
    bus = get_memory_bus()
    bus.update_task(task_id, set_summary=summary, mark_completed=completed)
    task = bus.tasks[task_id]
    outro = OutroBuilder.build(task)
    outro_path = Path(f"~/.nexus_pi/state/outro_{task_id}.md").expanduser()
    outro_path.write_text(outro)
    return outro


def handoff_to(
    task_id: str,
    from_model: str,
    from_provider: str,
    to_model: str,
    to_provider: str,
    reason: str,
    resume_instructions: str = "",
) -> str:
    """Record model swap and return the outro for the new model to read."""
    bus = get_memory_bus()
    note = bus.record_handoff(
        task_id=task_id,
        from_model=from_model,
        from_provider=from_provider,
        to_model=to_model,
        to_provider=to_provider,
        reason=reason,
        resume_instructions=resume_instructions,
    )
    task = bus.tasks[task_id]
    outro = OutroBuilder.build(task, note)
    outro_path = Path(f"~/.nexus_pi/state/handoff_{note.note_id}.md").expanduser()
    outro_path.write_text(outro)
    return outro


if __name__ == "__main__":
    # Demo usage
    tid = start_task(
        title="Test Persistent Memory Demo",
        description="Demonstrate model handoff intro/outro system",
        model="nim/nvidia/nemotron-3-ultra-550b-a55b",
        provider="nvidia",
    )
    record_progress(tid, add_finding="Built MemoryBus singleton")
    record_progress(tid, add_decision={"by_model": "nim/nvidia/nemotron-3-ultra-550b-a55b", "decision": "Use persistent memory for context", "reason": "Avoid context loss on model swap"})
    record_progress(tid, set_next_steps=["Build quota tracker", "Wire into ModelRelay router"])
    print(f"Created task {tid}")
    print("---")
    print(end_task(tid, summary="Demo complete. MemoryBus + OutroBuilder verified."))
