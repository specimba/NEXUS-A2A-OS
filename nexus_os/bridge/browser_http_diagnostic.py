"""Governed browser HTTP diagnostics through the GROSS bridge.

This module turns the GROSS ``http_diagnostic`` MCP tool into a bounded NEXUS
capability for browser-agent work. It does not provide general internet access:
requests are HTTPS-only, read-only, private-network targets are blocked, and
domains must match an explicit allowlist.
"""

from __future__ import annotations

import ipaddress
import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_ALLOWED_HOSTS = frozenset(
    {
        "huggingface.co",
        "hf.co",
        "cdn-lfs.huggingface.co",
        "raw.githubusercontent.com",
        "github.com",
        "pypi.org",
        "files.pythonhosted.org",
        "grok.com",
        "files.grok.com",
    }
)

BLOCKED_HEADER_PREFIXES = (
    "authorization",
    "cookie",
    "proxy-authorization",
    "x-api-key",
    "x-auth-token",
    "x-csrf-token",
    "x-xsrf-token",
)


@dataclass(frozen=True)
class BrowserDiagnosticPolicy:
    """Policy for browser/Grok diagnostic requests."""

    allowed_hosts: frozenset[str] = DEFAULT_ALLOWED_HOSTS
    allowed_methods: frozenset[str] = frozenset({"GET", "HEAD"})
    max_preview_bytes: int = 500
    max_timeout_seconds: float = 15.0
    require_https: bool = True
    block_private_targets: bool = True

    @classmethod
    def from_env(cls, prefix: str = "NEXUS_BROWSER_HTTP") -> "BrowserDiagnosticPolicy":
        """Build policy from environment without exposing secrets.

        Operators can expand read-only research reach by setting
        ``NEXUS_BROWSER_HTTP_ALLOWED_HOSTS`` to a comma-separated host list.
        This intentionally controls only hosts, preview size, and timeout;
        method/header/private-network restrictions remain hard defaults unless
        code is reviewed.
        """

        allowed_hosts_raw = os.getenv(f"{prefix}_ALLOWED_HOSTS", "")
        allowed_hosts = _parse_host_allowlist(allowed_hosts_raw) or DEFAULT_ALLOWED_HOSTS
        max_preview = _env_int(f"{prefix}_MAX_PREVIEW_BYTES", 500)
        timeout = _env_float(f"{prefix}_TIMEOUT_SECONDS", 15.0)
        return cls(
            allowed_hosts=frozenset(allowed_hosts),
            max_preview_bytes=max(0, min(max_preview, 4096)),
            max_timeout_seconds=max(1.0, min(timeout, 30.0)),
        )


@dataclass(frozen=True)
class BrowserDiagnosticRequest:
    """Validated request passed to the GROSS ``http_diagnostic`` tool."""

    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    safe_preview_max: int = 500
    audit_id: str = ""
    scenario: str = "browser_http_diagnostic"
    operator: str = "nexus"
    mode: str = "dry_run"

    def to_gross_arguments(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "method": self.method,
            "headers_json": json.dumps(self.headers, sort_keys=True),
            "safe_preview_max": self.safe_preview_max,
            "audit_id": self.audit_id,
            "scenario": self.scenario,
            "operator": self.operator,
            "mode": self.mode,
        }


@dataclass(frozen=True)
class BrowserDiagnosticDecision:
    allowed: bool
    reason: str
    request: BrowserDiagnosticRequest | None = None
    gross_arguments: dict[str, Any] | None = None


