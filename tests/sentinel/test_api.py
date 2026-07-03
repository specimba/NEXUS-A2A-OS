from fastapi import FastAPI
from fastapi.testclient import TestClient

from nexus_os.sentinel.api import router, set_sentinel_service
from nexus_os.sentinel.models import CreateCaseRequest


def test_sentinel_router_contract(sentinel_factory):
    service, _, _ = sentinel_factory()
    set_sentinel_service(service)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    created = client.post(
        "/api/sentinel/cases",
        json={
            "case_id": "CASE-API",
            "title": "API case",
            "actor_id": "operator",
            "idempotency_key": "create-api-case",
        },
    )
    assert created.status_code == 201
    assert created.json()["stage"] == "INVESTIGATION"

    listing = client.get("/api/sentinel/cases")
    assert listing.status_code == 200
    assert listing.json()["cases"][0]["case_id"] == "CASE-API"
    assert listing.json()["cases"][0]["evidence_count"] == 0
    assert listing.json()["cases"][0]["event_count"] == 1
    assert listing.json()["cases"][0]["evidence_complete"] is True

    timeline = client.get("/api/sentinel/cases/CASE-API/timeline")
    assert timeline.status_code == 200
    assert timeline.json()["events"][0]["event_type"] == "case_created"

    set_sentinel_service(None)


def test_brain_api_registers_sentinel_routes():
    from nexus_os.api.brain_api import brain_app

    paths = {route.path for route in brain_app.routes}
    assert "/api/sentinel/cases" in paths
    assert "/api/sentinel/cases/{case_id}/verify" in paths
    assert "/api/sentinel/claims/validate" in paths

