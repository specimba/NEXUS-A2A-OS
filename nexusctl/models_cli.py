"""`nexusctl models verify` — registry vs live-provider vs health-sidecar diff.

Read-only against providers (GET /models listings + bounded 1-token chat
probes for absentees); writes only the runtime health sidecar at
~/.nexus/registry_health.json. Never touches the committed registry.
"""
from __future__ import annotations

import copy
import json


def run_models_verify(provider: str | None = None, no_chat_probe: bool = False) -> int:
    from nexus_os.relay.provider_refresher import ProviderRefresher

    refresher = ProviderRefresher()
    results = refresher.refresh_all(only=provider, chat_probe=not no_chat_probe)
    report = refresher.diff_report(results)

    ok = 0
    for slug, entry in sorted(report["providers"].items()):
        if not entry["reachable"]:
            print(f"[--] {slug:<14} UNREACHABLE: {entry['error']}")
            continue
        missing = entry["missing_from_listing"]
        confirmed = entry["chat_confirmed_despite_missing"]
        truly_missing = [m for m in missing if m not in confirmed]
        flag = "[OK]" if not truly_missing else "[!!]"
        if not truly_missing:
            ok += 1
        print(
            f"{flag} {slug:<14} registered={entry['registered']:<3} "
            f"listed={entry['listed']:<4} missing={len(truly_missing)} "
            f"chat-confirmed={len(confirmed)}"
        )
        for mid in truly_missing:
            side = entry["sidecar_flags"].get(mid, "active")
            print(f"       MISSING {mid}  (sidecar: {side})")

    print(json.dumps({"summary": {"providers_probed": len(report["providers"]), "fully_ok": ok}}, indent=2))
    return 0


def run_models_reconcile(provider: str | None = None, dry_run: bool = True) -> int:
    """Compare active registry models to provider listings without chat fan-out."""
    from nexus_os.relay.provider_refresher import ProviderRefresher

    refresher = ProviderRefresher(persist=not dry_run)
    results = refresher.refresh_all(only=provider, chat_probe=False)
    report = refresher.diff_report(results)
    report["dry_run"] = dry_run
    report["chat_probes"] = 0
    report["sidecar_written"] = not dry_run
    print(json.dumps(report, indent=2, sort_keys=True))
    healthy = all(
        entry["reachable"] and not entry["missing_from_listing"]
        for entry in report["providers"].values()
    )
    return 0 if healthy else 2


def run_models_status(provider: str | None = None) -> int:
    """Return committed registry plus runtime sidecar state without network calls."""
    from nexus_os.relay.provider_refresher import ProviderRefresher

    refresher = ProviderRefresher(persist=False)
    registry = refresher.registry
    providers = registry.get("providers", {})
    if provider:
        providers = {provider: providers.get(provider)} if provider in providers else {}
    models = []
    for model in registry.get("models", []):
        if provider and model["provider"] != provider:
            continue
        committed_status = model["status"]
        runtime_status = (
            refresher.health.get("models", {})
            .get(f"{model['provider']}:{model['id']}", {})
            .get("status", "unknown")
        )
        if committed_status != "active":
            runtime_status = committed_status
        models.append(
            {
                "provider": model["provider"],
                "id": model["id"],
                "status": committed_status,
                "context": model.get("context"),
                "roles": model.get("roles", []),
                "lanes": model.get("lanes", []),
                "runtime_status": runtime_status,
            }
        )
    safe_providers = copy.deepcopy(providers)
    for config in safe_providers.values():
        if isinstance(config, dict):
            config.pop("api_key", None)
    print(json.dumps({"providers": safe_providers, "models": models}, indent=2, sort_keys=True))
    return 0 if providers else 2
