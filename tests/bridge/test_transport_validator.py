"""Tests for the MCP transport validator wired into Bridge layer."""

import pytest
from nexus_os.bridge.transport_validator import (
    TransportValidation,
    validate_mcp_transport,
    validate_gateway_url,
    validate_request_source,
    validate_tool_invocation,
    MCPTransportError,
)


class TestMCPTransportValidation:
    def test_blocks_remote_stdio(self):
        result = validate_mcp_transport("stdio", remote=True)
        assert result.allowed is False
        assert "CVE-2026-26015" in result.reason
        assert result.severity == "critical"

    def test_allows_local_stdio(self):
        result = validate_mcp_transport("stdio", remote=False)
        assert result.allowed is True

    def test_allows_sse(self):
        result = validate_mcp_transport("sse", remote=True)
        assert result.allowed is True

    def test_allows_websocket(self):
        result = validate_mcp_transport("websocket", remote=True)
        assert result.allowed is True

    def test_allows_streamable_http(self):
        result = validate_mcp_transport("streamable-http", remote=True)
        assert result.allowed is True

    def test_blocks_unknown_transport(self):
        result = validate_mcp_transport("custom-tcp", remote=True)
        assert result.allowed is False

    def test_blocks_empty_transport(self):
        result = validate_mcp_transport("", remote=True)
        assert result.allowed is False

    def test_normalizes_dash_to_underscore(self):
        result = validate_mcp_transport("streamable-http", remote=True)
        assert result.allowed is True

    def test_to_dict_serializable(self):
        result = validate_mcp_transport("stdio", remote=True)
        d = result.to_dict()
        assert d["allowed"] is False
        assert d["severity"] == "critical"


class TestGatewayURLValidation:
    def test_accepts_localhost_http(self):
        result = validate_gateway_url("http://localhost:7352")
        assert result.allowed is True

    def test_accepts_localhost_ws(self):
        result = validate_gateway_url("ws://localhost:7352")
        assert result.allowed is True

    def test_accepts_127_0_0_1(self):
        result = validate_gateway_url("http://127.0.0.1:7352")
        assert result.allowed is True

    def test_accepts_tailscale_hostname(self):
        result = validate_gateway_url("http://agent-box.ts.net:7352")
        assert result.allowed is True

    def test_accepts_tailscale_ip(self):
        result = validate_gateway_url("http://100.64.0.1:7352")
        assert result.allowed is True

    def test_rejects_embedded_credentials(self):
        result = validate_gateway_url("http://user:pass@evil.com:7352")
        assert result.allowed is False

    def test_rejects_query_param_tokens(self):
        result = validate_gateway_url("ws://localhost:7352?token=leaked")
        assert result.allowed is False

    def test_rejects_external_host(self):
        result = validate_gateway_url("http://evil.com:7352")
        assert result.allowed is False

    def test_rejects_unknown_scheme(self):
        result = validate_gateway_url("ftp://localhost:7352")
        assert result.allowed is False


class TestSourceValidation:
    def test_accepts_identified_source(self):
        result = validate_request_source({"source": "agent-1"})
        assert result.allowed is True

    def test_accepts_agent_id(self):
        result = validate_request_source({"agent_id": "codex-main"})
        assert result.allowed is True

    def test_rejects_empty_source(self):
        result = validate_request_source({})
        assert result.allowed is False

    def test_rejects_empty_string_source(self):
        result = validate_request_source({"source": ""})
        assert result.allowed is False


class TestToolInvocationValidation:
    def test_accepts_normal_call(self):
        result = validate_tool_invocation("read_file", {"path": "/tmp/test.txt"})
        assert result.allowed is True

    def test_empty_tool_name(self):
        result = validate_tool_invocation("", {})
        assert result.allowed is False

    def test_non_string_tool_name(self):
        result = validate_tool_invocation(123, {})
        assert result.allowed is False

    def test_overlong_string_parameter(self):
        result = validate_tool_invocation("write_file", {"content": "x" * 10001})
        assert result.allowed is False
        assert "exceeds" in result.reason

    def test_short_string_parameter_accepted(self):
        result = validate_tool_invocation("write_file", {"content": "hello"})
        assert result.allowed is True
