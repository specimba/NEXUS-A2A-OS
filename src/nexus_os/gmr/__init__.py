"""GMR — Genius Model Rotator Engine v3.0.

Dual-pool architecture for cost-optimized model routing.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time
import math
import logging

logger = logging.getLogger(__name__)

# ── Enums ─────────────────────────────────────────────────────

class ModelPool(Enum):
    FAST = "fast"       # Local, cheap, <500ms latency
    PREMIUM = "premium" # Cloud, capable, >500ms latency


class IntentCategory(Enum):
    CODE = "code"
    RESEARCH = "research"
    REASONING = "reasoning"
    SPEED = "speed"
    GENERAL = "general"
    SECURITY = "security"


# ── Data Classes ──────────────────────────────────────────────

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
    cost_per_million: float  # USD
    tier: int
    status: str  # "up", "degraded", "down", "local"
    max_context: int = 8192
    _failure_count: int = 0
    _circuit_open_until: Optional[float] = None
    
    def is_available(self) -> bool:
        """Check if model is available (status + circuit breaker)."""
        if self.status.lower() not in {"up", "local"}:
            return False
        if self._circuit_open_until and time.time() < self._circuit_open_until:
            return False
        return True
    
    def record_failure(self, window_seconds: int = 300):
        """Record failure for circuit breaker logic."""
        self._failure_count += 1
        if self._failure_count >= 3:
            self._circuit_open_until = time.time() + 60  # 60s cooldown
            logger.warning(f"Circuit opened for {self.name}")
    
    def reset_failure_count(self):
        """Reset failure count on success."""
        self._failure_count = 0
        self._circuit_open_until = None


@dataclass
class ModelSelection:
    """Result of model selection."""
    primary: str
    fallbacks: List[str]
    reason: str
    pool: ModelPool
    estimated_cost: float = 0.0


# ── Cost Estimation (FIXED: Use list of tuples, not range objects) ──

# FIXED: range objects are unhashable, use list of tuples
COST_TIERS = [
    (90, 15.0),   # Premium: tier >= 90
    (80, 10.0),   # High: tier >= 80
    (70, 5.0),    # Medium: tier >= 70
    (50, 2.0),    # Low: tier >= 50
    (0, 0.5),     # Budget: tier >= 0
]


def estimate_cost(model: ModelProfile, tokens: int) -> float:
    """Estimate cost for model usage.
    
    FIXED: Uses list of tuples instead of range objects.
    """
    if model.pool == ModelPool.FAST or model.provider == "ollama":
        return 0.0  # Local models are free
    
    for tier_min, cost_per_m in COST_TIERS:
        if model.tier >= tier_min:
            return (tokens / 1_000_000) * cost_per_m
    
    return 0.0


# ── Intent Classifier ─────────────────────────────────────────

class IntentClassifier:
    """Semantic intent classifier using keyword scoring."""
    
    # FIXED: Removed syntax error "an" instead of ","
    KEYWORDS = {
        IntentCategory.CODE: {
            "code", "function", "class", "debug", "fix", "implement",
            "api", "endpoint", "sql", "query", "refactor", "test",
            "deploy", "docker",
        },
        IntentCategory.RESEARCH: {
            "research", "analyze", "study", "paper", "source",
            "evidence", "cite", "literature", "review", "survey",
            "benchmark",
        },
        IntentCategory.REASONING: {
            "reasoning", "logic", "solve", "plan", "strategy",
            "optimize", "algorithm", "tradeoff", "decision", "why", "how",
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
        """Classify intent using keyword scoring."""
        text = prompt.lower()
        scores = {cat: 0 for cat in IntentCategory}
        
        for cat, keywords in cls.KEYWORDS.items():
            scores[cat] = sum(1 for kw in keywords if kw in text)
        
        # Metadata hints
        if metadata:
            if metadata.get("is_code_task"):
                scores[IntentCategory.CODE] += 5
            if metadata.get("requires_deep_reasoning"):
                scores[IntentCategory.REASONING] += 5
            if metadata.get("time_sensitive"):
                scores[IntentCategory.SPEED] += 3
        
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else IntentCategory.GENERAL


# ── GMR Engine ────────────────────────────────────────────────

class GMREngine:
    """Genius Model Rotator — V12 for AI, Zero Fuel.
    
    Features:
    - Dual-pool architecture (FAST/PREMIUM)
    - Circuit breaker for resilience
    - Budget-aware routing
    - Zero-context-loss fallback chains
    """
    
    # Pool selection rules
    POOL_RULES = {
        IntentCategory.SPEED: ModelPool.FAST,
        IntentCategory.CODE: ModelPool.FAST,
        IntentCategory.RESEARCH: ModelPool.PREMIUM,
        IntentCategory.REASONING: ModelPool.PREMIUM,
        IntentCategory.SECURITY: ModelPool.PREMIUM,
        IntentCategory.GENERAL: None,  # Auto-select by budget
    }
    
    def __init__(self):
        self.models: Dict[str, ModelProfile] = {}
        self._last_refresh: float = 0
        self._refresh_interval: int = 60
    
    def register_model(self, profile: ModelProfile):
        """Register a model for routing."""
        self.models[profile.name] = profile
        logger.info(f"Registered model: {profile.name} ({profile.pool.value})")
    
    def select(
        self,
        intent: IntentCategory,
        budget_remaining: int = 100000,
        max_latency_ms: int = 10000,
    ) -> ModelSelection:
        """Select best model for intent and budget.
        
        Args:
            intent: Task intent category
            budget_remaining: Token budget remaining
            max_latency_ms: Maximum acceptable latency
        
        Returns:
            ModelSelection with primary + fallback chain
        """
        # Determine pool based on budget
        target_pool = self.POOL_RULES.get(intent)
        if budget_remaining < 10000:
            target_pool = ModelPool.FAST  # Force local when budget low
        
        # Filter candidates
        candidates = []
        for model in self.models.values():
            if not model.is_available():
                continue
            if target_pool and model.pool != target_pool:
                continue
            if model.latency_ms > max_latency_ms:
                continue
            candidates.append(model)
        
        if not candidates:
            # Emergency: use any available local model
            local = [m for m in self.models.values() if m.pool == ModelPool.FAST]
            if local:
                return ModelSelection(
                    primary=local[0].name,
                    fallbacks=[m.name for m in local[1:4]],
                    reason="Emergency: No premium models available",
                    pool=ModelPool.FAST,
                )
            raise RuntimeError("No models available")
        
        # Sort by score (success_rate + latency)
        candidates.sort(
            key=lambda m: m.success_rate * 0.7 + (1000 / (m.latency_ms + 1)) * 0.3,
            reverse=True
        )
        
        # Build selection with fallbacks
        primary = candidates[0]
        fallbacks = [m.name for m in candidates[1:4]]
        
        return ModelSelection(
            primary=primary.name,
            fallbacks=fallbacks,
            reason=f"Top {primary.pool.value} model for {intent.value}",
            pool=primary.pool,
            estimated_cost=estimate_cost(primary, 1000),
        )
    
    def record_outcome(self, model_name: str, success: bool):
        """Record execution outcome for circuit breaker."""
        if model_name in self.models:
            if success:
                self.models[model_name].reset_failure_count()
            else:
                self.models[model_name].record_failure()
