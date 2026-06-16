"""Tests for NEXUS Brain API wiki + messaging + dashboard endpoints."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.api.brain_api import brain_app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(brain_app)


WIKI_ENDPOINTS = [
    "/api/wiki",
    "/api/wiki/pages",
    "/api/wiki/sources",
]

MESSAGING_ENDPOINTS = [
    "/api/messaging",
    "/api/messaging/history",
]

DASHBOARD_ENDPOINTS = [
    "/api/dashboard/sync",
]


class TestBrainAPIWikiEndpoints:
    @pytest.mark.parametrize("endpoint", WIKI_ENDPOINTS)
    def test_wiki_endpoints_return_200(self, client, endpoint):
        resp = client.get(endpoint, headers={"X-Api-Key": "test"})
        assert resp.status_code == 200

    def test_wiki_search_requires_q(self, client):
        resp = client.get("/api/wiki/search", headers={"X-Api-Key": "test"})
        assert resp.status_code == 422

    def test_wiki_search_with_query(self, client):
        resp = client.get("/api/wiki/search?q=test", headers={"X-Api-Key": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "query" in data

    def test_wiki_refresh_requires_auth(self, client):
        resp = client.post("/api/wiki/refresh")
        assert resp.status_code in (401, 403, 422)

    def test_wiki_page_not_found(self, client):
        resp = client.get("/api/wiki/nonexistent_page", headers={"X-Api-Key": "test"})
        assert resp.status_code == 404

    def test_wiki_status_structure(self, client):
        resp = client.get("/api/wiki", headers={"X-Api-Key": "test"})
        data = resp.json()
        assert "running" in data
        assert "pages" in data
        assert "dossiers" in data


class TestBrainAPIMessagingEndpoints:
    @pytest.mark.parametrize("endpoint", MESSAGING_ENDPOINTS)
    def test_messaging_endpoints_return_200(self, client, endpoint):
        resp = client.get(endpoint, headers={"X-Api-Key": "test"})
        assert resp.status_code == 200

    def test_messaging_status_structure(self, client):
        resp = client.get("/api/messaging", headers={"X-Api-Key": "test"})
        data = resp.json()
        assert "running" in data
        assert "enabled_platforms" in data
        assert "telegram" in data
        assert "slack" in data
        assert "discord" in data

    def test_messaging_history_structure(self, client):
        resp = client.get("/api/messaging/history", headers={"X-Api-Key": "test"})
        data = resp.json()
        assert "history" in data
        assert isinstance(data["history"], list)


class TestBrainAPIDashboardEndpoints:
    @pytest.mark.parametrize("endpoint", DASHBOARD_ENDPOINTS)
    def test_dashboard_endpoints_return_200(self, client, endpoint):
        resp = client.get(endpoint, headers={"X-Api-Key": "test"})
        assert resp.status_code == 200

    def test_dashboard_sync_structure(self, client):
        resp = client.get("/api/dashboard/sync", headers={"X-Api-Key": "test"})
        data = resp.json()
        assert "running" in data
        assert "ws_connected" in data
        assert "dashboard_url" in data


class TestBrainAPILegacyEndpoints:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_providers(self, client):
        resp = client.get("/api/providers", headers={"X-Api-Key": "test"})
        assert resp.status_code == 200

    def test_integrations(self, client):
        resp = client.get("/api/integrations", headers={"X-Api-Key": "test"})
        assert resp.status_code == 200

    def test_trust(self, client):
        resp = client.get("/api/trust", headers={"X-Api-Key": "test"})
        assert resp.status_code == 200

    def test_state(self, client):
        resp = client.get("/api/state", headers={"X-Api-Key": "test"})
        assert resp.status_code == 200
