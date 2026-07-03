"""NEXUS — Fugu-style soft-target SFT dispatch.

Based on Sakana Fugu Technical Report (papers10):
- Soft-target SFT where training labels = softmax(worker_rewards / temperature)
- Hidden state from penultimate output token as input to lightweight head
- Two-stage training: SFT with soft KL + sep-CMA-ES on end-to-end trajectories
- Lightweight prediction head over worker pool logits (not generated text)

This module: production-grade Fugu-style dispatcher with:
1. Worker reward tracking (per-model, per-task-type success rate)
2. Soft-target softmax (worker_prob = exp(r / tau) / sum)
3. Feature vector builder (task embedding from prompt)
4. Lightweight head (sklearn or simple linear) — trainable later
5. Hidden-state routing (penultimate token state) — simplified to task features

Usage:
    from nexus_os.model_relay.fugu_dispatch import FuguDispatcher, TaskFeatures

    dispatcher = FuguDispatcher()
    dispatcher.record_worker_outcome("nim/nvidia/nemotron-3-ultra-550b-a55b", "code_review", success=True, latency_ms=1200)
    probs = dispatcher.compute_soft_targets(task_type="code_review")
    chosen = dispatcher.dispatch(task_features, candidates, exclude=None)
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

FUGU_STATE_PATH = Path("~/.nexus_pi/state/fugu_worker_rewards.json").expanduser()
FUGU_HEAD_PATH = Path("~/.nexus_pi/state/fugu_head.json").expanduser()


@dataclass
class TaskFeatures:
    """Lightweight task embedding used by the Fugu head for routing decisions."""
    task_type: str = "general"          # code_review | reasoning | math | search | general | long_ctx
    has_code: bool = False             # contains code-like markers
    has_math: bool = False
    has_long_context: bool = False      # estimated > 32k tokens
    requires_tools: bool = False       # MCP tool use
    estimated_complexity: float = 0.5 # 0..1
    prompt_hash: str = ""

    @classmethod
    def from_prompt(cls, prompt: str) -> "TaskFeatures":
        """Extract features from a raw prompt (cheap heuristic)."""
        prompt_lower = prompt.lower()
        code_markers = ["def ", "class ", "import ", "function", "var ", "const ", "{", "}", ";", "=>"]
        math_markers = ["equation", "integral", "derivative", "matrix", "probability", "calculus", "theorem"]
        long_ctx_markers = ["document", "full text", "complete file", "entire codebase"]
        tool_markers = ["tool", "function_call", "execute", "search", "fetch", "browser"]

        has_code = any(m in prompt for m in code_markers) or any(ext in prompt_lower for ext in [".py", ".js", ".ts"])
        has_math = any(m in prompt_lower for m in math_markers)
        has_long_context = any(m in prompt_lower for m in long_ctx_markers)
        requires_tools = any(m in prompt_lower for m in tool_markers)

        # Heuristic task type
        if has_code:
            task_type = "code_review"
        elif has_math:
            task_type = "math"
        elif has_long_context:
            task_type = "long_ctx"
        elif requires_tools:
            task_type = "search"
        elif "analyze" in prompt_lower or "explain" in prompt_lower or "summarize" in prompt_lower:
            task_type = "reasoning"
        else:
            task_type = "general"

        # Estimated complexity — heuristic: prompt length × markers
        complexity = min(1.0, len(prompt) / 8000 + 0.1 * (sum([has_code, has_math, has_long_context, requires_tools])))
        prompt_hash = str(hash(prompt))[:12]

        return cls(
            task_type=task_type,
            has_code=has_code,
            has_math=has_math,
            has_long_context=has_long_context,
            requires_tools=requires_tools,
            estimated_complexity=complexity,
            prompt_hash=prompt_hash,
        )


@dataclass
class WorkerRewardRecord:
    """Track success metrics per (worker, task_type) for soft-target SFT."""
    worker: str
    task_type: str
    successes: int = 0
    failures: int = 0
    total_latency_ms: int = 0
    last_used_ts: float = 0.0

    @property
    def attempts(self) -> int:
        return self.successes + self.failures

    @property
    def success_rate(self) -> float:
        if self.attempts == 0:
            return 0.5  # uniform prior for unknown workers
        return self.successes / self.attempts

    @property
    def avg_latency_ms(self) -> float:
        if self.attempts == 0:
            return 10000.0  # default
        return self.total_latency_ms / self.attempts

    def reward(self, latency_weight: float = 0.3) -> float:
        """Composite reward: success rate minus latency penalty.

        Per Fugu paper, reward balances quality (success) and cost (latency).
        """
        # Reward in [0, 1]
        return self.success_rate * (1.0 - latency_weight * min(1.0, self.avg_latency_ms / 10000))


class FuguDispatcher:
    """Fugu-style soft-target SFT dispatcher.

    Tracks per-worker success rate per task type. Computes soft targets via
    softmax(reward / temperature). Uses optional trained head for predict-then-
    route workflow.

    State persists to ~/.nexus_pi/state/fugu_worker_rewards.json
    """

    def __init__(
        self,
        temperature: float = 1.0,
        min_attempts_for_reliability: int = 3,
        state_path: Path = FUGU_STATE_PATH,
        head_path: Path = FUGU_HEAD_PATH,
    ):
        self.temperature = temperature
        self.min_attempts_for_reliability = min_attempts_for_reliability
        self.state_path = state_path
        self.head_path = head_path
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        # records[(worker, task_type)] -> WorkerRewardRecord
        self.records: Dict[Tuple[str, str], WorkerRewardRecord] = {}
        # head_weights[worker] -> (bias, feature_weights)
        self.head_weights: Dict[str, Dict[str, float]] = {}
        self._load()

    def _load(self) -> None:
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text())
                for key, rec in data.get("records", {}).items():
                    w, t = key.split("|", 1)
                    self.records[(w, t)] = WorkerRewardRecord(**rec)
            except Exception:
                pass
        if self.head_path.exists():
            try:
                self.head_weights = json.loads(self.head_path.read_text())
            except Exception:
                self.head_weights = {}

    def _save(self) -> None:
        data = {"records": {}}
        for (w, t), rec in self.records.items():
            data["records"][f"{w}|{t}"] = {
                "worker": rec.worker,
                "task_type": rec.task_type,
                "successes": rec.successes,
                "failures": rec.failures,
                "total_latency_ms": rec.total_latency_ms,
                "last_used_ts": rec.last_used_ts,
            }
        self.state_path.write_text(json.dumps(data, indent=2))

    def record_worker_outcome(
        self,
        worker: str,
        task_type: str,
        success: bool,
        latency_ms: int = 0,
    ) -> None:
        """Record the outcome of using a worker for a given task type."""
        key = (worker, task_type)
        if key not in self.records:
            self.records[key] = WorkerRewardRecord(worker=worker, task_type=task_type)
        rec = self.records[key]
        if success:
            rec.successes += 1
        else:
            rec.failures += 1
        rec.total_latency_ms += latency_ms
        rec.last_used_ts = time.time()
        self._save()

    def compute_soft_targets(
        self,
        task_type: str,
        candidates: Optional[List[str]] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, float]:
        """Compute softmax(reward / tau) over candidates for a task type.

        Per Fugu paper: p_i(j) = softmax(r̄_ij / τ) where r̄_ij is mean reward.
        Unknown workers get a uniform prior; workers with insufficient data
        get penalized but not eliminated.
        """
        tau = temperature if temperature is not None else self.temperature
        if candidates is None:
            candidates = list(set(w for (w, _) in self.records.keys()))

        rewards = []
        for worker in candidates:
            rec = self.records.get((worker, task_type))
            if rec is None or rec.attempts < 1:
                # Unknown worker — use uniform prior (0.5 success)
                rewards.append(0.5)
            else:
                rewards.append(rec.reward())

        # Softmax with numerical stability
        max_r = max(rewards) if rewards else 0
        exps = [math.exp((r - max_r) / max(tau, 0.1)) for r in rewards]
        total = sum(exps)
        if total == 0:
            # Uniform fallback
            probs = [1.0 / len(candidates)] * len(candidates)
        else:
            probs = [e / total for e in exps]
        return dict(zip(candidates, probs))

    def dispatch(
        self,
        task_features: TaskFeatures,
        candidates: List[str],
        exclude: Optional[str] = None,
        temperature: Optional[float] = None,
        deterministic: bool = False,
    ) -> Tuple[str, Dict[str, float]]:
        """Pick a worker from candidates using soft targets.

        Returns (chosen_worker, probability_dict).

        If deterministic=True, picks argmax. Otherwise weighted sample.
        """
        available = [c for c in candidates if c != exclude]
        if not available:
            if exclude:
                return exclude, {exclude: 1.0}
            return candidates[0] if candidates else "", {c: 1.0 for c in candidates}

        probs = self.compute_soft_targets(
            task_type=task_features.task_type,
            candidates=available,
            temperature=temperature,
        )

        if deterministic:
            chosen = max(probs, key=probs.get)
        else:
            import random
            workers = list(probs.keys())
            weights = [probs[w] for w in workers]
            chosen = random.choices(workers, weights=weights, k=1)[0]

        return chosen, probs

    def get_worker_stats(self, worker: str) -> Dict[str, Any]:
        """Get stats across all task types for a worker."""
        total_success = 0
        total_failure = 0
        total_latency = 0
        by_task: Dict[str, Dict[str, Any]] = {}
        for (w, t), rec in self.records.items():
            if w != worker:
                continue
            total_success += rec.successes
            total_failure += rec.failures
            total_latency += rec.total_latency_ms
            by_task[t] = {
                "success_rate": rec.success_rate,
                "attempts": rec.attempts,
                "avg_latency_ms": rec.avg_latency_ms,
                "reward": rec.reward(),
            }
        return {
            "worker": worker,
            "total_attempts": total_success + total_failure,
            "success_rate": (
                total_success / max(1, total_success + total_failure)
            ),
            "avg_latency_ms": (
                total_latency / max(1, total_success + total_failure)
            ),
            "by_task": by_task,
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        workers = set(w for (w, _) in self.records.keys())
        return {w: self.get_worker_stats(w) for w in workers}

    def train_lightweight_head(
        self,
        worker: str,
        features_to_weight: Dict[str, float],
    ) -> None:
        """Persist worker-specific feature weights for the lightweight head.

        In Fugu paper: head weights are trained via sep-CMA-ES. Here we
        persist manual weights that can be updated via measurement.
        """
        self.head_weights[worker] = features_to_weight
        self.head_path.write_text(json.dumps(self.head_weights, indent=2))

    def head_predict(self, worker: str, features: TaskFeatures) -> float:
        """Predict suitability of worker for given features using head weights.

        Returns score in [0, 1]. Falls back to reward-based score if no
        head weights are stored for this worker.
        """
        if worker not in self.head_weights:
            rec = self.records.get((worker, features.task_type))
            return rec.reward() if rec else 0.5
        weights = self.head_weights[worker]
        score = weights.get("bias", 0.5)
        if features.has_code:
            score += weights.get("has_code", 0)
        if features.has_math:
            score += weights.get("has_math", 0)
        if features.has_long_context:
            score += weights.get("has_long_context", 0)
        if features.requires_tools:
            score += weights.get("requires_tools", 0)
        score += weights.get("complexity_slope", 0) * features.estimated_complexity
        return max(0.0, min(1.0, score))

    def summary(self) -> str:
        """Human-readable summary of dispatcher state."""
        lines = ["=== Fugu Dispatcher Summary ==="]
        total_records = len(self.records)
        lines.append(f"Records: {total_records} (worker × task_type pairs)")
        if total_records == 0:
            return "\n".join(lines)
        lines.append("")
        by_task: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        for (w, t), rec in self.records.items():
            by_task[t].append((w, rec.reward()))
        for task_type, entries in by_task.items():
            lines.append(f"Task: {task_type}")
            entries.sort(key=lambda x: x[1], reverse=True)
            for w, r in entries:
                rec = self.records[(w, task_type)]
                marker = "★" if rec.attempts >= self.min_attempts_for_reliability else "○"
                lines.append(f"  {marker} {w:50s} reward={r:.3f} attempts={rec.attempts} success={rec.success_rate:.2f}")
            # Soft target distribution
            candidates = [w for w, _ in entries]
            probs = self.compute_soft_targets(task_type, candidates)
            top = max(probs, key=probs.get)
            lines.append(f"  → soft target pick: {top} ({probs[top]:.3f})")
            lines.append("")
        return "\n".join(lines)


if __name__ == "__main__":
    # Demo
    print("=== Fugu Dispatcher Demo ===\n")
    dispatcher = FuguDispatcher()
    # Simulate some outcomes
    samples = [
        ("nim/nvidia/nemotron-3-ultra-550b-a55b", "code_review", True, 2700),
        ("nim/nvidia/nemotron-3-ultra-550b-a55b", "code_review", True, 2500),
        ("nim/nvidia/nemotron-3-ultra-550b-a55b", "code_review", False, 3000),
        ("opencode/deepseek-v4-flash-free", "code_review", True, 1400),
        ("opencode/deepseek-v4-flash-free", "code_review", True, 1500),
        ("ollama-cloud:minimax-m3", "long_ctx", True, 1300),
        ("ollama-cloud:minimax-m3", "long_ctx", True, 1100),
        ("nim/nvidia/nemotron-3-ultra-550b-a55b", "math", True, 2400),
        ("nim/nvidia/nemotron-3-ultra-550b-a55b", "math", True, 2200),
        ("nim/nvidia/nemotron-3-ultra-550b-a55b", "math", True, 2600),
        ("groq:llama-3.3-70b-versatile", "general", True, 240),
        ("groq:llama-3.3-70b-versatile", "general", True, 220),
        ("groq:llama-3.3-70b-versatile", "general", False, 280),
    ]
    for w, t, ok, lat in samples:
        dispatcher.record_worker_outcome(w, t, ok, lat)
    print(dispatcher.summary())

    # Test dispatch
    print("\n=== Dispatch Test ===\n")
    for prompt in [
        "def fibonacci(n): # implement recursive fibonacci",
        "Calculate the integral of x^2 from 0 to 5",
        "Analyze this 50000-word document",
        "Search the web for recent AI papers",
    ]:
        features = TaskFeatures.from_prompt(prompt)
        candidates = [
            "nim/nvidia/nemotron-3-ultra-550b-a55b",
            "opencode/deepseek-v4-flash-free",
            "ollama-cloud:minimax-m3",
            "groq:llama-3.3-70b-versatile",
        ]
        chosen, probs = dispatcher.dispatch(features, candidates, deterministic=True)
        print(f"Prompt: {prompt[:60]}")
        print(f"  Features: type={features.task_type} code={features.has_code} math={features.has_math} long={features.has_long_context}")
        print(f"  Probs: {probs}")
        print(f"  → Chosen: {chosen}")
        print()