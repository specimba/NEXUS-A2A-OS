"""ProviderChainAdapter — Bridges ProviderRouter into ProviderChain for GMR."""

from __future__ import annotations
import os
from typing import Any, Callable, Optional
from nexus_os.bridge.provider_router import ProviderRouter


class ProviderChainAdapter:
    @staticmethod
    def build_profiles(router: ProviderRouter) -> list[dict]:
        profiles = []
        for name, cfg in router.PROVIDERS.items():
            if cfg.get("dead") is True:
                continue
            key_var = cfg.get("api_key", "").strip("${} ")
            if key_var and not os.environ.get(key_var):
                continue
            profiles.append({
                "name": name,
                "priority": cfg.get("priority", 50),
                "models": cfg.get("models", []),
                "api_key": cfg.get("api_key", ""),
                "base_url": cfg.get("base_url", ""),
            })
        profiles.sort(key=lambda p: p["priority"])
        return profiles

    @staticmethod
    def build_exec_fn(router: ProviderRouter) -> Callable:
        async def execute_fn(prompt: str, model: Optional[str] = None) -> dict:
            try:
                result = await router.achat(prompt, model=model)
                return {"success": True, "content": result, "tokens": 0}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return execute_fn

    @staticmethod
    def build(router: ProviderRouter) -> tuple[list[dict], Callable]:
        profiles = ProviderChainAdapter.build_profiles(router)
        execute_fn = ProviderChainAdapter.build_exec_fn(router)
        return profiles, execute_fn
