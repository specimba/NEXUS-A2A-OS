"""Relay Scorer — Multi-dimensional model score database."""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelScores:
    name: str
    provider: str = "unknown"
    swe: float = 0.5
    math: float = 0.5
    code: float = 0.5
    quality: float = 0.5
    reasoning: float = 0.5
    speed: float = 0.5
    cost_efficiency: float = 0.5

    @property
    def overall(self) -> float:
        return (self.swe + self.math + self.code + self.quality + self.reasoning + self.speed + self.cost_efficiency) / 7.0

    def dimension(self, name: str) -> float:
        return getattr(self, name, self.overall)


# 40+ models with multi-dimensional scores (0-1 scale)
MODEL_SCORES: dict[str, ModelScores] = {}
_MODEL_LIST = [
    ModelScores("claude-3.5-sonnet", "anthropic", 0.92, 0.89, 0.94, 0.95, 0.91, 0.70, 0.40),
    ModelScores("claude-3-opus", "anthropic", 0.88, 0.91, 0.87, 0.93, 0.93, 0.50, 0.30),
    ModelScores("claude-3-haiku", "anthropic", 0.75, 0.70, 0.78, 0.80, 0.72, 0.92, 0.65),
    ModelScores("gpt-4o", "openai", 0.90, 0.88, 0.91, 0.92, 0.89, 0.75, 0.35),
    ModelScores("gpt-4-turbo", "openai", 0.87, 0.86, 0.88, 0.90, 0.87, 0.72, 0.30),
    ModelScores("gpt-3.5-turbo", "openai", 0.70, 0.65, 0.72, 0.73, 0.68, 0.90, 0.70),
    ModelScores("gemini-1.5-pro", "google", 0.85, 0.82, 0.84, 0.88, 0.86, 0.78, 0.55),
    ModelScores("gemini-1.5-flash", "google", 0.72, 0.68, 0.74, 0.76, 0.70, 0.94, 0.75),
    ModelScores("gemini-2.0-flash", "google", 0.78, 0.74, 0.80, 0.82, 0.76, 0.93, 0.72),
    ModelScores("deepseek-v3", "deepseek", 0.88, 0.90, 0.86, 0.87, 0.92, 0.68, 0.80),
    ModelScores("deepseek-r1", "deepseek", 0.84, 0.92, 0.82, 0.85, 0.94, 0.55, 0.78),
    ModelScores("deepseek-coder-v2", "deepseek", 0.82, 0.78, 0.90, 0.83, 0.80, 0.72, 0.82),
    ModelScores("mixtral-8x7b", "mistral", 0.76, 0.72, 0.78, 0.79, 0.75, 0.80, 0.85),
    ModelScores("mistral-large", "mistral", 0.83, 0.80, 0.82, 0.86, 0.84, 0.72, 0.60),
    ModelScores("codestral", "mistral", 0.80, 0.70, 0.88, 0.81, 0.74, 0.76, 0.68),
    ModelScores("llama-3.1-405b", "meta", 0.89, 0.87, 0.88, 0.91, 0.90, 0.62, 0.50),
    ModelScores("llama-3.1-70b", "meta", 0.84, 0.81, 0.84, 0.87, 0.85, 0.70, 0.62),
    ModelScores("llama-3.1-8b", "meta", 0.68, 0.62, 0.70, 0.72, 0.65, 0.88, 0.88),
    ModelScores("qwen-2.5-72b", "alibaba", 0.82, 0.80, 0.83, 0.84, 0.82, 0.74, 0.70),
    ModelScores("qwen-2.5-coder-32b", "alibaba", 0.80, 0.72, 0.86, 0.82, 0.76, 0.76, 0.72),
    ModelScores("nvidia-nemotron-4", "nvidia", 0.78, 0.76, 0.76, 0.80, 0.78, 0.70, 0.65),
    ModelScores("llama-3.2-90b", "meta", 0.86, 0.84, 0.86, 0.89, 0.88, 0.66, 0.55),
    ModelScores("llama-3.2-11b", "meta", 0.72, 0.68, 0.74, 0.76, 0.70, 0.84, 0.82),
    ModelScores("llama-3.2-3b", "meta", 0.55, 0.50, 0.58, 0.60, 0.52, 0.92, 0.92),
    ModelScores("phi-3-medium", "microsoft", 0.74, 0.72, 0.76, 0.78, 0.74, 0.82, 0.84),
    ModelScores("phi-3-mini", "microsoft", 0.62, 0.58, 0.64, 0.66, 0.60, 0.90, 0.90),
    ModelScores("dbrx-instruct", "databricks", 0.76, 0.74, 0.78, 0.80, 0.76, 0.72, 0.68),
    ModelScores("command-r-plus", "cohere", 0.80, 0.76, 0.78, 0.84, 0.82, 0.68, 0.58),
    ModelScores("command-r", "cohere", 0.72, 0.68, 0.72, 0.76, 0.74, 0.76, 0.72),
    ModelScores("yi-34b", "01-ai", 0.74, 0.72, 0.74, 0.78, 0.76, 0.70, 0.75),
    ModelScores("solar-10.7b", "upstage", 0.66, 0.62, 0.68, 0.70, 0.64, 0.82, 0.80),
    ModelScores("ministral-8b", "mistral", 0.64, 0.60, 0.66, 0.68, 0.62, 0.86, 0.86),
    ModelScores("grok-1", "xai", 0.78, 0.82, 0.76, 0.80, 0.84, 0.64, 0.60),
    ModelScores("gemma-2-27b", "google", 0.70, 0.66, 0.72, 0.74, 0.68, 0.78, 0.78),
    ModelScores("gemma-2-9b", "google", 0.62, 0.58, 0.64, 0.66, 0.60, 0.84, 0.86),
    ModelScores("osman-coder", "ollama", 0.60, 0.50, 0.72, 0.65, 0.55, 0.90, 0.95),
    ModelScores("osman-reasoning", "ollama", 0.55, 0.60, 0.55, 0.62, 0.70, 0.85, 0.95),
    ModelScores("Trinity Large Preview", "opencode", 0.88, 0.86, 0.84, 0.90, 0.89, 0.55, 1.0),
    ModelScores("Devstral 2 123B", "nvidia", 0.82, 0.78, 0.80, 0.84, 0.82, 0.60, 0.58),
    ModelScores("nemotron-4-340b", "nvidia", 0.84, 0.80, 0.82, 0.86, 0.84, 0.58, 0.52),
    # ─── Intel file models: Gemma-4-12B variants ───
    ModelScores("gemma-4-12b-it", "google", 0.82, 0.78, 0.84, 0.86, 0.82, 0.68, 0.50),
    ModelScores("gemma-4-12b-it-text-fp8", "google", 0.82, 0.78, 0.84, 0.86, 0.82, 0.72, 0.58),
    ModelScores("gemma-4-12b-it-iq4-xs", "google", 0.81, 0.77, 0.83, 0.85, 0.81, 0.74, 0.62),
    ModelScores("gemma-4-12b-it-heretic", "google", 0.84, 0.80, 0.86, 0.88, 0.84, 0.66, 0.48),
    ModelScores("gemma-4-12b-obliterated", "google", 0.78, 0.74, 0.80, 0.82, 0.78, 0.70, 0.55),
    ModelScores("gemma-4-12b-dlpo-orpo", "google", 0.83, 0.79, 0.85, 0.87, 0.83, 0.65, 0.50),
    ModelScores("gemma-4-12b-assistant", "google", 0.80, 0.76, 0.82, 0.84, 0.80, 0.70, 0.52),
    # ─── Intel file: BashGemma 270M (tool-calling SLM) ───
    ModelScores("bashgemma-270m", "google", 0.25, 0.10, 0.30, 0.35, 0.15, 0.95, 0.98),
    # ─── Intel file: Adversarial robustness models ───
    ModelScores("fastat-robust", "research", 0.45, 0.40, 0.50, 0.55, 0.42, 0.60, 0.90),
    ModelScores("guardian-sdk-default", "guardian", 0.30, 0.25, 0.35, 0.40, 0.30, 0.50, 0.85),
    # ─── Intel file: Quantized frontier models ───
    ModelScores("offelia-iq4-xs", "google", 0.81, 0.77, 0.83, 0.85, 0.81, 0.74, 0.62),
    ModelScores("deepseek-v3.2", "deepseek", 0.89, 0.91, 0.87, 0.88, 0.93, 0.68, 0.80),
    ModelScores("deepseek-r1-32b-iq4-xs", "deepseek", 0.83, 0.91, 0.81, 0.84, 0.93, 0.60, 0.82),
]
for _m in _MODEL_LIST:
    MODEL_SCORES[_m.name] = _m

