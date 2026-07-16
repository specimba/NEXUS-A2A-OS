"""Safely reconcile governed partner endpoints into Node ModelRelay.

This is intentionally a configuration-only tool.  Its default mode is a
read-only report.  ``--apply`` is the only write path and it is deliberately
staged (disabled) unless ``--activate`` is supplied as a second explicit
operator decision.  It never calls a provider, restarts ModelRelay, changes a
client default, or prints secret values.

The Node runtime recognises OpenAI-compatible endpoint instance keys such as
``openai-compatible:longcat``.  Historical top-level ``longcat`` and
``internai`` records are preserved for older adapters, but they are not a
substitute for those canonical runtime endpoint records.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


MANAGED_FIELD = "nexusManaged"
MANAGED_VALUE = "partner-provider-reconcile-v1"
DEFAULT_RELAY_URL = "http://127.0.0.1:7350"

# These records deliberately mirror the secret-free adapter contracts.  The
# config key is separate from the legacy native provider key because the Node
# relay only dynamically instantiates ``openai-compatible:<id>`` endpoints.
PARTNER_ENDPOINTS: dict[str, dict[str, Any]] = {
    "longcat": {
        "legacy_provider_key": "longcat",
        "endpoint_key": "openai-compatible:longcat",
        "name": "LongCat (governed partner)",
        "base_url": "https://api.longcat.chat/openai/v1",
        "model_id": "LongCat-2.0",
        "discover_models": False,
        "key_env_order": (
            "LONGCAT_MODELRELAY_API_KEY",
            "NEXUS_LONGCAT_API_KEY",
            "LONGCAT_API_KEY",
        ),
    },
    "internai": {
        "legacy_provider_key": "internai",
        "endpoint_key": "openai-compatible:internai",
        "name": "InternAI (governed partner)",
        "base_url": "https://chat.intern-ai.org.cn/api/v1",
        # The known general route is the safe fallback if GET /models is not
        # available.  Model discovery is metadata-only and is enabled only
        # after an operator explicitly activates this staged endpoint.
        "model_id": "intern-latest",
        "discover_models": True,
        "key_env_order": (
            "INTERN_MODELRELAY_API_KEY",
            "INTERN_API_KEY",
            "INTERN_API_KEY_2",
        ),
    },
}


class ConfigValidationError(ValueError):
    """A config could not be safely read, shaped, or round-tripped."""


def default_config_path() -> Path:
    """Respect an explicit runtime path while retaining ModelRelay's default."""

    configured = os.environ.get("MODELRELAY_CONFIG_PATH", "").strip()
    return Path(configured).expanduser() if configured else Path.home() / ".modelrelay.json"


def _normal_url(value: object) -> str:
    return str(value or "").strip().rstrip("/")


def _read_config(path: Path) -> tuple[bytes, dict[str, Any]]:
    if not path.exists() or not path.is_file() or path.is_symlink():
        raise ConfigValidationError("config_not_regular_file")
    try:
        raw = path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        # Never surface parser payloads: they may include a line containing a
        # credential in a malformed config.
        raise ConfigValidationError(f"config_unreadable_{type(exc).__name__}") from None
    if not isinstance(parsed, dict):
        raise ConfigValidationError("config_root_not_object")
    for key in ("apiKeys", "providers"):
        value = parsed.get(key)
        if value is not None and not isinstance(value, dict):
            raise ConfigValidationError(f"config_{key}_not_object")
    return raw, parsed


def _env_secret(spec: Mapping[str, Any], environ: Mapping[str, str]) -> tuple[str | None, str | None]:
    """Pick a non-empty secret without exposing it to a report."""

    for name in spec["key_env_order"]:
        value = environ.get(name)
        if isinstance(value, str) and value.strip():
            return name, value.strip()
    return None, None


def _proposed_record(spec: Mapping[str, Any], *, enabled: bool) -> dict[str, Any]:
    return {
        "name": spec["name"],
        "baseUrl": spec["base_url"],
        "modelId": spec["model_id"],
        "enabled": bool(enabled),
        "discoverModels": bool(spec["discover_models"]),
        MANAGED_FIELD: MANAGED_VALUE,
    }


