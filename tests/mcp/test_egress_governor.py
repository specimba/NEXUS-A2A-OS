from nexus_os.bridge.browser_http_diagnostic import BrowserHTTPDiagnosticRelay
from nexus_os.mcp import EgressRequest as PublicEgressRequest
from nexus_os.mcp import McpEgressGovernor as PublicMcpEgressGovernor
from nexus_os.mcp.egress_governor import EgressRequest, McpEgressGovernor



def test_public_mcp_package_exports_egress_governor():
    assert PublicEgressRequest is EgressRequest
    assert PublicMcpEgressGovernor is McpEgressGovernor


def test_governor_dry_run_plans_without_transport_call():
    called = False

    def fake_transport(_args):
        nonlocal called
        called = True
        return {}

    governor = McpEgressGovernor(relay=BrowserHTTPDiagnosticRelay(transport=fake_transport))
    result = governor.execute(EgressRequest(url="https://huggingface.co", dry_run=True))

    assert result.decision.allowed is True
    assert result.executed is False
    assert result.result["access_result"] == "planned"
    assert result.result["side_effects_enabled"] is False
    assert called is False


def test_governor_blocks_unlisted_hosts_before_transport():
    called = False

    def fake_transport(_args):
        nonlocal called
        called = True
        return {}

    governor = McpEgressGovernor(relay=BrowserHTTPDiagnosticRelay(transport=fake_transport))
    result = governor.execute(EgressRequest(url="https://example.com", dry_run=False))

    assert result.executed is False
    assert result.result["blocked"] is True
    assert "allowlist" in result.result["reason"]
    assert called is False


def test_governor_token_budget_denial_blocks_live_transport():
    called = False

    def fake_transport(_args):
        nonlocal called
        called = True
        return {}

    governor = McpEgressGovernor(
        relay=BrowserHTTPDiagnosticRelay(transport=fake_transport),
        token_budget_checker=lambda _payload: False,
    )
    result = governor.execute(EgressRequest(url="https://huggingface.co", dry_run=False))

    assert result.executed is False
    assert result.result["reason"] == "token_budget_denied"
    assert called is False


def test_governor_approval_denial_blocks_live_transport():
    called = False

    def fake_transport(_args):
        nonlocal called
        called = True
        return {}

    governor = McpEgressGovernor(
        relay=BrowserHTTPDiagnosticRelay(transport=fake_transport),
        approval_checker=lambda _payload: False,
    )
    result = governor.execute(EgressRequest(url="https://huggingface.co", dry_run=False))

    assert result.executed is False
    assert result.result["reason"] == "approval_denied"
    assert called is False


def test_governor_live_execution_invokes_validated_transport_and_memory():
    calls = []
    memory = []

    def fake_transport(args):
        calls.append(args)
        return {"status_code": 200, "access_result": "allowed"}

    governor = McpEgressGovernor(
        relay=BrowserHTTPDiagnosticRelay(transport=fake_transport),
        memory_sink=memory.append,
    )
    result = governor.execute(
        EgressRequest(
            url="https://huggingface.co",
            method="HEAD",
            dry_run=False,
            audit_id="audit-live",
            operator="grok-director",
        )
    )

    assert result.executed is True
    assert result.result["status_code"] == 200
    assert result.result["side_effects_enabled"] is False
    assert calls[0]["audit_id"] == "audit-live"
    assert calls[0]["operator"] == "grok-director"
    assert [item["phase"] for item in memory] == ["before", "after"]


def test_relay_execute_governed_dry_run_and_gate_order():
    called = False
    memory = []

    def fake_transport(_args):
        nonlocal called
        called = True
        return {}

    relay = BrowserHTTPDiagnosticRelay(transport=fake_transport)
    result = relay.execute_governed(
        "https://huggingface.co",
        dry_run=True,
        token_budget_checker=lambda payload: payload["bridge_tool"] == "http_diagnostic",
        memory_sink=memory.append,
    )

    assert result["access_result"] == "planned"
    assert result["side_effects_enabled"] is False
    assert called is False
    assert [item["phase"] for item in memory] == ["before", "after"]


