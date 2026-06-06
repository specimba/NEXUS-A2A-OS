"""DynamicRouter — Intent classification, cascade generation, and model scoring."""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from .config import PROVIDERS, ROUTING_STRATEGIES, INTENT_TO_DOMAIN, FALLBACK_CHAINS, DEFAULT_STRATEGY, LOGGER
from .provider_manager import ProviderManager, ProviderState
from .quota_guard import QuotaGuard
from .models_registry import ModelsRegistry, ModelInfo

class IntentCategory(Enum):
    CODE = "code"
    REASONING = "reasoning"
    RESEARCH = "research"
    SPEED = "speed"  # fast tasks
    GENERAL = "general"
    SECURITY = "security"

class RoutingStrategy(Enum):
    QUOTA_AWARE = "quota_aware"
    COST_OPTIMIZED = "cost_optimized"
    QUALITY_FIRST = "quality_first"
    LATENCY = "latency"

@dataclass
class RouteResult:
    """Result of a routing decision."""
    primary_model: str
    fallback_chain: List[str]
    provider: str
    intent: str
    strategy: str
    score: float
    estimated_latency_ms: int
    estimated_cost: float
    reasoning: str

@dataclass  
class RoutingCandidate:
    """A candidate model with scoring."""
    model_id: str
    provider: str
    score: float
    latency_ms: int
    cost: float
    tier: int
    is_free: bool
    is_local: bool

class IntentClassifier:
    """Semantic intent classifier using keyword + heuristic scoring."""

    KEYWORDS = {
        IntentCategory.CODE: {
            "code", "function", "class", "debug", "fix", "implement",
            "api", "endpoint", "sql", "query", "refactor", "test",
            "deploy", "docker", "git", "commit", "bug", "error",
            "python", "javascript", "typescript", "rust", "golang",
        },
        IntentCategory.REASONING: {
            "reasoning", "logic", "solve", "plan", "strategy",
            "optimize", "algorithm", "tradeoff", "decision",
            "analyze", "think", "explain", "reason",
        },
        IntentCategory.RESEARCH: {
            "research", "analyze", "study", "paper", "source",
            "evidence", "cite", "literature", "review", "survey",
            "find", "search", "investigate",
        },
        IntentCategory.SPEED: {
            "quick", "fast", "summarize", "list", "extract",
            "format", "convert", "translate", "brief",
            "short", "concise", "simple",
        },
        IntentCategory.SECURITY: {
            "security", "audit", "vulnerability", "auth", "encrypt",
            "permission", "compliance", "risk", "threat",
            "penetration", "exploit", "injection",
        },
    }

    @classmethod
    def classify(cls, prompt: str, metadata: Optional[Dict] = None) -> IntentCategory:
        """Classify intent from prompt text."""
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
            if metadata.get("is_security"):
                scores[IntentCategory.SECURITY] += 5
        
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else IntentCategory.GENERAL

