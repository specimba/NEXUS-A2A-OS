"""ModelRelay Gateway — Main relay service with zo.space API routes.

Integrates ProviderManager, QuotaGuard, DynamicRouter into a unified
OpenAI-compatible gateway with active monitoring and dynamic failover.
"""

import json
import time
import uuid
import logging
from typing import Dict, List, Optional, Any

from .config import PROVIDERS, DEFAULT_STRATEGY, LOGGER
from .provider_manager import ProviderManager, ProviderState
from .quota_guard import QuotaGuard
from .dynamic_router import DynamicRouter, IntentCategory, RoutingStrategy, RouteResult
from .models_registry import ModelsRegistry

class ModelRelayGateway:
    """Main gateway coordinating all model relay components."""

    def __init__(self):
        # Initialize components
        self.models_registry = ModelsRegistry()
        self.provider_manager = ProviderManager()
        self.quota_guard = QuotaGuard()
        self.router = DynamicRouter(
            provider_manager=self.provider_manager,
            quota_guard=self.quota_guard,
            models_registry=self.models_registry,
        )
        
        # Statistics
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "start_time": time.time(),
        }
        
        LOGGER.info("[ModelRelayGateway] Initialized with all components")

    def route_request(
        self,
        messages: List[Dict],
        strategy: str = DEFAULT_STRATEGY,
        model: str = "auto",
        max_tokens: int = 4000,
        temperature: float = 0.7,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Main routing method — select model and prepare execution plan."""
        
        self._stats["total_requests"] += 1
        
        # Build prompt from messages
        prompt = self._extract_prompt(messages)
        
        # Route to optimal model
        route_result = self.router.route(
            prompt=prompt,
            strategy=strategy,
            metadata=metadata,
        )
        
        # Prepare execution plan
        plan = {
            "request_id": f"relay-{uuid.uuid4().hex[:12]}",
            "primary_model": route_result.primary_model,
            "fallback_chain": route_result.fallback_chain,
            "provider": route_result.provider,
            "intent": route_result.intent,
            "strategy": route_result.strategy,
            "estimated_latency_ms": route_result.estimated_latency_ms,
            "estimated_cost": route_result.estimated_cost,
            "reasoning": route_result.reasoning,
            "timestamp": time.time(),
        }
        
        LOGGER.info(f"[ModelRelayGateway] Routed to {route_result.primary_model} (intent={route_result.intent})")
        
        return plan

    def execute_request(
        self,
        plan: Dict,
        messages: List[Dict],
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a routed request with fallback support."""
        
        request_id = plan["request_id"]
        primary = plan["primary_model"]
        fallbacks = plan["fallback_chain"]
        provider = plan["provider"]
        
        last_error = None
        for i, model_name in enumerate([primary] + fallbacks):
            try:
                result = self._call_provider(model_name, provider, messages, plan)
                
                if result.get("success"):
                    self._stats["successful_requests"] += 1
                    self._stats["total_tokens"] += result.get("tokens_used", 0)
                    self._stats["total_cost"] += result.get("cost", 0)
                    
                    # Record in quota guard
                    self.quota_guard.record_request(provider, result.get("tokens_used", 0))
                    
                    return {
                        "id": request_id,
                        "provider": provider,
                        "model": model_name,
                        "output": result.get("output", ""),
                        "usage": result.get("usage", {}),
                        "routing": {
                            "candidates": len(fallbacks) + 1,
                            "attempts": i + 1,
                            "latency_ms": result.get("latency_ms", 0),
                        },
                    }
                else:
                    last_error = result.get("error", "Unknown error")
                    self.provider_manager.record_failure(provider, last_error)
                    
            except Exception as e:
                last_error = str(e)
                LOGGER.error(f"[ModelRelayGateway] Provider {model_name} failed: {e}")
                self.provider_manager.record_failure(provider, str(e))
        
        self._stats["failed_requests"] += 1
        
        return {
            "error": f"All models failed: {last_error}",
            "request_id": request_id,
            "attempts": len(fallbacks) + 1,
        }

    def _call_provider(
        self,
        model_name: str,
        provider: str,
        messages: List[Dict],
        plan: Dict,
    ) -> Dict[str, Any]:
        """Make actual API call to provider."""
        
        start_time = time.time()
        
        # Map to actual provider config
        provider_config = PROVIDERS.get(provider, {})
        base_url = provider_config.get("base_url", "")
        chat_path = provider_config.get("chat_path", "/v1/chat/completions")
        
        # Handle different provider auth/styles
        headers = {
            "Content-Type": "application/json",
        }
        
        if provider == "openrouter":
            headers["Authorization"] = f"Bearer {api_key or self._get_key('openrouter')}"
        elif provider == "minimax":
            headers["Authorization"] = f"Bearer {api_key or self._get_key('minimax')}"
        elif provider == "groq":
            headers["Authorization"] = f"Bearer {api_key or self._get_key('groq')}"
        elif provider == "deepseek":
            headers["Authorization"] = f"Bearer {api_key or self._get_key('deepseek')}"
        
        # Build request
        url = f"{base_url}{chat_path}"
        body = {
            "model": model_name.split("/")[-1] if "/" in model_name else model_name,
            "messages": messages,
            "max_tokens": plan.get("max_tokens", 4000),
            "temperature": plan.get("temperature", 0.7),
        }
        
        try:
            import requests
            response = requests.post(
                url,
                headers=headers,
                json=body,
                timeout=60,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            self.provider_manager.record_success(provider, latency_ms)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract output
                output = ""
                if "choices" in data:
                    output = data["choices"][0].get("message", {}).get("content", "")
                
                # Extract usage
                usage = data.get("usage", {})
                
                return {
                    "success": True,
                    "output": output,
                    "usage": usage,
                    "tokens_used": usage.get("total_tokens", 0),
                    "cost": self._estimate_cost(model_name, usage),
                    "latency_ms": latency_ms,
                    "raw": data,
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "latency_ms": latency_ms,
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency_ms": int((time.time() - start_time) * 1000),
            }

    def _get_key(self, provider: str) -> str:
        """Get API key from environment."""
        import os
        key_map = {
            "openrouter": "OPENROUTER_API_KEY",
            "minimax": "MINIMAX_API_KEY",
            "groq": "GROQ_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
        }
        return os.environ.get(key_map.get(provider, ""), "")

    def _estimate_cost(self, model_name: str, usage: Dict) -> float:
        """Estimate cost based on token usage."""
        model = self.models_registry.get(model_name)
        if not model:
            return 0.0
        
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        cost = (
            input_tokens / 1_000_000 * model.cost_per_1m_input
            + output_tokens / 1_000_000 * model.cost_per_1m_output
        )
        return round(cost, 6)

    def _extract_prompt(self, messages: List[Dict]) -> str:
        """Extract prompt text from messages array."""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str):
                parts.append(f"{role}: {content}")
            else:
                parts.append(f"{role}: {str(content)}")
        return "\n".join(parts)

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive gateway status."""
        return {
            "providers": self.provider_manager.get_status_summary(),
            "quotas": self.quota_guard.get_status(),
            "statistics": {
                **self._stats,
                "uptime_seconds": int(time.time() - self._stats["start_time"]),
                "requests_per_minute": self._stats["total_requests"] / max(1, (time.time() - self._stats["start_time"]) / 60),
            },
            "active_strategy": DEFAULT_STRATEGY,
        }

    def get_providers(self) -> List[Dict]:
        """List all configured providers."""
        return [
            {
                "id": pid,
                "name": cfg["name"],
                "status": self.provider_manager.get_state(pid).value,
                "tier": cfg["tier"],
                "priority": cfg["priority"],
                "is_free": cfg["is_free"],
                "is_local": cfg["is_local"],
                "quota_type": cfg["quota_type"],
            }
            for pid, cfg in PROVIDERS.items()
        ]

    def health_check(self) -> Dict[str, Any]:
        """Gateway health check."""
        return {
            "status": "operational",
            "timestamp": time.time(),
            "components": {
                "provider_manager": "ok",
                "quota_guard": "ok",
                "router": "ok",
                "models_registry": f"{len(self.models_registry.all())} models",
            },
            "providers_available": len(self.provider_manager.get_available_providers()),
        }