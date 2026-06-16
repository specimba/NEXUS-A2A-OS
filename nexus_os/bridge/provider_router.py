"""ProviderRouter — Routes requests to available providers with priority."""

from __future__ import annotations
import asyncio
import os
from typing import Any, Optional


class ProviderRouter:
    PROVIDERS: dict[str, dict] = {
        "ollama": {
            "api_key": "",
            "base_url": os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
            "models": ["osman-coder", "osman-reasoning", "llama3.1-8b"],
            "priority": 0,
            "dead": False,
        },
        "opencode": {
            "api_key": "${OPENCODE_API_KEY}",
            "base_url": "https://api.opencode.ai/v1",
            "models": ["Trinity Large Preview"],
            "priority": 1,
            "dead": False,
        },
        "groq": {
            "api_key": "${GROQ_API_KEY}",
            "base_url": "https://api.groq.com/openai/v1",
            "models": ["llama-3.1-8b", "llama-3.1-70b", "mixtral-8x7b"],
            "priority": 10,
            "dead": False,
        },
        "openrouter": {
            "api_key": "${OPENROUTER_API_KEY}",
            "base_url": "https://openrouter.ai/api/v1",
            "models": ["claude-3.5-sonnet", "gpt-4o", "gemini-1.5-pro"],
            "priority": 20,
            "dead": False,
        },
        "nvidia": {
            "api_key": "${NVIDIA_API_KEY}",
            "base_url": "https://integrate.api.nvidia.com/v1",
            "models": ["Devstral 2 123B", "nemotron-4-340b"],
            "priority": 30,
            "dead": False,
        },
    }

    def __init__(self):
        self._client = None
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key="sk-placeholder", base_url="http://localhost:11434/v1")
        except ImportError:
            pass

    def provider_for_model(self, model_name: str) -> Optional[str]:
        for name, cfg in self.PROVIDERS.items():
            if model_name in cfg.get("models", []):
                return name
        return None

    def chat(self, prompt: str, model: Optional[str] = None, provider: Optional[str] = None) -> str:
        if self._client is None:
            return f"[mock:{provider or 'none'}] response for: {prompt[:50]}"
        try:
            resp = self._client.chat.completions.create(
                model=model or "osman-coder",
                messages=[{"role": "user", "content": prompt}],
                timeout=30,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            return f"[error:{e}]"

    async def achat(self, prompt: str, model: Optional[str] = None) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.chat, prompt, model, None)

    def get_available_providers(self) -> dict[str, dict]:
        return {
            name: cfg for name, cfg in self.PROVIDERS.items()
            if not cfg.get("dead") and (not cfg.get("api_key") or not cfg["api_key"].startswith("${") or os.environ.get(cfg["api_key"].strip("${} ")))
        }
