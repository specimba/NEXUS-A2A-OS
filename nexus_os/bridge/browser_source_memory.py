"""Browser-source memory registry for NEXUS governance.

Tracks verified browser/provider sources, their grounding state,
available artifacts, and high-grounding commands.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True)
class BrowserSourceEntry:
    name: str
    provider_id: str
    base_url: str
    auth_header: str
    auth_env: str
    models: tuple[str, ...]
    max_context: int | None
    supports_tools: bool
    supports_streaming: bool
    supports_multimodal: bool
    default_thinking: bool
    rate_limit_rpm: int | None
    status: str  # ready | blocked | degraded | pending
    grounding_notes: str
    direct_manage_env: tuple[str, ...]


BROWSER_SOURCES: dict[str, BrowserSourceEntry] = {
    "internai": BrowserSourceEntry(
        name="Intern AI / Shanghai ChatAPI",
        provider_id="internai",
        base_url="https://chat.intern-ai.org.cn/api/v1",
        auth_header="Authorization",
        auth_env="INTERN_API_KEY",
        models=("intern-s2-preview", "intern-latest", "internvl2.5-latest"),
        max_context=256_000,
        supports_tools=True,
        supports_streaming=True,
        supports_multimodal=True,
        default_thinking=True,
        rate_limit_rpm=30,
        status="ready",
        grounding_notes="OpenAI-compatible + Claude-compatible endpoint; strip stop; prefer thinking_mode for agent lanes.",
        direct_manage_env=(
            "INTERN_API_KEY",
            "INTERN_API_KEY_2",
            "INTERN_OPENCODE_API_KEY",
            "INTERN_KILOCODE_API_KEY",
            "INTERN_HERMES_API_KEY",
            "INTERN_CLAW_API_KEY",
            "INTERN_ZO_API_KEY",
            "INTERN_BASE_URL",
        ),
    ),
    "longcat": BrowserSourceEntry(
        name="LongCat",
        provider_id="longcat",
        base_url="https://api.longcat.chat/openai/v1",
        auth_header="Authorization",
        auth_env="NEXUS_LONGCAT_API_KEY",
        models=("LongCat-2.0-Preview",),
        max_context=1_000_000,
        supports_tools=True,
        supports_streaming=True,
        supports_multimodal=False,
        default_thinking=False,
        rate_limit_rpm=None,
        status="ready",
        grounding_notes="OpenAI/Anthropic format compatible; treated as governed cloud teacher/judge lane.",
        direct_manage_env=(
            "LONGCAT_API_KEY",
            "NEXUS_LONGCAT_API_KEY",
            "LONGCAT_MODELRELAY_API_KEY",
            "LONGCAT_HERMES_API_KEY",
            "LONGCAT_OPENCODE_API_KEY",
            "LONGCAT_KILOCODE_API_KEY",
            "LONGCAT_CLAW_API_KEY",
            "LONGCAT_ZO_API_KEY",
        ),
    ),
}


def get_browser_source(name: str) -> BrowserSourceEntry | None:
    return BROWSER_SOURCES.get(name.strip().lower())


def iter_browser_sources() -> Iterable[BrowserSourceEntry]:
    return BROWSER_SOURCES.values()


def browser_source_report() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key, entry in BROWSER_SOURCES.items():
        out[key] = {
            "name": entry.name,
            "provider_id": entry.provider_id,
            "base_url": entry.base_url,
            "auth_header": entry.auth_header,
            "auth_env": entry.auth_env,
            "key_masked": _mask(os.environ.get(entry.auth_env)),
            "models": list(entry.models),
            "max_context": entry.max_context,
            "supports_tools": entry.supports_tools,
            "supports_streaming": entry.supports_streaming,
            "supports_multimodal": entry.supports_multimodal,
            "default_thinking": entry.default_thinking,
            "rate_limit_rpm": entry.rate_limit_rpm,
            "status": entry.status,
            "grounding_notes": entry.grounding_notes,
            "direct_manage_env": list(entry.direct_manage_env),
        }
    return out


def _mask(value: str | None) -> str:
    if not value:
        return "missing"
    if len(value) <= 12:
        return "***"
    return f"{value[:6]}...{value[-4:]}"


def active_key_env(provider: str) -> str | None:
    entry = get_browser_source(provider)
    if not entry:
        return None
    for name in entry.direct_manage_env:
        if os.environ.get(name):
            return name
    return None
