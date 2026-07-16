import importlib.util
import json
from pathlib import Path

from nexus_os.security.mcp_gateway import (
    taint_tool_output,
    tool_schema_hashes,
    validate_registry_snapshot,
)

SERVER = Path("tools/browser_ai_mcp/grok_mcp_server_v2.py")


def _load_server(monkeypatch, tmp_path):
    monkeypatch.setenv("GROK_COORD_DIR", str(tmp_path / "coord"))
    monkeypatch.setenv("GROK_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("GROK_EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("GROK_PHASE2_DIR", str(tmp_path / "phase2"))
    monkeypatch.setenv("GROK_FALLBACK_RUNTIME_DIR", str(tmp_path / "fallback"))
    spec = importlib.util.spec_from_file_location("grok_mcp_server_v2_gateway_test", SERVER)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_schema_hash_mismatch_blocks_registry_snapshot():
    baseline = [
        {"name": "http_diagnostic", "description": "read-only", "input_schema": {"url": "str"}},
        {"name": "task_add", "description": "queue", "input_schema": {"prompt": "str"}},
    ]
    pinned = tool_schema_hashes(baseline)
    changed = [
        {"name": "http_diagnostic", "description": "read-write proxy", "input_schema": {"url": "str"}},
        {"name": "task_add", "description": "queue", "input_schema": {"prompt": "str"}},
    ]

    decision = validate_registry_snapshot(changed, pinned_schema_hashes=pinned)

    assert decision.allowed is False
    assert decision.reason == "schema_drift"
    assert decision.changed_tools == ("http_diagnostic",)


def test_duplicate_tool_shadowing_blocks_registry_snapshot():
    tools = [
        {"name": "task_add", "description": "trusted", "input_schema": {}},
        {"name": "task_add", "description": "shadowed", "input_schema": {"extra": True}},
    ]

    decision = validate_registry_snapshot(tools)

    assert decision.allowed is False
    assert decision.reason == "duplicate_tool_names"
    assert decision.duplicate_tools == ("task_add",)


def test_tool_output_taint_contains_source_and_payload_hash():
    payload = {"status_code": 200, "access_result": "allowed"}

    taint = taint_tool_output(payload, tool_name="http_diagnostic", source_mcp_server="nexus-grok-bridge-v2")

    assert taint["tainted"] is True
    assert taint["tool_name"] == "http_diagnostic"
    assert taint["source_mcp_server"] == "nexus-grok-bridge-v2"
    assert len(taint["payload_sha256"]) == 64


def test_registry_debug_exposes_schema_hashes_without_changing_tool_count(monkeypatch, tmp_path):
    server = _load_server(monkeypatch, tmp_path)

    registry = json.loads(server.handle_registry_debug())

    assert registry["tool_count"] == 25
    assert registry["mcp_tool_count"] == 25
    assert registry["l1_registry_schema_hash"] is True
    assert registry["l3_output_taint"] is True
    assert registry["schema_drift_decision"]["allowed"] is True
    assert registry["schema_drift_decision"]["reason"] == "no_pinned_schema_baseline"
    assert "registry_schema_hash" in registry
    assert registry["tool_schema_hashes"]["http_diagnostic"]


def test_http_diagnostic_private_egress_block_includes_taint(monkeypatch, tmp_path):
    server = _load_server(monkeypatch, tmp_path)

    result = json.loads(server.handle_http_diagnostic(url="https://127.0.0.1", method="HEAD"))

    assert result["access_result"] == "error"
    assert "Private" in result["error"]
    assert result["taint"]["tainted"] is True
    assert result["taint"]["tool_name"] == "http_diagnostic"
    assert result["taint"]["source_mcp_server"] == "nexus-grok-bridge-v2"
