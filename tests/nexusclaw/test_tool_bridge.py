from nexus_os.nexusclaw.tool_bridge import (
    ExternalMCPServer,
    BridgedTool,
    ToolBridgeResult,
    MCPToolBridge,
    get_tool_bridge,
)
import pytest
import asyncio


class TestExternalMCPServer:
    def test_server_defaults(self):
        server = ExternalMCPServer(name="test", url="http://localhost:9000")
        assert server.enabled is True
        assert server.trust_level == "review_required"
        assert server.headers == {}

    def test_server_with_custom_options(self):
        server = ExternalMCPServer(
            name="custom",
            url="http://localhost:8080",
            headers={"Authorization": "Bearer test"},
            enabled=False,
            trust_level="approved",
        )
        assert server.enabled is False
        assert server.trust_level == "approved"


class TestBridgedTool:
    def test_bridged_tool_to_mcp(self):
        tool = BridgedTool(
            name="test_tool",
            server_name="test_server",
            description="A test tool",
            input_schema={"type": "object"},
        )
        mcp = tool.to_mcp()

        assert mcp["name"] == "test_tool"
        assert mcp["description"] == "A test tool"
        assert mcp["governance"]["level"] == "medium"
        assert mcp["governance"]["requires_escalation"] is True
        assert mcp["governance"]["bridged_from"] == "test_server"

    def test_bridged_tool_custom_governance(self):
        tool = BridgedTool(
            name="high_risk",
            server_name="server",
            description="Tool",
            input_schema={},
            governance_level="high",
            requires_escalation=False,
        )
        mcp = tool.to_mcp()
        assert mcp["governance"]["level"] == "high"
        assert mcp["governance"]["requires_escalation"] is False


class TestToolBridgeResult:
    def test_success_result(self):
        result = ToolBridgeResult(tool="test", success=True, result={"data": "value"})
        assert result.success is True
        assert result.dry_run is True
        assert result.governance_required is True
        assert result.error is None

    def test_error_result(self):
        result = ToolBridgeResult(tool="test", success=False, error="Connection failed")
        assert result.success is False
        assert result.error == "Connection failed"


class TestMCPToolBridge:
    def test_get_server_returns_none_for_unknown(self):
        bridge = MCPToolBridge()
        assert bridge.get_server("unknown") is None

    def test_register_server_and_get_server(self):
        bridge = MCPToolBridge()
        server = ExternalMCPServer(name="test_server", url="http://localhost:9000")
        bridge.register_server(server)

        assert bridge.get_server("test_server") == server
        assert "test_server" in bridge.servers

    @pytest.mark.asyncio
    async def test_fetch_tools_returns_empty_for_unknown_server(self):
        bridge = MCPToolBridge()
        tools = await bridge.fetch_tools("unknown_server")
        assert tools == []

    @pytest.mark.asyncio
    async def test_fetch_tools_caches_tools(self):
        bridge = MCPToolBridge()
        bridge.register_server(ExternalMCPServer(name="cached_server", url="http://localhost"))
        bridge._tool_cache["cached_server"] = [BridgedTool(name="cached_tool", server_name="cached_server", description="cached", input_schema={})]

        tools = await bridge.fetch_tools("cached_server")
        assert len(tools) == 1
        assert tools[0].name == "cached_tool"


class TestCallTool:
    @pytest.mark.asyncio
    async def test_call_tool_returns_not_found_for_unknown_tool(self):
        bridge = MCPToolBridge()
        result = await bridge.call_tool("unknown_tool", {})
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_call_tool_held_governance_without_approval(self):
        bridge = MCPToolBridge()
        bridge.bridged_tools["test_tool"] = BridgedTool(
            name="test_tool",
            server_name="enabled_server",
            description="Test",
            input_schema={},
            requires_escalation=True,
        )
        bridge.servers["enabled_server"] = ExternalMCPServer(name="enabled_server", url="http://localhost", enabled=True)

        result = await bridge.call_tool("test_tool", {}, trustkernel_approved=False)
        assert result.success is True
        assert result.governance_required is True
        assert result.dry_run is True


class TestGetToolBridge:
    def test_singleton_returns_same_instance(self):
        bridge1 = get_tool_bridge()
        bridge2 = get_tool_bridge()
        assert bridge1 is bridge2


class TestLoadMCPBridgeFromEnv:
    def test_load_empty_env_returns_empty_bridge(self, monkeypatch):
        monkeypatch.setenv("NEXUS_MCP_BRIDGE_URLS", "")
        monkeypatch.setenv("NEXUS_MCP_BRIDGE_NAMES", "")

        from nexus_os.nexusclaw.tool_bridge import load_mcp_bridge_from_env
        bridge = load_mcp_bridge_from_env()

        assert len(bridge.servers) == 0

    def test_load_from_env_registers_servers(self, monkeypatch):
        monkeypatch.setenv("NEXUS_MCP_BRIDGE_URLS", "http://localhost:9000,http://localhost:9001")
        monkeypatch.setenv("NEXUS_MCP_BRIDGE_NAMES", "server1,server2")

        from nexus_os.nexusclaw.tool_bridge import load_mcp_bridge_from_env
        bridge = load_mcp_bridge_from_env()

        assert len(bridge.servers) == 2
        assert "server1" in bridge.servers
        assert "server2" in bridge.servers

    def test_load_from_env_handles_mismatch_lengths(self, monkeypatch):
        monkeypatch.setenv("NEXUS_MCP_BRIDGE_URLS", "http://localhost:9000")
        monkeypatch.setenv("NEXUS_MCP_BRIDGE_NAMES", "server1,server2,server3")

        from nexus_os.nexusclaw.tool_bridge import load_mcp_bridge_from_env
        bridge = load_mcp_bridge_from_env()

        assert len(bridge.servers) == 1