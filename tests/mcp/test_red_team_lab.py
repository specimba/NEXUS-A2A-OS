"""MCP Red Team Lab test stubs (MCP-01 through MCP-06).

These test cases replicate the MCP Red Team Lab scenarios found in the
Archivist fork (GROKsharedfolder / NEXUS_Red_Team_Lab). They are designed
to validate that NEXUSCLAW's transport, tool invocation, and governance gates
reject the same attack patterns.
"""

import json
import pytest

from nexus_os.bridge.transport_validator import (
    validate_mcp_transport,
    validate_gateway_url,
    validate_request_source,
    validate_tool_invocation,
    MCPTransportError,
)

from nexus_os.nexusclaw.security import (
    validate_openclaw_gateway,
    validate_runtime_config_patch,
    validate_model_intake,
    SecurityDecision,
)


class TestMCP01WorkspaceEscape:
    """MCP-01: Workspace/Root Directory Escape via MCP Tools."""

    def test_rejects_path_traversal_in_tool_args(self):
        result = validate_tool_invocation("read_file", {"path": "../../etc/passwd"})
        assert result.allowed is False
        assert "traversal" in result.reason.lower()

    def test_rejects_overlong_parameter(self):
        result = validate_tool_invocation("write_file", {"content": "A" * 10001})
        assert result.allowed is False
        assert "exceeds" in result.reason

    def test_rejects_empty_tool_name(self):
        result = validate_tool_invocation("", {})
        assert result.allowed is False


class TestMCP02CommandInjection:
    """MCP-02: Command Injection via MCP Tool Arguments."""

    def test_accepts_normal_tool_call(self):
        result = validate_tool_invocation("bash", {"command": "ls -la"})
        assert result.allowed is True

    def test_rejects_dangerous_shell_command(self):
        result = validate_tool_invocation("bash", {"command": "rm -rf /"})
        assert result.allowed is False

    def test_rejects_empty_tool_name_for_shell(self):
        result = validate_tool_invocation("", {"command": "rm -rf /"})
        assert result.allowed is False


class TestMCP03TransportSecurity:
    """MCP-03: Unauthorized STDIO Transport (CVE-2026-26015)."""

    def test_blocks_remote_stdio(self):
        result = validate_mcp_transport("stdio", remote=True)
        assert result.allowed is False
        assert "CVE-2026-26015" in result.reason

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
        result = validate_mcp_transport("custom-raw-tcp", remote=True)
        assert result.allowed is False

    def test_blocks_empty_transport(self):
        result = validate_mcp_transport("", remote=True)
        assert result.allowed is False

    def test_normalizes_dash_to_underscore(self):
        result = validate_mcp_transport("streamable-http", remote=True)
        assert result.allowed is True


class TestMCP04GatewaySecurity:
    """MCP-04: Gateway URL / WebSocket Origin Validation."""

    def test_accepts_localhost_gateway(self):
        result = validate_gateway_url("http://localhost:7352")
        assert result.allowed is True

    def test_accepts_tailscale_gateway(self):
        result = validate_gateway_url("http://agent-box.ts.net:7352")
        assert result.allowed is True

    def test_rejects_embedded_credentials(self):
        result = validate_gateway_url("http://user:pass@evil.com:7352")
        assert result.allowed is False
        assert "credentials" in result.reason

    def test_rejects_query_param_tokens(self):
        result = validate_gateway_url("ws://localhost:7352?token=leaked")
        assert result.allowed is False
        assert "query" in result.reason

    def test_rejects_external_gateway_host(self):
        result = validate_gateway_url("http://evil-server.com:7352")
        assert result.allowed is False

    def test_openclaw_gateway_without_token(self):
        result = validate_openclaw_gateway(
            "http://localhost:18789",
            origin="http://localhost:3000",
            token_bound=False,
        )
        assert result.allowed is False
        assert "token" in result.reason

    def test_openclaw_gateway_with_token(self):
        result = validate_openclaw_gateway(
            "http://localhost:18789",
            origin="http://localhost:3000",
            token_bound=True,
        )
        assert result.allowed is True


class TestMCP05ConfigTampering:
    """MCP-05: Immutable Approval/Sandbox Configuration Tampering."""

    def test_requires_kaiju_and_vap_for_sensitive_config(self):
        patch = {"approval_policy": "auto-approve-all"}
        result = validate_runtime_config_patch(patch, kaiju_approved=False, vap_record_id=None)
        assert result.allowed is False
        assert "KAIJU" in result.reason

    def test_allows_with_kaiju_and_vap(self):
        patch = {"approval_policy": "auto-approve-all"}
        result = validate_runtime_config_patch(
            patch, kaiju_approved=True, vap_record_id="vap-abc-123"
        )
        assert result.allowed is True

    def test_rejects_sandbox_mode_change_without_vap(self):
        patch = [{"op": "replace", "path": "/sandbox_mode", "value": "none"}]
        result = validate_runtime_config_patch(patch, kaiju_approved=False, vap_record_id=None)
        assert result.allowed is False

    def test_allows_nonsensitive_config_change(self):
        patch = {"theme": "dark"}
        result = validate_runtime_config_patch(patch, kaiju_approved=False, vap_record_id=None)
        assert result.allowed is True


class TestMCP06ModelSupplyChain:
    """MCP-06: Malicious Model Intake / Supply Chain Quarantine."""

    def test_blocks_pickle_model(self):
        result = validate_model_intake("model.pkl")
        assert result.allowed is False
        assert "pickle" in result.reason

    def test_blocks_pytorch_model(self):
        result = validate_model_intake("checkpoint.pt")
        assert result.allowed is False

    def test_blocks_trust_remote_code(self):
        result = validate_model_intake("huggingface/model", trust_remote_code=True)
        assert result.allowed is False
        assert "trust_remote_code" in result.reason

    def test_blocks_uncensored_label(self):
        result = validate_model_intake("huggingface/model-abliterated", labels=["uncensored"])
        assert result.allowed is False

    def test_blocks_red_team_model(self):
        result = validate_model_intake("huggingface/harmbench-v1", labels=["red-team"])
        assert result.allowed is False

    def test_accepts_safe_model(self):
        result = validate_model_intake("huggingface/mistral-7b", trust_remote_code=False, labels=["general"])
        assert result.allowed is True

    def test_blocks_unsafe_suffixes(self):
        for suffix in [".pkl", ".pickle", ".bin", ".pt", ".pth", ".ckpt"]:
            result = validate_model_intake(f"model{suffix}")
            assert result.allowed is False, f"expected blocked: model{suffix}"
