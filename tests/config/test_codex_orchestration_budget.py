"""Claim gates for the project-local Codex long-run budget policy."""
from __future__ import annotations

import tomllib
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO / ".codex" / "config.toml"


def _config() -> dict:
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_gpt56_context_window_is_pinned_to_272k() -> None:
    config = _config()

    assert config["model_context_window"] == 272_000
    assert config["model_context_window"] != 372_000


def test_auto_compaction_leaves_headroom_below_effective_window() -> None:
    config = _config()

    assert config["model_auto_compact_token_limit_scope"] == "total"
    assert 0 < config["model_auto_compact_token_limit"] < int(272_000 * 0.95)


def test_default_reasoning_is_long_run_efficient() -> None:
    assert _config()["model_reasoning_effort"] in {"low", "medium"}


def test_subagent_fanout_is_bounded() -> None:
    agents = _config()["agents"]

    assert 1 <= agents["max_threads"] <= 4
