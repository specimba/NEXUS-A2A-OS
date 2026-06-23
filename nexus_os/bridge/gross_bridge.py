"""bridge/gross_bridge.py — GROSS MCP Bridge Governance Registration

Registers the GROSS MCP bridge (port 7354) as an external MCP agent
in the NEXUS governance system. Provides trust-gated access to bridge
tools with a minimum trust threshold of 90 for governance operations.

Wraps GovernedMCPClient with agent registration and trust-scoring.

Integration:
  - Register as ``external_mcp`` agent type in Governor/AgentPool
  - Tools are categorized by governance_level (low/medium/high)
  - Trust gate >= 90 required for "high" or "critical" tools
  - Health checks verify bridge connectivity

Usage:
    bridge = GrossMCPBridge()
    bridge.register()  # Register as external MCP agent
    tools = bridge.list_tools()
    result = bridge.call_tool("system.health", {}, trust_score=95.0)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from nexus_os.mcp.client import (
    GovernedMCPClient,
    MCPConnectionConfig,
    MCPCallResult,
    MCPToolInfo,
    GOVERNANCE_TOOLS_TRUST_THRESHOLD,
)

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

GROSS_BRIDGE_PORT = 7354
DEFAULT_GROSS_URL = f"http://127.0.0.1:{GROSS_BRIDGE_PORT}"

# Canonical agent ID for the GROSS bridge in governance system
GROSS_AGENT_ID = "gross-mcp-bridge"

# Canonical external agent metadata
GROSS_AGENT_METADATA: Dict[str, Any] = {
    "type": "external_mcp",
    "subtype": "gross_bridge",
    "protocol": "json-rpc-2.0",
    "transport": "http+sse",
    "version": "0.5-phase6-nexus",
    "trust_threshold": GOVERNANCE_TOOLS_TRUST_THRESHOLD,
    "description": "GROSS MCP bridge — governed evidence collection and monitoring",
}


@dataclass
class BridgeRegistration:
    """Result of registering the GROSS bridge as an external agent."""
    success: bool
    agent_id: str = GROSS_AGENT_ID
    tool_count: int = 0
    error: Optional[str] = None
    health: Optional[Dict[str, Any]] = None


# ── Bridge Wrapper ─────────────────────────────────────────────────────────────


class GrossMCPBridge:
    """Governance wrapper for the GROSS MCP bridge.

    Wraps GovernedMCPClient with governance semantics:
    - Registration as external_mcp agent type
    - Trust-gated tool access (>= 90 for governance tools)
    - Health monitoring and connectivity checks
    - Agent metadata enrichment for governance integration
    """

    def __init__(
        self,
        bridge_url: Optional[str] = None,
        trust_threshold: float = GOVERNANCE_TOOLS_TRUST_THRESHOLD,
        privilege_policy: Optional[Any] = None,
    ) -> None:
        config = MCPConnectionConfig(
            bridge_url=bridge_url or DEFAULT_GROSS_URL,
            trust_threshold=trust_threshold,
            agent_id=GROSS_AGENT_ID,
        )
        self._client = GovernedMCPClient(config)
        self._agent_id = GROSS_AGENT_ID
        self._registered = False
        try:
            from nexus_os.bridge.intern_discovery import InternDiscoveryClient
            self._intern_client = InternDiscoveryClient()
        except ImportError:
            self._intern_client = None

        from nexus_os.governor.privilege_control import ProgentPrivilegeControl
        self._privilege_control = ProgentPrivilegeControl(privilege_policy)
        self._custom_policy_provided = privilege_policy is not None

    # ── Properties ─────────────────────────────────────────────────

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def is_registered(self) -> bool:
        return self._registered

    @property
    def metadata(self) -> Dict[str, Any]:
        return {**GROSS_AGENT_METADATA}

    # ── Registration ───────────────────────────────────────────────

    def register(self, governor: Optional[Any] = None) -> BridgeRegistration:
        """Register the GROSS bridge as an external MCP agent.

        Connects to the bridge, discovers tools, and optionally registers
        with a Governor instance for governance oversight.

        Args:
            governor: Optional Governor or AgentPool instance for agent
                      registration. If None, registration is logical
                      (in-memory) only.

        Returns:
            BridgeRegistration with registration details.
        """
        # Connect and initialize
        connected = self._client.connect()
        if not connected:
            return BridgeRegistration(
                success=False,
                error=f"Failed to connect to GROSS MCP bridge at {self._client.config.bridge_url}",
            )

        # Discover tools
        tools = self._client.list_tools()
        if self._intern_client:
            try:
                scp_tools = self._intern_client.discover_scp_tools()
                for tool in scp_tools:
                    self._client._tools[tool.name] = tool
                tools = self._client.list_tools()
                logger.info("Mounted %d SCP tools from Intern Discovery", len(scp_tools))
            except Exception as e:
                logger.error("Failed to mount SCP tools from Intern Discovery: %s", e)
        logger.info(
            "GROSS MCP bridge connected: %d tools discovered at %s",
            len(tools), self._client.config.bridge_url,
        )

        # If no custom policy was provided, populate default policy allowing all discovered tools
        if not self._custom_policy_provided:
            for tool in tools:
                if tool.name not in self._privilege_control.policy.allowed_tools:
                    self._privilege_control.policy.allowed_tools[tool.name] = {}

        # Register with governor if provided
        if governor is not None:
            try:
                self._register_with_governor(governor, tools)
            except Exception as e:
                logger.error("GROSS bridge governor registration failed: %s", e)
                return BridgeRegistration(
                    success=False,
                    error=f"Governor registration failed: {e}",
                    tool_count=len(tools),
                )

        self._registered = True
        return BridgeRegistration(
            success=True,
            tool_count=len(tools),
            health=self._client.health_check(),
        )

    def _register_with_governor(self, governor: Any, tools: List[MCPToolInfo]) -> None:
        """Register as an external_mcp agent with the governance system.

        Attempts to use governor.register_agent() if available, otherwise
        logs a warning and proceeds with logical registration.
        """
        if hasattr(governor, "register_agent"):
            governor.register_agent(
                agent_id=self._agent_id,
                agent_type="external_mcp",
                metadata={
                    **GROSS_AGENT_METADATA,
                    "tool_names": [t.name for t in tools],
                    "tool_count": len(tools),
                    "governance_tools": [t.name for t in tools if t.governance_level in ("high", "critical")],
                },
            )
            logger.info("GROSS bridge registered with governor: agent_id=%s", self._agent_id)
        elif hasattr(governor, "agents"):
            # AgentPool-style registration
            metadata = {
                **GROSS_AGENT_METADATA,
                "tools": [t.name for t in tools],
            }
            if hasattr(governor, "register"):
                governor.register(self._agent_id, metadata=metadata)
                logger.info("GROSS bridge registered with agent pool: agent_id=%s", self._agent_id)
            else:
                logger.warning("Governor has no register() method — logical registration only")
        else:
            logger.warning(
                "Governor has no register_agent() or register() method — proceeding with logical registration"
            )

    # ── Tool Access ────────────────────────────────────────────────

    def list_tools(self) -> List[MCPToolInfo]:
        """List available tools from the bridge."""
        return self._client.list_tools()

    def get_tool(self, name: str) -> Optional[MCPToolInfo]:
        return self._client.get_tool(name)

    def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        trust_score: Optional[float] = None,
    ) -> MCPCallResult:
        """Call a bridge tool with optional trust gate.

        Args:
            name: Tool name.
            arguments: Tool arguments.
            trust_score: Agent trust score (0-100). Tools with governance_level
                        "high" or "critical" require trust >= threshold.

        Returns:
            MCPCallResult with result or rejection.
        """
        # Progent privilege control check
        args_dict = arguments or {}
        if not self._privilege_control.check_call(name, args_dict):
            logger.warning("GROSS Bridge: Tool call '%s' blocked by Progent privilege control", name)
            return MCPCallResult(
                tool=name,
                blocked=True,
                reason=f"Blocked by Progent privilege control: tool or arguments violation",
            )

        # Route scientific SCP tools via InternDiscoveryClient
        if self._intern_client and name in self._intern_client._scp_tools:
            tool = self._intern_client._scp_tools[name]
            if (
                trust_score is not None
                and tool.governance_level in ("high", "critical")
                and trust_score < self._client.config.trust_threshold
            ):
                return MCPCallResult(
                    tool=name,
                    blocked=True,
                    reason=(
                        f"Trust gate blocked: trust={trust_score:.1f} < "
                        f"threshold={self._client.config.trust_threshold} for "
                        f"governance tool '{name}'"
                    ),
                )
            return self._intern_client.call_scp_tool(name, arguments or {})

        return self._client.call_tool(name, arguments or {}, trust_score=trust_score)

    # ── Health ─────────────────────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        """Check bridge health and connectivity."""
        return self._client.health_check()

    def check_trust_gate(self, trust_score: float) -> Dict[str, Any]:
        """Check whether the given trust score clears the governance gate.

        Returns a dict with gate status and affected tools.
        """
        governance_tools = [
            t for t in self._client.list_tools()
            if t.governance_level in ("high", "critical")
        ]
        passed = trust_score >= self._client.config.trust_threshold
        return {
            "gate_passed": passed,
            "trust_score": trust_score,
            "threshold": self._client.config.trust_threshold,
            "governance_tool_count": len(governance_tools),
            "message": (
                f"Trust gate passed: {trust_score:.1f} >= {self._client.config.trust_threshold}"
                if passed
                else f"Trust gate blocked: {trust_score:.1f} < {self._client.config.trust_threshold}"
            ),
        }

    # ── Convenience ────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get full bridge status overview."""
        health = self.health_check()
        return {
            "agent_id": self._agent_id,
            "registered": self._registered,
            "connected": self._client.is_connected(),
            "tools": len(self._client.list_tools()),
            "bridge_url": self._client.config.bridge_url,
            "trust_threshold": self._client.config.trust_threshold,
            "health": health,
        }
