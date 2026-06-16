import json

from nexus_os.governor.trust_kernel import TrustKernel
from nexus_os.mcp.server import GovernedMCPServer, MCPConfig, TrustKernelMCPAdapter


def _tool_payload(response):
    return json.loads(response["result"]["content"][0]["text"])


def test_initialize_and_tools_list():
    server = GovernedMCPServer(MCPConfig(trustkernel_mode="stub"))

    init = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert init["result"]["serverInfo"]["name"] == "nexus-os-governed-mcp"
    assert init["result"]["capabilities"] == {"tools": {}}

    listed = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tool_names = {tool["name"] for tool in listed["result"]["tools"]}
    assert "governance.get_status" in tool_names
    assert "memory.create_checkpoint" in tool_names
    assert "telegram.send_message" in tool_names


def test_read_only_drift_sweep_is_allowed():
    server = GovernedMCPServer(MCPConfig(trustkernel_mode="stub"))
    response = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "drift_monitor.run_sweep", "arguments": {"scope": "recent"}},
        }
    )

    payload = _tool_payload(response)
    assert payload["result"]["status"] == "completed"
    assert payload["trust_decision"]["allowed"] is True


def test_side_effect_tool_is_blocked_by_default():
    server = GovernedMCPServer(MCPConfig(trustkernel_mode="real", allow_side_effects=False))
    response = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "telegram.send_message",
                "arguments": {"chat_id": "123", "text": "hello"},
            },
        }
    )

    assert response["result"]["isError"] is True
    payload = _tool_payload(response)
    assert payload["blocked"] is True
    assert "explicit operator enablement" in payload["reason"]
    assert server.audit_events[-1].blocked is True


def test_checkpoint_requires_approval_by_default():
    server = GovernedMCPServer(MCPConfig(trustkernel_mode="stub"))
    response = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "memory.create_checkpoint",
                "arguments": {"note": "phase 6 checkpoint"},
            },
        }
    )

    payload = _tool_payload(response)
    assert payload["blocked"] is True
    assert response["result"]["isError"] is True


def test_unknown_tool_returns_jsonrpc_error():
    server = GovernedMCPServer(MCPConfig(trustkernel_mode="stub"))
    response = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "missing.tool", "arguments": {}},
        }
    )

    assert response["error"]["code"] == -32601


def test_side_effect_can_dry_run_when_explicitly_enabled():
    kernel = TrustKernel()
    for idx in range(5):
        kernel.record_task_outcome(
            agent_id="mcp-client",
            task_id=f"trusted-{idx}",
            success=True,
            lane="implementation",
        )
    server = GovernedMCPServer(
        MCPConfig(trustkernel_mode="real", allow_side_effects=True),
        trust_adapter=TrustKernelMCPAdapter(kernel=kernel, mode="real"),
    )
    # Memory checkpoints remain approval-required even when generic side effects are enabled.
    server.tools["telegram.send_message"] = server.tools["telegram.send_message"].__class__(
        **{**server.tools["telegram.send_message"].__dict__, "approval_required": False}
    )
    response = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "telegram.send_message",
                "arguments": {"chat_id": "123", "text": "hello"},
            },
        }
    )

    payload = _tool_payload(response)
    assert payload["result"]["status"] == "dry_run"
    assert payload["trust_decision"]["allowed"] is True

def test_governed_mcp_claim_pipeline():
    server = GovernedMCPServer(MCPConfig(trustkernel_mode="stub"))
    
    # 1. Request transient token
    req_token_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "governance.request_cycle_token", "arguments": {}},
        }
    )
    token_payload = _tool_payload(req_token_resp)
    assert token_payload["result"]["status"] == "granted"
    cycle_token = token_payload["result"]["cycle_token"]
    assert cycle_token.startswith("CYCLE-")

    # 2. Submit claim using the transient token
    submit_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "governance.submit_claim",
                "arguments": {
                    "claim_id": "mcp-claim-01",
                    "agent_id": "speci",
                    "description": "verified build works",
                    "evidence_items": [
                        {
                            "type": "command_output",
                            "content": "0 errors, build successfully completed",
                            "source": "runner",
                        }
                    ],
                    "cycle_token": cycle_token,
                },
            },
        }
    )
    submit_payload = _tool_payload(submit_resp)
    assert submit_payload["result"]["status"] == "pending"

    # 3. Verify the claim and check DB status tracking
    verify_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "governance.verify_claim",
                "arguments": {"claim_id": "mcp-claim-01"},
            },
        }
    )
    verify_payload = _tool_payload(verify_resp)
    assert verify_payload["result"]["status"] == "verified"

    # 4. Attempt submission without transient token -> must be rejected as INSUFFICIENT
    bad_submit_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "governance.submit_claim",
                "arguments": {
                    "claim_id": "mcp-claim-02",
                    "agent_id": "speci",
                    "description": "unauthorized build",
                    "evidence_items": [],
                },
            },
        }
    )
    bad_payload = _tool_payload(bad_submit_resp)
    assert bad_payload["result"]["status"] == "insufficient"

