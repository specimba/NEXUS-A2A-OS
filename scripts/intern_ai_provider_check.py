"""Read-only Intern AI provider boot check for NEXUS OS.

Default mode does not call the network. Use --live only when the operator wants
to spend one request from the Intern AI quota.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PROVIDER_ID = "internai"
ENV_KEY = "INTERN_API_KEY"
BASE_URL_ENV = "INTERN_BASE_URL"
DEFAULT_BASE_URL = "https://chat.intern-ai.org.cn/api/v1"
THINKING_MODE_MODELS = {"intern-s2-preview", "intern-s1-pro", "intern-s1", "intern-s1-mini"}


def mask_secret(value: str | None) -> str:
    if not value:
        return "missing"
    if len(value) <= 12:
        return "***"
    return f"{value[:6]}...{value[-4:]}"


def load_static_state() -> dict[str, Any]:
    from nexus_os.bridge.secrets import PROVIDER_CONFIG
    from upload.intern_ai_lanes import get_intern_ai_lane_report
    from upload.config import PROVIDERS
    from upload.models_registry import ModelsRegistry

    registry = ModelsRegistry()
    models = registry.get_by_provider(PROVIDER_ID)

    return {
        "bridge_provider_configured": PROVIDER_ID in PROVIDER_CONFIG,
        "upload_provider_configured": PROVIDER_ID in PROVIDERS,
        "upload_models": [m.model_id for m in models],
        "capabilities": {
            "chat": True,
            "streaming": all(m.supports_streaming for m in models),
            "tools": all(m.supports_function_calling for m in models),
            "vision_models": [m.model_id for m in models if m.supports_vision],
            "max_context_window": max((m.context_window for m in models), default=0),
        },
        "configured_base_url": PROVIDER_CONFIG.get(PROVIDER_ID, {}).get("base_url"),
        "rate_limit_rpm": PROVIDER_CONFIG.get(PROVIDER_ID, {}).get("rpm_limit"),
        "lanes": get_intern_ai_lane_report(),
    }


def live_probe(base_url: str, api_key: str, model: str) -> dict[str, Any]:
    import requests

    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": "Health check: respond with OK"}],
        "max_tokens": 16,
        "temperature": 0,
        "stream": False,
    }
    if model in THINKING_MODE_MODELS:
        payload["thinking_mode"] = True

    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )

    result: dict[str, Any] = {
        "status_code": response.status_code,
        "ok": response.ok,
        "model": model,
    }
    try:
        body = response.json()
    except ValueError:
        body = {"text": response.text[:240]}

    if response.ok:
        choice = (body.get("choices") or [{}])[0]
        message = choice.get("message", {})
        result["content_preview"] = str(message.get("content", ""))[:80]
        result["has_tool_calls"] = bool(message.get("tool_calls"))
        result["usage"] = body.get("usage", {})
    else:
        result["error_preview"] = json.dumps(body, ensure_ascii=True)[:300]

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Intern AI provider boot check")
    parser.add_argument("--live", action="store_true", help="Run one live ChatAPI health request")
    parser.add_argument("--model", default="intern-latest", help="Model to use for --live")
    parser.add_argument("--lane", default="default", help="Intern AI lane to use for --live")
    args = parser.parse_args()

    from upload.intern_ai_lanes import resolve_intern_ai_key

    resolved_key = resolve_intern_ai_key(args.lane)
    api_key = resolved_key.value
    base_url = os.environ.get(BASE_URL_ENV, DEFAULT_BASE_URL)

    report: dict[str, Any] = {
        "provider": PROVIDER_ID,
        "lane": resolved_key.lane,
        "active_key_env": resolved_key.env_var,
        "env": {
            ENV_KEY: mask_secret(os.environ.get(ENV_KEY)),
            "resolved_key": mask_secret(api_key),
            BASE_URL_ENV: base_url,
        },
        "static_state": load_static_state(),
        "live_probe": "skipped",
    }

    if args.live:
        if not api_key:
            report["live_probe"] = {"ok": False, "error": f"{ENV_KEY} is not set"}
        else:
            report["live_probe"] = live_probe(base_url, api_key, args.model)

    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
