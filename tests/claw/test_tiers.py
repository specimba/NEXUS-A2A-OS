"""tests/claw/test_tiers.py — Model tier classification."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from nexus_os.claw.tiers import (
    ModelTier,
    ModelTierStore,
    TrustThreshold,
    classify_model,
    estimate_trust_threshold,
)
from nexus_os.claw.store import MemoryStore, PreferenceStore


def test_thorough_models() -> None:
    assert classify_model("claude-opus-4") == ModelTier.THOROUGH
    assert classify_model("gpt-5") == ModelTier.THOROUGH
    assert classify_model("gemini-2.5-pro") == ModelTier.THOROUGH
    assert classify_model("deepseek-r1") == ModelTier.THOROUGH
    assert classify_model("o4-mini") == ModelTier.THOROUGH


def test_quick_models() -> None:
    assert classify_model("gpt-4o-mini") == ModelTier.QUICK
    assert classify_model("gemini-1.5-flash") == ModelTier.QUICK
    assert classify_model("claude-3-haiku") == ModelTier.QUICK
    assert classify_model("llama-guard") == ModelTier.QUICK
    assert classify_model("qwen2.5-0.5b") == ModelTier.QUICK


def test_standard_fallback() -> None:
    assert classify_model("gpt-4o") == ModelTier.STANDARD
    assert classify_model("llama-3.1-70b") == ModelTier.STANDARD
    assert classify_model("unknown-model-1234") == ModelTier.STANDARD


def test_trust_threshold_mapping() -> None:
    assert estimate_trust_threshold("claude-opus-4") == TrustThreshold.CAUTION
    assert estimate_trust_threshold("gpt-4o-mini") == TrustThreshold.HARDWALL
    assert estimate_trust_threshold("gpt-4o") == TrustThreshold.RESTRICTED


def test_tier_store_override() -> None:
    store = ModelTierStore(PreferenceStore(MemoryStore()))
    assert store.get_tier("gpt-4o") == ModelTier.STANDARD
    store.set_tier("gpt-4o", ModelTier.QUICK)
    assert store.get_tier("gpt-4o") == ModelTier.QUICK


def test_tier_store_clear() -> None:
    store = ModelTierStore(PreferenceStore(MemoryStore()))
    store.set_tier("gpt-4o", ModelTier.QUICK)
    store.clear_overrides()
    assert store.get_tier("gpt-4o") == ModelTier.STANDARD


def test_tier_store_trust_method() -> None:
    store = ModelTierStore(PreferenceStore(MemoryStore()))
    assert store.get_trust("gpt-5") == TrustThreshold.CAUTION
    assert store.get_trust("gpt-4o-mini") == TrustThreshold.HARDWALL


if __name__ == "__main__":
    pytest.main([__file__])
