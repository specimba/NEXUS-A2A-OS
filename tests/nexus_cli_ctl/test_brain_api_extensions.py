"""Tests for NEXUS Brain API wiki + messaging + dashboard endpoints."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.api.brain_api import brain_app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _auth_token(monkeypatch):
    # Auth is a real shared secret now; make the suite's static "test"
    # header the valid token for these endpoint tests.
    monkeypatch.setenv("NEXUS_BRAIN_TOKEN", "test")


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


class TestBrainAPIModelRelayAliases:
    def test_models_alias_delegates_to_lazy_inventory(self, client, monkeypatch):
        calls = []

        class FakeProxy:
            async def list_models(self):
                calls.append("list_models")
                return {"object": "list", "data": [{"id": "safe-small-guard"}]}

        monkeypatch.setattr("nexus_os.api.brain_api.get_relay_proxy", lambda: FakeProxy())

        resp = client.get("/models", headers={"X-Api-Key": "test"})

        assert resp.status_code == 200
        assert resp.json()["data"][0]["id"] == "safe-small-guard"
        assert calls == ["list_models"]

    def test_model_health_alias_is_explicit_health_call_only(self, client, monkeypatch):
        calls = []

        class FakeProxy:
            async def health(self):
                calls.append("health")
                return {"status": "ok", "relay": "fake"}

        monkeypatch.setattr("nexus_os.api.brain_api.get_relay_proxy", lambda: FakeProxy())

        resp = client.get("/model/health", headers={"X-Api-Key": "test"})

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "relay": "fake"}
        assert calls == ["health"]

    def test_model_select_alias_uses_registry_name_not_missing_id(self, client, monkeypatch):
        from nexus_os.models.registry import ModelRegistry

        registry = ModelRegistry()
        registry.register_model(
            "walledguard-edge",
            "local",
            role="core",
            params_b=0.6,
            allowed_lanes=["core"],
        )
        registry.register_domain(
            "security",
            models=[registry.get_model("walledguard-edge")],
        )

        monkeypatch.setattr("nexus_os.models.registry.get_registry", lambda: registry)

        resp = client.get("/model/select?task_type=security", headers={"X-Api-Key": "test"})

        assert resp.status_code == 200
        assert resp.json()["model_id"] == "walledguard-edge"
        assert resp.json()["selected_via"] == "registry"


class TestBrainAPIStressReport:
    def test_stress_report_writes_to_current_sink_interfaces(self, client, monkeypatch):
        calls = {"sync": [], "archivist": [], "broadcast": []}

        class FakeOrchestrator:
            def sync_memory_context(self, **kwargs):
                calls["sync"].append(kwargs)
                return {"ok": True}

        async def fake_broadcast(topic, payload):
            calls["broadcast"].append((topic, payload))

        def fake_generate_log_entry(action, summary, details=None):
            calls["archivist"].append({
                "action": action,
                "summary": summary,
                "details": details,
            })
            return "entry"

        monkeypatch.setattr("nexus_os.api.brain_api.get_orchestrator", lambda: FakeOrchestrator())
        monkeypatch.setattr("nexus_os.api.brain_api.ws_manager.broadcast", fake_broadcast)
        monkeypatch.setattr(
            "nexus_os.archivist.archivist.generate_log_entry",
            fake_generate_log_entry,
        )

        resp = client.post(
            "/api/stress/report",
            headers={"X-Api-Key": "test"},
            json={
                "run_id": "stress-test-001",
                "team": "purple",
                "scenario": "injection",
                "count": 3,
                "model": "walledguard-edge",
                "attack_success_rate": 0.25,
                "refusal_rate": 0.5,
                "robustness_score": 0.75,
                "latency_ms": 42,
                "tokens_used": 123,
                "results": [{"id": "case-1", "ok": True}],
                "metadata": {"source": "unit"},
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["run_id"] == "stress-test-001"
        assert data["sinks"] == {
            "vault_episodic": True,
            "websocket_broadcast": True,
            "archivist_queue": True,
        }

        assert calls["sync"] == [{
            "agent_id": "nexusctl_stress_lab",
            "query": "stress_report:stress-test-001:purple:injection:ASR=0.25",
            "action": "write",
        }]
        assert calls["broadcast"][0][0] == "stress"
        assert calls["broadcast"][0][1]["run_id"] == "stress-test-001"
        assert calls["archivist"][0]["action"] == "stress_report:purple:injection"
        assert calls["archivist"][0]["details"]["run_id"] == "stress-test-001"

    def test_stress_report_does_not_reference_removed_sink_names(self):
        import inspect
        import nexus_os.api.brain_api as brain_api

        source = inspect.getsource(brain_api.stress_report)
        assert "log_to_worklog" not in source
        assert "ingest_stress_report" not in source
        assert "sync_memory_context" in source
        assert "generate_log_entry" in source
