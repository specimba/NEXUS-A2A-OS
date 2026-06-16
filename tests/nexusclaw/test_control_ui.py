from fastapi.testclient import TestClient

from nexus_os.nexusclaw.control_ui import control_app


def test_control_ui_dashboard_renders_operator_shell():
    client = TestClient(control_app)

    response = client.get("/")

    assert response.status_code == 200
    assert "NEXUSCLAW" in response.text
    assert "Preview Governed Send" in response.text
    assert "Dry-run-first" in response.text


def test_control_ui_status_is_dry_run_first():
    client = TestClient(control_app)

    response = client.get("/api/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "nexusclaw-control-ui"
    assert payload["default_dry_run"] is True
    assert payload["active_connections"] == 0
    assert "slack" in payload["available_platforms"]


def test_control_ui_favicon_is_quiet_no_content():
    client = TestClient(control_app)

    response = client.get("/favicon.ico")

    assert response.status_code == 204


def test_control_ui_message_dry_run_does_not_require_provider_token():
    client = TestClient(control_app)

    response = client.post(
        "/api/message",
        json={
            "platform": "slack",
            "target": "#ops",
            "text": "NEXUSCLAW dry-run validation",
            "dry_run": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["dry_run"] is True
    assert payload["platform"] == "slack"


def test_control_ui_message_rejects_empty_text():
    client = TestClient(control_app)

    response = client.post(
        "/api/message",
        json={"platform": "slack", "target": "#ops", "text": "", "dry_run": True},
    )

    assert response.status_code == 422
