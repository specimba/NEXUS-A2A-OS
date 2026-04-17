"""GMR v3.0 — Genius Model Rotator (Dual-Pool, Zero-Context-Loss)"""
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from .context_packet import ContextPacket
from .domain_mapping import DOMAIN_MAPPING
from .savings import SavingsTracker
from .telemetry import TelemetryIngest, ModelTelemetry

logger = logging.getLogger("nexus.gmr.rotator")


class ModelPool(Enum):
    FAST = "fast"       # Local, cheap, <500ms latency
    PREMIUM = "premium"  # Cloud, capable, >500ms latency


class IntentCategory(Enum):
    CODE = "code"
    RESEARCH = "research"
    REASONING = "reasoning"
    SPEED = "speed"  # Maps to fast
    GENERAL = "general"
    SECURITY = "security"


@dataclass
class ModelProfile:
    """Live model telemetry + capability metadata."""
    name: str
    provider: str
    pool: ModelPool
    intent_categories: List[IntentCategory]
    latency_ms: int
    success_rate: float
    tokens_per_sec: float
    cost_per_million: float
    status: str
    max_context: int = 8192
    supports_tools: bool = False
    supports_vision: bool = False
    _failure_count: int = field(default=0, repr=False)
    _circuit_open_until: Optional[float] = field(default=None, repr=False)

    def is_available(self) -> bool:
        if self.status.lower() not in ("up", "local"):
            return False
        if self._circuit_open_until and time.time() < self._circuit_open_until:
            return False
        return True

    def record_failure(self):
        self._failure_count += 1
        if self._failure_count >= 3:
            self._circuit_open_until = time.time() + 60
            logger.warning(f"Circuit opened for {self.name}")

    def reset_failure_count(self):
        self._failure_count = 0
        self._circuit_open_until = None


class IntentClassifier:
    """Semantic intent classifier using keyword + heuristic scoring."""

    KEYWORDS = {
        IntentCategory.CODE: {
            "code", "function", "class", "debug", "fix", "implement",
            "api", "endpoint", "sql", "query", "refactor", "test",
            "deploy", "docker",
        },
        IntentCategory.RESEARCH: {
            "research", "analyze", "study", "paper", "source",
            "evidence", "cite", "literature", "review", "survey",
        },
        IntentCategory.REASONING: {
            "reasoning", "logic", "solve", "plan", "strategy",
            "optimize", "algorithm", "tradeoff", "decision",
        },
        IntentCategory.SPEED: {
            "quick", "fast", "summarize", "list", "extract",
            "format", "convert", "translate", "brief",
        },
        IntentCategory.SECURITY: {
            "security", "audit", "vulnerability", "auth", "encrypt",
            "permission", "compliance", "risk", "threat",
        },
    }

    @classmethod
    def classify(cls, prompt: str, metadata: Optional[Dict] = None) -> IntentCategory:
        text = prompt.lower()
        scores = {cat: 0 for cat in IntentCategory}
        for cat, keywords in cls.KEYWORDS.items():
            scores[cat] = sum(1 for kw in keywords if kw in text)
        if metadata:
            if metadata.get("is_code_task"):
                scores[IntentCategory.CODE] += 5
            if metadata.get("requires_deep_reasoning"):
                scores[IntentCategory.REASONING] += 5
            if metadata.get("time_sensitive"):
                scores[IntentCategory.SPEED] += 3
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else IntentCategory.GENERAL




# Compatibility alias for downstream consumers (Hermes, Coordinator)
@dataclass
class GMRSelection:
    """Result of model selection (compatibility alias)."""
    primary: str
    fallbacks: List[str]
    reason: str
    pool: ModelPool = ModelPool.FAST
    estimated_cost: float = 0.0
    estimated_latency_ms: int = 0


class CircuitBreaker:
    """Simple circuit breaker for model resilience."""
    def __init__(self):
        self._failures = {}
        self._cooldowns = {}
        
    def record_failure(self, model: str):
        self._failures[model] = self._failures.get(model, 0) + 1
        if self._failures[model] >= 3:
            self._cooldowns[model] = time.time() + 60
            logger.warning(f"Circuit opened for {model}")
            
    def should_open(self, model: str) -> bool:
        if model in self._cooldowns and time.time() < self._cooldowns[model]:
            return True
        return False
    
    def reset(self, model: str):
        self._failures[model] = 0
        self._cooldowns.pop(model, None)


@dataclass
class GMRSelection:
    """Selection result for GMR (legacy API compatibility)."""
    primary: str
    fallbacks: List[str]
    reason: str
    budget_remaining: int
    tier_used: int


