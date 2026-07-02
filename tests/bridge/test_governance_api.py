"""Focused tests for the governance REST wrapper on port 7352."""

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from nexus_os.bridge.server import BridgeServer, create_app
from nexus_os.governor.kaiju_auth import AuthResult, Decision


class _DenyingGovernor:
    def __init__(self):
        self.calls = []

    def check_access(self, **kwargs):
        self.calls.append(kwargs)
        return AuthResult(Decision.DENY, "canonical denial", kwargs.get("trace_id"))


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "governance-test.db"
    app = create_app(governance_db_path=str(db_path))
    return TestClient(app)


class TestGovernanceEndpoints:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "ok"
        assert payload["governance_rest_wrapper"] is True
        assert payload["governance_db_path"].endswith("governance-test.db")

    def test_skills_propose(self, client):
        payload = {
            "skill": "vault.store",
            "params": {"track": "EVENT", "data": "test"},
            "agent_id": "test-agent",
            "provenance": "pytest",
        }
        resp = client.post("/skills/propose", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["skill"] == "vault.store"
        assert "id" in data
        assert data["status"] in ("approved", "needs_review", "denied")

    def test_skills_status(self, client):
        create_resp = client.post(
            "/skills/propose",
            json={"skill": "test.lookup", "params": {}, "agent_id": "test-agent"},
        )
        pid = create_resp.json()["id"]
        resp = client.get(f"/skills/status/{pid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == pid

    def test_skills_status_not_found(self, client):
        resp = client.get("/skills/status/PROP-NONEXISTENT")
        assert resp.status_code == 404

    def test_dashboard_stats(self, client):
        resp = client.get("/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "vault" in data
        assert "agents" in data
        assert "recent_proposals" in data
        assert data["service"] == "nexus-governance"

    def test_governance_proposals(self, client):
        resp = client.get("/governance/proposals")
        assert resp.status_code == 200
        data = resp.json()
        assert "proposals" in data
        assert "count" in data

    def test_governance_approve(self, client):
        create_resp = client.post(
            "/skills/propose",
            json={"skill": "test.approve", "params": {}, "agent_id": "test-agent"},
        )
        pid = create_resp.json()["id"]
        resp = client.post(
            "/governance/approve",
            json={"proposal_id": pid, "approver": "test-admin", "decision": "approve"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_tasks_heartbeat(self, client):
        resp = client.post("/tasks/heartbeat", json={"agent_id": "test-agent"})
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ALIVE", "KILLED", "QUARANTINED", "CIRCUIT_BROKEN")

    def test_tasks_result(self, client):
        payload = {
            "task_id": "task-test-001",
            "agent_id": "test-agent",
            "status": "completed",
            "output": "Task completed successfully",
        }
        resp = client.post("/tasks/result", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "recorded"
        assert data["vap_logged"] is True
        assert data["durable_storage"] == "sqlite"

def test_dashboard_proposal_uses_canonical_governor(tmp_path):
    governor = _DenyingGovernor()
    bridge = BridgeServer(
        governor=governor,
        db_path=str(tmp_path / "governance-parity.db"),
    )
    client = TestClient(create_app(bridge=bridge))
    response = client.post(
        "/skills/propose",
        json={
            "skill": "custom.operation",
            "params": {"intent": "verify canonical parity"},
            "agent_id": "test-agent",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "denied"
    assert governor.calls[0]["action"] == "custom.operation"
