"""Strict mode — Real provider profiles for production routing."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StrictProvider:
    name: str
    priority: int
    api_key_env: str
    base_url: str
    models: list[str] = field(default_factory=list)


STRICT_PROVIDERS: list[StrictProvider] = [
    StrictProvider("ollama", 0, "", "http://localhost:11434", ["osman-coder", "osman-reasoning", "llama3.1-8b"]),
    StrictProvider("opencode", 1, "OPENCODE_API_KEY", "https://api.opencode.ai/v1", ["Trinity Large Preview"]),
    StrictProvider("groq", 10, "GROQ_API_KEY", "https://api.groq.com/openai/v1", ["llama-3.1-8b", "llama-3.1-70b", "mixtral-8x7b"]),
    StrictProvider("openrouter", 20, "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", ["claude-3.5-sonnet", "gpt-4o", "gemini-1.5-pro"]),
    StrictProvider("nvidia", 30, "NVIDIA_API_KEY", "https://integrate.api.nvidia.com/v1", ["Devstral 2 123B", "nemotron-4-340b"]),
    StrictProvider("googleai", 40, "GOOGLEAI_API_KEY", "https://generativelanguage.googleapis.com/v1beta", ["gemini-1.5-pro", "gemini-1.5-flash"]),
    StrictProvider("cerebras", 50, "CEREBRAS_API_KEY", "https://api.cerebras.ai/v1", ["llama-3.1-8b"]),
    StrictProvider("mistral", 60, "MISTRAL_API_KEY", "https://api.mistral.ai/v1", ["mistral-large", "ministral-8b"]),
    StrictProvider("anthropic", 70, "ANTHROPIC_API_KEY", "https://api.anthropic.com/v1", ["claude-3.5-sonnet", "claude-3-haiku"]),
    StrictProvider("openai", 80, "OPENAI_API_KEY", "https://api.openai.com/v1", ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]),
    StrictProvider("deepseek", 90, "DEEPSEEK_API_KEY", "https://api.deepseek.com/v1", ["deepseek-v3", "deepseek-r1", "deepseek-coder-v2"]),
]


def get_strict_providers() -> list[StrictProvider]:
    return list(STRICT_PROVIDERS)


def get_strict_provider(name: str) -> Optional[StrictProvider]:
    for p in STRICT_PROVIDERS:
        if p.name == name:
            return p
    return None