def validate_browser_diagnostic_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    safe_preview_max: int | None = None,
    audit_id: str = "",
    scenario: str = "browser_http_diagnostic",
    operator: str = "nexus",
    mode: str = "dry_run",
    policy: BrowserDiagnosticPolicy | None = None,
) -> BrowserDiagnosticDecision:
    """Validate and normalize a browser diagnostic request."""

    active_policy = policy or BrowserDiagnosticPolicy()
    normalized_method = method.upper().strip()
    parsed = urlparse(url)

    if active_policy.require_https and parsed.scheme != "https":
        return BrowserDiagnosticDecision(False, "Only HTTPS diagnostic URLs are allowed")
    if not parsed.netloc:
        return BrowserDiagnosticDecision(False, "URL must include a host")
    if normalized_method not in active_policy.allowed_methods:
        return BrowserDiagnosticDecision(False, f"Method {normalized_method} is not allowed")

    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return BrowserDiagnosticDecision(False, "URL host could not be parsed")
    if active_policy.block_private_targets and _is_private_or_local_host(host):
        return BrowserDiagnosticDecision(False, "Private, localhost, and link-local targets are blocked")
    if not _host_allowed(host, active_policy.allowed_hosts):
        return BrowserDiagnosticDecision(False, f"Host {host} is not in the diagnostic allowlist")

    clean_headers = _sanitize_headers(headers or {})
    preview = safe_preview_max if safe_preview_max is not None else active_policy.max_preview_bytes
    preview = max(0, min(int(preview), active_policy.max_preview_bytes))
    request = BrowserDiagnosticRequest(
        url=url,
        method=normalized_method,
        headers=clean_headers,
        safe_preview_max=preview,
        audit_id=audit_id,
        scenario=scenario,
        operator=operator,
        mode=mode,
    )
    return BrowserDiagnosticDecision(
        True,
        "Request accepted by browser diagnostic policy",
        request=request,
        gross_arguments=request.to_gross_arguments(),
    )


