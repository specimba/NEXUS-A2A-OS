"""Frontier mode — Deterministic mock providers for testing and sandbox."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FrontierProvider:
    name: str
    priority: int
    models: list[str] = field(default_factory=list)
    mock_latency_ms: float = 50.0
    mock_success_rate: float = 1.0


FRONTIER_PROVIDERS: list[FrontierProvider] = [
    FrontierProvider("ollama-mock", 0, ["osman-coder-mock", "osman-reasoning-mock"], 30.0, 1.0),
    FrontierProvider("opencode-mock", 1, ["Trinity Large Preview Mock"], 100.0, 0.95),
    FrontierProvider("groq-mock", 10, ["llama3-8b-mock", "llama3-70b-mock"], 80.0, 0.98),
    FrontierProvider("nvidia-mock", 20, ["Devstral Mock", "nemotron-mock"], 200.0, 0.90),
    FrontierProvider("openrouter-mock", 30, ["sonnet-mock", "gpt4o-mock"], 300.0, 0.85),
]


def get_frontier_providers() -> list[FrontierProvider]:
    return list(FRONTIER_PROVIDERS)


def get_frontier_provider(name: str) -> Optional[FrontierProvider]:
    for p in FRONTIER_PROVIDERS:
        if p.name == name:
            return p
    return None
