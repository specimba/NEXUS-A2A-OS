import ast
from pathlib import Path

SERVER = Path("tools/browser_ai_mcp/grok_mcp_server_v2.py")


def _source() -> str:
    return SERVER.read_text(encoding="utf-8")


def test_grok_mcp_server_v2_parses_as_python():
    ast.parse(_source())


def test_http_diagnostic_has_public_egress_guards():
    src = _source()

    assert "GROK_HTTP_ALLOWED_HOSTS" in src
    assert "BLOCKED_HTTP_HEADER_PREFIXES" in src
    assert "_diagnostic_private_or_local_host" in src
    assert "_NoRedirectHandler" in src
    assert "HTTP_MAX_BODY_BYTES" in src
    assert "urllib.request.urlopen(req" not in src
    assert "opener.open(req" in src


def test_http_diagnostic_description_is_bounded_not_general_proxy():
    src = _source()

    assert "Scoped HTTPS GET/HEAD diagnostic" in src
    assert "never performs writes" in src
    assert "arbitrary" not in src[src.index('name="http_diagnostic"'):src.index('def _http_diagnostic_log')].lower()


def test_health_exposes_hardening_fingerprint():
    src = _source()

    assert '"hardening": _http_diagnostic_policy_snapshot()' in src
    assert '"mcp_tool_count": len(TOOL_NAMES)' in src
    assert "continuity_append" in src
    assert "continuity_tail" in src
    assert "cdp_window_probe" in src
    assert "_resolve_continuity_path" in src

def test_runtime_writes_have_repo_local_fallback():
    src = _source()

    assert "GROK_FALLBACK_RUNTIME_DIR" in src
    assert "_write_jsonl_with_fallback" in src
    assert "_write_text_with_fallback" in src
    assert "_write_bytes_with_fallback" in src
    assert "written_evidence_file = _write_text_with_fallback" in src
    assert "written_dest = _write_bytes_with_fallback" in src
    assert '"runtime_write_policy"' in src

