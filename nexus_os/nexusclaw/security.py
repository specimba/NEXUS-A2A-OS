"""NexusClaw Core V0 security gates."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from pathlib import PurePath
from typing import Any
from urllib.parse import urlparse


SAFE_REMOTE_TRANSPORTS = {"http", "https", "sse", "streamable_http", "websocket", "ws", "wss"}
FORBIDDEN_REMOTE_TRANSPORTS = {"stdio"}
SAFE_GATEWAY_SCHEMES = {"ws", "wss", "http", "https"}
SAFE_GATEWAY_HOSTS = {"localhost", "127.0.0.1", "::1"}
SENSITIVE_CONFIG_KEYS = {
    "approval",
    "approvals",
    "approval_policy",
    "ask",
    "sandbox",
    "sandbox_mode",
    "permission_mode",
    "permissions",
    "trustedproxies",
    "trusted_proxies",
    "gateway_url",
    "gatewayurl",
    "tools.exec.host",
}
FORBIDDEN_MODEL_SUFFIXES = {".pkl", ".pickle", ".bin", ".pt", ".pth", ".ckpt"}
QUARANTINE_LABELS = {
    "abliterated",
    "uncensored",
    "heretic",
    "jailbreak",
    "red-team",
    "red_team",
    "harmbench",
    "nsfw",
}


@dataclass(frozen=True)
class SecurityDecision:
    allowed: bool
    reason: str
    severity: str = "info"

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "severity": self.severity,
        }


def validate_mcp_transport(transport: str, *, remote: bool) -> SecurityDecision:
    normalized = transport.strip().lower().replace("-", "_")
    if not normalized:
        return SecurityDecision(False, "transport is required", "high")
    if remote and normalized in FORBIDDEN_REMOTE_TRANSPORTS:
        return SecurityDecision(False, "remote stdio transport is forbidden", "critical")
    if remote and normalized not in SAFE_REMOTE_TRANSPORTS:
        return SecurityDecision(False, f"remote transport {transport!r} is not allowlisted", "high")
    return SecurityDecision(True, "transport accepted")


def validate_openclaw_gateway(
    gateway_url: str,
    *,
    origin: str,
    token_bound: bool,
    allowed_origins: set[str] | None = None,
) -> SecurityDecision:
    parsed = urlparse(gateway_url)
    if parsed.scheme not in SAFE_GATEWAY_SCHEMES:
        return SecurityDecision(False, "gatewayUrl scheme is not allowlisted", "critical")
    if parsed.username or parsed.password:
        return SecurityDecision(False, "gatewayUrl must not contain userinfo credentials", "critical")
    if parsed.query:
        return SecurityDecision(False, "gatewayUrl must not carry tokens or config in query params", "critical")
    if not token_bound:
        return SecurityDecision(False, "OpenClaw gateway requires a bound access token", "critical")

    host = parsed.hostname or ""
    if not _is_safe_gateway_host(host):
        return SecurityDecision(False, "gatewayUrl host must be localhost or Tailscale-scoped", "high")

    origin_set = allowed_origins or {
        "http://localhost",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "https://localhost",
    }
    normalized_origin = origin.rstrip("/")
    if (
        normalized_origin not in {item.rstrip("/") for item in origin_set}
        and not _is_safe_origin(normalized_origin)
    ):
        return SecurityDecision(False, "WebSocket Origin is not allowlisted", "critical")

    return SecurityDecision(True, "OpenClaw gateway accepted")


def validate_runtime_config_patch(
    patch: dict[str, Any] | list[dict[str, Any]],
    *,
    kaiju_approved: bool,
    vap_record_id: str | None,
) -> SecurityDecision:
    touched_keys = _flatten_keys(patch)
    sensitive_hits = sorted(key for key in touched_keys if _is_sensitive_config_key(key))
    if sensitive_hits and (not kaiju_approved or not vap_record_id):
        return SecurityDecision(
            False,
            "approval/sandbox/security config patches require KAIJU approval and VAP record",
            "critical",
        )
    return SecurityDecision(True, "runtime config patch accepted")


def validate_model_intake(
    model_path_or_name: str,
    *,
    trust_remote_code: bool = False,
    labels: list[str] | None = None,
) -> SecurityDecision:
    lowered_name = model_path_or_name.lower()
    suffix = PurePath(lowered_name).suffix
    if suffix in FORBIDDEN_MODEL_SUFFIXES:
        return SecurityDecision(False, "pickle model artifacts are blocked", "critical")
    if trust_remote_code:
        return SecurityDecision(False, "trust_remote_code is blocked for NexusClaw intake", "critical")

    label_text = " ".join(labels or []) + " " + lowered_name
    if any(label in label_text for label in QUARANTINE_LABELS):
        return SecurityDecision(False, "model label requires quarantine before routing", "high")
    return SecurityDecision(True, "model intake accepted")


def _flatten_keys(value: dict[str, Any], prefix: str = "") -> set[str]:
    keys: set[str] = set()
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                keys.update(_flatten_keys(item, prefix))
        return keys
    for key, item in value.items():
        key_text = str(key)
        path = f"{prefix}.{key_text}" if prefix else key_text
        keys.add(path)
        keys.add(key_text)
        if key_text == "path" and isinstance(item, str):
            keys.add(item.strip("/").replace("/", "."))
        if isinstance(item, dict):
            keys.update(_flatten_keys(item, path))
    return keys


def _is_sensitive_config_key(key: str) -> bool:
    normalized = key.replace("-", "_").lower()
    if normalized in SENSITIVE_CONFIG_KEYS:
        return True
    return any(part in SENSITIVE_CONFIG_KEYS for part in normalized.split("."))


def _is_safe_gateway_host(host: str) -> bool:
    if host in SAFE_GATEWAY_HOSTS or host.endswith(".ts.net"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip in ipaddress.ip_network("100.64.0.0/10")


def _is_safe_origin(origin: str) -> bool:
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname or ""
    if host in SAFE_GATEWAY_HOSTS:
        return True
    return host.endswith(".ts.net") or _is_safe_gateway_host(host)
