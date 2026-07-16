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
from typing import Any, Iterable

from nexus_os.security.secrets import get_secret


PROVIDER_PROFILES = {
    # Public discovery surface: model metadata is available without consuming
    # inference credits.  It is a candidate source only, never a route
    # promotion signal.
    "openrouter": {
        "models_url": "https://openrouter.ai/api/v1/models?output_modalities=text&sort=newest",
        "auth_env": "OPENROUTER_API_KEY",
        "key_ref": "openrouter",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "requires_auth": False,
        "timeout_seconds": 12,
        "rpm_floor": 0.05,
        "data_path": "data.id",
    },
    "nvidia": {
        "models_url": "https://integrate.api.nvidia.com/v1/models",
        "auth_env": "NVIDIA_API_KEY",
        "key_ref": "nvidia",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout_seconds": 12,
        "rpm_floor": 0.05,
        "data_path": "data.id",
    },
    "ollama-cloud": {
        "models_url": "https://ollama.com/v1/models",
        "auth_env": "OLLAMA_CLOUD_API_KEY",
        "key_ref": "ollama-cloud",
        "timeout_seconds": 10,
        "rpm_floor": 0.05,
        "data_path": "data.id",
    },
    "longcat": {
        "models_url": "https://api.longcat.chat/openai/v1/models",
        "auth_env": "LONGCAT_API_KEY",
        "key_ref": "longcat",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout_seconds": 10,
        "rpm_floor": 0.05,
        "data_path": "data.id",
    },
    "internai": {
        "models_url": "https://chat.intern-ai.org.cn/api/v1/models",
        "auth_env": "INTERN_API_KEY",
        "key_ref": "internai",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout_seconds": 10,
        "rpm_floor": 0.05,
        "data_path": "data.id",
    },
    "mistral": {
        "models_url": "https://api.mistral.ai/v1/models",
        "auth_env": "MISTRAL_API_KEY",
        "key_ref": "openai-compatible:mistral",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout_seconds": 10,
        "rpm_floor": 0.05,
        "data_path": "data.id",
    },
    "groq": {
        "models_url": "https://api.groq.com/openai/v1/models",
        "auth_env": "GROQ_API_KEY",
        "key_ref": "groq",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout_seconds": 10,
        "rpm_floor": 0.05,
        "data_path": "data.id",
    },
    "codestral": {
        "models_url": "https://codestral.mistral.ai/v1/models",
        "auth_env": "CODESTRAL_API_KEY",
        "key_ref": "codestral",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout_seconds": 10,
        "rpm_floor": 0.05,
        "data_path": "data.id",
        "skip_catalog_when_404": True,
        "_comment": "no_list_endpoint_only_chat",
    },
    "github": {
        # GitHub's current catalog is distinct from its inference endpoint.
        # The catalog includes capabilities and published rate-limit tier.
        "models_url": "https://models.github.ai/catalog/models",
        "auth_env": "GITHUB_API_KEY",
        "key_ref": "openai-compatible:github",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "extra_headers": {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        },
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
    # A bounded, non-secret metadata excerpt for newly discovered model IDs.
    # It is evidence for a source card, not a benchmark score or a registry
    # promotion authority.
    model_metadata: dict[str, dict[str, Any]] = field(default_factory=dict)


def _walk_path(obj: dict, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _read_key(env: str, key_ref: str | None = None) -> str:
    """Use the one sanctioned resolver; never log or serialize the value."""
    return get_secret(env, provider=key_ref or None)


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


def _catalog_rows(payload: Any, profile: dict) -> list[dict[str, Any]]:
    """Return catalogue rows for optional, bounded metadata extraction."""
    raw_root_path = profile.get("raw_root_path", "")
    if raw_root_path == "" and isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if raw_root_path:
        current: Any = payload
        for part in raw_root_path.split("."):
            if not isinstance(current, dict):
                return []
            current = current.get(part)
        return [row for row in current if isinstance(row, dict)] if isinstance(current, list) else []
    data_path = str(profile.get("data_path", "data.id"))
    root_name = data_path.split(".", 1)[0]
    rows = _walk_path(payload, root_name) if isinstance(payload, dict) else None
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _bounded_metadata(row: dict[str, Any]) -> dict[str, Any]:
    """Extract stable, non-secret discovery facts from a provider row.

    Provider catalogues evolve independently.  We preserve only fields that
    inform later operator review (context, modality, tool support, limits and
    a *hint* about free pricing) and cap every collection before persistence.
    """
    metadata: dict[str, Any] = {}
    for key in ("canonical_slug", "name", "publisher", "created", "expiration_date", "rate_limit_tier"):
        value = row.get(key)
        if isinstance(value, (str, int, float, bool)):
            text = str(value)
            metadata[key] = text[:256] if isinstance(value, str) else value

    limits = row.get("limits") if isinstance(row.get("limits"), dict) else {}
    context = row.get("context_length", limits.get("max_input_tokens"))
    max_output = row.get("max_output_tokens", limits.get("max_output_tokens"))
    for key, value in (("context_tokens", context), ("max_output_tokens", max_output)):
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
            metadata[key] = int(value)

    for source_key, target_key in (
        ("supported_parameters", "supported_parameters"),
        ("capabilities", "capabilities"),
        ("supported_input_modalities", "input_modalities"),
        ("supported_output_modalities", "output_modalities"),
    ):
        value = row.get(source_key)
        if isinstance(value, list):
            metadata[target_key] = [str(item)[:128] for item in value[:32] if isinstance(item, (str, int, float, bool))]

    pricing = row.get("pricing")
    if isinstance(pricing, dict):
        safe_pricing = {
            str(key)[:64]: str(value)[:64]
            for key, value in pricing.items()
            if isinstance(key, str) and isinstance(value, (str, int, float))
        }
        if safe_pricing:
            metadata["pricing"] = safe_pricing
            numeric = []
            for value in safe_pricing.values():
                try:
                    numeric.append(float(value))
                except ValueError:
                    pass
            if numeric and all(value == 0.0 for value in numeric):
                metadata["free_hint"] = "zero_catalog_pricing"
    return metadata


def _extract_metadata(payload: Any, profile: dict, model_ids: list[str]) -> dict[str, dict[str, Any]]:
    allowed = set(model_ids)
    metadata: dict[str, dict[str, Any]] = {}
    for row in _catalog_rows(payload, profile):
        model_id = row.get("id") or row.get("modelId") or row.get("model") or row.get("name")
        if not isinstance(model_id, str) or model_id not in allowed:
            continue
        excerpt = _bounded_metadata(row)
        if model_id.endswith(":free"):
            excerpt.setdefault("free_hint", "id_suffix")
        if excerpt:
            metadata[model_id] = excerpt
    return metadata


def pull_provider_catalog(provider: str, profile: dict) -> ProviderCatalog:
    out = ProviderCatalog(
        provider=provider,
        fetched_at=time.time(),
        source_url=profile["models_url"],
    )
    key = _read_key(profile["auth_env"], profile.get("key_ref"))
    if not key and profile.get("requires_auth", True):
        out.error = "no_key_resolvable"
        out.status = "no_key"
        return out
    headers = {"User-Agent": "NEXUS-FrontierScanner/0.1"}
    extra_headers = profile.get("extra_headers")
    if isinstance(extra_headers, dict):
        headers.update({str(name): str(value) for name, value in extra_headers.items()})
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
            out.model_metadata = _extract_metadata(payload, profile, ids)
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
