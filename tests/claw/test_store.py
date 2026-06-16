"""tests/claw/test_store.py — Preference store tests."""

from __future__ import annotations

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from nexus_os.claw.store import FileTreeStore, MemoryStore, PreferenceStore


@pytest.fixture
def mem_prefs() -> PreferenceStore:
    return PreferenceStore(MemoryStore())


@pytest.fixture
def file_prefs(tmp_path: Path) -> PreferenceStore:
    return PreferenceStore(FileTreeStore(tmp_path))


# ── Memory backend ──────────────────────────────────────────────────────


def test_load_none_when_empty(mem_prefs: PreferenceStore) -> None:
    assert mem_prefs.load_preferences("agent-1") == {}


def test_save_and_load_preferences(mem_prefs: PreferenceStore) -> None:
    mem_prefs.save_preferences("agent-1", {"mode": "strict", "retries": 3})
    loaded = mem_prefs.load_preferences("agent-1")
    assert loaded["mode"] == "strict"
    assert loaded["retries"] == 3


def test_delete_clears_preferences(mem_prefs: PreferenceStore) -> None:
    mem_prefs.save_preferences("agent-1", {"mode": "strict"})
    mem_prefs.delete_preferences("agent-1")
    assert mem_prefs.load_preferences("agent-1") == {}


def test_load_none_after_delete(mem_prefs: PreferenceStore) -> None:
    mem_prefs.save_preferences("agent-1", {"mode": "strict"})
    mem_prefs.delete_preferences("agent-1")
    assert mem_prefs.load_preferences("agent-1") == {}


def test_save_and_load_tiers(mem_prefs: PreferenceStore) -> None:
    mem_prefs.save_model_tiers({"gpt-4o": "quick", "claude-opus": "thorough"})
    loaded = mem_prefs.load_model_tiers()
    assert loaded["gpt-4o"] == "quick"
    assert loaded["claude-opus"] == "thorough"


def test_store_isolation(mem_prefs: PreferenceStore) -> None:
    mem_prefs.save_preferences("agent-1", {"mode": "strict"})
    mem_prefs.save_model_tiers({"gpt-4o": "thorough"})
    assert "mode" not in mem_prefs.load_model_tiers()


# ── File backend ────────────────────────────────────────────────────────


def test_file_persistence(file_prefs: PreferenceStore) -> None:
    file_prefs.save_preferences("agent-1", {"mode": "permissive"})
    loaded = file_prefs.load_preferences("agent-1")
    assert loaded["mode"] == "permissive"


def test_file_trust_config(file_prefs: PreferenceStore) -> None:
    file_prefs.save_trust_config("agent-1", {"threshold": "HARDWALL"})
    loaded = file_prefs.load_trust_config("agent-1")
    assert loaded["threshold"] == "HARDWALL"
    file_prefs.delete_trust_config("agent-1")
    assert file_prefs.load_trust_config("agent-1") == {}


if __name__ == "__main__":
    pytest.main([__file__])