class DynamicRouter:
    """Intelligent model router with multi-strategy support."""

    # Weights for scoring
    WEIGHTS = {
        "success_rate": 0.10,
        "throughput": 0.05,
        "latency_inverse": 0.30,
        "cost_inverse": 0.25,
        "intent_match": 0.30,
    }

    POOL_RULES = {
        IntentCategory.SPEED: "fast",
        IntentCategory.CODE: "fast",  # Local OK for simple code
        IntentCategory.REASONING: "premium",
        IntentCategory.RESEARCH: "premium",
        IntentCategory.SECURITY: "premium",
        IntentCategory.GENERAL: "all",
    }

    def __init__(
        self,
        provider_manager: ProviderManager,
        quota_guard: QuotaGuard,
        models_registry: Optional[ModelsRegistry] = None,
    ):
        self.provider_manager = provider_manager
        self.quota_guard = quota_guard
        self.models = models_registry or ModelsRegistry()

    def route(
        self,
        prompt: str,
        strategy: str = DEFAULT_STRATEGY,
        metadata: Optional[Dict] = None,
        required_capabilities: Optional[List[str]] = None,
        max_cost_per_request: Optional[float] = None,
    ) -> RouteResult:
        """Determine optimal model for request."""
        
        # 1. Classify intent
        intent = IntentClassifier.classify(prompt, metadata)
        
        # 2. Get strategy config
        strat_config = ROUTING_STRATEGIES.get(strategy, ROUTING_STRATEGIES["quota_aware"])
        
        # 3. Get candidates
        candidates = self._score_candidates(intent, strat_config, metadata, required_capabilities, max_cost_per_request)
        
        if not candidates:
            LOGGER.warning(f"[DynamicRouter] No candidates for intent={intent.value}")
            return self._fallback_result(intent, strategy)
        
        # 4. Select best
        best = candidates[0]
        
        # 5. Generate fallback chain
        fallback_chain = self._generate_fallback_chain(intent, best, candidates)
        
        # 6. Build reasoning
        reasoning = self._build_reasoning(intent, best, candidates, strategy)
        
        return RouteResult(
            primary_model=best.model_id,
            fallback_chain=fallback_chain,
            provider=best.provider,
            intent=intent.value,
            strategy=strategy,
            score=best.score,
            estimated_latency_ms=best.latency_ms,
            estimated_cost=best.cost,
            reasoning=reasoning,
        )

    def _score_candidates(
        self,
        intent: IntentCategory,
        strat_config: Dict,
        metadata: Optional[Dict],
        required_capabilities: Optional[List[str]],
        max_cost_per_request: Optional[float],
    ) -> List[RoutingCandidate]:
        """Score all available models."""
        
        pool_filter = strat_config.get("pool_filter", "all")
        candidates: List[RoutingCandidate] = []
        
        # Get available providers from quota guard
        available_providers = self.quota_guard.get_available_providers()
        if not available_providers:
            # Fall back to all providers if quota guard has no info
            available_providers = list(PROVIDERS.keys())
        
        for model in self.models.all():
            # Skip if provider not available
            if model.provider not in available_providers:
                continue
            
            # Pool filter
            if pool_filter == "free" and not model.is_free:
                continue
            if pool_filter == "local" and not model.is_local:
                continue
            
            # Skip if exhausted in quota guard
            quota = self.quota_guard.get_quota(model.provider)
            if quota and not quota.is_available():
                continue
            
            # Cost filter
            if max_cost_per_request and model.cost_per_1m_total > max_cost_per_request:
                continue
            
            # Capability filter
            if required_capabilities:
                if "vision" in required_capabilities and not model.supports_vision:
                    continue
                if "function_calling" in required_capabilities and not model.supports_function_calling:
                    continue
            
            # Get provider health
            health = self.provider_manager.get_health(model.provider)
            if health and not health.is_available():
                continue
            
            # Calculate score
            score = self._calculate_score(model, intent, health, strat_config)
            
            candidates.append(RoutingCandidate(
                model_id=model.model_id,
                provider=model.provider,
                score=score,
                latency_ms=health.latency_ms if health else model.latency_ms_typical,
                cost=model.cost_per_1m_total,
                tier=model.tier,
                is_free=model.is_free,
                is_local=model.is_local,
            ))
        
        # Sort by score descending
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates

    def _calculate_score(
        self,
        model: ModelInfo,
        intent: IntentCategory,
        health,
        strat_config: Dict,
    ) -> float:
        """Compute composite score for model selection."""
        
        # Base metric scores
        latency_inv = 1000 / (model.latency_ms_typical + 1)
        cost_inv = 1 / (model.cost_per_1m_total + 0.01) if model.cost_per_1m_total > 0 else 1000
        quality = model.quality_score
        
        # Weights from strategy
        w_latency = strat_config.get("latency_weight", 0.30)
        w_cost = strat_config.get("cost_weight", 0.25)
        w_quality = strat_config.get("quality_weight", 0.30)
        w_avail = strat_config.get("availability_weight", 0.20)
        
        # Base score
        score = (
            latency_inv * w_latency
            + cost_inv * w_cost
            + quality * w_quality
        )
        
        # Availability bonus/penalty
        if health:
            if health.state == ProviderState.UP:
                score *= 1.0
            elif health.state == ProviderState.DEGRADED:
                score *= 0.7
            else:
                score *= 0.0  # Down or cooldown
        
        # Intent category matching bonus
        if self._supports_intent(model, intent):
            score += w_avail
        
        # Free/local bonus (cost is already low, but add reliability bonus)
        if model.is_free:
            score *= 1.1
        if model.is_local:
            score *= 1.05
        
        # Pool preference bonus
        preferred_pool = self.POOL_RULES.get(intent)
        if preferred_pool == "fast" and model.is_local:
            score *= 1.15
        elif preferred_pool == "premium" and not model.is_local:
            score *= 1.1
        
        return round(score, 4)

    def _supports_intent(self, model: ModelInfo, intent: IntentCategory) -> bool:
        """Check if model supports intent category."""
        # Simple mapping: models with high tier support most intents
        # For code: prefer models with function calling
        # For reasoning: prefer higher tier
        if intent == IntentCategory.CODE:
            return model.supports_function_calling or model.tier >= 50
        elif intent == IntentCategory.REASONING:
            return model.tier >= 70
        elif intent == IntentCategory.SPEED:
            return model.is_local or model.latency_ms_typical < 200
        elif intent == IntentCategory.SECURITY:
            return model.tier >= 80
        else:
            return True  # General supports all

    def _generate_fallback_chain(
        self,
        intent: IntentCategory,
        primary: RoutingCandidate,
        candidates: List[RoutingCandidate],
    ) -> List[str]:
        """Generate ordered fallback chain."""
        
        chain = [primary.model_id]
        
        # Add from same provider family
        for c in candidates[1:]:
            if c.provider != primary.provider and c.model_id not in chain:
                chain.append(c.model_id)
                if len(chain) >= 3:
                    break
        
        # Fill from domain mapping fallback
        domain_fallbacks = FALLBACK_CHAINS.get(intent.value, [])
        for fallback_id in domain_fallbacks:
            if fallback_id not in chain:
                chain.append(fallback_id)
                if len(chain) >= 5:
                    break
        
        return chain[:5]  # Max 5 fallbacks

    def _fallback_result(self, intent: IntentCategory, strategy: str) -> RouteResult:
        """Return fallback when no candidates available."""
        fallback_list = FALLBACK_CHAINS.get(intent.value, ["osman-coder"])
        return RouteResult(
            primary_model=fallback_list[0],
            fallback_chain=fallback_list[1:],
            provider="fallback",
            intent=intent.value,
            strategy=strategy,
            score=0.0,
            estimated_latency_ms=999,
            estimated_cost=0.0,
            reasoning="No candidates available, using hard fallback",
        )

    def _build_reasoning(
        self,
        intent: IntentCategory,
        best: RoutingCandidate,
        candidates: List[RoutingCandidate],
        strategy: str,
    ) -> str:
        """Build human-readable reasoning for selection."""
        parts = [
            f"Intent: {intent.value}",
            f"Strategy: {strategy}",
            f"Selected: {best.model_id} (score={best.score})",
            f"Latency: ~{best.latency_ms}ms",
            f"Cost: ${best.cost:.4f}/1M tokens",
            f"Candidates considered: {len(candidates)}",
        ]
        if best.is_free:
            parts.append("Free tier")
        if best.is_local:
            parts.append("Local model")
        return " | ".join(parts)

    def get_routing_cascade(
        self,
        prompt: str,
        strategy: str = DEFAULT_STRATEGY,
        metadata: Optional[Dict] = None,
    ) -> Tuple[List[str], Dict]:
        """Get ordered cascade of models (legacy GMR compatibility)."""
        
        result = self.route(prompt, strategy, metadata)
        
        cascade = [result.primary_model] + result.fallback_chain
        
        context = {
            "intent": result.intent,
            "strategy": result.strategy,
            "score": result.score,
            "provider": result.provider,
            "reasoning": result.reasoning,
        }
        
        return cascade, context