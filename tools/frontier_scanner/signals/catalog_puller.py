"""
NEXUS Frontier Scanner — signals catalog puller.

Fetches /v1/models from each registered provider, returns sorted de-duplicated
set of model IDs per (provider, model) tuple. Designed for silent operation:
- Single call per cycle per provider
- No inference path triggered
- Cached locally to avoid network storms
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable


PROVIDER_PROFILES = {
    "nvidia": {
        "models_url": "https://integrate.api.nvidia.com/v1/models",
        "auth_env": "NVIDIA_API_KEY",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout_seconds": 12,
        "rpm_floor": 0.05,
        "data_path": "data.id",
    },
    "ollama-cloud": {
        "models_url": "https://ollama.com/v1/models",
        "auth_env": "OLLAMA_CLOUD_API_KEY",
        "timeout_seconds": 10,
        "rpm_floor": 0.05,
        "data_path": "data.id",
    },
    "longcat": {
        "models_url": "https://api.longcat.chat/openai/v1/models",
        "auth_env": "LONGCAT_API_KEY",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout_seconds": 10,
        "rpm_floor": 0.05,
        "data_path": "data.id",
    },
    "internai": {
        "models_url": "https://chat.intern-ai.org.cn/api/v1/models",
        "auth_env": "INTERN_API_KEY",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout_seconds": 10,
        "rpm_floor": 0.05,
        "data_path": "data.id",
    },
    "mistral": {
        "models_url": "https://api.mistral.ai/v1/models",
        "auth_env": "MISTRAL_API_KEY",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout_seconds": 10,
        "rpm_floor": 0.05,
        "data_path": "data.id",
    },
    "groq": {
        "models_url": "https://api.groq.com/openai/v1/models",
        "auth_env": "GROQ_API_KEY",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout_seconds": 10,
        "rpm_floor": 0.05,
        "data_path": "data.id",
    },
    "codestral": {
        "models_url": "https://codestral.mistral.ai/v1/models",
        "auth_env": "CODESTRAL_API_KEY",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout_seconds": 10,
        "rpm_floor": 0.05,
        "data_path": "data.id",
        "skip_catalog_when_404": True,
        "_comment": "no_list_endpoint_only_chat",
    },
    "github": {
        "models_url": "https://models.inference.ai.azure.com/models",
        "auth_env": "GITHUB_API_KEY",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout_seconds": 10,
        "rpm_floor": 0.05,
        "data_path": "data.id",
        "raw_root_path": "",  # github returns top-level array
    },
}


@dataclass
class ProviderCatalog:
    provider: str
    fetched_at: float
    source_url: str
    model_ids: list[str] = field(default_factory=list)
    error: str | None = None
    status: str = "unknown"
    raw_count: int = 0


def _walk_path(obj: dict, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _read_key(env: str) -> str:
    import os
    return os.environ.get(env, "").strip()


def _extract_ids(payload, profile: dict) -> list[str]:
    raw_root_path = profile.get("raw_root_path", "")
    if raw_root_path == "" and isinstance(payload, list):
        ids: list[str] = []
        for entry in payload:
            if isinstance(entry, dict) and "id" in entry:
                ids.append(str(entry["id"]))
            elif isinstance(entry, str):
                ids.append(entry)
        return sorted(set(ids))
    if raw_root_path:
        cur: object = payload
        for part in raw_root_path.split("."):
            if not isinstance(cur, dict):
                cur = None
                break
            cur = cur.get(part)
        if isinstance(cur, list):
            ids = []
            for entry in cur:
                if isinstance(entry, dict) and "id" in entry:
                    ids.append(str(entry["id"]))
            return sorted(set(ids))
    data_path = profile.get("data_path", "data.id")
    root = _walk_path(payload, data_path.split(".")[0]) if isinstance(payload, dict) else None
    if isinstance(root, list):
        ids = []
        if data_path.endswith(".id"):
            for entry in root:
                if isinstance(entry, dict) and "id" in entry:
                    ids.append(str(entry["id"]))
        else:
            ids = [str(x) for x in root if x is not None]
        return sorted(set(ids))
    return []


def pull_provider_catalog(provider: str, profile: dict) -> ProviderCatalog:
    out = ProviderCatalog(
        provider=provider,
        fetched_at=time.time(),
        source_url=profile["models_url"],
    )
    key = _read_key(profile["auth_env"])
    headers = {"User-Agent": "NEXUS-FrontierScanner/0.1"}
    if key:
        auth_header = profile.get("auth_header")
        if auth_header:
            headers[auth_header] = profile["auth_prefix"] + key
    req = urllib.request.Request(profile["models_url"], headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=profile["timeout_seconds"]) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(body)
            ids = _extract_ids(payload, profile)
            out.model_ids = ids
            out.raw_count = len(ids)
            out.status = "ok"
    except urllib.error.HTTPError as e:
        if e.code == 404 and profile.get("skip_catalog_when_404"):
            out.status = "no_list_endpoint"
            out.model_ids = []
            out.raw_count = 0
            return out
        out.error = f"http_{e.code}"
        out.status = "http_error"
    except urllib.error.URLError as e:
        out.error = f"url_{e.reason}"
        out.status = "url_error"
    except (TimeoutError, json.JSONDecodeError) as e:
        out.error = str(e)[:120]
        out.status = "fetch_error"
    return out


def pull_all_catalogs(
    providers: Iterable[str] | None = None,
    state_dir: Path | None = None,
) -> dict[str, ProviderCatalog]:
    selected = list(providers) if providers else list(PROVIDER_PROFILES)
    catalogs: dict[str, ProviderCatalog] = {}
    for name in selected:
        profile = PROVIDER_PROFILES.get(name)
        if not profile:
            continue
        catalog = pull_provider_catalog(name, profile)
        catalogs[name] = catalog
        if state_dir is not None:
            state_dir.mkdir(parents=True, exist_ok=True)
            out_path = state_dir / f"catalog__{name}.json"
            out_path.write_text(
                json.dumps(asdict(catalog), indent=2, sort_keys=True),
                encoding="utf-8",
            )
    return catalogs


def catalog_summary_text(catalogs: dict[str, ProviderCatalog]) -> str:
    lines = []
    total = 0
    for name, cat in sorted(catalogs.items()):
        lines.append(
            f"{name}: {cat.status} ({cat.raw_count} models)"
            + (f" [err={cat.error}]" if cat.error else "")
        )
        total += cat.raw_count
    lines.append(f"-- total unique across providers: {total}")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pull frontier catalogs.")
    parser.add_argument("--providers", nargs="*", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args()

    state_dir = Path(args.state_dir) if args.state_dir else None
    cats = pull_all_catalogs(args.providers, state_dir=state_dir)
    print(catalog_summary_text(cats))
