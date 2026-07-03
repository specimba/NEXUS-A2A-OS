"""Models Registry — Model capabilities, costs, and provider mapping."""

from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class ModelInfo:
    """Single model metadata."""
    model_id: str           # e.g. "nvidia/llama-3.3-nemotron-super-128k"
    provider: str           # e.g. "openrouter", "ollama", "minimax"
    name: str               # Display name
    tier: int               # Quality tier 0-100
    cost_per_1m_input: float
    cost_per_1m_output: float
    context_window: int    # Max tokens
    latency_ms_typical: int
    supports_vision: bool = False
    supports_function_calling: bool = False
    supports_streaming: bool = True
    is_free: bool = False
    is_local: bool = False
    status: str = "up"      # up|degraded|down

    @property
    def cost_per_1m_total(self) -> float:
        return self.cost_per_1m_input + self.cost_per_1m_output

    @property
    def quality_score(self) -> float:
        return min(self.tier / 100, 1.0)


class ModelsRegistry:
    """Central registry of all available models."""

    # Default model list (can be extended via config)
    DEFAULT_MODELS: List[ModelInfo] = [
        # ── MiniMax (Primary, quota limited) ─────────────────────────────────
        ModelInfo(
            model_id="MiniMax/M2.7",
            provider="minimax",
            name="MiniMax M2.7",
            tier=99,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=128000,
            latency_ms_typical=300,
            supports_vision=True,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=True,
            is_local=False,
        ),
        # ── OpenRouter Free/Low-Cost ─────────────────────────────────────────
        ModelInfo(
            model_id="openrouter/nvidia/llama-3.3-nemotron-super-128k",
            provider="openrouter",
            name="Nemotron Super 128K",
            tier=85,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=128000,
            latency_ms_typical=200,
            supports_vision=False,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=True,
            is_local=False,
        ),
        ModelInfo(
            model_id="openrouter/deepseek/deepseek-chat-v3-0324",
            provider="openrouter",
            name="DeepSeek Chat V3",
            tier=82,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=64000,
            latency_ms_typical=180,
            supports_vision=False,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=True,
            is_local=False,
        ),
        ModelInfo(
            model_id="openrouter/google/gemini-2.5-pro-preview",
            provider="openrouter",
            name="Gemini 2.5 Pro",
            tier=97,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=1000000,
            latency_ms_typical=400,
            supports_vision=True,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=True,
            is_local=False,
        ),
        # ── Ollama Local Models ─────────────────────────────────────────────
        ModelInfo(
            model_id="ollama/osman-coder",
            provider="ollama",
            name="Osman Coder (Local)",
            tier=40,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=8192,
            latency_ms_typical=50,
            supports_vision=False,
            supports_function_calling=False,
            supports_streaming=True,
            is_free=True,
            is_local=True,
        ),
        ModelInfo(
            model_id="ollama/osman-fast",
            provider="ollama",
            name="Osman Fast (Local)",
            tier=40,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=4096,
            latency_ms_typical=20,
            supports_vision=False,
            supports_function_calling=False,
            supports_streaming=True,
            is_free=True,
            is_local=True,
        ),
        ModelInfo(
            model_id="ollama/osman-reasoning",
            provider="ollama",
            name="Osman Reasoning (Local)",
            tier=40,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=8192,
            latency_ms_typical=80,
            supports_vision=False,
            supports_function_calling=False,
            supports_streaming=True,
            is_free=True,
            is_local=True,
        ),
        ModelInfo(
            model_id="ollama/osman-agent",
            provider="ollama",
            name="Osman Agent (Local)",
            tier=40,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=8192,
            latency_ms_typical=50,
            supports_vision=False,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=True,
            is_local=True,
        ),
        # ── Groq Models ──────────────────────────────────────────────────────
        ModelInfo(
            model_id="groq/llama-3.3-70b-versatile",
            provider="groq",
            name="Llama 3.3 70B (Groq)",
            tier=75,
            cost_per_1m_input=0.59,
            cost_per_1m_output=0.79,
            context_window=128000,
            latency_ms_typical=150,
            supports_vision=False,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=False,
            is_local=False,
        ),
        ModelInfo(
            model_id="groq/mixtral-8x7b-32768",
            provider="groq",
            name="Mixtral 8x7B (Groq)",
            tier=70,
            cost_per_1m_input=0.24,
            cost_per_1m_output=0.24,
            context_window=32768,
            latency_ms_typical=120,
            supports_vision=False,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=False,
            is_local=False,
        ),
        # ── Cerebras Models ──────────────────────────────────────────────────
        ModelInfo(
            model_id="cerebras/llama-3.3-70b",
            provider="cerebras",
            name="Llama 3.3 70B (Cerebras)",
            tier=72,
            cost_per_1m_input=0.6,
            cost_per_1m_output=0.6,
            context_window=128000,
            latency_ms_typical=100,
            supports_vision=False,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=False,
            is_local=False,
        ),
        # ── Together AI Models ──────────────────────────────────────────────
        ModelInfo(
            model_id="together/llama-3.3-70b-instruct-turbo",
            provider="together",
            name="Llama 3.3 70B Turbo (Together)",
            tier=78,
            cost_per_1m_input=0.88,
            cost_per_1m_output=0.88,
            context_window=128000,
            latency_ms_typical=250,
            supports_vision=False,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=False,
            is_local=False,
        ),
        # ── DeepSeek ─────────────────────────────────────────────────────────
        ModelInfo(
            model_id="deepseek/deepseek-chat",
            provider="deepseek",
            name="DeepSeek Chat",
            tier=80,
            cost_per_1m_input=0.27,
            cost_per_1m_output=1.1,
            context_window=64000,
            latency_ms_typical=200,
            supports_vision=False,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=False,
            is_local=False,
        ),
        # ── InternAI ──────────────────────────────────────────────────────────
        ModelInfo(
            model_id="internai/intern-s2-preview",
            provider="internai",
            name="Intern S2 Preview",
            tier=95,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=256000,
            latency_ms_typical=250,
            supports_vision=False,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=True,
            is_local=False,
        ),
        ModelInfo(
            model_id="internai/intern-latest",
            provider="internai",
            name="Intern Latest",
            tier=90,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=256000,
            latency_ms_typical=200,
            supports_vision=False,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=True,
            is_local=False,
        ),
        ModelInfo(
            model_id="internai/internvl3.5-latest",
            provider="internai",
            name="InternVL3.5 Latest",
            tier=92,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=32000,
            latency_ms_typical=300,
            supports_vision=True,
            supports_function_calling=False,
            supports_streaming=True,
            is_free=True,
            is_local=False,
        ),
        ModelInfo(
            model_id="internai/intern-s1-pro",
            provider="internai", name="Intern S1 Pro", tier=82,
            cost_per_1m_input=0.0, cost_per_1m_output=0.0,
            context_window=256000, latency_ms_typical=300,
            supports_function_calling=True, supports_streaming=True,
            is_free=True, is_local=False,
        ),
        ModelInfo(
            model_id="internai/intern-s1", provider="internai", name="Intern S1", tier=75,
            cost_per_1m_input=0.0, cost_per_1m_output=0.0,
            context_window=32000, latency_ms_typical=250,
            supports_function_calling=True, supports_streaming=True,
            is_free=True, is_local=False,
        ),
        ModelInfo(
            model_id="internai/intern-s1-mini", provider="internai", name="Intern S1 Mini", tier=70,
            cost_per_1m_input=0.0, cost_per_1m_output=0.0,
            context_window=32000, latency_ms_typical=180,
            supports_function_calling=True, supports_streaming=True,
            is_free=True, is_local=False,
        ),
        ModelInfo(
            model_id="internai/internvl3.5-241b-a28b", provider="internai",
            name="InternVL3.5 241B A28B", tier=78,
            cost_per_1m_input=0.0, cost_per_1m_output=0.0,
            context_window=32000, latency_ms_typical=400,
            supports_vision=True, supports_streaming=True,
            is_free=True, is_local=False,
        ),
        ModelInfo(
            model_id="internai/internvl-latest", provider="internai", name="InternVL Latest", tier=72,
            cost_per_1m_input=0.0, cost_per_1m_output=0.0,
            context_window=32000, latency_ms_typical=350,
            supports_vision=True, supports_streaming=True,
            is_free=True, is_local=False,
        ),
        # -- OpenModel / DeepSeek V4 Flash ------------------------------------
        ModelInfo(
            model_id="openmodel/deepseek-v4-flash-free",
            provider="openmodel",
            name="DeepSeek V4 Flash Free",
            tier=86,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=131000,
            latency_ms_typical=450,
            supports_vision=False,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=True,
            is_local=False,
        ),
        # -- Sakana Fugu -------------------------------------------------------
        ModelInfo(
            model_id="sakana/fugu",
            provider="sakana",
            name="Sakana Fugu",
            tier=90,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=1000000,
            latency_ms_typical=1200,
            supports_vision=True,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=True,
            is_local=False,
        ),
        ModelInfo(
            model_id="sakana/fugu-ultra",
            provider="sakana",
            name="Sakana Fugu Ultra",
            tier=94,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=1000000,
            latency_ms_typical=2500,
            supports_vision=True,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=True,
            is_local=False,
        ),
        # -- LongCat ---------------------------------------------------------
        ModelInfo(
            model_id="longcat/LongCat-2.0",
            provider="longcat",
            name="LongCat 2.0",
            tier=94,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
            context_window=1000000,
            latency_ms_typical=1000,
            supports_vision=False,
            supports_function_calling=True,
            supports_streaming=True,
            is_free=True,
            is_local=False,
        ),
    ]

    def __init__(self, custom_models: Optional[List[ModelInfo]] = None):
        self._models: Dict[str, ModelInfo] = {}
        for m in (custom_models or self.DEFAULT_MODELS):
            self._models[m.model_id] = m

    def get(self, model_id: str) -> Optional[ModelInfo]:
        return self._models.get(model_id)

    def get_by_provider(self, provider: str) -> List[ModelInfo]:
        return [m for m in self._models.values() if m.provider == provider]

    def get_by_capability(self, supports_vision: bool = False,
                          supports_fn: bool = False) -> List[ModelInfo]:
        result = []
        for m in self._models.values():
            if supports_vision and not m.supports_vision:
                continue
            if supports_fn and not m.supports_function_calling:
                continue
            result.append(m)
        return result

    def get_free(self) -> List[ModelInfo]:
        return [m for m in self._models.values() if m.is_free]

    def get_local(self) -> List[ModelInfo]:
        return [m for m in self._models.values() if m.is_local]

    def get_up(self) -> List[ModelInfo]:
        return [m for m in self._models.values() if m.status == "up"]

    def update_status(self, model_id: str, status: str):
        if model_id in self._models:
            self._models[model_id].status = status

    def all(self) -> List[ModelInfo]:
        return list(self._models.values())

    def all_ids(self) -> List[str]:
        return list(self._models.keys())


