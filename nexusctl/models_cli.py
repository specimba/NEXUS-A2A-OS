"""`nexusctl models verify` — registry vs live-provider vs health-sidecar diff.

Read-only against providers (GET /models listings + bounded 1-token chat
probes for absentees); writes only the runtime health sidecar at
~/.nexus/registry_health.json. Never touches the committed registry.
"""
from __future__ import annotations

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
