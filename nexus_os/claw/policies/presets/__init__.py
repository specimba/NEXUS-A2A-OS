"""Policy preset definitions (deny-by-default baseline + platform presets)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PRESETS_DIR = Path(__file__).parent


def _load_preset(name: str) -> dict[str, Any]:
    path = _PRESETS_DIR / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Policy preset not found: {name}")
    return json.loads(path.read_text())


def sandbox_preset() -> dict[str, Any]:
    """Deny-by-default baseline sandbox policy."""
    return _load_preset("sandbox")


def github_preset() -> dict[str, Any]:
    return _load_preset("github")


def discord_preset() -> dict[str, Any]:
    return _load_preset("discord")


def telegram_preset() -> dict[str, Any]:
    return _load_preset("telegram")


def slack_preset() -> dict[str, Any]:
    return _load_preset("slack")


def huggingface_preset() -> dict[str, Any]:
    return _load_preset("huggingface")


def npm_preset() -> dict[str, Any]:
    return _load_preset("npm")


def pypi_preset() -> dict[str, Any]:
    return _load_preset("pypi")


_PRESET_REGISTRY: dict[str, Any] = {
    "sandbox": sandbox_preset,
    "github": github_preset,
    "discord": discord_preset,
    "telegram": telegram_preset,
    "slack": slack_preset,
    "huggingface": huggingface_preset,
    "npm": npm_preset,
    "pypi": pypi_preset,
}


def load_preset(name: str) -> dict[str, Any]:
    loader = _PRESET_REGISTRY.get(name)
    if loader is None:
        raise KeyError(f"Unknown policy preset: {name}")
    return loader()


def list_presets() -> list[str]:
    return list(_PRESET_REGISTRY)
