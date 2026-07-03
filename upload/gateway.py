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
from nexus_os.model_relay.provider_budget import BudgetDenied, ProviderBudgetLedger

class ModelRelayGateway:
    """Main gateway coordinating all model relay components."""

    GOVERNED_PROVIDERS = {"longcat", "internai", "nvidia"}

    def __init__(self, budget_ledger: ProviderBudgetLedger | None = None):
        # Initialize components
        self.models_registry = ModelsRegistry()
        self.provider_manager = ProviderManager()
        self.budget_ledger = budget_ledger or ProviderBudgetLedger()
        self.quota_guard = QuotaGuard(budget_ledger=self.budget_ledger)
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
            "max_tokens": max_tokens,
            "temperature": temperature,
            "metadata": metadata or {},
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
        metadata = plan.get("metadata") or {}
        governed = provider in self.GOVERNED_PROVIDERS
        for i, model_name in enumerate([primary] + fallbacks):
            attempt_id = request_id if i == 0 else f"{request_id}-fallback-{i}"
            model_short = model_name.split("/")[-1]
            thinking_mode = provider == "internai" and model_short in {
                "intern-s2-preview", "intern-s1-pro", "intern-s1", "intern-s1-mini"
            }
            if governed:
                prompt_tokens = max(1, len(self._extract_prompt(messages).encode("utf-8")) // 4)
                estimate = prompt_tokens + int(plan.get("max_tokens", 4000))
                try:
                    self.budget_ledger.reserve(
                        attempt_id,
                        provider,
                        estimate,
                        probe=bool(metadata.get("quota_probe")),
                        corpus=bool(metadata.get("corpus_task")),
                        requested_model=model_name,
                        thinking_mode=thinking_mode,
                        emergency_override=bool(metadata.get("quota_emergency_override")),
                    )
                except BudgetDenied as exc:
                    last_error = str(exc)
                    break
            try:
                result = self._call_provider(model_name, provider, messages, plan, api_key=api_key)

                if result.get("success"):
                    usage = result.get("usage") or {}
                    try:
                        if governed:
                            self.budget_ledger.complete(
                                attempt_id,
                                input_tokens=usage.get("prompt_tokens"),
                                output_tokens=usage.get("completion_tokens"),
                                resolved_model=result.get("resolved_model", model_short),
                                provider_echo=result.get("provider_echo"),
                                fallback_reason="prior_attempt_failed" if i else None,
                                latency_ms=result.get("latency_ms"),
                            )
                    except BudgetDenied as exc:
                        last_error = str(exc)
                        self.provider_manager.record_failure(provider, last_error)
                        continue
                    self._stats["successful_requests"] += 1
                    self._stats["total_tokens"] += result.get("tokens_used", 0)
                    self._stats["total_cost"] += result.get("cost", 0)
                    if not governed:
                        self.quota_guard.record_request(provider, result.get("tokens_used", 0))

                    return {
                        "id": request_id,
                        "provider": provider,
                        "model": model_name,
                        "requested_model": model_name,
                        "resolved_model": result.get("resolved_model", model_short),
                        "provider_echo": result.get("provider_echo"),
                        "fallback_reason": "prior_attempt_failed" if i else None,
                        "thinking_mode": thinking_mode,
                        "output": result.get("output", ""),
                        "usage": usage,
                        "routing": {
                            "candidates": len(fallbacks) + 1,
                            "attempts": i + 1,
                            "latency_ms": result.get("latency_ms", 0),
                        },
                    }
                last_error = result.get("error", "Unknown error")
                if governed:
                    self.budget_ledger.fail(
                        attempt_id,
                        status_code=result.get("status_code"),
                        retry_after_seconds=result.get("retry_after_seconds"),
                        reason=last_error,
                    )
                self.provider_manager.record_failure(provider, last_error)

            except Exception as exc:
                last_error = str(exc)
                if governed:
                    self.budget_ledger.fail(attempt_id, reason=last_error)
                LOGGER.error(f"[ModelRelayGateway] Provider {model_name} failed: {exc}")
                self.provider_manager.record_failure(provider, str(exc))
        
        self._stats["failed_requests"] += 1
        
        return {
            "error": f"All models failed: {last_error}",
            "request_id": request_id,
            "attempts": len(fallbacks) + 1,
            "quota_status": "denied" if governed and last_error else "available",
        }

    def _call_provider(
        self,
        model_name: str,
        provider: str,
        messages: List[Dict],
        plan: Dict,
        api_key: Optional[str] = None,
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
        elif provider == "internai":
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            else:
                lane = plan.get("provider_lane")
                from upload.intern_ai_lanes import resolve_intern_ai_key
                resolved_key = resolve_intern_ai_key(lane)
                key_val = resolved_key.value or ""
                headers["Authorization"] = f"Bearer {key_val}"
        elif provider == "openmodel":
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            else:
                lane = plan.get("provider_lane")
                from upload.openmodel_lanes import resolve_openmodel_key
                resolved_key = resolve_openmodel_key(lane)
                key_val = resolved_key.value or ""
                headers["Authorization"] = f"Bearer {key_val}"
        elif provider == "sakana":
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            else:
                lane = plan.get("provider_lane")
                from upload.sakana_lanes import resolve_sakana_key
                resolved_key = resolve_sakana_key(lane)
                key_val = resolved_key.value or ""
                headers["Authorization"] = f"Bearer {key_val}"
        elif provider == "longcat":
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            else:
                lane = plan.get("provider_lane")
                from upload.longcat_lanes import resolve_longcat_key
                resolved_key = resolve_longcat_key(lane)
                key_val = resolved_key.value or ""
                headers["Authorization"] = f"Bearer {key_val}"
        
        # Build request
        url = f"{base_url}{chat_path}"
        body = {
            "model": model_name.split("/")[-1] if "/" in model_name else model_name,
            "messages": messages,
            "max_tokens": plan.get("max_tokens", 4000),
            "temperature": plan.get("temperature", 0.7),
        }
        
        if provider == "internai":
            model_short = model_name.split("/")[-1] if "/" in model_name else model_name
            from upload.intern_ai_lanes import THINKING_MODE_MODELS
            if model_short in THINKING_MODE_MODELS:
                body["thinking_mode"] = True
        
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
                    "status_code": 200,
                    "output": output,
                    "usage": usage,
                    "resolved_model": body["model"],
                    "provider_echo": data.get("model"),
                    "tokens_used": usage.get("total_tokens", 0),
                    "cost": self._estimate_cost(model_name, usage),
                    "latency_ms": latency_ms,
                    "raw": data,
                }
            else:
                error = f"HTTP {response.status_code}: {response.text[:200]}"
                result = {
                    "success": False,
                    "status_code": response.status_code,
                    "error": error,
                    "latency_ms": latency_ms,
                }
                if response.status_code == 429:
                    result["retry_after"] = response.headers.get("Retry-After")
                    try:
                        result["retry_after_seconds"] = float(result["retry_after"] or 0)
                    except (TypeError, ValueError):
                        result["retry_after_seconds"] = 0.0
                    result["quota_signal"] = "rate_limited"
                return result
                
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
            "openmodel": "NEXUS_OPENMODEL_API_KEY",
            "sakana": "NEXUS_SAKANA_API_KEY",
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
            "durable_provider_budgets": self.budget_ledger.all_status()["providers"],
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


