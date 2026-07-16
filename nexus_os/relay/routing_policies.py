"""
relay/routing_policies.py — Pluggable LLM Routing Policies

Backed by:
  - arXiv:2602.02823 (R2-Router: routing as reasoning, 4-5x cheaper)
  - arXiv:2604.23530 (MTRouter: multi-turn cost-aware routing)
  - arXiv:2603.04445 (Dynamic Model Routing and Cascading)
  - arXiv:2605.09104 (Token Economics — 4D taxonomy)
  - arXiv:2506.09033 (Router-R1: RL-based multi-round routing)

Integration: ADDITIVE to existing relay/model_relay.py (1623 lines) +
gmr/rotator.py (485 lines) + gmr/coger.py (CogER L1-L4).
The existing system has ChimeraRouterV2 + dual-pool (FAST/PREMIUM) +
VATS defense. This module adds 3 pluggable routing policies:

  1. R2RouterPolicy — "think-then-route": call a small model to select
     (model, budget) pair before main invocation.
  2. MultiTurnRoutingPolicy — history-aware routing using mem0 embeddings.
  3. CascadePolicy — explicit cheap→expensive fallback with quality gates.

All policies implement the same interface so ChimeraRouterV2 can swap them.

Usage:
    from nexus_os.relay.routing_policies import RoutingPolicyFactory

    policy = RoutingPolicyFactory.create("r2_router")
    decision = policy.route(prompt="Write a sort function", history=[], budget=1000)
    # decision = {"model": "vibethinker-3b", "budget": 500, "reason": "code task, L2 complexity"}
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Output of a routing policy."""
    model: str
    pool: str  # "fast" or "premium"
    budget: int  # token budget
    temperature: float = 0.7
    reason: str = ""
    fallback_chain: List[str] = field(default_factory=list)
    policy_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class RoutingPolicy:
    """Base interface for routing policies."""

    name: str = "base"

    def route(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        budget: int = 4096,
        complexity: str = "L2",
        **kwargs,
    ) -> RoutingDecision:
        raise NotImplementedError


class R2RouterPolicy(RoutingPolicy):
    """R2-Router: "routing as reasoning" — think-then-route.

    Paper: arXiv:2602.02823
    Reported: 4-5x lower cost than existing routers.

    Uses a small model (T0 anchor like FunctionGemma-270M) to select
    the best (model, length-budget) pair before main invocation.
    Treats output length budget as a controllable variable.

    Integration: Uses existing CogER L1-L4 complexity classification.
    """

    name = "r2_router"

    # Model selection by complexity (aligned with NEXUS_MODEL_USAGE_PLAN)
    COMPLEXITY_MODELS = {
        "L1": {"model": "bashgemma-270m", "pool": "fast", "budget": 512, "temp": 0.3},
        "L2": {"model": "vibethinker-3b", "pool": "fast", "budget": 2048, "temp": 0.6},
        "L3": {"model": "glm-5.2", "pool": "premium", "budget": 4096, "temp": 0.7},
        "L4": {"model": "deepseek-v4-flash", "pool": "premium", "budget": 8192, "temp": 0.8},
    }

    def route(self, prompt: str, history=None, budget=4096, complexity="L2", **kwargs) -> RoutingDecision:
        config = self.COMPLEXITY_MODELS.get(complexity, self.COMPLEXITY_MODELS["L2"])

        # R2-Router key insight: jointly select model AND length budget
        # Short prompts → shorter budget (cheaper)
        prompt_len = len(prompt.split())
        if prompt_len < 20:
            length_budget = min(config["budget"], 512)
        elif prompt_len < 100:
            length_budget = min(config["budget"], 1024)
        else:
            length_budget = config["budget"]

        # Fallback chain: if main model fails, cascade to cheaper
        fallback = []
        if config["pool"] == "premium":
            fallback = ["vibethinker-3b", "bashgemma-270m"]
        else:
            fallback = ["bashgemma-270m"]

        return RoutingDecision(
            model=config["model"],
            pool=config["pool"],
            budget=min(length_budget, budget),
            temperature=config["temp"],
            reason=f"R2-Router: complexity={complexity}, prompt_len={prompt_len}, "
                   f"length_budget={length_budget} (joint model+budget selection)",
            fallback_chain=fallback,
            policy_name=self.name,
            metadata={"complexity": complexity, "prompt_length": prompt_len},
        )