class BrowserHTTPDiagnosticRelay:
    """Small client for invoking GROSS ``http_diagnostic`` over JSON-RPC.

    The relay intentionally separates validation from execution. Operators can
    call ``prepare`` to get the exact MCP arguments for Grok/GPT browser use,
    or ``invoke`` to call a compatible local bridge endpoint.
    """

    def __init__(
        self,
        *,
        bridge_url: str = "http://127.0.0.1:7354",
        policy: BrowserDiagnosticPolicy | None = None,
        transport: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        protocol: str = "a2a",
    ) -> None:
        self.bridge_url = bridge_url.rstrip("/")
        self.policy = policy or BrowserDiagnosticPolicy.from_env()
        self._transport = transport
        self.protocol = protocol

    def prepare(self, url: str, **kwargs: Any) -> BrowserDiagnosticDecision:
        return validate_browser_diagnostic_request(url, policy=self.policy, **kwargs)

    def invoke(self, url: str, **kwargs: Any) -> dict[str, Any]:
        decision = self.prepare(url, mode=kwargs.pop("mode", "live"), **kwargs)
        if not decision.allowed:
            return {"blocked": True, "reason": decision.reason}
        assert decision.gross_arguments is not None
        if self._transport is not None:
            return self._transport(decision.gross_arguments)
        if self.protocol == "jsonrpc":
            return self._jsonrpc_tool_call("http_diagnostic", decision.gross_arguments)
        return self._a2a_tool_call("browser_http_diagnostic", decision.gross_arguments)

    def execute_governed(
        self,
        url: str,
        *,
        method: str = "HEAD",
        headers: dict[str, str] | None = None,
        audit_id: str = "browser-http-governed",
        operator: str = "nexus",
        dry_run: bool = True,
        token_budget_checker: Callable[[dict[str, Any]], bool] | None = None,
        approval_checker: Callable[[dict[str, Any]], bool] | None = None,
        memory_sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Governed execution boundary for browser-agent egress.

        The default is a dry run that returns the exact GROSS arguments without
        invoking transport. Live execution requires the same HTTPS/read-only/
        allowlist validation as ``invoke`` plus optional TokenGuard/approval
        callbacks before any bridge call.
        """

        mode = "dry_run" if dry_run else "live"
        decision = self.prepare(
            url,
            method=method,
            headers=headers,
            audit_id=audit_id,
            operator=operator,
            mode=mode,
        )
        gate_payload = {
            "url": url,
            "method": method.upper(),
            "audit_id": audit_id,
            "operator": operator,
            "bridge_url": self.bridge_url,
            "bridge_tool": "http_diagnostic",
            "dry_run": dry_run,
            "allowed": decision.allowed,
            "reason": decision.reason,
        }
        if memory_sink is not None:
            memory_sink({"phase": "before", **gate_payload})
        if not decision.allowed:
            result = {"blocked": True, "reason": decision.reason, "side_effects_enabled": False}
            if memory_sink is not None:
                memory_sink({"phase": "after", **gate_payload, "result": result})
            return result
        if token_budget_checker is not None and not token_budget_checker(gate_payload):
            result = {"blocked": True, "reason": "token_budget_denied", "side_effects_enabled": False}
            if memory_sink is not None:
                memory_sink({"phase": "after", **gate_payload, "result": result})
            return result
        if not dry_run and approval_checker is not None and not approval_checker(gate_payload):
            result = {"blocked": True, "reason": "approval_denied", "side_effects_enabled": False}
            if memory_sink is not None:
                memory_sink({"phase": "after", **gate_payload, "result": result})
            return result

        assert decision.gross_arguments is not None
        if dry_run:
            result = {
                "blocked": False,
                "dry_run": True,
                "access_result": "planned",
                "side_effects_enabled": False,
                "gross_arguments": decision.gross_arguments,
            }
        else:
            result = self.invoke(
                url,
                method=method,
                headers=headers,
                audit_id=audit_id,
                operator=operator,
                mode="live",
            )
            result.setdefault("side_effects_enabled", False)
        if memory_sink is not None:
            memory_sink({"phase": "after", **gate_payload, "result": result})
        return result
    def _jsonrpc_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": "nexus-browser-http-diagnostic",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        request = Request(
            f"{self.bridge_url}/invoke",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.policy.max_timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            return {"blocked": True, "reason": f"Bridge JSON-RPC HTTP {exc.code}: {exc.reason}"}
        except (URLError, OSError, ValueError) as exc:
            return {"blocked": True, "reason": f"Bridge JSON-RPC call failed: {exc}"}
        if "error" in raw:
            return {"blocked": True, "reason": raw["error"]}
        return raw.get("result", raw)

    def _a2a_tool_call(self, skill_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": "nexus-browser-http-diagnostic",
            "method": f"tasks/send.{skill_id}",
            "params": {
                "skill_id": skill_id,
                "sender": arguments.get("operator") or "nexus",
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": json.dumps(arguments, sort_keys=True)}],
                },
                **arguments,
            },
        }
        request = Request(
            f"{self.bridge_url}/a2a/tasks/send",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.policy.max_timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            return {"blocked": True, "reason": f"Bridge A2A HTTP {exc.code}: {exc.reason}"}
        except (URLError, OSError, ValueError) as exc:
            return {"blocked": True, "reason": f"Bridge A2A call failed: {exc}"}
        if "error" in raw:
            return {"blocked": True, "reason": raw["error"]}
        result = raw.get("result", {})
        artifacts = result.get("artifacts", [])
        if artifacts and isinstance(artifacts[0], dict):
            text = artifacts[0].get("text", "")
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return {"raw": text, "task": result}
            if isinstance(parsed, dict) and "error" in parsed:
                return {"blocked": True, "reason": parsed["error"], "task": result}
            return parsed
        return result


def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    clean: dict[str, str] = {}
    for key, value in headers.items():
        lowered = str(key).strip().lower()
        if any(lowered.startswith(prefix) for prefix in BLOCKED_HEADER_PREFIXES):
            continue
        clean[str(key).strip()] = str(value)
    return clean


def _host_allowed(host: str, allowed_hosts: frozenset[str]) -> bool:
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts)


def _is_private_or_local_host(host: str) -> bool:
    if host in {"localhost", "localhost.localdomain"}:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast


def _parse_host_allowlist(raw: str) -> set[str]:
    hosts: set[str] = set()
    for item in raw.split(","):
        host = item.strip().lower().rstrip(".")
        if not host or "/" in host or ":" in host:
            continue
        hosts.add(host)
    return hosts


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


