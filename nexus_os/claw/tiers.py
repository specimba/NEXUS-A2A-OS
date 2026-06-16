"""Model tier classification for NEXUSCLAW.

Heuristic model tiering based on model name patterns, with support for
explicit overrides persisted via ``PreferenceStore``.
"""

from __future__ import annotations

import enum
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class ModelTier(enum.Enum):
    QUICK = "quick"
    STANDARD = "standard"
    THOROUGH = "thorough"


class TrustThreshold(enum.Enum):
    """ERNIE TrustKernel-style trust thresholds.

    Maps to ERNIE Session 13/14 HARDWALL/CAUTION/RESTRICTED pattern.
    """
    HARDWALL = "hardwall"
    CAUTION = "caution"
    RESTRICTED = "restricted"


# Heuristic model name patterns for each tier.
# These match known model families from providers, sorted by capability.

_QUICK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(gpt-4o-mini|gpt-mini|gpt-4\.1-nano)"),
    re.compile(r"(?i)(gemini-1\.5-flash|gemini-2\.0-flash|gemini-flash)"),
    re.compile(r"(?i)(claude-haiku|claude-3-haiku)"),
    re.compile(r"(?i)(mistral-small|mistral-7b|mixtral-8x7b)"),
    re.compile(r"(?i)(llama-3\.[12]-?8b|llama-guard|qwen2\.5-0\.5b)"),
    re.compile(r"(?i)(deepseek-v2-lite|deepseek-coder)"),
]

_THOROUGH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(gpt-4\.5|gpt-5|o1|o3|o4)"),
    re.compile(r"(?i)(claude-opus|claude-4|claude-3\.5-sonnet|claude-sonnet-4)"),
    re.compile(r"(?i)(gemini-2\.5-pro|gemini-1\.5-pro|gemini-ultra)"),
    re.compile(r"(?i)(deepseek-r1|deepseek-v3)"),
    re.compile(r"(?i)(qwen-?2\.5-?72b|qwen-?3-?72b)"),
    re.compile(r"(?i)(llama-3\.1-?405b|llama-4)"),
]

# Standard patterns are catch-all: anything not quick or thorough.
# But we still define patterns that explicitly match medium models.
_STANDARD_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(gpt-4o|gpt-4\.1|gpt-4-turbo|gpt-4)"),
    re.compile(r"(?i)(claude-sonnet|claude-3-sonnet)"),
    re.compile(r"(?i)(gemini-1\.5-pro|gemini-2\.0-pro)"),
    re.compile(r"(?i)(mistral-large|mixtral-8x22b)"),
    re.compile(r"(?i)(llama-3\.[12]-?70b)"),
    re.compile(r"(?i)(qwen-?2\.5-?32b|qwen-?2\.5-?14b|qwen-?3-?32b)"),
    re.compile(r"(?i)(deepseek-v2)"),
    re.compile(r"(?i)(command-r|command-r-plus)"),
    re.compile(r"(?i)(nemotron)"),
]


_RESERVED_KEYWORDS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(mini|small|light|tiny|nano|1b|0\.5b|3b)"),
    re.compile(r"(?i)(flash|fast)"),
    re.compile(r"(?i)(haiku)"),
]


def classify_model(model_name: str) -> ModelTier:
    """Classify a model into a tier based on its name.

    Checks thorough patterns first, then quick, then standard as fallback.
    """
    for pattern in _THOROUGH_PATTERNS:
        if pattern.search(model_name):
            return ModelTier.THOROUGH
    for pattern in _QUICK_PATTERNS:
        if pattern.search(model_name):
            return ModelTier.QUICK
    for pattern in _STANDARD_PATTERNS:
        if pattern.search(model_name):
            return ModelTier.STANDARD
    return ModelTier.STANDARD


def estimate_trust_threshold(model_name: str) -> TrustThreshold:
    """Estimate an appropriate trust threshold based on model tier.

    Thorough models can handle more autonomy (CAUTION).
    Quick/small models need HARDWALL oversight.
    """
    tier = classify_model(model_name)
    if tier == ModelTier.THOROUGH:
        return TrustThreshold.CAUTION
    if tier == ModelTier.QUICK:
        return TrustThreshold.HARDWALL
    return TrustThreshold.RESTRICTED


class ModelTierStore:
    """Persistent model tier overrides backed by a preference store."""

    def __init__(self, store: Any = None) -> None:
        from nexus_os.claw.store import MemoryStore, PreferenceStore
        self._ps = store if isinstance(store, PreferenceStore) else PreferenceStore(MemoryStore())

    def get_tier(self, model_name: str) -> ModelTier:
        overrides = self._ps.load_model_tiers()
        if model_name in overrides:
            return ModelTier(overrides[model_name])
        return classify_model(model_name)

    def set_tier(self, model_name: str, tier: ModelTier) -> None:
        overrides = self._ps.load_model_tiers()
        overrides[model_name] = tier.value
        self._ps.save_model_tiers(overrides)

    def clear_overrides(self) -> None:
        self._ps.save_model_tiers({})

    def get_trust(self, model_name: str) -> TrustThreshold:
        tier = self.get_tier(model_name)
        if tier == ModelTier.THOROUGH:
            return TrustThreshold.CAUTION
        if tier == ModelTier.QUICK:
            return TrustThreshold.HARDWALL
        return TrustThreshold.RESTRICTED
