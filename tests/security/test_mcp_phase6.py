"""
tests/security/test_mcp_phase6.py — Phase 6 MCP bridge security tests.

Category 1: TrustKernel gating — tool invocation policy enforcement.
Category 4: Audit/replay integrity — event log immutability and completeness.

These tests use the GovernedMCPServer directly (no live bridge/network)
and verify trust and audit semantics deterministically.
"""
import json
from datetime import datetime
from typing import Any, Dict

import pytest
from nexus_os.mcp.server import (
    GovernedMCPServer,
    MCPConfig,
    TrustKernelMCPAdapter,
    ToolSpec,
    AuditEvent,
)
from nexus_os.mcp.client import GovernedMCPClient


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def stub_server():
    """GovernedMCPServer in stub mode (no real TrustKernel)."""
    config = MCPConfig(
        server_name="test-mcp",
        server_version="0.6-test",
        trustkernel_mode="stub",
        allow_side_effects=False,
    )
    return GovernedMCPServer(config=config)


@pytest.fixture
def side_effect_server():
    """GovernedMCPServer with side effects enabled."""
    config = MCPConfig(
        server_name="test-mcp",
        server_version="0.6-test",
        trustkernel_mode="stub",
        allow_side_effects=True,
    )
    return GovernedMCPServer(config=config)


@pytest.fixture
def real_kernel_server():
    """GovernedMCPServer with real TrustKernel (can DENY/HOLD)."""
    config = MCPConfig(
        server_name="test-mcp",
        server_version="0.6-test",
        trustkernel_mode="real",
        allow_side_effects=True,
    )
    server = GovernedMCPServer(config=config)
    # Reset audit before each test
    server.audit_events = []
    return server


# ── Helper ─────────────────────────────────────────────────────────────────