class GeniusModelRotator:
    """GMR v3.0 - Production-grade model orchestrator.

    Features:
    - Dual-pool architecture (fast/premium)
    - Semantic intent classification
    - Zero-context-loss handoff with structured packets
    - Circuit breaker for resilience
    - Budget-aware dynamic re-ranking
    """

    WEIGHTS = {
        "success_rate": 0.10,
        "throughput": 0.05,
        "latency_inverse": 0.30,
        "cost_inverse": 0.25,
        "intent_match": 0.30,
    }

    POOL_RULES = {
        IntentCategory.SPEED: ModelPool.FAST,
        IntentCategory.CODE: ModelPool.FAST,
        IntentCategory.RESEARCH: ModelPool.PREMIUM,
        IntentCategory.REASONING: ModelPool.PREMIUM,
        IntentCategory.SECURITY: ModelPool.PREMIUM,
        IntentCategory.GENERAL: None,
    }

    def __init__(
        self,
        token_guard=None,
        relay_url: str = "http://localhost:7352",
        config: Optional[Dict] = None,
    ):
        self.token_guard = token_guard
        self.config = config or {}
        self.telemetry = TelemetryIngest(url=relay_url)
        self.savings = SavingsTracker()
        self.models: Dict[str, ModelProfile] = {}
        self._last_refresh: float = 0
        self._refresh_interval: int = self.config.get("refresh_interval_seconds", 300)
        # Initialize models from domain mapping
        self.register_from_mapping()
        logger.info("GMR v3.0 initialized (dual-pool, telemetry, savings)")

    def refresh_telemetry(self, force: bool = False) -> int:
        """Refresh from modelrelay."""
        now = time.time()
        if not force and now - self._last_refresh < self._refresh_interval:
            return len(self.models)
        self.telemetry.fetch()
        self._sync_profiles()
        self._last_refresh = now
        return len(self.models)

    def _sync_profiles(self):
        """Sync telemetry cache into ModelProfile objects."""
        for name, tel in self.telemetry.cache.items():
            if name in self.models:
                m = self.models[name]
                m.latency_ms = tel.latency_ms
                m.success_rate = tel.uptime_pct
                m.status = tel.status
                m.cost_per_million = float(tel.tier)

    def register_model(self, profile: ModelProfile):
        """Register a model for routing."""
        self.models[profile.name] = profile

    def select(self, task_type: str, budget_remaining: int = 100000, required_tier: Optional[int] = None) -> GMRSelection:
        """Legacy API: Select model using old-style interface."""
        intent_map = {
            "code": IntentCategory.CODE,
            "reasoning": IntentCategory.REASONING,
            "research": IntentCategory.RESEARCH,
            "fast": IntentCategory.SPEED,
            "general": IntentCategory.GENERAL,
            "security": IntentCategory.SECURITY,
        }
        intent = intent_map.get(task_type, IntentCategory.GENERAL)
        cascade, context = self.get_routing_cascade(
            prompt=f"task_type={task_type}",
            intent=intent,
            metadata={"is_code_task": task_type == "code"},
            task_id=f"select-{task_type}",
        )
        # Fallbacks from domain mapping
        fallback_list = DOMAIN_MAPPING.get(task_type, {}).get("fallback_chain", [])
        # Re-filter by required tier if specified
        if required_tier:
            filtered = [m for m in cascade if self.models.get(m, ModelProfile("", "", ModelPool.FAST, [], 0, 0, 0, 0, "")).cost_per_million >= required_tier]
            if filtered:
                cascade = filtered
        # Get tier from model
        primary_model = self.models.get(cascade[0]) if cascade else None
        tier_used = int(primary_model.cost_per_million * 10) if primary_model else 40
        return GMRSelection(
            primary=cascade[0] if cascade else "osman-coder",
            fallbacks=cascade[1:] if cascade else fallback_list[:3],
            reason=f"domain={task_type}, budget={budget_remaining}",
            budget_remaining=budget_remaining,
            tier_used=tier_used,
        )

    def register_from_mapping(self):
        """Register all models from DOMAIN_MAPPING."""
        pool_map = {"fast": ModelPool.FAST, "premium": ModelPool.PREMIUM, "local": ModelPool.FAST}
        # Map domain keys to IntentCategory
        intent_map = {
            "code": IntentCategory.CODE,
            "reasoning": IntentCategory.REASONING,
            "research": IntentCategory.RESEARCH,
            "fast": IntentCategory.SPEED,
            "general": IntentCategory.GENERAL,
            "security": IntentCategory.SECURITY,
        }
        for intent_val, data in DOMAIN_MAPPING.items():
            intent = intent_map.get(intent_val, IntentCategory.GENERAL)
            for spec in data.get("primary", []):
                name = spec["model"]
                cost = spec.get("cost_per_1m", 0)
                # Pool determination: local/free = FAST, paid = PREMIUM
                if cost == 0:
                    pool = ModelPool.FAST
                else:
                    pool = ModelPool.PREMIUM
                if name not in self.models:
                    self.register_model(ModelProfile(
                        name=name,
                        provider=spec.get("provider", "unknown"),
                        pool=pool,
                        intent_categories=[intent],
                        latency_ms=spec.get("latency_ms", 9999),
                        success_rate=1.0,
                        tokens_per_sec=0.0,
                        cost_per_million=float(cost),
                        status=spec.get("status", "up"),
                    ))
                else:
                    if intent not in self.models[name].intent_categories:
                        self.models[name].intent_categories.append(intent)

    def _calculate_model_score(self, model: ModelProfile, intent: IntentCategory) -> float:
        """Compute composite score for model selection."""
        # Base score from metrics
        score = (
            model.success_rate * self.WEIGHTS["success_rate"]
            + (model.tokens_per_sec / 100) * self.WEIGHTS["throughput"]
            + (1000 / (model.latency_ms + 1)) * self.WEIGHTS["latency_inverse"]
            + (1 / (model.cost_per_million + 0.01)) * self.WEIGHTS["cost_inverse"]
        )
        # Intent category matching bonus
        if intent in model.intent_categories:
            score += self.WEIGHTS["intent_match"]
        # Preferred pool bonus
        preferred_pool = self.POOL_RULES.get(intent)
        if preferred_pool and model.pool == preferred_pool:
            score *= 1.1
        return round(score, 4)

    def _select_pool(self, intent: IntentCategory, budget_remaining: int) -> ModelPool:
        """Select pool based on intent + budget constraints.
        
        Budget thresholds:
        - < 50k: FAST (local/free only)
        - 50k-200k: FAST or PREMIUM (intent-based)
        - > 200k: Any pool (prefer intent)
        """
        preferred = self.POOL_RULES.get(intent)
        if budget_remaining < 50000:
            return ModelPool.FAST
        # For higher budgets, return None to allow all pools
        return None

    def get_routing_cascade(
        self,
        prompt: str,
        intent: Optional[IntentCategory] = None,
        metadata: Optional[Dict] = None,
        max_tokens: int = 8000,
        task_id: Optional[str] = None,
    ) -> Tuple[List[str], ContextPacket]:
        """Get ordered cascade of models for zero-context-loss execution."""
        task_id = task_id or f"task-{int(time.time())}"

        if intent is None:
            intent = IntentClassifier.classify(prompt, metadata)

        self.refresh_telemetry()

        budget_remaining = (
            self.token_guard.get_remaining_budget("gmr")
            if self.token_guard and hasattr(self.token_guard, "get_remaining_budget")
            else 100000
        )
        target_pool = self._select_pool(intent, budget_remaining)

        candidates = []
        for model in self.models.values():
            if not model.is_available():
                continue
            # Pool filter: only apply if target_pool is specified
            if target_pool and model.pool != target_pool:
                continue
            score = self._calculate_model_score(model, intent)
            candidates.append((model, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        cascade = [m.name for m, _ in candidates[:3]]
        
        # Fallback: If cascade empty, use fallbacks from domain mapping
        if not cascade:
            domain_fallbacks = DOMAIN_MAPPING.get(intent.value, {}).get("fallback_chain", [])
            cascade = domain_fallbacks[:3] if domain_fallbacks else ["osman-coder"]
            logger.warning(f"No candidates for {intent.value}, using fallbacks: {cascade}")

        context = ContextPacket(
            task_id=task_id,
            original_prompt=prompt,
            intent=intent.value,
            budget_remaining=budget_remaining,
            core_facts=[],
            decisions_made=[],
            pending_actions=[],
            tool_state={},
            trace_id=f"trace-{task_id}",
        )

        if cascade:
            logger.info(f"GMR cascade: {cascade[0]} -> {cascade[1:]} (intent={intent.value})")

        return cascade, context

    def execute_with_fallback(
        self,
        prompt: str,
        execute_fn,
        intent: Optional[IntentCategory] = None,
        metadata: Optional[Dict] = None,
        max_tokens: int = 8000,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute prompt with automatic zero-context-loss fallback."""
        cascade, context = self.get_routing_cascade(
            prompt=prompt, intent=intent, metadata=metadata,
            max_tokens=max_tokens, task_id=task_id,
        )

        if not cascade:
            return {"success": False, "error": "No available models", "trace_id": context.trace_id}

        last_error = None
        for i, model_name in enumerate(cascade):
            context.handoff_count = i
            context.previous_models = cascade[:i]
            effective_prompt = (
                context.to_prompt_prefix() + "\n\n" + context.original_prompt
                if i > 0 else context.original_prompt
            )
            try:
                result = execute_fn(model_name, effective_prompt, context)
                if result.get("success"):
                    if model_name in self.models:
                        self.models[model_name].reset_failure_count()
                    tokens_used = result.get("tokens_used", 0)
                    if self.token_guard:
                        self.token_guard.track("gmr", tokens_used, {"model": model_name})
                    self.savings.record(
                        task_type=context.intent,
                        primary=cascade[0],
                        fallback=model_name if i > 0 else "",
                        tokens_used=tokens_used,
                        tokens_saved=0,
                        cost_saved=0.0,
                        reason=f"Completed on {model_name} (attempt {i+1})",
                    )
                    return {
                        "success": True,
                        "output": result["output"],
                        "model_used": model_name,
                        "fallback_count": i,
                        "tokens_used": tokens_used,
                        "trace_id": context.trace_id,
                    }
                else:
                    last_error = result.get("error", "Unknown error")
                    if model_name in self.models:
                        self.models[model_name].record_failure()
            except Exception as e:
                last_error = str(e)
                if model_name in self.models:
                    self.models[model_name].record_failure()

        return {
            "success": False,
            "error": f"All models failed: {last_error}",
            "fallback_count": len(cascade),
            "trace_id": context.trace_id,
        }
