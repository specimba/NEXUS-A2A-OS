"""GMR Router — Main orchestration for model selection.

Coordinates between:
- ModelRegistry (available models)
- GMREngine (selection logic)
- TokenGuard (budget enforcement)
- TrustScorer (trust scoring)
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from nexus_os.gmr import GMREngine, ModelProfile, ModelPool, IntentCategory, IntentClassifier
from nexus_os.gmr.registry import ModelRegistry
from nexus_os.monitoring.token_guard import TokenGuard
from nexus_os.monitoring.trust_scorer import TrustScorer

logger = logging.getLogger(__name__)


@dataclass
class RouteResult:
    """Result of model routing decision."""
    model_name: str
    provider: str
    pool: str
    reason: str
    trust_score: Optional[float]
    budget_remaining: int
    estimated_cost: float


class GMRRouter:
    """
    Main GMR Router that coordinates all components.
    
    Flow:
    1. Get available models from registry
    2. Check budget with TokenGuard
    3. Classify intent with GMREngine
    4. Select model with GMREngine
    5. Verify trust with TrustScorer
    6. Return RouteResult
    """
    
    # Default models for each pool
    DEFAULT_LOCAL_MODELS = {
        "osman-coder": {"provider": "ollama", "tier": 40, "latency_ms": 50},
        "osman-reason": {"provider": "ollama", "tier": 45, "latency_ms": 80},
        "qwen2.5-coder": {"provider": "ollama", "tier": 50, "latency_ms": 100},
    }
    
    DEFAULT_CLOUD_MODELS = {
        "gpt-4o": {"provider": "openai", "tier": 95, "latency_ms": 2500},
        "claude-3-5": {"provider": "anthropic", "tier": 92, "latency_ms": 3000},
        "gemini-pro": {"provider": "google", "tier": 90, "latency_ms": 2000},
    }
    
    def __init__(
        self,
        token_guard: Optional[TokenGuard] = None,
        trust_scorer: Optional[TrustScorer] = None,
    ):
        self.token_guard = token_guard or TokenGuard()
        self.trust_scorer = trust_scorer or TrustScorer()
        self.registry = ModelRegistry()
        self.engine = GMREngine()
        
        # Initialize with default models
        self._register_default_models()
    
    def _register_default_models(self):
        """Register default model profiles."""
        # Register local models
        for name, info in self.DEFAULT_LOCAL_MODELS.items():
            profile = ModelProfile(
                name=name,
                provider=info["provider"],
                pool=ModelPool.FAST,
                intent_categories=[
                    IntentCategory.CODE,
                    IntentCategory.SPEED,
                    IntentCategory.GENERAL,
                ],
                latency_ms=info["latency_ms"],
                success_rate=0.95,
                tokens_per_sec=50,
                cost_per_million=0.0,
                tier=info["tier"],
                status="local",
            )
            self.engine.register_model(profile)
        
        # Register cloud models
        for name, info in self.DEFAULT_CLOUD_MODELS.items():
            profile = ModelProfile(
                name=name,
                provider=info["provider"],
                pool=ModelPool.PREMIUM,
                intent_categories=[
                    IntentCategory.REASONING,
                    IntentCategory.RESEARCH,
                    IntentCategory.SECURITY,
                ],
                latency_ms=info["latency_ms"],
                success_rate=0.97,
                tokens_per_sec=30,
                cost_per_million=10.0,
                tier=info["tier"],
                status="up",
            )
            self.engine.register_model(profile)
    
    def route(
        self,
        prompt: str,
        agent_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RouteResult:
        """
        Route a prompt to the best model.
        
        Args:
            prompt: The user prompt/task description
            agent_id: Agent performing the task
            metadata: Additional context (is_code_task, etc.)
        
        Returns:
            RouteResult with selected model details
        """
        metadata = metadata or {}
        
        # 1. Check budget
        budget_remaining = self.token_guard.remaining(agent_id)
        if budget_remaining < 1000:
            logger.warning(f"GMRRouter: Agent {agent_id} budget low ({budget_remaining})")
        
        # 2. Classify intent
        intent = IntentClassifier.classify(prompt, metadata)
        logger.debug(f"GMRRouter: Intent classified as {intent.value}")
        
        # 3. Select model
        try:
            selection = self.engine.select(
                intent=intent,
                budget_remaining=budget_remaining,
                max_latency_ms=metadata.get("max_latency_ms", 10000),
            )
        except RuntimeError as e:
            logger.error(f"GMRRouter: No model available: {e}")
            return RouteResult(
                model_name="error",
                provider="none",
                pool="none",
                reason=str(e),
                trust_score=None,
                budget_remaining=budget_remaining,
                estimated_cost=0.0,
            )
        
        # 4. Get trust score (if trust scorer has hot path)
        trust_score = None
        if hasattr(self.trust_scorer, "get_score_hotpath"):
            Q = metadata.get("evidence_confidence", 0.7)
            n = metadata.get("evidence_count", 1)
            trust_score = self.trust_scorer.get_score_hotpath(
                agent_id=agent_id,
                Q=Q,
                n=n,
                lane=metadata.get("lane", "general"),
            )
        
        return RouteResult(
            model_name=selection.primary,
            provider=self.engine.models[selection.primary].provider,
            pool=selection.pool.value,
            reason=selection.reason,
            trust_score=trust_score,
            budget_remaining=budget_remaining,
            estimated_cost=selection.estimated_cost,
        )
    
    def record_outcome(self, model_name: str, success: bool):
        """Record execution outcome for circuit breaker."""
        self.engine.record_outcome(model_name, success)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get GMR router statistics."""
        return {
            "models_registered": len(self.engine.models),
            "local_models": sum(
                1 for m in self.engine.models.values()
                if m.pool == ModelPool.FAST
            ),
            "cloud_models": sum(
                1 for m in self.engine.models.values()
                if m.pool == ModelPool.PREMIUM
            ),
            "budget_categories": list(TokenGuard()._budgets.keys()) if hasattr(TokenGuard(), "_budgets") else [],
        }