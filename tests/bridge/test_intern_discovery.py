"""tests/bridge/test_intern_discovery.py — Intern Discovery & SCP Tool Tests"""

import os
import pytest
from unittest.mock import MagicMock, patch

from nexus_os.bridge.intern_discovery import InternDiscoveryClient, DEFAULT_INTERN_BASE_URL
from nexus_os.bridge.gross_bridge import GrossMCPBridge
from nexus_os.mcp.client import MCPCallResult, MCPToolInfo


class TestInternDiscoveryClient:

    def test_client_init_defaults(self, monkeypatch):
        monkeypatch.setenv("NEXUS_INTERN_DISCOVERY_TOKEN", "env_token_value")
        client = InternDiscoveryClient()
        assert client.base_url == DEFAULT_INTERN_BASE_URL
        assert client.token == "env_token_value"

    def test_client_init_explicit(self):
        client = InternDiscoveryClient(base_url="https://test.discovery.org", token="explicit_token")
        assert client.base_url == "https://test.discovery.org"
        assert client.token == "explicit_token"

    def test_headers_include_token(self):
        client = InternDiscoveryClient(token="my_token")
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer my_token"

    def test_headers_without_token(self):
        client = InternDiscoveryClient(token="")
        headers = client._get_headers()
        assert "Authorization" not in headers

    def test_discover_scp_tools(self):
        client = InternDiscoveryClient()
        tools = client.discover_scp_tools()
        assert len(tools) == 8
        
        # Check specific tool properties
        tool_names = [t.name for t in tools]
        assert "multiomics_integration" in tool_names
        assert "chemical_safety_assessment" in tool_names
        assert "alanine_scanning_pipeline" in tool_names
        
        # Verify governance mappings
        safety_tool = next(t for t in tools if t.name == "chemical_safety_assessment")
        assert safety_tool.governance_level == "high"
        assert safety_tool.side_effects is False

    def test_call_scp_tool_success(self):
        client = InternDiscoveryClient()
        args = {"uniprot_id": "P12345", "genes": ["BRCA1", "TP53"]}
        res = client.call_scp_tool("multiomics_integration", args)
        
        assert isinstance(res, MCPCallResult)
        assert res.tool == "multiomics_integration"
        assert res.blocked is False
        assert res.is_error is False
        assert res.result["success"] is True
        assert res.result["output"]["inputs_received"] == args

    def test_call_scp_tool_nonexistent(self):
        client = InternDiscoveryClient()
        res = client.call_scp_tool("nonexistent_scientific_tool", {})
        assert res.is_error is True
        assert "not found" in res.error_message


class TestGrossBridgeInternDiscoveryIntegration:

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock out the underlying GovernedMCPClient of GrossMCPBridge."""
        with patch("nexus_os.bridge.gross_bridge.GovernedMCPClient") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.connect.return_value = True
            mock_inst._tools = {
                "system.health": MCPToolInfo("system.health", "Check health", {}, governance_level="low")
            }
            mock_inst.list_tools.side_effect = lambda: list(mock_inst._tools.values())
            mock_inst.config.trust_threshold = 90
            mock_cls.return_value = mock_inst
            yield mock_inst

    def test_bridge_mounts_scp_tools(self, mock_mcp_client):
        # Initialize bridge and register
        bridge = GrossMCPBridge(bridge_url="http://localhost:7354")
        
        # Run registration
        res = bridge.register()
        assert res.success is True
        
        # Bridge should have normal tools + 8 mounted SCP tools
        assert len(mock_mcp_client._tools) == 9  # 1 normal + 8 SCP
        assert "multiomics_integration" in mock_mcp_client._tools
        assert "system.health" in mock_mcp_client._tools

    def test_call_tool_routes_to_scp(self, mock_mcp_client):
        bridge = GrossMCPBridge(bridge_url="http://localhost:7354")
        bridge.register()
        
        # Calling SCP tool should route to InternDiscoveryClient and bypass normal MCP Client call_tool
        args = {"smiles": "CC(=O)NC1=CC=C(O)C=C1"}
        res = bridge.call_tool("admet_druglikeness_report", args, trust_score=95.0)
        
        assert res.blocked is False
        assert res.result["success"] is True
        assert res.result["output"]["inputs_received"] == args
        mock_mcp_client.call_tool.assert_not_called()

    def test_call_tool_blocked_by_trust_gate(self, mock_mcp_client):
        bridge = GrossMCPBridge(bridge_url="http://localhost:7354")
        bridge.register()
        
        # chemical_safety_assessment is a high-governance tool, requires trust >= 90
        # Call with trust=50 should block
        res = bridge.call_tool("chemical_safety_assessment", {"compound_name": "aspirin"}, trust_score=50.0)
        assert res.blocked is True
        assert "Trust gate blocked" in res.reason

        # Call with trust=95 should succeed
        res_ok = bridge.call_tool("chemical_safety_assessment", {"compound_name": "aspirin"}, trust_score=95.0)
        assert res_ok.blocked is False
        assert res_ok.result["success"] is True
