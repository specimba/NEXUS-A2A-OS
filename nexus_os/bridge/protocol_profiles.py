"""
bridge/protocol_profiles.py — Protocol profile descriptors for A2A/MCP/IDE ACP/ANP

Backed by:
  - arXiv:2606.19135 (Technical Taxonomy of LLM Agent Communication Protocols)
  - arXiv:2505.02279 (Survey of Agent Interoperability Protocols)
  - arXiv:2510.17149 (ProtocolBench)

Integration: ADDITIVE to existing bridge/a2a_channels.py (460 lines).
The existing A2AChannelBus has typed JSONL-backed channels.
This module adds formal ProtocolProfile abstraction:
  - name (A2A, MCP, IDE Agent Client Protocol, ANP)
  - security_level (unauthenticated / authenticated / attested)
  - capability_advertisement format
  - message_schema (JSON-RPC, REST, etc.)

Protocol selection is informed by ProtocolBench metrics.

Usage:
    from nexus_os.bridge.protocol_profiles import ProtocolProfile, ProtocolSelector

    # Define profiles
    a2a = ProtocolProfile.a2a_default()
    mcp = ProtocolProfile.mcp_default()

    # Select best protocol for a task
    selector = ProtocolSelector()
    chosen = selector.select(task_sensitivity="high", need_evidence=True)
    # chosen = ProtocolProfile (attested A2A with evidence exchange)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ProtocolName(Enum):
    """Agent communication protocols from arXiv:2505.02279 survey."""
    A2A = "a2a"      # Agent-to-Agent (Google, peer-to-peer task delegation)
    MCP = "mcp"      # Model Context Protocol (JSON-RPC, tool invocation)
    IDE_AGENT_CLIENT = "ide_agent_client_protocol"
    # Compatibility spelling: ACP in current NEXUS doctrine means the IDE
    # Agent Client Protocol edge, never the historical IBM/BeeAI bus.
    ACP = "ide_agent_client_protocol"
    LEGACY_IBM_BEEAI = "legacy_ibm_beeai_agent_communication"
    ANP = "anp"      # Agent Network Protocol (W3C DIDs, JSON-LD, decentralized)


class SecurityLevel(Enum):
    """Security level from arXiv:2606.19135 taxonomy dimension."""
    UNAUTHENTICATED = "unauthenticated"
    AUTHENTICATED = "authenticated"
    ATTESTED = "attested"  # Cryptographic attestation required


class MessageSchema(Enum):
    """Message framing schema."""
    JSON_RPC = "json_rpc"       # MCP and descriptor-only IDE ACP style
    RESTFUL_HTTP = "restful"    # legacy IBM/BeeAI style
    SSE_STREAM = "sse"          # A2A style
    JSON_LD = "json_ld"         # ANP style


@dataclass
class ProtocolProfile:
    """Protocol profile abstraction.

    Papers: arXiv:2606.19135 (Taxonomy), arXiv:2505.02279 (Survey)
    """
    name: ProtocolName
    version: str
    security_level: SecurityLevel
    message_schema: MessageSchema
    capability_advertisement: str  # How capabilities are announced
    supports_streaming: bool = False
    supports_async: bool = False
    supports_delegation: bool = False
    supports_evidence_exchange: bool = False
    max_payload_kb: int = 1024
    latency_budget_ms: int = 100
    description: str = ""
    # Profiles are metadata only.  They neither bind a port nor activate a
    # protocol adapter; implementation must terminate at Bridge/Governor.
    protocol_namespace: str = ""
    runtime_adapter_enabled: bool = False

    @classmethod
    def a2a_default(cls) -> "ProtocolProfile":
        """A2A protocol profile (Google, peer-to-peer).

        Best for: inter-agent task delegation, capability-based Agent Cards.
        Security: authenticated (can be elevated to attested).
        """
        return cls(
            name=ProtocolName.A2A,
            version="1.0",
            security_level=SecurityLevel.AUTHENTICATED,
            message_schema=MessageSchema.SSE_STREAM,
            capability_advertisement="agent_card",
            supports_streaming=True,
            supports_async=True,
            supports_delegation=True,
            supports_evidence_exchange=True,
            max_payload_kb=4096,
            latency_budget_ms=500,
            description="Google A2A: peer-to-peer task delegation with Agent Cards",
            protocol_namespace="a2a.v1",
        )

    @classmethod
    def a2a_attested(cls) -> "ProtocolProfile":
        """A2A with attested security (for high-sensitivity tasks)."""
        p = cls.a2a_default()
        p.security_level = SecurityLevel.ATTESTED
        return p

    @classmethod
    def mcp_default(cls) -> "ProtocolProfile":
        """MCP protocol profile (JSON-RPC, tool invocation).

        Best for: agent-to-tool communication, structured data exchange.
        Security: unauthenticated by default (upgrade to authenticated).
        """
        return cls(
            name=ProtocolName.MCP,
            version="1.0",
            security_level=SecurityLevel.UNAUTHENTICATED,
            message_schema=MessageSchema.JSON_RPC,
            capability_advertisement="tool_schema",
            supports_streaming=False,
            supports_async=False,
            supports_delegation=False,
            supports_evidence_exchange=False,
            max_payload_kb=1024,
            latency_budget_ms=50,
            description="MCP: JSON-RPC client-server for tool invocation",
            protocol_namespace="mcp.tool-client",
        )

    @classmethod
    def mcp_authenticated(cls) -> "ProtocolProfile":
        """MCP with authentication."""
        p = cls.mcp_default()
        p.security_level = SecurityLevel.AUTHENTICATED
        return p

    @classmethod
    def ide_acp_default(cls) -> "ProtocolProfile":
        """Descriptor for the optional IDE Agent Client Protocol edge.

        This is intentionally not an A2A delegation bus and not a listener.
        A future adapter must map IDE sessions/tools into canonical governed
        proposal envelopes before it can claim any runtime integration.
        """
        return cls(
            name=ProtocolName.IDE_AGENT_CLIENT,
            version="1.0",
            security_level=SecurityLevel.AUTHENTICATED,
            message_schema=MessageSchema.JSON_RPC,
            capability_advertisement="ide_session_capabilities",
            supports_streaming=True,
            supports_async=True,
            supports_delegation=False,
            supports_evidence_exchange=False,
            max_payload_kb=1024,
            latency_budget_ms=100,
            description="IDE Agent Client Protocol descriptor; adapter disabled by default",
            protocol_namespace="ide.agent-client-protocol",
        )

    @classmethod
    def acp_default(cls) -> "ProtocolProfile":
        """Backward-compatible ACP factory for the IDE Agent Client Protocol.

        Callers that used the historical short name get the current IDE
        descriptor; they cannot accidentally select IBM/BeeAI semantics.
        """
        return cls.ide_acp_default()

    @classmethod
    def legacy_ibm_beeai_default(cls) -> "ProtocolProfile":
        """Historical IBM/BeeAI descriptor, excluded from default selection.

        It exists only to retain intelligible archival metadata.  It is not an
        IDE ACP implementation and never enables a competing transport.
        """
        return cls(
            name=ProtocolName.LEGACY_IBM_BEEAI,
            version="historical",
            security_level=SecurityLevel.AUTHENTICATED,
            message_schema=MessageSchema.RESTFUL_HTTP,
            capability_advertisement="legacy_session_metadata",
            supports_streaming=True,
            supports_async=True,
            supports_delegation=True,
            supports_evidence_exchange=False,
            max_payload_kb=8192,
            latency_budget_ms=200,
            description="Legacy IBM/BeeAI agent-communication descriptor; not selectable by default",
            protocol_namespace="legacy.ibm-beeai-agent-communication",
        )

    @classmethod
    def anp_default(cls) -> "ProtocolProfile":
        """ANP protocol profile (W3C DIDs, JSON-LD, decentralized).

        Best for: open network agent discovery, decentralized marketplaces.
        Security: attested (DID-based).
        """
        return cls(
            name=ProtocolName.ANP,
            version="0.1",
            security_level=SecurityLevel.ATTESTED,
            message_schema=MessageSchema.JSON_LD,
            capability_advertisement="did_document",
            supports_streaming=False,
            supports_async=True,
            supports_delegation=True,
            supports_evidence_exchange=True,
            max_payload_kb=2048,
            latency_budget_ms=1000,
            description="ANP: W3C DIDs + JSON-LD for decentralized discovery",
            protocol_namespace="anp.did-jsonld",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name.value,
            "version": self.version,
            "security_level": self.security_level.value,
            "message_schema": self.message_schema.value,
            "capability_advertisement": self.capability_advertisement,
            "supports_streaming": self.supports_streaming,
            "supports_async": self.supports_async,
            "supports_delegation": self.supports_delegation,
            "supports_evidence_exchange": self.supports_evidence_exchange,
            "max_payload_kb": self.max_payload_kb,
            "latency_budget_ms": self.latency_budget_ms,
            "description": self.description,
            "protocol_namespace": self.protocol_namespace,
            "runtime_adapter_enabled": self.runtime_adapter_enabled,
        }


class ProtocolSelector:
    """Select best protocol profile based on task requirements.

    Paper: arXiv:2510.17149 (ProtocolBench — systematic protocol evaluation)
    """

    def __init__(self):
        self._profiles = {
            ProtocolName.A2A: [ProtocolProfile.a2a_default(), ProtocolProfile.a2a_attested()],
            ProtocolName.MCP: [ProtocolProfile.mcp_default(), ProtocolProfile.mcp_authenticated()],
            ProtocolName.IDE_AGENT_CLIENT: [ProtocolProfile.ide_acp_default()],
            ProtocolName.ANP: [ProtocolProfile.anp_default()],
        }

    def select(
        self,
        task_sensitivity: str = "medium",
        need_evidence: bool = False,
        need_delegation: bool = False,
        need_streaming: bool = False,
        latency_budget_ms: int = 500,
    ) -> ProtocolProfile:
        """Select the best protocol profile for the given requirements.

        Selection logic (informed by ProtocolBench):
        - High sensitivity → attested security required
        - Evidence exchange needed → A2A or ANP
        - Delegation needed → A2A or ANP
        - Streaming needed → A2A or IDE ACP
        - Low latency → MCP or IDE ACP
        """
        candidates: List[ProtocolProfile] = []
        for profiles in self._profiles.values():
            candidates.extend(profiles)

        # Filter by requirements
        if task_sensitivity == "high":
            candidates = [p for p in candidates if p.security_level == SecurityLevel.ATTESTED]
        elif task_sensitivity == "medium":
            candidates = [p for p in candidates if p.security_level != SecurityLevel.UNAUTHENTICATED]

        if need_evidence:
            candidates = [p for p in candidates if p.supports_evidence_exchange]

        if need_delegation:
            candidates = [p for p in candidates if p.supports_delegation]

        if need_streaming:
            candidates = [p for p in candidates if p.supports_streaming]

        candidates = [p for p in candidates if p.latency_budget_ms <= latency_budget_ms]

        if not candidates:
            # Fallback: authenticated A2A
            return ProtocolProfile.a2a_default()

        # Prefer by priority: attested > authenticated > unauthenticated
        # Then by lower latency
        candidates.sort(key=lambda p: (
            -self._security_rank(p.security_level),
            p.latency_budget_ms,
        ))
        return candidates[0]

    @staticmethod
    def _security_rank(level: SecurityLevel) -> int:
        return {SecurityLevel.ATTESTED: 3, SecurityLevel.AUTHENTICATED: 2, SecurityLevel.UNAUTHENTICATED: 1}.get(level, 0)

    def get_all_profiles(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            name.value: [p.to_dict() for p in profiles]
            for name, profiles in self._profiles.items()
        }
