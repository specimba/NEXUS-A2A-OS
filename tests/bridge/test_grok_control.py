import pytest

from nexus_os.bridge.grok_control import validate_grok_control_event


def _event(**overrides):
    payload = {
        "kind": "grok_control_state",
        "generated_at": "2026-06-18T00:00:00.000Z",
        "tab_id": 1,
        "url": "https://grok.com/share/test",
        "status": "idle",
        "response_chars": 120,
        "continue_count": 0,
        "surface_sweep_suspected": True,
        "action_taken": "observe_only",
        "preview": "short answer",
    }
    payload.update(overrides)
    return payload


def test_grok_control_event_is_telemetry_only():
    decision = validate_grok_control_event(_event())

    assert decision.accepted is True
    data = decision.to_dict()
    assert data["acceptance_scope"] == "telemetry_only_not_task_acceptance"
    assert data["recommendation"] == "draft_continue_or_assign_concrete_artifact"


def test_grok_control_event_caps_preview_and_counters():
    decision = validate_grok_control_event(
        _event(preview="x" * 900, response_chars=2_000_000, continue_count=999)
    )

    assert decision.accepted is True
    assert len(decision.normalized["preview"]) == 500
    assert decision.normalized["response_chars"] == 1_000_000
    assert decision.normalized["continue_count"] == 100


def test_grok_control_event_rejects_unknown_status():
    decision = validate_grok_control_event(_event(status="done-and-approved"))

    assert decision.accepted is False
    assert "invalid_status" in decision.reason


fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient
from nexus_os.bridge.server import create_app


def test_grok_control_route_accepts_local_telemetry(tmp_path):
    app = create_app(governance_db_path=str(tmp_path / "governance.db"))
    client = TestClient(app)

    response = client.post("/api/grok-control/events", json=_event())

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["acceptance_scope"] == "telemetry_only_not_task_acceptance"