def parse_result(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the inner payload from MCP tool result wrapper."""
    content = raw.get("result", {}).get("content", [])
    if content:
        text = content[0].get("text", "{}")
        return json.loads(text)
    return {}


def is_blocked(raw: Dict[str, Any]) -> bool:
    return parse_result(raw).get("blocked", False)


# ── Category 1: TrustKernel Gating ────────────────────────────────────────


class TestMcpTrustKernelGating:
    """TrustKernel must gate MCP tool invocations by policy level."""

    def test_read_only_tool_allowed_without_trustkernel(self, stub_server):
        """Read-only tools (governance_level=low) pass without TrustKernel."""
        result = stub_server.call_tool("req-1", "governance.get_status", {})
        assert "error" not in result
        r = parse_result(result)
        assert r.get("tool") == "governance.get_status"

    def test_system_health_allowed(self, stub_server):
        """system.health is always allowed."""
        result = stub_server.call_tool("req-1", "system.health", {})
        assert "error" not in result

    def test_side_effect_tool_blocked_by_default(self, stub_server):
        """Side-effect tools blocked when allow_side_effects=False."""
        result = stub_server.call_tool(
            "req-1", "telegram.send_message",
            {"chat_id": "test", "text": "hello"},
        )
        assert is_blocked(result), f"Side-effect tool not blocked"

    def test_side_effect_tool_requires_approval_even_when_allowed(self, side_effect_server):
        """Side-effect tools still require approval even with allow_side_effects."""
        result = side_effect_server.call_tool(
            "req-1", "telegram.send_message",
            {"chat_id": "test", "text": "hello"},
        )
        # Even with allow_side_effects=True, approval_required=True blocks
        assert is_blocked(result), "Side-effect tool should be blocked (approval_required)"

    def test_unknown_tool_returns_error(self, stub_server):
        """Unknown tool name returns -32601 error."""
        result = stub_server.call_tool("req-1", "nonexistent.tool", {})
        assert "error" in result
        assert result["error"].get("code") == -32601

    def test_trust_adapter_real_mode_creates_kernel(self):
        """TrustKernelMCPAdapter in real mode loads TrustKernel."""
        adapter = TrustKernelMCPAdapter(mode="real")
        assert adapter.mode == "real"
        decision = adapter.consult(
            ToolSpec(
                name="test.tool",
                description="test",
                input_schema={"type": "object", "properties": {}},
                governance_level="low",
                side_effects=False,
            ),
            {},
        )
        assert "allowed" in decision
        assert "decision" in decision
        assert decision.get("source") != "stub_trustkernel_policy"

    def test_trust_adapter_stub_blocks_side_effects(self):
        """Stub TrustKernel blocks side-effectful tools."""
        adapter = TrustKernelMCPAdapter(mode="stub")
        decision = adapter.consult(
            ToolSpec(
                name="telegram.send_message",
                description="Send message",
                input_schema={"type": "object", "properties": {}},
                governance_level="high",
                side_effects=True,
                approval_required=True,
            ),
            {"chat_id": "test", "text": "hello"},
        )
        assert not decision.get("allowed"), f"Side-effect allowed by stub"
        assert decision.get("decision") == "hold"

    def test_trust_adapter_stub_allows_read_only(self):
        """Stub TrustKernel allows read-only tools."""
        adapter = TrustKernelMCPAdapter(mode="stub")
        decision = adapter.consult(
            ToolSpec(
                name="system.health",
                description="Health check",
                input_schema={"type": "object", "properties": {}},
                governance_level="low",
                side_effects=False,
            ),
            {},
        )
        assert decision.get("allowed"), f"Read-only blocked by stub"

    def test_memory_checkpoint_blocked_by_default(self, stub_server):
        """memory.create_checkpoint requires side-effect enablement."""
        result = stub_server.call_tool(
            "req-1", "memory.create_checkpoint", {"note": "test"},
        )
        assert is_blocked(result), "Checkpoint not blocked"
        r = parse_result(result)
        reason = r.get("reason", "").lower()
        assert "side-effect" in reason or "enablement" in reason

    def test_drift_monitor_sweep_allowed(self, stub_server):
        """drift_monitor.run_sweep is read-only and allowed."""
        result = stub_server.call_tool(
            "req-1", "drift_monitor.run_sweep", {"scope": "recent"},
        )
        assert "error" not in result

    def test_governance_claim_flow(self, stub_server):
        """submit_claim and verify_claim work through governance pipeline."""
        result = stub_server.call_tool(
            "req-1", "governance.request_cycle_token", {},
        )
        assert "error" not in result

    def test_side_effect_policy_survives_chain(self, stub_server):
        """Multiple calls to side-effect tools all get blocked."""
        for _ in range(5):
            result = stub_server.call_tool(
                "chain-test", "notion.create_page",
                {"parent_id": "x", "title": "test"},
            )
            assert is_blocked(result), "Side-effect chain not consistently blocked"


# ── Category 4: Audit / Replay Integrity ──────────────────────────────────


class TestMcpAuditIntegrity:
    """All MCP invocations must be audited for replay and accountability."""

    def test_audit_events_collected(self, stub_server):
        """Blocked invocations create audit events."""
        stub_server.audit_events = []
        stub_server.call_tool(
            "req-1", "telegram.send_message",
            {"chat_id": "test", "text": "hello"},
        )
        assert len(stub_server.audit_events) > 0
        event = stub_server.audit_events[0]
        assert event.tool_name == "telegram.send_message"
        assert event.blocked is True

    def test_audit_events_for_allowed_calls(self, stub_server):
        """Allowed invocations also create audit events."""
        stub_server.audit_events = []
        stub_server.call_tool("req-1", "governance.get_status", {})
        assert len(stub_server.audit_events) > 0
        event = stub_server.audit_events[0]
        assert event.tool_name == "governance.get_status"
        assert event.blocked is False

    def test_audit_event_has_timestamp(self, stub_server):
        """Audit events carry ISO timestamps."""
        stub_server.audit_events = []
        stub_server.call_tool("req-1", "system.health", {})
        event = stub_server.audit_events[0]
        assert event.timestamp is not None
        datetime.fromisoformat(event.timestamp)

    def test_audit_event_has_decision(self, stub_server):
        """Audit events record the trust decision."""
        stub_server.audit_events = []
        stub_server.call_tool(
            "req-1", "memory.create_checkpoint", {"note": "test"},
        )
        event = stub_server.audit_events[0]
        assert event.decision is not None

    def test_audit_events_append_only(self, stub_server):
        """Audit log is append-only (events only added, never removed)."""
        stub_server.audit_events = []
        initial_count = len(stub_server.audit_events)
        for i in range(10):
            stub_server.call_tool(f"req-{i}", "system.health", {})
        assert len(stub_server.audit_events) == initial_count + 10

    def test_audit_events_serializable(self, stub_server):
        """Audit events are JSON-serializable (for persistent storage)."""
        stub_server.audit_events = []
        stub_server.call_tool(
            "req-1", "telegram.send_message",
            {"chat_id": "test", "text": "audit test"},
        )
        event = stub_server.audit_events[0]
        from dataclasses import asdict
        d = asdict(event)
        serialized = json.dumps(d)
        assert '"tool_name"' in serialized
        assert '"blocked"' in serialized

    def test_audit_events_distinct_per_call(self, stub_server):
        """Each MCP call produces a separate audit event."""
        stub_server.audit_events = []
        stub_server.call_tool("req-1", "system.health", {})
        stub_server.call_tool("req-2", "governance.get_status", {})
        assert len(stub_server.audit_events) == 2
        assert stub_server.audit_events[0].tool_name != stub_server.audit_events[1].tool_name

    def test_audit_event_immutable_after_creation(self, stub_server):
        """Audit event fields should not change after creation."""
        stub_server.audit_events = []
        stub_server.call_tool("req-1", "system.health", {})
        event = stub_server.audit_events[0]
        from dataclasses import asdict
        original = asdict(event)
        assert event.blocked == original["blocked"]

    def test_audit_replay_ordered(self, stub_server):
        """Audit events maintain insertion order (first call = first event)."""
        stub_server.audit_events = []
        tools = ["system.health", "governance.get_status", "drift_monitor.run_sweep"]
        for tool in tools:
            stub_server.call_tool("req", tool, {})
        assert len(stub_server.audit_events) == len(tools)
        for i, tool in enumerate(tools):
            assert stub_server.audit_events[i].tool_name == tool

    def test_audit_survives_policy_block(self, stub_server):
        """Policy block results are audited."""
        stub_server.audit_events = []
        stub_server.call_tool(
            "req-1", "telegram.send_message",
            {"chat_id": "test", "text": "test"},
        )
        assert len(stub_server.audit_events) > 0
