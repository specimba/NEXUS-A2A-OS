"""Protocol identity contracts for the optional IDE Agent Client edge.

These profiles are descriptors only.  They must not conflate the future
IDE/client protocol adapter with historical IBM/BeeAI agent-communication
semantics or imply that either transport is listening.
"""
from __future__ import annotations

from nexus_os.bridge.protocol_profiles import (
    MessageSchema,
    ProtocolName,
    ProtocolProfile,
    ProtocolSelector,
)


def test_compatibility_acp_descriptor_now_means_ide_agent_client_protocol():
    profile = ProtocolProfile.acp_default()

    assert profile.name is ProtocolName.IDE_AGENT_CLIENT
    assert ProtocolName.ACP is ProtocolName.IDE_AGENT_CLIENT
    assert profile.message_schema is MessageSchema.JSON_RPC
    assert profile.supports_delegation is False
    descriptor = profile.to_dict()
    assert descriptor["protocol_namespace"] == "ide.agent-client-protocol"
    assert "IBM" not in descriptor["description"]
    assert descriptor["runtime_adapter_enabled"] is False


def test_legacy_ibm_beeai_descriptor_is_explicit_and_not_default_selectable():
    legacy = ProtocolProfile.legacy_ibm_beeai_default()
    selector = ProtocolSelector()

    assert legacy.name is ProtocolName.LEGACY_IBM_BEEAI
    assert legacy.message_schema is MessageSchema.RESTFUL_HTTP
    assert legacy.to_dict()["protocol_namespace"] == "legacy.ibm-beeai-agent-communication"
    assert "legacy" in legacy.description.lower()
    advertised = selector.get_all_profiles()
    assert ProtocolName.LEGACY_IBM_BEEAI.value not in advertised
    assert all(
        profile["protocol_namespace"] != "legacy.ibm-beeai-agent-communication"
        for profiles in advertised.values()
        for profile in profiles
    )


def test_low_latency_streaming_selects_ide_acp_descriptor_not_legacy_bus():
    selected = ProtocolSelector().select(
        task_sensitivity="medium",
        need_streaming=True,
        latency_budget_ms=200,
    )

    assert selected.name is ProtocolName.IDE_AGENT_CLIENT
    assert selected.to_dict()["runtime_adapter_enabled"] is False
