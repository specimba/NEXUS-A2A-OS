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
DEFAULT_ZO_SOURCE_ID = "zo-browser-lab"
DEFAULT_ZO_CHAT_URL = (
    "https://specimba.zo.computer/?chat=con_EL8I2vKUvldsLVJ6"
)
DEFAULT_CHATGPT_CHAT_URL = "https://chatgpt.com/c/6a4600ec-0db0-83eb-932c-9d3496adbba0"
DEFAULT_GLM_Z_AI_CHAT_URL = (
    "https://chat.z.ai/c/1b1cd50b-c78c-403d-9280-0612c76a56b3"
)
DEFAULT_GEMINI_APP_URL = "https://gemini.google.com/app/6fba62a56f165a08"
DEFAULT_GMICLOUD_PLAYGROUND_URL = (
    "https://console.gmicloud.ai/user-console/ie/playground/llm/"
    "1f12423b-ac10-4690-a670-36f768d7b9bf"
)
DEFAULT_CHATGPT_SOURCE_ID = "openai-chatgpt-lab"
DEFAULT_GPT_AUDIT_MCP_SSE_URL = "https://sharply-unethical-various.ngrok-free.dev/sse"


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


def zo_cdp_tunnel_url() -> str:
    """URL Zo uses to reach Windows CDP (often localhost after SSH -L)."""
    return os.environ.get("NEXUS_ZO_CDP_TUNNEL_URL", "").strip() or (
        f"http://127.0.0.1:{grok_cdp_port()}"
    )


def zo_source_id() -> str:
    return os.environ.get("NEXUS_ZO_SOURCE_ID", "").strip() or DEFAULT_ZO_SOURCE_ID


def zo_chat_url() -> str:
    return os.environ.get("NEXUS_ZO_CHAT_URL", "").strip() or DEFAULT_ZO_CHAT_URL


def chatgpt_chat_url() -> str:
    return (
        os.environ.get("NEXUS_CHATGPT_CHAT_URL", "").strip()
        or os.environ.get("NEXUS_OPENAI_CHAT_URL", "").strip()
        or DEFAULT_CHATGPT_CHAT_URL
    )


def glm_z_ai_chat_url() -> str:
    return (
        os.environ.get("NEXUS_GLM_CHAT_URL", "").strip()
        or os.environ.get("NEXUS_Z_AI_CHAT_URL", "").strip()
        or DEFAULT_GLM_Z_AI_CHAT_URL
    )


def gemini_app_url() -> str:
    return (
        os.environ.get("NEXUS_GEMINI_APP_URL", "").strip()
        or os.environ.get("NEXUS_GEMINI_NOTEBOOK_URL", "").strip()
        or DEFAULT_GEMINI_APP_URL
    )


def gmicloud_playground_url() -> str:
    return (
        os.environ.get("NEXUS_GMICLOUD_PLAYGROUND_URL", "").strip()
        or DEFAULT_GMICLOUD_PLAYGROUND_URL
    )


def chatgpt_source_id() -> str:
    return os.environ.get("NEXUS_CHATGPT_SOURCE_ID", "").strip() or DEFAULT_CHATGPT_SOURCE_ID


def gpt_audit_mcp_sse_url() -> str:
    return (
        os.environ.get("NEXUS_GPT_AUDIT_MCP_SSE_URL", "").strip()
        or DEFAULT_GPT_AUDIT_MCP_SSE_URL
    )