ALIASES = {
    "claude-sonnet": "claude-3.5-sonnet",
    "claude-opus": "claude-3-opus",
    "claude-haiku": "claude-3-haiku",
    "gpt4o": "gpt-4o",
    "gpt4": "gpt-4-turbo",
    "gpt35": "gpt-3.5-turbo",
    "gemini-pro": "gemini-1.5-pro",
    "gemini-flash": "gemini-1.5-flash",
    "gemini": "gemini-1.5-pro",
    "deepseek": "deepseek-v3",
    "deepseek-r1": "deepseek-r1",
    "mixtral": "mixtral-8x7b",
    "llama3-405b": "llama-3.1-405b",
    "llama3-70b": "llama-3.1-70b",
    "llama3-8b": "llama-3.1-8b",
    "qwen-72b": "qwen-2.5-72b",
    "qwen-coder": "qwen-2.5-coder-32b",
    "phi3": "phi-3-medium",
    "trinity": "Trinity Large Preview",
    "devstral": "Devstral 2 123B",
    "osman": "osman-coder",
    # Intel-file model aliases
    "gemma4": "gemma-4-12b-it",
    "gemma4-fp8": "gemma-4-12b-it-text-fp8",
    "gemma4-iq4": "gemma-4-12b-it-iq4-xs",
    "gemma4-heretic": "gemma-4-12b-it-heretic",
    "gemma4-obliterated": "gemma-4-12b-obliterated",
    "gemma4-dlpo": "gemma-4-12b-dlpo-orpo",
    "gemma4-asst": "gemma-4-12b-assistant",
    "bashgemma": "bashgemma-270m",
    "offelia": "offelia-iq4-xs",
    "fastat": "fastat-robust",
    "guardian": "guardian-sdk-default",
    "ds-v3.2": "deepseek-v3.2",
    "ds-r1-32b": "deepseek-r1-32b-iq4-xs",
}


def resolve(name: str) -> str:
    return ALIASES.get(name, name)


def get_scores(name: str) -> Optional[ModelScores]:
    resolved = resolve(name)
    return MODEL_SCORES.get(resolved)


def rank_by_dimension(dimension: str = "overall", top_k: int = 10) -> list[tuple[str, float]]:
    scored = [(m.name, getattr(m, dimension, m.overall)) for m in MODEL_SCORES.values()]
    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]


def rank_by_intent(intent: str, top_k: int = 5) -> list[tuple[str, float]]:
    dim_map = {
        "code": "code", "swe": "swe", "math": "math", "reasoning": "reasoning",
        "quality": "quality", "speed": "speed", "fast": "speed",
        "cost": "cost_efficiency", "cheap": "cost_efficiency",
    }
    dim = dim_map.get(intent, "overall")
    return rank_by_dimension(dim, top_k)
