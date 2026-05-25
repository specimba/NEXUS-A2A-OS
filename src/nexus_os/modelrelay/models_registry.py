"""ModelsRegistry — verified model capabilities and metadata."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ModelInfo:
    model_id: str
    provider: str
    name: str
    tier: int  # 0-100 quality score
    cost_per_1m_input: float
    cost_per_1m_output: float
    context_window: int = 32768
    latency_ms_typical: int = 300
    supports_vision: bool = False
    supports_function_calling: bool = False
    supports_streaming: bool = True
    is_free: bool = False
    is_local: bool = False
    quality_score: float = 50.0  # 0-100
    domains: List[str] = field(default_factory=lambda: ["general"])

    @property
    def cost_per_1m_total(self) -> float:
        return self.cost_per_1m_input + self.cost_per_1m_output


class ModelsRegistry:
    """Registry of all verified models across providers."""

    def __init__(self):
        self._models: List[ModelInfo] = []
        self._load_verified_models()

    def _load_verified_models(self):
        """Load only verified working models (tested 2026-05-24)."""

        # ── OpenRouter Free Tier (verified working) ──────────────────────
        self._models.extend([
            ModelInfo(
                model_id="openai/gpt-oss-120b:free",
                provider="openrouter",
                name="GPT-OSS 120B (free)",
                tier=78,
                cost_per_1m_input=0.0,
                cost_per_1m_output=0.0,
                context_window=131072,
                latency_ms_typical=250,
                supports_vision=False,
                supports_function_calling=True,
                supports_streaming=True,
                is_free=True,
                is_local=False,
                quality_score=82.0,
                domains=["code", "reasoning", "general"],
            ),
            ModelInfo(
                model_id="openai/gpt-oss-20b:free",
                provider="openrouter",
                name="GPT-OSS 20B (free)",
                tier=72,
                cost_per_1m_input=0.0,
                cost_per_1m_output=0.0,
                context_window=32768,
                latency_ms_typical=180,
                supports_vision=False,
                supports_function_calling=True,
                supports_streaming=True,
                is_free=True,
                is_local=False,
                quality_score=75.0,
                domains=["code", "general", "fast"],
            ),
            ModelInfo(
                model_id="arcee-ai/trinity-large-thinking:free",
                provider="openrouter",
                name="Trinity Large Thinking (free)",
                tier=80,
                cost_per_1m_input=0.0,
                cost_per_1m_output=0.0,
                context_window=65536,
                latency_ms_typical=300,
                supports_vision=False,
                supports_function_calling=True,
                supports_streaming=True,
                is_free=True,
                is_local=False,
                quality_score=84.0,
                domains=["reasoning", "research", "security"],
            ),
            ModelInfo(
                model_id="z-ai/glm-4.5-air:free",
                provider="openrouter",
                name="GLM-4.5 Air (free)",
                tier=76,
                cost_per_1m_input=0.0,
                cost_per_1m_output=0.0,
                context_window=131072,
                latency_ms_typical=200,
                supports_vision=False,
                supports_function_calling=True,
                supports_streaming=True,
                is_free=True,
                is_local=False,
                quality_score=78.0,
                domains=["general", "code", "fast"],
            ),
            ModelInfo(
                model_id="nvidia/nemotron-nano-9b-v2:free",
                provider="openrouter",
                name="Nemotron Nano 9B (free)",
                tier=65,
                cost_per_1m_input=0.0,
                cost_per_1m_output=0.0,
                context_window=32768,
                latency_ms_typical=120,
                supports_vision=False,
                supports_function_calling=True,
                supports_streaming=True,
                is_free=True,
                is_local=False,
                quality_score=68.0,
                domains=["fast", "general"],
            ),
        ])

    def all(self) -> List[ModelInfo]:
        return list(self._models)

    def by_provider(self, provider: str) -> List[ModelInfo]:
        return [m for m in self._models if m.provider == provider]

    def by_domain(self, domain: str) -> List[ModelInfo]:
        return [m for m in self._models if domain in m.domains]

    def free_only(self) -> List[ModelInfo]:
        return [m for m in self._models if m.is_free]

    def get(self, model_id: str) -> Optional[ModelInfo]:
        for m in self._models:
            if m.model_id == model_id:
                return m
        return None