def _endpoint_state(config: Mapping[str, Any], spec: Mapping[str, Any]) -> str:
    providers = config.get("providers") if isinstance(config.get("providers"), Mapping) else {}
    existing = providers.get(spec["endpoint_key"])
    if existing is None:
        return "missing"
    if not isinstance(existing, Mapping):
        return "conflict_unmanaged"
    if existing.get(MANAGED_FIELD) == MANAGED_VALUE:
        return "managed_active" if existing.get("enabled") is not False else "managed_staged"

    # An exact operator-owned record is already usable; do not take ownership
    # or overwrite it.  Any other record under the same endpoint key is a
    # conflict, even if it happens to share one field with the proposed one.
    if (
        _normal_url(existing.get("baseUrl")) == _normal_url(spec["base_url"])
        and str(existing.get("modelId") or "").strip() == str(spec["model_id"])
    ):
        return "compatible_unmanaged"
    return "conflict_unmanaged"


def _legacy_summary(config: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    providers = config.get("providers") if isinstance(config.get("providers"), Mapping) else {}
    api_keys = config.get("apiKeys") if isinstance(config.get("apiKeys"), Mapping) else {}
    legacy = providers.get(spec["legacy_provider_key"])
    if not isinstance(legacy, Mapping):
        return {"legacy_record_present": False, "legacy_key_configured": False, "legacy_models": []}
    models = legacy.get("models")
    safe_models = [str(item) for item in models if isinstance(item, (str, int, float))] if isinstance(models, list) else []
    return {
        "legacy_record_present": True,
        "legacy_key_configured": bool(api_keys.get(spec["legacy_provider_key"])),
        "legacy_models": safe_models,
    }


def _provider_report(config: Mapping[str, Any], provider: str, environ: Mapping[str, str]) -> dict[str, Any]:
    spec = PARTNER_ENDPOINTS[provider]
    selected_env, secret = _env_secret(spec, environ)
    report = {
        "endpoint_key": spec["endpoint_key"],
        "endpoint_state": _endpoint_state(config, spec),
        "selected_key_env": selected_env,
        "key_available_in_environment": secret is not None,
        "key_env_order": list(spec["key_env_order"]),
        "proposed_record": _proposed_record(spec, enabled=False),
        **_legacy_summary(config, spec),
    }
    # Secret is deliberately not returned.  It is resolved again only inside
    # the explicitly requested write path.
    return report


def _strip_targeted_records(config: Mapping[str, Any], endpoint_keys: tuple[str, ...]) -> dict[str, Any]:
    """Copy a config with only the intended nested mutation sites removed."""

    clone = copy.deepcopy(dict(config))
    for root in ("apiKeys", "providers"):
        source_had_root = root in config
        bucket = clone.get(root)
        if isinstance(bucket, dict):
            for endpoint_key in endpoint_keys:
                bucket.pop(endpoint_key, None)
            if not bucket and not source_had_root:
                clone.pop(root, None)
    return clone


def _validate_candidate_roundtrip(original: Mapping[str, Any], candidate: Mapping[str, Any], endpoint_keys: tuple[str, ...]) -> str:
    if _strip_targeted_records(original, endpoint_keys) != _strip_targeted_records(candidate, endpoint_keys):
        raise ConfigValidationError("unrelated_config_changed")
    try:
        serialized = json.dumps(candidate, indent=2, ensure_ascii=False) + "\n"
        reparsed = json.loads(serialized)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ConfigValidationError(f"candidate_not_roundtrippable_{type(exc).__name__}") from None
    if reparsed != candidate:
        raise ConfigValidationError("candidate_roundtrip_mismatch")
    return serialized


def _atomic_write_with_backup(path: Path, original: bytes, rendered: str) -> None:
    """Keep an exact backup and replace only after all validation is complete."""

    backup = path.with_name(path.name + ".partner-reconcile.bak")
    temp_name: str | None = None
    try:
        backup.write_bytes(original)
        try:
            os.chmod(backup, 0o600)
        except OSError:
            pass
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=path.name + ".partner-reconcile-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
            temp_name = handle.name
        try:
            os.chmod(temp_name, 0o600)
        except OSError:
            pass
        os.replace(temp_name, path)
        temp_name = None
    except OSError as exc:
        raise ConfigValidationError(f"config_write_failed_{type(exc).__name__}") from None
    finally:
        if temp_name:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass


def reconcile_file(
    path: Path,
    *,
    providers: tuple[str, ...] = tuple(PARTNER_ENDPOINTS),
    apply: bool = False,
    activate: bool = False,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build a secret-safe report and optionally apply a validated config edit."""

    environment = os.environ if environ is None else environ
    selected = tuple(dict.fromkeys(providers))
    unknown = [provider for provider in selected if provider not in PARTNER_ENDPOINTS]
    if unknown:
        raise ValueError("unknown_partner_provider")
    if activate and not apply:
        raise ValueError("activate_requires_apply")

    report: dict[str, Any] = {
        "schema_version": 1,
        "tool": "nexus.partner-modelrelay-reconcile",
        "mode": "report",
        "config_path": str(path),
        "providers": {},
        "inference_performed": False,
        "restart_performed": False,
        "client_default_changed": False,
        "routing_eligibility_after_refresh": "unchanged",
        "apply": {"requested": bool(apply), "ok": None, "reason": None, "backup_path": None},
    }

    try:
        original_bytes, original = _read_config(path)
    except ConfigValidationError as exc:
        report["config_state"] = str(exc)
        report["apply"]["ok"] = False if apply else None
        report["apply"]["reason"] = "config_not_safe_to_modify" if apply else None
        return report

    report["config_state"] = "roundtrippable"
    report["providers"] = {
        provider: _provider_report(original, provider, environment) for provider in selected
    }
    if not apply:
        return report

    missing_env = [
        provider for provider in selected if not report["providers"][provider]["key_available_in_environment"]
    ]
    if missing_env:
        report["apply"]["ok"] = False
        report["apply"]["reason"] = "required_environment_key_missing"
        report["apply"]["missing_key_for"] = missing_env
        return report

    conflicts = [
        provider
        for provider in selected
        if report["providers"][provider]["endpoint_state"] == "conflict_unmanaged"
    ]
    if conflicts:
        report["apply"]["ok"] = False
        report["apply"]["reason"] = "unmanaged_endpoint_conflict"
        report["apply"]["conflicts"] = conflicts
        return report

    candidate = copy.deepcopy(original)
    candidate.setdefault("apiKeys", {})
    candidate.setdefault("providers", {})
    if not isinstance(candidate["apiKeys"], dict) or not isinstance(candidate["providers"], dict):
        # Defensive redundancy: _read_config already validates this shape.
        report["apply"]["ok"] = False
        report["apply"]["reason"] = "config_not_safe_to_modify"
        return report

    endpoint_keys: list[str] = []
    for provider in selected:
        spec = PARTNER_ENDPOINTS[provider]
        endpoint_key = spec["endpoint_key"]
        endpoint_keys.append(endpoint_key)
        _, secret = _env_secret(spec, environment)
        # The preflight above proved presence.  Keep failure closed if the
        # process environment changes between report and write.
        if not secret:
            report["apply"]["ok"] = False
            report["apply"]["reason"] = "required_environment_key_missing"
            return report
        current_state = report["providers"][provider]["endpoint_state"]
        if current_state != "compatible_unmanaged":
            candidate["providers"][endpoint_key] = _proposed_record(spec, enabled=activate)
        # A matching operator-owned record is left exactly as-is.  It is
        # already a valid runtime endpoint and must not be silently claimed.
        candidate["apiKeys"][endpoint_key] = secret

    try:
        rendered = _validate_candidate_roundtrip(original, candidate, tuple(endpoint_keys))
        if candidate != original:
            _atomic_write_with_backup(path, original_bytes, rendered)
            report["apply"]["backup_path"] = str(path.with_name(path.name + ".partner-reconcile.bak"))
        report["apply"]["ok"] = True
        report["apply"]["reason"] = "applied" if candidate != original else "already_reconciled"
    except ConfigValidationError as exc:
        report["apply"]["ok"] = False
        report["apply"]["reason"] = "roundtrip_or_write_guard_failed"
        report["config_state"] = str(exc)
        return report

    report["mode"] = "applied_active" if activate else "applied_staged"
    report["routing_eligibility_after_refresh"] = "may_become_eligible" if activate else "staged_disabled"
    return report


FetchJson = Callable[[str, float], Any]


def _fetch_json(url: str, timeout: float) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def probe_runtime(relay_url: str, *, fetch_json: FetchJson = _fetch_json, timeout: float = 3.0) -> dict[str, Any]:
    """Read only the safe local config/model endpoints; never probe a model."""

    base = relay_url.rstrip("/")
    report: dict[str, Any] = {
        "checked": False,
        "relay_url": base,
        "inference_performed": False,
        "providers": {
            name: {"endpoint_configured": False, "model_rows": []} for name in PARTNER_ENDPOINTS
        },
        "errors": {},
    }
    try:
        config_payload = fetch_json(f"{base}/api/config", timeout)
        config_rows = config_payload if isinstance(config_payload, list) else []
        endpoint_keys = {
            str(row.get("key") or row.get("providerKey") or "")
            for row in config_rows
            if isinstance(row, Mapping)
        }
        for name, spec in PARTNER_ENDPOINTS.items():
            report["providers"][name]["endpoint_configured"] = spec["endpoint_key"] in endpoint_keys
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, ValueError, json.JSONDecodeError) as exc:
        report["errors"]["config"] = type(exc).__name__

    try:
        models_payload = fetch_json(f"{base}/api/models", timeout)
        model_rows = models_payload.get("models", []) if isinstance(models_payload, Mapping) else []
        for name, spec in PARTNER_ENDPOINTS.items():
            report["providers"][name]["model_rows"] = [
                {
                    "model_id": str(row.get("modelId") or ""),
                    "status": str(row.get("status") or "unknown"),
                }
                for row in model_rows
                if isinstance(row, Mapping) and row.get("providerKey") == spec["endpoint_key"]
            ]
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, ValueError, json.JSONDecodeError) as exc:
        report["errors"]["models"] = type(exc).__name__

    report["checked"] = not report["errors"]
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely reconcile LongCat and InternAI ModelRelay endpoint records")
    parser.add_argument("--config", type=Path, default=default_config_path(), help="ModelRelay JSON config path")
    parser.add_argument("--relay-url", default=DEFAULT_RELAY_URL, help="Local ModelRelay URL for read-only representation check")
    parser.add_argument("--no-runtime-check", action="store_true", help="Skip read-only GET checks against the local relay")
    parser.add_argument("--provider", action="append", choices=sorted(PARTNER_ENDPOINTS), help="Limit to a partner provider (repeatable)")
    parser.add_argument("--apply", action="store_true", help="Write validated endpoint records; default is report-only")
    parser.add_argument("--activate", action="store_true", help="Enable records after --apply; otherwise write staged disabled records")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.activate and not args.apply:
        parser.error("--activate requires --apply")
    selected = tuple(args.provider or PARTNER_ENDPOINTS.keys())
    report = reconcile_file(
        args.config,
        providers=selected,
        apply=args.apply,
        activate=args.activate,
    )
    if not args.no_runtime_check:
        report["runtime"] = probe_runtime(args.relay_url)
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if args.apply and report["apply"]["ok"] is not True:
        return 2
    return 0 if report.get("config_state") == "roundtrippable" else 2


if __name__ == "__main__":
    raise SystemExit(main())
