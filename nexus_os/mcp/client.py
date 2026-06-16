"""mcp/client.py — JSON-RPC MCP Client for NEXUS OS MCP bridges.

Communicates with MCP bridge servers (port 7354 GROSS bridge, etc.)
via HTTP/JSON-RPC 2.0. Supports tool listing, invocation, SSE streaming,
and trust-gated governance filtering.

Usage:
    client = GovernedMCPClient("http://127.0.0.1:7354")
    tools = client.list_tools()
    result = client.call_tool("system.health", {})
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_BRIDGE_URL = "http://127.0.0.1:7354"
DEFAULT_TIMEOUT = 30.0
GOVERNANCE_TOOLS_TRUST_THRESHOLD = 90.0  # Trust >= 90 for governance operations

# MCP protocol version
MCP_PROTOCOL_VERSION = "2024-11-05"


# ── Dataclasses ────────────────────────────────────────────────────────────────


@dataclass
class MCPToolInfo:
    name: str
    description: str
    input_schema: Dict[str, Any]
    governance_level: str = "low"
    side_effects: bool = False
    approval_required: bool = False

    @classmethod
    def from_mcp(cls, raw: Dict[str, Any]) -> "MCPToolInfo":
        governance = raw.get("governance", {})
        return cls(
            name=raw.get("name", ""),
            description=raw.get("description", ""),
            input_schema=raw.get("inputSchema", {}),
            governance_level=governance.get("level", "low"),
            side_effects=governance.get("side_effects", False),
            approval_required=governance.get("approval_required", False),
        )


@dataclass
class MCPCallResult:
    tool: str
    result: Optional[Dict[str, Any]] = None
    blocked: bool = False
    reason: Optional[str] = None
    trust_decision: Optional[Dict[str, Any]] = None
    is_error: bool = False
    error_message: Optional[str] = None


@dataclass
class MCPConnectionConfig:
    bridge_url: str = DEFAULT_BRIDGE_URL
    timeout: float = DEFAULT_TIMEOUT
    trust_threshold: float = GOVERNANCE_TOOLS_TRUST_THRESHOLD
    agent_id: str = "gross-bridge-client"
    max_retries: int = 3
    retry_delay: float = 1.0


# ── Client ─────────────────────────────────────────────────────────────────────


class GovernedMCPClient:
    """JSON-RPC client for MCP bridge servers with trust-gated governance.

    Communicates with the bridge via HTTP POST /invoke (JSON-RPC 2.0).
    All responses include trust decisions.
    """

    def __init__(self, config: Optional[MCPConnectionConfig] = None) -> None:
        self.config = config or MCPConnectionConfig()
        self._tools: Dict[str, MCPToolInfo] = {}
        self._server_info: Optional[Dict[str, Any]] = None
        self._initialized = False

    # ── Connection ─────────────────────────────────────────────────

    def connect(self) -> bool:
        """Initialize the MCP connection. Returns True on success."""
        return self._initialize()

    def _initialize(self) -> bool:
        """Send initialize request to the MCP bridge."""
        try:
            response = self._jsonrpc_call("initialize", {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "nexus-os-governed-client",
                    "version": "0.5",
                },
            })
            if response and "result" in response:
                self._server_info = response["result"]
                self._initialized = True
                # Fetch tools
                self._fetch_tools()
                return True
        except Exception as e:
            logger.warning("MCP initialize failed: %s", e)
        return False

    def _fetch_tools(self) -> None:
        """Fetch available tools from the bridge."""
        try:
            response = self._jsonrpc_call("tools/list", {})
            if response and "result" in response:
                tools_raw = response["result"].get("tools", [])
                self._tools = {
                    t["name"]: MCPToolInfo.from_mcp(t)
                    for t in tools_raw
                }
                logger.debug("MCP client: loaded %d tools", len(self._tools))
        except Exception as e:
            logger.warning("MCP tools/list failed: %s", e)

    # ── JSON-RPC ───────────────────────────────────────────────────

    def _jsonrpc_call(
        self,
        method: str,
        params: Dict[str, Any],
        req_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make a JSON-RPC 2.0 call to the bridge via HTTP POST."""
        request_id = req_id or f"{method}-{uuid.uuid4().hex[:8]}"
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        url = f"{self.config.bridge_url}/invoke"

        last_error: Optional[Exception] = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                data = json.dumps(payload).encode("utf-8")
                req = Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(req, timeout=self.config.timeout) as resp:
                    body = resp.read().decode("utf-8")
                    return json.loads(body)
            except URLError as e:
                last_error = e
                if attempt < self.config.max_retries:
                    logger.debug(
                        "MCP call %s attempt %d failed: %s. Retrying in %.1fs...",
                        method, attempt, e, self.config.retry_delay,
                    )
                    time.sleep(self.config.retry_delay)
            except (json.JSONDecodeError, OSError, ValueError) as e:
                last_error = e
                break

        logger.error("MCP call %s failed after %d attempts: %s", method, self.config.max_retries, last_error)
        return None

    # ── Tool Discovery ─────────────────────────────────────────────

    def list_tools(self) -> List[MCPToolInfo]:
        """Return cached tool list."""
        if not self._tools:
            self._fetch_tools()
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[MCPToolInfo]:
        """Get tool info by name."""
        return self._tools.get(name)

    def get_server_info(self) -> Optional[Dict[str, Any]]:
        return self._server_info

    def is_connected(self) -> bool:
        return self._initialized

    def health_check(self) -> Dict[str, Any]:
        """Check bridge health."""
        try:
            response = self._jsonrpc_call("tools/call", {
                "name": "system.health",
                "arguments": {},
            })
            if response and "result" in response:
                return {
                    "ok": True,
                    "bridge_health": response["result"],
                }
        except Exception:
            pass
        return {"ok": False, "bridge_health": None}

    # ── Tool Invocation ────────────────────────────────────────────

    def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        trust_score: Optional[float] = None,
    ) -> MCPCallResult:
        """Invoke an MCP tool with optional trust gate.

        Args:
            name: Tool name.
            arguments: Tool arguments.
            trust_score: Agent trust score (0-100). If provided and below
                GOVERNANCE_TOOLS_TRUST_THRESHOLD, governance tools are blocked.

        Returns:
            MCPCallResult with the tool output or block reason.
        """
        # Auto-connect if not initialized
        if not self._initialized:
            ok = self._initialize()
            if not ok:
                return MCPCallResult(
                    tool=name,
                    blocked=True,
                    reason="MCP client not connected to bridge",
                    is_error=True,
                )

        # Re-check tools after connect
        tool = self._tools.get(name)
        if tool is None:
            return MCPCallResult(
                tool=name,
                blocked=True,
                reason=f"Tool '{name}' not found in bridge tool list",
                is_error=True,
            )

        # Trust gate: block governance tools if trust < threshold
        if (
            trust_score is not None
            and tool.governance_level in ("high", "critical")
            and trust_score < self.config.trust_threshold
        ):
            return MCPCallResult(
                tool=name,
                blocked=True,
                reason=(
                    f"Trust gate blocked: trust={trust_score:.1f} < "
                    f"threshold={self.config.trust_threshold} for "
                    f"governance tool '{name}'"
                ),
            )

        response = self._jsonrpc_call("tools/call", {
            "name": name,
            "arguments": arguments,
        })

        if response is None:
            return MCPCallResult(
                tool=name,
                blocked=True,
                reason="Bridge did not respond",
                is_error=True,
            )

        # Check for JSON-RPC error
        if "error" in response:
            err = response["error"]
            return MCPCallResult(
                tool=name,
                blocked=True,
                reason=err.get("message", "JSON-RPC error"),
                is_error=True,
                error_message=str(err),
            )

        result_data = response.get("result", {})
        content_list = result_data.get("content", [])
        payload: Dict[str, Any] = {}
        for item in content_list:
            if item.get("type") == "text":
                try:
                    payload = json.loads(item.get("text", "{}"))
                except json.JSONDecodeError:
                    payload = {"raw": item.get("text", "")}

        is_blocked = payload.get("blocked", False)
        return MCPCallResult(
            tool=name,
            result=payload.get("result", payload),
            blocked=is_blocked,
            reason=payload.get("reason"),
            trust_decision=payload.get("trust_decision"),
            is_error=result_data.get("isError", False) or is_blocked,
        )

    # ─── Convenience Wrappers ──────────────────────────────────────

    def governance_get_status(self) -> Optional[Dict[str, Any]]:
        result = self.call_tool("governance.get_status", {})
        return result.result

    def system_health(self) -> Optional[Dict[str, Any]]:
        result = self.call_tool("system.health", {})
        return result.result

    # ── SSE Stream (low-level) ─────────────────────────────────────

    def connect_sse(self) -> Optional[Any]:
        """Connect to the SSE stream endpoint. Returns a response-like object
        or None if unavailable. Caller must iterate over the response body.

        Note: This is low-level and not used for standard tool calls.
        """
        try:
            from urllib.request import urlopen
            url = f"{self.config.bridge_url}/sse"
            return urlopen(url, timeout=self.config.timeout)
        except Exception as e:
            logger.warning("MCP SSE connection failed: %s", e)
            return None


# ── Convenience ─────────────────────────────────────────────────────────────────


_default_client: Optional[GovernedMCPClient] = None


def get_client(url: Optional[str] = None) -> GovernedMCPClient:
    global _default_client
    if _default_client is None:
        config = MCPConnectionConfig(bridge_url=url or DEFAULT_BRIDGE_URL)
        _default_client = GovernedMCPClient(config)
    return _default_client
