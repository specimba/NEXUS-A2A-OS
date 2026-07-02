"""Canonical Grok browser-lane URLs and CDP port (env-overridable)."""

from __future__ import annotations

import os

DEFAULT_GROK_PROJECT_ID = "99253cca-2469-4454-8593-0f173b7f640f"
DEFAULT_GROK_CHAT_ID = "4d8d8598-9da7-4639-918e-4ceb6a8812ba"
DEFAULT_GROK_PROJECT_URL = (
    f"https://grok.com/project/{DEFAULT_GROK_PROJECT_ID}"
)
DEFAULT_GROK_PROJECT_CHAT_URL = (
    f"https://grok.com/project/{DEFAULT_GROK_PROJECT_ID}"
    f"?chat={DEFAULT_GROK_CHAT_ID}"
)
DEFAULT_GROK_CDP_PORT = 9224


def grok_project_url() -> str:
    return (
        os.environ.get("NEXUS_GROK_PROJECT_URL", "").strip()
        or os.environ.get("NEXUS_GROK_PROJECT_CHAT_URL", "").strip()
        or DEFAULT_GROK_PROJECT_CHAT_URL
    )


def grok_cdp_port() -> int:
    raw = os.environ.get("NEXUS_GROK_CDP_PORT", "").strip()
    if not raw:
        return DEFAULT_GROK_CDP_PORT
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_GROK_CDP_PORT