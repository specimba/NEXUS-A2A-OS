from nexus_os.bridge.browser_http_diagnostic import (
    BrowserDiagnosticPolicy,
    BrowserHTTPDiagnosticRelay,
    validate_browser_diagnostic_request,
)


def test_prepare_allows_huggingface_https_get():
    decision = validate_browser_diagnostic_request(
        "https://huggingface.co/specimba/test",
        method="GET",
        headers={"User-Agent": "NEXUS", "Authorization": "Bearer secret"},
        audit_id="audit-1",
        operator="codex",
    )

    assert decision.allowed is True
    assert decision.gross_arguments is not None
    assert decision.gross_arguments["url"] == "https://huggingface.co/specimba/test"
    assert decision.gross_arguments["method"] == "GET"
    assert "Authorization" not in decision.gross_arguments["headers_json"]
    assert "User-Agent" in decision.gross_arguments["headers_json"]


def test_prepare_blocks_http_private_and_unlisted_hosts():
    assert not validate_browser_diagnostic_request("http://huggingface.co").allowed
    assert not validate_browser_diagnostic_request("https://127.0.0.1:7354/health").allowed
    assert not validate_browser_diagnostic_request("https://example.com").allowed


def test_prepare_caps_preview_size_to_policy():
    policy = BrowserDiagnosticPolicy(max_preview_bytes=128)
    decision = validate_browser_diagnostic_request(
        "https://raw.githubusercontent.com/specimba/nexus/main/README.md",
        safe_preview_max=9999,
        policy=policy,
    )

    assert decision.allowed is True
    assert decision.gross_arguments is not None
    assert decision.gross_arguments["safe_preview_max"] == 128


def test_prepare_rejects_mutating_methods():
    decision = validate_browser_diagnostic_request(
        "https://huggingface.co",
        method="POST",
    )

    assert decision.allowed is False
    assert "not allowed" in decision.reason


def test_relay_invoke_uses_validated_arguments_with_mock_transport():
    captured = {}

    def fake_transport(args):
        captured.update(args)
        return {"status_code": 200, "access_result": "allowed", "side_effects_enabled": False}

    relay = BrowserHTTPDiagnosticRelay(transport=fake_transport)
    result = relay.invoke(
        "https://huggingface.co",
        method="HEAD",
        audit_id="audit-2",
        operator="gpt-browser",
    )

    assert result["status_code"] == 200
    assert captured["method"] == "HEAD"
    assert captured["mode"] == "live"
    assert captured["audit_id"] == "audit-2"


def test_relay_invokes_a2a_transport_by_default(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return (
                b'{"jsonrpc":"2.0","result":{"id":"task-1","status":"completed",'
                b'"artifacts":[{"type":"text","text":"{\\"status_code\\": 200, \\"access_result\\": \\"allowed\\"}"}]}}'
            )

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = request.data.decode("utf-8")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("nexus_os.bridge.browser_http_diagnostic.urlopen", fake_urlopen)
    relay = BrowserHTTPDiagnosticRelay(bridge_url="http://127.0.0.1:7354")
    result = relay.invoke("https://huggingface.co", method="HEAD")

    assert result["status_code"] == 200
    assert captured["url"] == "http://127.0.0.1:7354/a2a/tasks/send"
    assert "browser_http_diagnostic" in captured["body"]


def test_relay_reports_jsonrpc_bridge_404_without_crashing():
    relay = BrowserHTTPDiagnosticRelay(
        bridge_url="http://127.0.0.1:1",
        protocol="jsonrpc",
        policy=BrowserDiagnosticPolicy(max_timeout_seconds=0.01),
    )
    result = relay.invoke("https://huggingface.co", method="HEAD")

    assert result["blocked"] is True
    assert "Bridge JSON-RPC call failed" in result["reason"] or "Bridge JSON-RPC HTTP" in result["reason"]


def test_relay_invoke_returns_block_without_transport_call():
    called = False

    def fake_transport(_args):
        nonlocal called
        called = True
        return {}

    relay = BrowserHTTPDiagnosticRelay(transport=fake_transport)
    result = relay.invoke("https://not-allowed.invalid")

    assert result["blocked"] is True
    assert called is False


def test_policy_from_env_expands_allowed_hosts_without_disabling_guards(monkeypatch):
    monkeypatch.setenv("NEXUS_BROWSER_HTTP_ALLOWED_HOSTS", "modelcontextprotocol.io, arxiv.org, bad:443, /bad")
    monkeypatch.setenv("NEXUS_BROWSER_HTTP_MAX_PREVIEW_BYTES", "99999")
    monkeypatch.setenv("NEXUS_BROWSER_HTTP_TIMEOUT_SECONDS", "99")

    relay = BrowserHTTPDiagnosticRelay()
    decision = relay.prepare("https://modelcontextprotocol.io/specification", method="GET", safe_preview_max=9000)

    assert decision.allowed is True
    assert relay.policy.max_preview_bytes == 4096
    assert relay.policy.max_timeout_seconds == 30.0
    assert decision.gross_arguments is not None
    assert decision.gross_arguments["safe_preview_max"] == 4096
    assert relay.prepare("https://127.0.0.1/secret").allowed is False


def test_prepare_strips_browser_secret_headers_case_and_space():
    decision = validate_browser_diagnostic_request(
        "https://huggingface.co",
        headers={
            " Authorization ": "Bearer secret",
            "Proxy-Authorization": "Basic secret",
            "X-CSRF-Token": "secret",
            "Accept": "text/html",
        },
    )

    assert decision.allowed is True
    assert decision.gross_arguments is not None
    headers_json = decision.gross_arguments["headers_json"]
    assert "secret" not in headers_json
    assert "Accept" in headers_json