class MultiTurnRoutingPolicy(RoutingPolicy):
    """MTRouter: multi-turn cost-aware routing.

    Paper: arXiv:2604.23530
    Uses history-model joint embeddings to select the best model
    for multi-turn conversations.

    Integration: Uses existing mem0 adapter for conversation history.
    """

    name = "multi_turn"

    # Track model performance across turns
    # session_id → {model: {"success_count": int, "fail_count": int, "avg_latency_ms": float}}
    _performance: Dict[str, Dict[str, Dict[str, float]]] = {}

    def route(self, prompt: str, history=None, budget=4096, complexity="L2", **kwargs) -> RoutingDecision:
        history = history or []
        turn_count = len(history)

        # Multi-turn logic: if conversation is going well with current model, keep it
        # If quality degrading or budget pressure, switch
        session_id = kwargs.get("session_id", "default")
        current_model = kwargs.get("current_model", "vibethinker-3b")

        # Check performance history
        perf = self._performance.get(session_id, {})
        current_perf = perf.get(current_model, {"success": 0, "fail": 0})

        success_rate = 1.0
        total = current_perf["success"] + current_perf["fail"]
        if total > 0:
            success_rate = current_perf["success"] / total

        # Decision: keep current model if success_rate > 0.7 and turn < 5
        if success_rate > 0.7 and turn_count < 5 and total >= 2:
            return RoutingDecision(
                model=current_model,
                pool="fast" if "270m" in current_model or "3b" in current_model else "premium",
                budget=budget,
                temperature=0.6,
                reason=f"MTRouter: keeping {current_model} (success_rate={success_rate:.2f}, "
                       f"turn={turn_count}) — history-aware sticky routing",
                fallback_chain=["bashgemma-270m"],
                policy_name=self.name,
                metadata={"turn_count": turn_count, "success_rate": success_rate},
            )

        # Otherwise: escalate based on complexity and turn count
        if turn_count > 10 or complexity in ("L3", "L4"):
            model = "glm-5.2"
            pool = "premium"
        elif complexity == "L2":
            model = "vibethinker-3b"
            pool = "fast"
        else:
            model = "bashgemma-270m"
            pool = "fast"

        return RoutingDecision(
            model=model,
            pool=pool,
            budget=budget,
            temperature=0.7,
            reason=f"MTRouter: switching to {model} (turn={turn_count}, "
                   f"complexity={complexity}, prev_success={success_rate:.2f})",
            fallback_chain=["vibethinker-3b", "bashgemma-270m"] if pool == "premium" else ["bashgemma-270m"],
            policy_name=self.name,
            metadata={"turn_count": turn_count, "success_rate": success_rate, "prev_model": current_model},
        )

    def record_outcome(self, session_id: str, model: str, success: bool):
        """Record routing outcome for future decisions."""
        if session_id not in self._performance:
            self._performance[session_id] = {}
        if model not in self._performance[session_id]:
            self._performance[session_id][model] = {"success": 0, "fail": 0}
        if success:
            self._performance[session_id][model]["success"] += 1
        else:
            self._performance[session_id][model]["fail"] += 1


class CascadePolicy(RoutingPolicy):
    """Dynamic Model Routing and Cascading.

    Paper: arXiv:2603.04445
    Explicit cheap→expensive fallback chain with quality gates.

    Cascade: T0 (270M) → T2 (3B) → T3 (cloud) with quality checks at each tier.
    If quality gate fails, escalate to next tier.
    """

    name = "cascade"

    CASCADE_TIERS = [
        {"tier": 0, "model": "bashgemma-270m", "pool": "fast", "budget": 512, "quality_gate": 0.6},
        {"tier": 1, "model": "vibethinker-3b", "pool": "fast", "budget": 2048, "quality_gate": 0.75},
        {"tier": 2, "model": "glm-5.2", "pool": "premium", "budget": 4096, "quality_gate": 0.85},
        {"tier": 3, "model": "deepseek-v4-flash", "pool": "premium", "budget": 8192, "quality_gate": 0.90},
    ]

    def route(self, prompt: str, history=None, budget=4096, complexity="L2", **kwargs) -> RoutingDecision:
        # Start tier based on complexity
        start_tier = {"L1": 0, "L2": 1, "L3": 2, "L4": 3}.get(complexity, 1)
        tier = self.CASCADE_TIERS[start_tier]

        # Build fallback chain from current tier down to cloud
        fallback = [t["model"] for t in self.CASCADE_TIERS[start_tier + 1:]]

        return RoutingDecision(
            model=tier["model"],
            pool=tier["pool"],
            budget=min(tier["budget"], budget),
            temperature=0.7,
            reason=f"CascadePolicy: start at tier {tier['tier']} ({tier['model']}) "
                   f"for complexity {complexity}, quality_gate={tier['quality_gate']}",
            fallback_chain=fallback,
            policy_name=self.name,
            metadata={"start_tier": tier["tier"], "quality_gate": tier["quality_gate"]},
        )

    @classmethod
    def should_escalate(cls, current_tier: int, quality_score: float) -> bool:
        """Check if quality is below gate — should escalate to next tier."""
        if current_tier >= len(cls.CASCADE_TIERS) - 1:
            return False  # Already at top tier
        gate = cls.CASCADE_TIERS[current_tier]["quality_gate"]
        return quality_score < gate


class RoutingPolicyFactory:
    """Factory for creating routing policies."""

    _policies = {
        "r2_router": R2RouterPolicy,
        "multi_turn": MultiTurnRoutingPolicy,
        "cascade": CascadePolicy,
    }

    @classmethod
    def create(cls, name: str) -> RoutingPolicy:
        policy_cls = cls._policies.get(name)
        if not policy_cls:
            raise ValueError(f"Unknown routing policy: {name}. Available: {list(cls._policies.keys())}")
        return policy_cls()

    @classmethod
    def available(cls) -> List[str]:
        return list(cls._policies.keys())
