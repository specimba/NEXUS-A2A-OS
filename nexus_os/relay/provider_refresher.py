"""Generic provider/model liveness refresher for the canonical registry.

Generalizes nvidia_refresher's suspend(7d)/deprecate(30d) state machine
across every provider in config/models.registry.json:

1. GET {baseUrl}{modelsPath} — cheap catalog listing.
2. For registered model IDs absent from the listing, an optional 1-token
   chat probe before suspending (several providers omit models from
   their listings while still serving them).

Health is persisted to a runtime sidecar (~/.nexus/registry_health.json),
NEVER into the committed registry — git stays deterministic; the sidecar
carries the live truth. `nexusctl models verify` prints the 3-way diff
(registry vs live listing vs health sidecar).

Keys resolve via nexus_os.security.secrets (keyRef slug -> env ->
~/.nexus/secrets.json -> ~/.modelrelay.json apiKeys); no literals.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from nexus_os.security.secrets import get_secret

logger = logging.getLogger("nexus.relay.provider_refresher")

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "config" / "models.registry.json"
HEALTH_SIDECAR = Path.home() / ".nexus" / "registry_health.json"

SUSPEND_AFTER_DAYS = 7
DEPRECATE_AFTER_DAYS = 30
PROBE_TIMEOUT_S = 15


@dataclass
class ProbeResult:
    provider: str
    reachable: bool
    listed_models: List[str] = field(default_factory=list)
    missing_from_listing: List[str] = field(default_factory=list)
    chat_confirmed: List[str] = field(default_factory=list)
    error: Optional[str] = None


def _key_for(prov: dict) -> str:
    ref = prov.get("keyRef")
    if not ref:
        return ""
    # keyRef IS the apiKeys slug; get_secret's provider= arg points the
    # ~/.modelrelay.json fallback straight at it.
    env_name = ref.split(":", 1)[-1].upper().replace("-", "_") + "_API_KEY"
    return get_secret(env_name, provider=ref)


class ProviderRefresher:
    """Registry-driven liveness prober with a persistent health sidecar."""

    def __init__(self, registry_path: Path = REGISTRY_PATH, sidecar_path: Path = HEALTH_SIDECAR):
        self.registry_path = registry_path
        self.sidecar_path = sidecar_path
        self.registry = json.loads(registry_path.read_text(encoding="utf-8"))
        self.health = self._load_sidecar()

    # ── Sidecar persistence ────────────────────────────────────────

    def _load_sidecar(self) -> dict:
        try:
            return json.loads(self.sidecar_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"models": {}, "providers": {}}

    def _save_sidecar(self) -> None:
        self.sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        self.sidecar_path.write_text(
            json.dumps(self.health, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ── Probing ────────────────────────────────────────────────────

    def probe_provider(self, slug: str, *, chat_probe_absentees: bool = True) -> ProbeResult:
        prov = self.registry["providers"].get(slug)
        if prov is None:
            return ProbeResult(provider=slug, reachable=False, error="not in registry")
        base = (prov.get("baseUrl") or "").rstrip("/")
        if not base:
            return ProbeResult(provider=slug, reachable=False, error="discovery-only (no baseUrl)")
        key = _key_for(prov)
        if prov.get("keyRef") and not key:
            return ProbeResult(provider=slug, reachable=False, error="no key resolvable for keyRef")

        headers = {"Content-Type": "application/json"}
        auth_header = prov.get("authHeader", "Authorization")
        scheme = prov.get("authScheme", "Bearer")
        if key:
            headers[auth_header] = key if auth_header != "Authorization" else f"{scheme} {key}"

        listed: List[str] = []
        try:
            resp = requests.get(f"{base}{prov.get('modelsPath', '/models')}", headers=headers, timeout=PROBE_TIMEOUT_S)
            if resp.ok:
                data = resp.json()
                items = data.get("data", data if isinstance(data, list) else [])
                listed = [m.get("id", "") for m in items if isinstance(m, dict)]
        except (requests.RequestException, ValueError) as exc:
            return ProbeResult(provider=slug, reachable=False, error=f"{exc.__class__.__name__}: {exc}")

        # Only registry-ACTIVE models count as expectations; suspended/
        # deprecated entries are already flagged in the registry itself.
        registered = [
            m["id"] for m in self.registry["models"]
            if m["provider"] == slug and m["status"] == "active"
        ]
        listed_set = set(listed)
        missing = [mid for mid in registered if mid not in listed_set]

        confirmed: List[str] = []
        if chat_probe_absentees and missing and key:
            for mid in missing[:5]:  # bounded — never hammer a provider
                if self._chat_probe(base, prov, headers, mid):
                    confirmed.append(mid)

        result = ProbeResult(
            provider=slug, reachable=True, listed_models=listed,
            missing_from_listing=missing, chat_confirmed=confirmed,
        )
        self._record(slug, registered, listed_set, set(confirmed))
        return result

    def _chat_probe(self, base: str, prov: dict, headers: dict, model_id: str) -> bool:
        try:
            resp = requests.post(
                f"{base}{prov.get('chatPath', '/chat/completions')}",
                headers=headers,
                json={"model": model_id, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                timeout=PROBE_TIMEOUT_S,
            )
            return resp.ok
        except requests.RequestException:
            return False

    # ── State machine (nvidia_refresher semantics, generalized) ───

    def _record(self, slug: str, registered: List[str], listed: set, confirmed: set) -> None:
        now = time.time()
        self.health.setdefault("providers", {})[slug] = {"last_probe": now, "listed_count": len(listed)}
        models = self.health.setdefault("models", {})
        for mid in registered:
            key = f"{slug}:{mid}"
            state = models.get(key, {"status": "active", "first_missing": None})
            if mid in listed or mid in confirmed:
                state = {"status": "active", "first_missing": None, "last_seen": now}
            else:
                first = state.get("first_missing") or now
                days_missing = (now - first) / 86400.0
                status = (
                    "deprecated" if days_missing >= DEPRECATE_AFTER_DAYS
                    else "suspended" if days_missing >= SUSPEND_AFTER_DAYS
                    else state.get("status", "active")
                )
                state = {"status": status, "first_missing": first, "last_seen": state.get("last_seen")}
            models[key] = state
        self._save_sidecar()

    # ── Reporting ──────────────────────────────────────────────────

    def diff_report(self, results: List[ProbeResult]) -> Dict[str, Any]:
        """3-way diff: registry vs live listing vs health sidecar."""
        report: Dict[str, Any] = {"providers": {}, "generated_at": time.time()}
        for r in results:
            entry: Dict[str, Any] = {
                "reachable": r.reachable,
                "error": r.error,
                "registered": len([m for m in self.registry["models"] if m["provider"] == r.provider]),
                "listed": len(r.listed_models),
                "missing_from_listing": r.missing_from_listing,
                "chat_confirmed_despite_missing": r.chat_confirmed,
            }
            sidecar = {
                k.split(":", 1)[1]: v["status"]
                for k, v in self.health.get("models", {}).items()
                if k.startswith(f"{r.provider}:") and v["status"] != "active"
            }
            entry["sidecar_flags"] = sidecar
            report["providers"][r.provider] = entry
        return report

    def refresh_all(self, *, only: Optional[str] = None, chat_probe: bool = True) -> List[ProbeResult]:
        results = []
        for slug, prov in self.registry["providers"].items():
            if only and slug != only:
                continue
            if prov["status"] in ("deprecated",):
                continue
            results.append(self.probe_provider(slug, chat_probe_absentees=chat_probe))
        return results
