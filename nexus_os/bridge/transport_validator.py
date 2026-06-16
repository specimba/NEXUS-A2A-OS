"""MCP transport validator for CVE-2026-26015 mitigation.

Wired into the Bridge and MCP server request paths to enforce:
- No remote stdio transport (CVE-2026-26015)
- Allowlisted remote transports only (SSE, WebSocket, Streamable HTTP)
- Source identity validation per request
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ALLOWED_REMOTE_TRANSPORTS = frozenset({
    "sse",
    "websocket",
    "streamable_http",
    "http",
    "https",
    "ws",
    "wss",
})

BLOCKED_REMOTE_TRANSPORTS = frozenset({"stdio"})

ALLOWED_GATEWAY_SCHEMES = frozenset({"ws", "wss", "http", "https"})
SAFE_GATEWAY_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class MCPTransportError(Exception):
    def __init__(self, message: str, code: str = "TRANSPORT_BLOCKED") -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class TransportValidation:
    allowed: bool
    transport: str
    source: str
    reason: str
    severity: str = "info"

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "allowed": self.allowed,
            "transport": self.transport,
            "source": self.source,
            "reason": self.reason,
            "severity": self.severity,
        }


def validate_mcp_transport(
    transport: str,
    *,
    remote: bool = True,
) -> TransportValidation:
    """Validate MCP transport against CVE-2026-26015 rule.

    Args:
        transport: The transport type string (e.g. 'stdio', 'sse')
        remote: Whether this is a remote source (default True)

    Returns:
        TransportValidation with allowed=True/False and reason
    """
    normalized = transport.strip().lower().replace("-", "_")
    if not normalized:
        return TransportValidation(False, transport, "unknown", "transport is required", "high")

    if remote and normalized in BLOCKED_REMOTE_TRANSPORTS:
        return TransportValidation(
            False, transport, "remote",
            "remote stdio transport is forbidden (CVE-2026-26015)", "critical",
        )

    if remote and normalized not in ALLOWED_REMOTE_TRANSPORTS:
        return TransportValidation(
            False, transport, "remote",
            f"remote transport '{transport}' is not in allowlist", "high",
        )

    return TransportValidation(True, transport, "remote" if remote else "local", "transport accepted")


def validate_gateway_url(gateway_url: str) -> TransportValidation:
    """Validate gateway URL for MCP connections.

    Rejects URLs with embedded credentials, query-param tokens,
    and non-localhost hosts unless Tailscale-scoped.
    """
    from urllib.parse import urlparse
    import ipaddress

    parsed = urlparse(gateway_url)
    if parsed.scheme not in ALLOWED_GATEWAY_SCHEMES:
        return TransportValidation(False, parsed.scheme, gateway_url, "gateway scheme not allowlisted", "critical")
    if parsed.username or parsed.password:
        return TransportValidation(False, parsed.scheme, gateway_url, "gateway must not contain embedded credentials", "critical")
    if parsed.query:
        return TransportValidation(False, parsed.scheme, gateway_url, "gateway must not carry query-param tokens", "critical")

    host = parsed.hostname or ""
    if host in SAFE_GATEWAY_HOSTS:
        return TransportValidation(True, parsed.scheme, gateway_url, "gateway accepted (localhost)")
    if host.endswith(".ts.net"):
        return TransportValidation(True, parsed.scheme, gateway_url, "gateway accepted (Tailscale)")
    try:
        ip = ipaddress.ip_address(host)
        if ip in ipaddress.ip_network("100.64.0.0/10"):
            return TransportValidation(True, parsed.scheme, gateway_url, "gateway accepted (Tailscale IP)")
    except ValueError:
        pass

    return TransportValidation(False, parsed.scheme, gateway_url, "gateway host must be localhost or Tailscale-scoped", "high")


def validate_request_source(
    request: dict[str, Any],
) -> TransportValidation:
    """Validate source identity in an MCP request dict.

    Requires agent_id header/source field bound to the request.
    """
    source = request.get("source") or request.get("agent_id") or ""
    if not source.strip():
        return TransportValidation(False, "unknown", source, "request requires source identity", "critical")
    return TransportValidation(True, "identified", source, f"source identity: {source}")


def validate_tool_invocation(tool_name: str, arguments: dict[str, Any]) -> TransportValidation:
    """Validate that tool invocation parameters match expected schema rules.

    Rejects:
    - Non-string tool names
    - Overlong parameters (>10kB)
    - Path traversal patterns in path/file args
    - Shell injection patterns in command args
    """
    if not tool_name or not isinstance(tool_name, str):
        return TransportValidation(False, tool_name, "unknown", "tool name must be a non-empty string", "critical")

    import os
    path_keys = {"path", "file", "filepath", "target"}
    shell_keys = {"command", "shell", "cmd", "exec"}

    for key, value in arguments.items():
        if isinstance(value, str):
            if len(value) > 10000:
                return TransportValidation(False, tool_name, key, "parameter exceeds 10k character limit", "medium")
            if key in path_keys:
                if ".." in value or value.startswith("/") and "/etc/" in value:
                    return TransportValidation(False, tool_name, key, "path traversal escape detected", "critical")
            if key in shell_keys:
                dangerous = {"rm -rf", "sudo", "chmod 777", "> /etc", "curl | bash", "wget | sh"}
                if any(d in value.lower() for d in dangerous):
                    return TransportValidation(False, tool_name, key, "dangerous shell command detected", "critical")

    return TransportValidation(True, tool_name, "tool", "tool invocation accepted")
