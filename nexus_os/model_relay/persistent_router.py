"""NEXUS Model Relay — Persistent Router.

Smart model selection with:
1. Persistent memory handoff (intro on pick-up, outro on swap)
2. Quota-aware rotation (use OpenCode/KiloCode first in day, save for later)
3. Model continuity preference (don't switch mid-task unless forced)
4. Verified active frontier providers rotate without suspended-model fallback
5. LongCat + InternAI as safe logging/memory fallbacks
6. OpenRouter FUSION as high-stakes task option

Usage:
    from nexus_os.model_relay.persistent_router import PersistentRouter

    router = PersistentRouter()
    model_id, provider, intro = router.pick_for_task(
        task_title="Analyze DeepSeek V4 Pro router behavior",
        task_description="...",
        tier="primary",  # primary | fallback | specialist | high_stakes
    )
    print(f"Using {model_id} via {provider}")
    print(intro)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from nexus_os.model_relay.persistent_memory import (
    MemoryBus,
    OutroBuilder,
    TaskIntroBuilder,
    get_memory_bus,
    start_task,
)
from nexus_os.model_relay.quota_tracker import KNOWN_QUOTAS, QuotaTracker
from nexus_os.model_relay.fugu_dispatch import FuguDispatcher, TaskFeatures

# ── Tier definitions ───────────────────────────────────────────────────────────

# Tier 1: PRIMARY ROTATION. Permanent NIM failures are excluded; transient
# availability is handled by the durable budget and provider health gates.
TIER_PRIMARY = {
    "name": "primary_rotation",
    "models": [
        ("baseten", "zai-org/GLM-5.2", "Baseten GLM 5.2 — reasoning opt-in, 131k ctx"),
        ("nim", "nvidia/nemotron-3-ultra-550b-a55b", "NVIDIA NIM Nemotron 3 Ultra — 550B MoE, 1M ctx"),
        ("nim", "minimaxai/minimax-m3", "NVIDIA NIM MiniMax M3 — active serial fallback"),
        ("nim", "qwen/qwen3.5-122b-a10b", "NVIDIA NIM Qwen3.5 122B — active serial fallback"),
    ],
    "rotation_strategy": "alternate_on_quota_or_rate_limit",
    "fallback_after_both_exhausted": "TIER_FALLBACK",
}

# Tier 2: SAFE FALLBACKS — used for logging/memory consistency
# LongCat and InternAI provide stable logging endpoints with consistent behavior
# These are NOT primary (less cutting-edge) but reliable for non-flashy work
TIER_FALLBACK = {
    "name": "safe_fallback",
    "models": [
        ("longcat", "LongCat-2.0", "LongCat — 1M context, 128K output, OpenAI+Anthropic compatible"),
        ("internai", "intern-s2-preview", "Intern AI — Shanghai Lab, 256K context, thinking_mode, OpenAI+Claude compatible"),
    ],
    "purpose": "logging + memory consistency (no random new models, no 0-cached entries)",
    "use_when": "logging critical events, memory writes, audit records, or quota exhausted",
}

# Tier 3: SPECIALIST — purpose-specific picks
TIER_SPECIALIST = {
    "name": "specialist",
    "models": [
        ("opencode", "deepseek-v4-flash-free", "DeepSeek V4 Flash free on OpenCode Zen — 85% intell, 1.4s"),
        ("opencode", "north-mini-code-free", "Code-specialist, 0.7s, OpenCode Zen"),
        ("kilocode", "nvidia/nemotron-3-super-120b-a12b:free", "Nemotron 3 Super 120B — emergency only"),
        ("ollama-cloud", "qwen3-coder:480b", "Qwen3 Coder 480B — code specialist"),
        ("ollama-cloud", "devstral-small-2:24b", "Devstral Small 24B — code agent"),
        ("baseten", "moonshotai/Kimi-K2.7-Code", "Baseten Kimi K2.7 Code — 262k ctx, tools/structured, $0.40/M input"),
    ],
    "purpose": "code, SWE-bench, agentic tasks",
}

# Tier 3.5: EVALUATION — benchmark comparison runs, model scoring
# LongCat and Baseten models used as judges/reviewers for NEXUS-Bench
# Track per-model token usage for quota management and feedback reporting
TIER_EVAL = {
    "name": "evaluation_pool",
    "models": [
        ("longcat", "LongCat-2.0", "LongCat — 560B MoE, 128K output, benchmark judge"),
        ("baseten", "zai-org/GLM-5.2", "Baseten GLM 5.2 — reasoning scorer, $1.50/M input"),
        ("baseten", "moonshotai/Kimi-K2.7-Code", "Baseten Kimi K2.7 Code — code+reasoning evaluator"),
    ],
    "purpose": "cross-model benchmark comparisons, teacher/eval/review, feedback generation",
    "use_when": "running NEXUS-Bench, scoring model outputs, generating usage reports",
}

# Tier 4: HIGH-STAKES — NEXUSCLAW, Brain, security probes
# OpenRouter FUSION can call multiple models in parallel + judge
TIER_HIGH_STAKES = {
    "name": "high_stakes_fusion",
    "models": [
        ("openrouter", "openrouter/fusion", "OpenRouter Fusion — multi-model + judge, 69% DRACO Fable 5+GPT-5.5"),
    ],
    "purpose": "NEXUSCLAW multi-step, Brain API proposals, security probes, anything where >70% accuracy matters",
}

# Daily quota priority — use these FIRST in the day
DAILY_QUOTA_PRIORITY = [
    "opencode:deepseek-v4-flash-free",
    "opencode:north-mini-code-free",
    "opencode:nemotron-3-ultra-free",
    "opencode:qwen3.6-plus-free",
    "opencode:mimo-v2.5-free",
    "opencode:nemotron-3-ultra-free",
    "kilocode:nvidia/nemotron-3-super-120b-a12b:free",
    "kilocode:kilo-auto/free",
    "kilocode:stepfun/step-3.7-flash:free",
    "kilocode:poolside/laguna-m.1:free",
]


@dataclass
class RouterDecision:
    provider: str
    model_id: str
    tier: str
    task_id: str
    intro_text: str
    reason: str
    rotation_alternative: Optional[Tuple[str, str]] = None
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None


class PersistentRouter:
    """Quota-aware, memory-persistent model router.

    Uses Fugu-style soft-target SFT for worker selection. Worker reward
    scores are tracked per task type, and dispatch uses
    softmax(reward / temperature) to pick a worker.
    """

    def __init__(self):
        self.bus = get_memory_bus()
        self.quota = QuotaTracker()
        self.fugu = FuguDispatcher()
        self._last_primary_used: Optional[str] = None
        self._recent_failures: Dict[str, List[float]] = {}
        self._FAILURE_WINDOW_SEC = 3600
        self._FAILURE_THRESHOLD = 3

    def _record_failure(self, provider: str, model: str) -> None:
        key = f"{provider}:{model}"
        now = time.time()
        self._recent_failures.setdefault(key, [])
        self._recent_failures[key].append(now)
        cutoff = now - self._FAILURE_WINDOW_SEC
        self._recent_failures[key] = [t for t in self._recent_failures[key] if t >= cutoff]

    def _is_degraded(self, provider: str, model: str) -> bool:
        key = f"{provider}:{model}"
        now = time.time()
        cutoff = now - self._FAILURE_WINDOW_SEC
        return sum(1 for t in self._recent_failures.get(key, []) if t >= cutoff) >= self._FAILURE_THRESHOLD

    def _recover_success(self, provider: str, model: str) -> None:
        key = f"{provider}:{model}"
        if key in self._recent_failures and self._recent_failures[key]:
            self._recent_failures[key].pop()

    def pick_for_task(
        self,
        task_title: str,
        task_description: str,
        tier: str = "primary",
        prefer_continuity: bool = True,
        use_fugu: bool = True,
    ) -> RouterDecision:
        """Pick a model for a new task. Creates persistent task context."""
        # Extract task features for Fugu routing
        task_features = TaskFeatures.from_prompt(task_description)

        # Create task + intro (use Fugu-selected model if enabled)
        model_provider, model_id, reason = self._select_from_tier(
            tier, task_features=task_features, use_fugu=use_fugu
        )
        task_id = start_task(
            title=task_title,
            description=task_description,
            model=model_id,
            provider=model_provider,
        )

        # Record quota call
        self.quota.record_call(model_provider, model_id)

        # Determine rotation alternative (use Fugu if enabled)
        tier_def = _tier_def(tier)
        alternative = None
        candidates = [f"{p}:{m}" for p, m, _ in tier_def["models"]]
        if use_fugu:
            # Use Fugu for alternative selection too — pick second-best
            chosen_key = f"{model_provider}:{model_id}"
            candidates_filtered = [c for c in candidates if c != chosen_key]
            if candidates_filtered:
                alt_provider, alt_model = self.fugu.dispatch(
                    task_features, candidates_filtered, deterministic=True
                )[0].split(":", 1)
                alternative = (alt_provider, alt_model)
        else:
            for p, m, _ in tier_def["models"]:
                if m != model_id:
                    alternative = (p, m)
                    break

        # Determine safe fallback
        fallback_p, fallback_m, _ = TIER_FALLBACK["models"][0]

        # Build intro
        task = self.bus.tasks[task_id]
        intro = TaskIntroBuilder.build(task)

        # Track last primary for continuity
        if tier == "primary":
            self._last_primary_used = f"{model_provider}:{model_id}"

        return RouterDecision(
            provider=model_provider,
            model_id=model_id,
            tier=tier,
            task_id=task_id,
            intro_text=intro,
            reason=reason,
            rotation_alternative=alternative,
            fallback_provider=fallback_p,
            fallback_model=fallback_m,
        )

    def record_outcome(
        self,
        worker: str,
        task_type: str,
        success: bool,
        latency_ms: int = 0,
    ) -> None:
        """Record worker outcome for Fugu soft-target training.

        Call this after each task completion to improve future routing.
        """
        if not success and ":" in worker:
            provider, model = worker.split(":", 1)
            self._record_failure(provider, model)
        else:
            if ":" in worker:
                provider, model = worker.split(":", 1)
                self._recover_success(provider, model)
        self.fugu.record_worker_outcome(worker, task_type, success, latency_ms)

    def continue_task(
        self, task_id: str, prefer_same: bool = True
    ) -> RouterDecision:
        """Continue an existing task. Prefer same model unless quota exhausted."""
        task = self.bus.tasks.get(task_id)
        if task is None:
            raise ValueError(f"Unknown task: {task_id}")

        current_model = task.working_model
        current_provider = task.working_provider

        if prefer_same and not self.quota.is_quota_exhausted(current_provider):
            self.quota.record_call(current_provider, current_model)
            intro = TaskIntroBuilder.build(task)
            return RouterDecision(
                provider=current_provider,
                model_id=current_model,
                tier="continuity",
                task_id=task_id,
                intro_text=intro,
                reason=f"Continuing on {current_provider}:{current_model} (quota available)",
            )

        # Need to rotate — pick from tier
        tier = self._infer_tier(current_model, current_provider)
        model_provider, model_id, reason = self._select_from_tier(tier, exclude=f"{current_provider}:{current_model}")
        note = self.bus.record_handoff(
            task_id=task_id,
            from_model=current_model,
            from_provider=current_provider,
            to_model=model_id,
            to_provider=model_provider,
            reason="quota_exhausted" if self.quota.is_quota_exhausted(current_provider) else "better_model",
        )
        outro = OutroBuilder.build(task, note)
        self.quota.record_call(model_provider, model_id)
        intro = TaskIntroBuilder.build(task)
        return RouterDecision(
            provider=model_provider,
            model_id=model_id,
            tier=tier,
            task_id=task_id,
            intro_text=intro,
            reason=reason,
        )

    def end_task(self, task_id: str, summary: str) -> str:
        """Write outro + mark complete."""
        from nexus_os.model_relay.persistent_memory import end_task as _end
        return _end(task_id, summary, completed=True)

    def get_daily_quota_strategy(self) -> str:
        """Return a recommendation: which provider to use first today."""
        lines = ["=== Daily Quota Strategy ==="]
        now_utc = time.gmtime()
        lines.append(f"Current UTC time: {now_utc.tm_hour:02d}:{now_utc.tm_min:02d}")
        lines.append(f"Time to UTC midnight reset: {self.quota.get_time_to_utc_reset()}")
        lines.append("")
        lines.append("Use these FIRST today (daily quota depletes):")
        for entry in DAILY_QUOTA_PRIORITY:
            provider = entry.split(":")[0]
            remaining = self.quota.get_remaining_for_today(provider)
            if remaining == 0:
                lines.append(f"  [EXHAUSTED] {entry}")
            elif remaining == -1:
                lines.append(f"  [UNLIMITED] {entry}")
            else:
                lines.append(f"  [{remaining:3d} left] {entry}")
        lines.append("")
        lines.append("Recommended order:")
        priority = self.quota.get_priority_order()
        for i, p in enumerate(priority, 1):
            rem = self.quota.get_remaining_for_today(p)
            marker = "EXHAUSTED" if rem == 0 else f"{rem} left"
            lines.append(f"  {i}. {p} ({marker})")
        return "\n".join(lines)

    def _select_from_tier(
        self, tier: str, exclude: Optional[str] = None,
        task_features: Optional[TaskFeatures] = None, use_fugu: bool = True,
    ) -> Tuple[str, str, str]:
        """Select a model from the named tier using Fugu soft-target SFT."""
        tier_def = _tier_def(tier)

        # Check OpenCode daily quota first (use early in day)
        if tier == "primary" and self.quota.should_use_opencode_first():
            # Even on primary, prefer OpenCode first call of day
            for entry in DAILY_QUOTA_PRIORITY:
                provider, model = entry.split(":", 1)
                if f"{provider}:{model}" == exclude:
                    continue
                if not self.quota.is_quota_exhausted(provider):
                    return provider, model, f"OpenCode daily quota fresh — using {provider}:{model} first today"

        # Get all candidates for this tier (excluding exclude + exhausted)
        all_candidates = [(p, m) for p, m, _ in tier_def["models"]]
        available = [
            (p, m) for p, m in all_candidates
            if f"{p}:{m}" != exclude and not self.quota.is_quota_exhausted(p)
        ]

        # Partition candidates: healthy first, then degraded.
        healthy = []
        degraded = []
        for provider, model in available:
            if self._is_degraded(provider, model):
                degraded.append((provider, model))
            else:
                healthy.append((provider, model))

        dispatch_pool = healthy or degraded
        if use_fugu and task_features is not None and dispatch_pool:
            candidate_keys = [f"{p}:{m}" for p, m in dispatch_pool]
            chosen_key, probs = self.fugu.dispatch(
                task_features, candidate_keys, deterministic=True
            )
            chosen_provider, chosen_model = chosen_key.split(":", 1)
            reason = next(
                (r for p, m, r in tier_def["models"] if p == chosen_provider and m == chosen_model),
                f"Fugu soft-target dispatch (chosen with prob={probs.get(chosen_key, 0):.3f})"
            )
            if healthy and (chosen_provider, chosen_model) not in healthy:
                reason += " [DEGRADED_CANDIDATE]"
            return chosen_provider, chosen_model, reason

        for provider, model, reason in tier_def["models"]:
            key = f"{provider}:{model}"
            if key == exclude:
                continue
            if self.quota.is_quota_exhausted(provider):
                continue
            if key in [f"{p}:{m}" for p, m in healthy]:
                return provider, model, reason
            if not healthy and key in [f"{p}:{m}" for p, m in degraded]:
                return provider, model, reason + " [DEGRADED_CANDIDATE]"

        if tier == "primary":
            for provider, model, reason in TIER_FALLBACK["models"]:
                key = f"{provider}:{model}"
                if key == exclude:
                    continue
                if self._is_degraded(provider, model):
                    continue
                if self.quota.is_quota_exhausted(provider):
                    continue
                return provider, model, f"Primary exhausted -> fallback {provider}:{model}"

        for fallback_provider, fallback_model, _ in TIER_FALLBACK["models"]:
            if f"{fallback_provider}:{fallback_model}" == exclude:
                continue
            if self.quota.is_quota_exhausted(fallback_provider):
                continue
            return fallback_provider, fallback_model, "Last-resort governed fallback"

        raise RuntimeError("No quota-eligible model is available for this tier")

    def _infer_tier(self, model: str, provider: str) -> str:
        for tier_name, tier_def in [
            ("primary", TIER_PRIMARY),
            ("specialist", TIER_SPECIALIST),
            ("high_stakes", TIER_HIGH_STAKES),
            ("fallback", TIER_FALLBACK),
        ]:
            for p, m, _ in tier_def["models"]:
                if m == model and p == provider:
                    return tier_name
        return "primary"


def _tier_def(tier: str) -> Dict[str, Any]:
    return {
        "primary": TIER_PRIMARY,
        "fallback": TIER_FALLBACK,
        "specialist": TIER_SPECIALIST,
        "high_stakes": TIER_HIGH_STAKES,
    }.get(tier, TIER_PRIMARY)


if __name__ == "__main__":
    router = PersistentRouter()
    print(router.get_daily_quota_strategy())
    print("\n" + "=" * 60 + "\n")
    decision = router.pick_for_task(
        task_title="Demonstrate persistent router",
        task_description="Build a memory-aware model router that swaps with intro/outro handoff.",
        tier="primary",
    )
    print(f"DECISION: provider={decision.provider} model={decision.model_id}")
    print(f"REASON: {decision.reason}")
    print(f"ROTATION ALT: {decision.rotation_alternative}")
    print(f"FALLBACK: {decision.fallback_provider}:{decision.fallback_model}")
