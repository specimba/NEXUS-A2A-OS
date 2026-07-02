"""Central secret resolution for NEXUS OS.

Audit P0 (2026-06-29): provider key literals were committed in tracked
files. The scrub removed them; this module is the sanctioned way for
code to obtain keys afterwards — no call site should ever carry a
literal fallback again.

Resolution order for ``get_secret("NVIDIA_API_KEY")``:

1. Environment variable of the same name.
2. NEXUS secrets vault file: ``$NEXUS_SECRETS_FILE`` if set, else
   ``~/.nexus/secrets.json`` — a flat ``{"NAME": "value"}`` JSON map
   kept outside the repository.
3. The ModelRelay operator config ``~/.modelrelay.json`` (override via
   ``$MODELRELAY_CONFIG``): ``apiKeys[<provider slug>]``. The slug is
   passed explicitly or derived from the conventional
   ``<PROVIDER>_API_KEY`` name (``LONGCAT_API_KEY`` -> ``longcat``).

Values are never logged. Missing or unreadable stores are treated as
"no secret there", not as errors — use :func:`require_secret` for the
hard-fail contract.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nexus.security.secrets")

__all__ = ["MissingSecretError", "get_secret", "require_secret"]


class MissingSecretError(RuntimeError):
    """Raised by require_secret when no source provides the secret."""


def _vault_path() -> Path:
    override = os.environ.get("NEXUS_SECRETS_FILE", "")
    if override:
        return Path(override)
    return Path.home() / ".nexus" / "secrets.json"


def _modelrelay_config_path() -> Path:
    override = os.environ.get("MODELRELAY_CONFIG", "")
    if override:
        return Path(override)
    return Path.home() / ".modelrelay.json"


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _provider_slug(name: str) -> Optional[str]:
    """Derive the ModelRelay apiKeys slug from a conventional env name.

    ``NVIDIA_API_KEY`` -> ``nvidia``; names not ending in ``_API_KEY``
    have no derivable slug.
    """
    if name.endswith("_API_KEY") and len(name) > len("_API_KEY"):
        return name[: -len("_API_KEY")].lower()
    return None


def get_secret(name: str, *, provider: Optional[str] = None, default: str = "") -> str:
    """Resolve a secret by name: env var, then vault file, then ModelRelay apiKeys."""
    value = os.environ.get(name, "")
    if value:
        return value

    vault = _read_json(_vault_path())
    value = vault.get(name, "")
    if isinstance(value, str) and value:
        return value

    slug = provider or _provider_slug(name)
    if slug:
        api_keys = _read_json(_modelrelay_config_path()).get("apiKeys", {})
        if isinstance(api_keys, dict):
            value = api_keys.get(slug, "")
            if isinstance(value, str) and value:
                return value

    return default


def require_secret(name: str, *, provider: Optional[str] = None) -> str:
    """Resolve a secret or raise MissingSecretError (hard-fail default).

    The error names the secret and the sources consulted but never a value.
    """
    value = get_secret(name, provider=provider)
    if not value:
        raise MissingSecretError(
            f"Secret {name!r} not found in environment, "
            f"{_vault_path()}, or {_modelrelay_config_path()} apiKeys. "
            "No committed fallback exists by design (audit P0)."
        )
    return value
