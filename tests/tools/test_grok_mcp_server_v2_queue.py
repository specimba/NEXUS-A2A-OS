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

import asyncio


class _A2ARequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def test_a2a_send_is_proposal_bound_and_never_directly_dispatches(monkeypatch, tmp_path):
    server = _load_server(monkeypatch, tmp_path)

    def direct_dispatch_must_not_run(*args, **kwargs):
        raise AssertionError("inbound A2A must not directly dispatch an MCP skill")

    monkeypatch.setattr(server, "_a2a_dispatch_skill", direct_dispatch_must_not_run)
    response = asyncio.run(
        server.handle_a2a_tasks_send(
            _A2ARequest(
                {
                    "jsonrpc": "2.0",
                    "id": "rpc-1",
                    "method": "tasks/send",
                    "params": {
                        "id": "a2a-proposal-smoke",
                        "skill_id": "coordination_queue",
                        "sender": "external-test",
                        "mode": "live",
                        "approval_state": "approved",
                        "message": {"parts": [{"type": "text", "text": "write a task"}]},
                    },
                }
            )
        )
    )
    payload = json.loads(response.body)

    assert payload["result"]["status"] == "proposed"
    result_text = json.loads(payload["result"]["artifacts"][0]["text"])
    assert result_text["proposal_only"] is True
    stored = server._a2a_task_load("a2a-proposal-smoke")
    assert stored["governance"]["execution_allowed"] is False
    assert stored["governance"]["envelope"]["approval_state"] == "pending"
    assert stored["governance"]["nexusclaw"]["status"] == "dry_run"
