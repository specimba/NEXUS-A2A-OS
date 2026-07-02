"""Tests for nexus_os/api/nexusclaw_routes.py (Phase E1 endpoints).

Covers audit findings on the /status endpoint reporting fabricated
stats (hardcoded avgTrust=75.0, online/busy/error keys the pool never
returns) and a NameError in /intervene (intervention_id referenced in
its own initializer).
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import nexus_os.api.nexusclaw_routes as routes


@pytest.fixture(autouse=True)
def _auth_token(monkeypatch):
    # Router auth now validates the Brain API shared secret (the old
    # startswith("nexus-") pattern is rejected as guessable).
    monkeypatch.setenv("NEXUS_BRAIN_TOKEN", "nexus-test-key")


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


class FakePool:
    def stats(self):
        return {
            "total_agents": 5,
            "available_agents": 4,
            "by_type": {"internal": 5},
            "by_status": {"online": 3, "busy": 1, "degraded": 1, "offline": 0, "halted": 0},
            "avg_trust": 88.0,
            "capabilities": {},
        }


class FakeOrchStatus:
    active_brainstorms = 2


class FakeOrchestrator:
    def status(self):
        return FakeOrchStatus()


class TestStatusEndpoint:
    def test_reports_real_pool_stats(self, client, monkeypatch):
        """avgTrust must come from the pool, not a hardcoded 75.0; agent
        counts must come from by_status (the keys stats() actually returns)."""
        monkeypatch.setattr(routes, "get_agent_pool", lambda: FakePool())
        monkeypatch.setattr(routes, "get_orchestrator", lambda: FakeOrchestrator())

        resp = client.get("/api/nexusclaw/status")

        assert resp.status_code == 200
        stats = resp.json()["stats"]
        assert stats["trustEngine"]["avgTrust"] == 88.0
        assert stats["trustEngine"]["degradedAgents"] == 1
        assert stats["agentPool"]["total"] == 5
        assert stats["agentPool"]["online"] == 3
        assert stats["agentPool"]["busy"] == 1

    def test_empty_pool_reports_zero_not_75(self, client, monkeypatch):
        class EmptyPool:
            def stats(self):
                return {"total_agents": 0, "by_status": {}, "avg_trust": 0.0}

        monkeypatch.setattr(routes, "get_agent_pool", lambda: EmptyPool())
        monkeypatch.setattr(routes, "get_orchestrator", lambda: FakeOrchestrator())

        resp = client.get("/api/nexusclaw/status")

        assert resp.status_code == 200
        assert resp.json()["stats"]["trustEngine"]["avgTrust"] == 0.0


class TestInterventionEndpoint:
    def test_intervene_returns_generated_id(self, client):
        """The handler used to raise NameError (intervention_id referenced
        before assignment), surfacing as HTTP 500 on every call."""
        resp = client.post(
            "/api/nexusclaw/intervene",
            json={"intervention": "pause", "target": "nexus-vault"},
            headers={"X-API-Key": "nexus-test-key"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["intervention_id"].startswith("intervene-")
        assert len(body["intervention_id"]) > len("intervene-")

    def test_intervene_requires_api_key(self, client):
        resp = client.post(
            "/api/nexusclaw/intervene",
            json={"intervention": "pause", "target": "nexus-vault"},
        )
        assert resp.status_code == 401
