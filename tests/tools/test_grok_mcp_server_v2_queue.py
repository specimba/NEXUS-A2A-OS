import importlib.util
import json
from pathlib import Path


SERVER = Path("tools/browser_ai_mcp/grok_mcp_server_v2.py")


def _load_server(monkeypatch, tmp_path):
    monkeypatch.setenv("GROK_COORD_DIR", str(tmp_path / "coord"))
    monkeypatch.setenv("GROK_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("GROK_EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("GROK_PHASE2_DIR", str(tmp_path / "phase2"))
    monkeypatch.setenv("GROK_FALLBACK_RUNTIME_DIR", str(tmp_path / "fallback"))
    spec = importlib.util.spec_from_file_location("grok_mcp_server_v2_test", SERVER)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_task_add_is_immediately_visible_in_list_and_status(monkeypatch, tmp_path):
    server = _load_server(monkeypatch, tmp_path)

    created = json.loads(server.handle_task_add("diagnostic", "queue visibility regression", 3))
    task_id = created["task_id"]

    assert created["last_added_task_id"] == task_id
    assert created["queue_revision"] == 1
    assert created["visible_in_task_list"] is True

    listed = json.loads(server.handle_task_list("all", task_id))
    assert listed["last_added_task_id"] == task_id
    assert listed["queue_revision"] == 1
    assert listed["filter_task_id"] == task_id
    assert [task["id"] for task in listed["tasks"]["pending"]] == [task_id]

    status = json.loads(server.handle_coordination_status())
    assert status["last_added_task_id"] == task_id
    assert status["queue_revision"] == 1
    assert status["queue_counts"]["pending"] == 1
    assert status["total"] == 1
