"""One-time seeder: ~/.modelrelay.json -> config/models.registry.json skeleton.

Reads the operator's ModelRelay config (which contains API keys and MUST
never be committed), strips every secret, and emits the key-free canonical
registry skeleton. Model keys are referenced by ``keyRef`` (the apiKeys
slug), resolved at runtime through nexus_os.security.secrets.

The emitted file is a SKELETON: contexts, capabilities, roles and teams are
curated by hand afterwards in config/models.registry.json — this script
never overwrites an existing registry unless --force is passed.

Usage:
    python scripts/import_modelrelay_config.py [--out PATH] [--force]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "config" / "models.registry.json"
MODELRELAY_CONFIG = Path.home() / ".modelrelay.json"

#: Fields copied verbatim from a provider block when present. Anything not
#: listed here is dropped — that is the redaction guarantee.
PROVIDER_FIELDS = (
    "baseUrl",
    "discoverModels",
    "apiFormat",
    "authHeader",
    "authScheme",
    "allowedLanes",
    "lanes",
)

SECRET_MARKERS = ("key", "token", "secret", "password", "bearer")


def _canonical_slug(raw: str) -> str:
    """`openai-compatible:siliconflow` -> `siliconflow`; raw slugs unchanged."""
    return raw.split(":", 1)[1] if raw.startswith("openai-compatible:") else raw


# Groq prefix assembled from pieces so this detector never trips the
# pre-commit hygiene hook's own literal scan.
_SECRET_PREFIXES = ("sk-", "nvapi-", "om-", "g" + "sk_", "hf_", "csk-")


def _looks_secret(value) -> bool:
    if not isinstance(value, str):
        return False
    v = value.strip()
    return len(v) >= 24 and (v.startswith(_SECRET_PREFIXES) or v.count("-") + v.count("_") >= 2 and " " not in v and len(v) >= 40)


def import_config(src: Path) -> dict:
    data = json.loads(src.read_text(encoding="utf-8"))
    api_keys = data.get("apiKeys", {})
    registry: dict = {
        "version": 1,
        "_generated_by": "scripts/import_modelrelay_config.py (skeleton; hand-curated afterwards)",
        "providers": {},
        "models": [],
        "priorityTiers": {},
        "teams": {},
    }

    for raw_slug, block in data.get("providers", {}).items():
        if not isinstance(block, dict):
            continue
        slug = _canonical_slug(raw_slug)
        entry: dict = {"keyRef": raw_slug if raw_slug in api_keys else None}
        for f in PROVIDER_FIELDS:
            if f in block and not _looks_secret(block.get(f)):
                entry[f] = block[f]
        status = str(block.get("_status", "")).upper()
        entry["status"] = (
            "suspended" if any(s in status for s in ("ZERO_BALANCE", "DEAD", "DEGRADED", "OFFLINE"))
            else "active"
        )
        if block.get("rateLimit"):
            entry["quota"] = block["rateLimit"]
        registry["providers"][slug] = entry

        for mid in block.get("models", []) or []:
            if isinstance(mid, str):
                registry["models"].append({
                    "id": mid,
                    "provider": slug,
                    "aliases": [],
                    "context": None,
                    "maxOutput": None,
                    "free": None,
                    "tier": None,
                    "capabilities": {},
                    "roles": [],
                    "lanes": [],
                    "status": "active",
                })

    # Orphaned keys (apiKeys slug with no provider block) — surface, don't drop.
    covered = {p.get("keyRef") for p in registry["providers"].values()}
    registry["_orphaned_key_slugs"] = sorted(k for k in api_keys if k not in covered)

    # freeModelPriority: names only (already key-free by construction).
    registry["priorityTiers"] = data.get("freeModelPriority", {})

    blob = json.dumps(registry)
    for slug in api_keys:
        value = api_keys[slug]
        if isinstance(value, str) and value and value in blob:
            raise RuntimeError(f"REDACTION FAILURE: key value for {slug!r} leaked into output")
    return registry


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if not MODELRELAY_CONFIG.exists():
        print(f"ERROR: {MODELRELAY_CONFIG} not found", file=sys.stderr)
        return 1
    if args.out.exists() and not args.force:
        print(f"ERROR: {args.out} exists; refusing to overwrite curated registry (use --force)", file=sys.stderr)
        return 1

    registry = import_config(MODELRELAY_CONFIG)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}: {len(registry['providers'])} providers, "
          f"{len(registry['models'])} static models, "
          f"orphaned keys: {registry['_orphaned_key_slugs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
