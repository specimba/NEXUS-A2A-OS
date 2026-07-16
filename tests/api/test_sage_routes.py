from __future__ import annotations

import asyncio
import base64
import json
from fastapi import FastAPI
import sqlite3
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
import httpx
import pytest

from nexus_os.sage_gateway import routes

from nexus_os.sage_gateway.security import (
    SageBodyLimitMiddleware,
    sage_request_validation_handler,
)

TEST_KEY = "sage-test-key-" + ("a" * 48)


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("NEXUS_SAGE_API_KEY", TEST_KEY)
    monkeypatch.setenv("NEXUS_SAGE_API_KEY_FILE", str(tmp_path / "missing-sage-token"))
    monkeypatch.setenv("NEXUS_SAGE_GATEWAY_MODE", "observe_only")
    monkeypatch.setenv("NEXUS_SAGE_RUNTIME_DIR", str(tmp_path / "sage-runtime"))
    routes.reset_sage_stores_for_tests()
    app = FastAPI()
    app.add_middleware(SageBodyLimitMiddleware)
    app.add_exception_handler(RequestValidationError, sage_request_validation_handler)
    app.include_router(routes.router)
    with TestClient(app) as test_client:
        yield test_client
    routes.reset_sage_stores_for_tests()


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_KEY}"}


def test_sage_health_and_capabilities_are_truthful(client: TestClient) -> None:
    health = client.get("/api/sage/v1/health", headers=_headers())
    capabilities = client.get("/api/sage/v1/capabilities", headers=_headers())

    assert health.status_code == 200
    assert health.json()["plane"] == "brain-governance"
    assert health.json()["port_owner"] == 7352
    assert health.json()["execution_allowed"] is False
    assert capabilities.status_code == 200
    assert capabilities.json()["proposal_writes_enabled"] is False
    assert capabilities.json()["arbitrary_program_execution"] is False
    assert capabilities.json()["raw_memory_export"] is False
    assert capabilities.json()["self_approval"] is False



def test_sage_auth_accepts_operator_key_file_without_echoing_it(
    monkeypatch,
    tmp_path,
) -> None:
    key_file = tmp_path / ".sage_api_token"
    key_file.write_text(TEST_KEY, encoding="utf-8")
    monkeypatch.delenv("NEXUS_SAGE_API_KEY", raising=False)
    monkeypatch.setenv("NEXUS_SAGE_API_KEY_FILE", str(key_file))
    monkeypatch.setenv("NEXUS_SAGE_GATEWAY_MODE", "observe_only")
    app = FastAPI()
    app.add_middleware(SageBodyLimitMiddleware)
    app.add_exception_handler(RequestValidationError, sage_request_validation_handler)
    app.include_router(routes.router)

    with TestClient(app) as test_client:
        response = test_client.get("/api/sage/v1/health", headers=_headers())

    assert response.status_code == 200
    assert TEST_KEY not in response.text
    assert response.json()["principal"].startswith("nexus-sage:")


def test_sage_auth_fails_closed(client: TestClient, monkeypatch) -> None:
    assert client.get("/api/sage/v1/health").status_code == 401
    assert client.get(
        "/api/sage/v1/health",
        headers={"Authorization": "Bearer wrong"},
    ).status_code == 401

    monkeypatch.delenv("NEXUS_SAGE_API_KEY")
    assert client.get("/api/sage/v1/health", headers=_headers()).status_code == 503


def test_grounding_returns_manifest_without_file_content_or_paths(client: TestClient) -> None:
    response = client.get("/api/sage/v1/grounding", headers=_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["content_included"] is False
    assert payload["files"]
    serialized = response.text
    assert "file_content" not in serialized
    assert "C:\\Users" not in serialized
    assert all("name" in item and "available" in item for item in payload["files"])


def test_sage_body_limit_counts_actual_bytes(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_SAGE_MAX_BODY_BYTES", "1024")
    response = client.post(
        "/api/sage/v1/jobs",
        headers={**_headers(), "Content-Type": "application/json"},
        content=b'{"padding":"' + (b"x" * 2_000) + b'"}',
    )

    assert response.status_code == 413
    assert response.json()["code"] == "sage_payload_too_large"


def test_observe_only_mode_rejects_proposal_jobs(client: TestClient) -> None:
    response = client.post(
        "/api/sage/v1/jobs",
        headers=_headers(),
        json={
            "workflow_type": "grounding_audit",
            "parameters": {"files": ["NEXUS_MANIFEST.md"]},
            "idempotency_key": "observe-only-001",
        },
    )

    assert response.status_code == 403


def test_proposal_job_is_pending_governed_and_payload_idempotent(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("NEXUS_SAGE_GATEWAY_MODE", "proposal_write")
    body = {
        "workflow_type": "parallel_audit_proposal",
        "parameters": {
            "objective": "Audit relay and memory integration boundaries.",
            "domains": ["relay", "memory"],
            "max_agents": 4,
        },
        "idempotency_key": "proposal-job-001",
        "source_msg_id": "sage-message-1",
    }

    first = client.post("/api/sage/v1/jobs", headers=_headers(), json=body)
    duplicate = client.post("/api/sage/v1/jobs", headers=_headers(), json=body)
    changed = client.post(
        "/api/sage/v1/jobs",
        headers=_headers(),
        json={**body, "parameters": {
            "objective": "Audit relay only.",
            "domains": ["relay"],
            "max_agents": 2,
        }},
    )

    assert first.status_code == 202
    payload = first.json()
    assert payload["status"] == "pending_review"
    assert payload["execution_allowed"] is False
    assert payload["proposal"]["proposal_only"] is True
    assert payload["proposal"]["envelope"]["approval_state"] == "pending"
    assert payload["proposal"]["envelope"]["human_approved"] is False
    assert payload["expires_at"] > payload["created_at"]
    assert duplicate.status_code == 202
    assert duplicate.json() == payload
    assert duplicate.headers["X-NEXUS-Idempotency"] == "duplicate"
    assert changed.status_code == 409

    status = client.get(
        f"/api/sage/v1/jobs/{payload['job_id']}",
        headers=_headers(),
    )
    assert status.status_code == 200
    assert status.json()["status"] == "pending_review"
    assert status.json()["execution_allowed"] is False
    assert status.json()["expires_at"] == payload["expires_at"]


def test_pending_job_emits_receipt_bound_nexusclaw_handoff(
    client: TestClient,
    monkeypatch,
) -> None:
    """The existing six-operation boundary exposes a pending-only dry-run handoff."""

    monkeypatch.setenv("NEXUS_SAGE_GATEWAY_MODE", "proposal_write")
    body = {
        "workflow_type": "evidence_search",
        "parameters": {
            "query": "Audit the governed relay-health evidence boundary.",
            "sources": ["audit"],
            "max_results": 3,
        },
        "idempotency_key": "handoff-receipt-001",
    }

    created = client.post("/api/sage/v1/jobs", headers=_headers(), json=body)
    assert created.status_code == 202
    created_payload = created.json()

    status = client.get(
        f"/api/sage/v1/jobs/{created_payload['job_id']}",
        headers=_headers(),
    )
    assert status.status_code == 200

    for payload in (created_payload, status.json()):
        handoff = payload["nexusclaw_handoff"]
        assert handoff["schema"] == "nexus.sage-nexusclaw-handoff.v1"
        assert handoff["job_id"] == created_payload["job_id"]
        assert handoff["receipt"] == {
            "state": "pending_review",
            "workflow_type": "evidence_search",
            "proposal_sha256": handoff["receipt"]["proposal_sha256"],
            "parameters_sha256": payload["proposal"]["parameters_sha256"],
            "principal_verified": True,
        }
        assert handoff["proposal_only"] is True
        assert handoff["execution_allowed"] is False
        assert handoff["envelope"] == payload["proposal"]["envelope"]
        assert handoff["envelope"]["approval_state"] == "pending"
        assert handoff["envelope"]["human_approved"] is False
        assert "query" not in handoff
        assert "principal" not in handoff
        assert body["parameters"]["query"] not in str(handoff)


def test_pending_job_handoff_refuses_a_tampered_persisted_receipt(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("NEXUS_SAGE_GATEWAY_MODE", "proposal_write")
    body = {
        "workflow_type": "evidence_search",
        "parameters": {
            "query": "Inspect the canonical governed receipt seam.",
            "sources": ["grounding"],
            "max_results": 2,
        },
        "idempotency_key": "handoff-tamper-001",
    }
    created = client.post("/api/sage/v1/jobs", headers=_headers(), json=body)
    assert created.status_code == 202
    payload = created.json()

    tampered_proposal = dict(payload["proposal"])
    tampered_proposal["execution_allowed"] = True
    with sqlite3.connect(routes._store().path) as connection:
        connection.execute(
            "UPDATE sage_jobs SET proposal_json=? WHERE job_id=?",
            (json.dumps(tampered_proposal), payload["job_id"]),
        )

    response = client.get(
        f"/api/sage/v1/jobs/{payload['job_id']}",
        headers=_headers(),
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "SAGE pending receipt is not eligible for a governed handoff"
    }
    assert body["parameters"]["query"] not in response.text


@pytest.mark.parametrize("field", ["api_key", "password", "program", "command"])
def test_proposal_jobs_reject_secrets_and_execution_payloads(
    client: TestClient,
    monkeypatch,
    field: str,
) -> None:
    monkeypatch.setenv("NEXUS_SAGE_GATEWAY_MODE", "proposal_write")
    sentinel = "DUMMY_SECRET_SENTINEL_MUST_NOT_RETURN"
    response = client.post(
        "/api/sage/v1/jobs",
        headers=_headers(),
        json={
            "workflow_type": "grounding_audit",
            "parameters": {"files": ["NEXUS_MANIFEST.md"], field: sentinel},
            "idempotency_key": f"forbidden-{field}-001",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "sage_validation_error"
    assert sentinel not in response.text
    assert field in response.text
    assert all(set(item) == {"loc", "type"} for item in response.json()["detail"])
    assert field in response.text



@pytest.mark.parametrize(
    "unsafe_objective",
    [
        "api_key=sk-example-secret-material-1234567890",
        "Authorization: Bearer example-secret-material-1234567890",
        "-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJzYWdlLW9wZXJhdG9yIn0.signature123456",
        r"Inspect C:/Users/operator/.ssh/id_rsa",
        "Inspect /home/operator/.ssh/id_rsa",
        "Fetch https://example.invalid/private-evidence",
        "```python\nimport os\nprint(os.environ)\n```",
        "powershell -Command Get-ChildItem Env:",
        "subprocess.run(['whoami'])",
        "ａｐｉ＿ｋｅｙ＝ｓｋ－example-secret-material-1234567890",
        "api\u200b_key=example-secret-material-1234567890",
        "api%5Fkey%3Dsk-example-secret-material-1234567890",
        base64.b64encode(
            b"api_key=sk-example-secret-material-1234567890"
        ).decode("ascii"),
    ],
)
def test_proposal_jobs_reject_sensitive_persisted_string_content_without_echo(
    client: TestClient,
    monkeypatch,
    unsafe_objective: str,
) -> None:
    monkeypatch.setenv("NEXUS_SAGE_GATEWAY_MODE", "proposal_write")
    response = client.post(
        "/api/sage/v1/jobs",
        headers=_headers(),
        json={
            "workflow_type": "parallel_audit_proposal",
            "parameters": {
                "objective": unsafe_objective,
                "domains": ["relay"],
                "max_agents": 2,
            },
            "idempotency_key": "content-dlp-rejection-001",
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "SAGE proposal content was rejected by persistence policy"
    }
    assert unsafe_objective not in response.text
    with sqlite3.connect(routes._store().path) as connection:
        job_count = connection.execute("SELECT COUNT(*) FROM sage_jobs").fetchone()
        idempotency_count = connection.execute(
            "SELECT COUNT(*) FROM sage_job_idempotency"
        ).fetchone()
    assert job_count == (0,)
    assert idempotency_count == (0,)



@pytest.mark.parametrize(
    ("metadata_field", "sensitive_value"),
    [
        ("source_msg_id", "https://example.invalid/private-message"),
        ("idempotency_key", "sk-example-secret-material-1234567890"),
    ],
)
def test_proposal_content_dlp_covers_persisted_submission_metadata(
    client: TestClient,
    monkeypatch,
    metadata_field: str,
    sensitive_value: str,
) -> None:
    monkeypatch.setenv("NEXUS_SAGE_GATEWAY_MODE", "proposal_write")
    body = {
        "workflow_type": "evidence_search",
        "parameters": {
            "query": "Find relay health evidence.",
            "sources": ["audit"],
            "max_results": 5,
        },
        "idempotency_key": "metadata-content-dlp-001",
        "source_msg_id": "sage-message-safe-001",
    }
    body[metadata_field] = sensitive_value

    response = client.post(
        "/api/sage/v1/jobs",
        headers=_headers(),
        json=body,
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "SAGE proposal content was rejected by persistence policy"
    }
    assert sensitive_value not in response.text


def test_proposal_content_dlp_allows_normal_research_language(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("NEXUS_SAGE_GATEWAY_MODE", "proposal_write")
    response = client.post(
        "/api/sage/v1/jobs",
        headers=_headers(),
        json={
            "workflow_type": "parallel_audit_proposal",
            "parameters": {
                "objective": (
                    "Audit API-key handling descriptions, provider endpoint changes, "
                    "token exhaustion evidence, and shell-execution policy boundaries."
                ),
                "domains": ["modelrelay", "openai-compatible:mistral", "health_checks"],
                "max_agents": 3,
            },
            "idempotency_key": "content-dlp-normal-language-001",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "pending_review"


def test_proposal_content_dlp_allows_safe_encoded_reference(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("NEXUS_SAGE_GATEWAY_MODE", "proposal_write")
    safe_reference = base64.b64encode(b"grounding-evidence-2026").decode("ascii")
    response = client.post(
        "/api/sage/v1/jobs",
        headers=_headers(),
        json={
            "workflow_type": "evidence_search",
            "parameters": {
                "query": f"Find artifact {safe_reference} in the grounding index.",
                "sources": ["grounding"],
                "max_results": 5,
            },
            "idempotency_key": "content-dlp-safe-encoding-001",
        },
    )

    assert response.status_code == 202


def test_model_card_fetch_is_pinned_and_ignores_ambient_url(monkeypatch) -> None:
    seen: list[httpx.Request] = []
    monkeypatch.setenv("NEXUS_MODEL_CARD_URL", "http://attacker.invalid/collect")

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"models": []})

    payload = asyncio.run(
        routes._fetch_model_cards_projection(
            transport=httpx.MockTransport(handler),
        )
    )

    assert payload == {"models": []}
    assert len(seen) == 1
    assert str(seen[0].url) == "http://127.0.0.1:7356/api/model-cards"


def test_model_card_fetch_rejects_redirects() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            307,
            headers={"Location": "http://attacker.invalid/collect"},
        )

    with pytest.raises(ValueError, match="redirected"):
        asyncio.run(
            routes._fetch_model_cards_projection(
                transport=httpx.MockTransport(handler),
            )
        )


def test_model_card_fetch_caps_response_bytes() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"x" * (routes._MAX_MODEL_CARD_RESPONSE_BYTES + 1),
        )

    with pytest.raises(ValueError, match="size limit"):
        asyncio.run(
            routes._fetch_model_cards_projection(
                transport=httpx.MockTransport(handler),
            )
        )

def test_model_cards_use_canonical_projection_and_strip_runtime_errors(
    client: TestClient,
    monkeypatch,
) -> None:
    sentinel = "DUMMY_MODEL_CARD_SECRET_MUST_NOT_RETURN"

    async def fake_projection():
        return {
            "schema_version": 1,
            "generated_at": "2026-07-13T00:00:00Z",
            "benchmark_contract": {
                "dimensions": ["quality", "code", "reasoning", "swe", "speed", "cost_efficiency"],
                "no_data": "null",
                "policy_prior_is_not_benchmark": True,
                "provider_error": sentinel,
            },
            "summary": {
                "catalogue_offers": 236,
                "cli_model_ids": 133,
                "cli_visible_offers": 120,
                "observed_healthy": 1,
                "health_unverified": 200,
                "unavailable": 12,
                "rate_limited": 3,
                "evidence_backed_offers": 8,
                "configured_providers": 15,
                "authenticated_providers": 7,
                "api_key": sentinel,
            },
            "models": [
                {
                    "model_id": "z-ai/glm-5.2",
                    "label": "GLM-5.2",
                    "provider_key": "nvidia",
                    "routing": {
                        "cli_visible": True,
                        "cli_route_id": "z-ai/glm-5.2",
                        "eligible": True,
                        "state": "cli_visible",
                        "endpoint": "https://provider.invalid/v1",
                        "authorization": sentinel,
                    },
                    "health": {
                        "state": "unverified",
                        "raw_status": "pending",
                        "observed": False,
                        "latency_ms": None,
                        "uptime_percent": None,
                        "verdict": f"provider error: {sentinel}",
                        "last_checked_at": None,
                        "is_rate_limited": False,
                    },
                    "benchmarks": {
                        "status": "evidence_backed",
                        "dimensions": {
                            "quality": 0.7161,
                            "code": 0.684,
                            "reasoning": None,
                            "swe": None,
                            "speed": None,
                            "cost_efficiency": None,
                            "credential": sentinel,
                        },
                        "coverage": ["quality", "code", "credential"],
                        "confidence": "high",
                        "sources": [
                            "aa_coding",
                            "https://provider.invalid/private-score",
                            f"api_key={sentinel}",
                        ],
                        "as_of": "2026-07-08T00:00:00+00:00",
                        "catalogue_score": None,
                        "catalogue_score_label": None,
                        "matched_registry_id": "z-ai/glm-5.2",
                        "raw_provider_payload": {"secret": sentinel},
                    },
                    "policy_prior": {
                        "registry_tier": 96,
                        "label": "registry_policy_tier",
                        "secret": sentinel,
                    },
                    "registry": {
                        "context_tokens": 1048576,
                        "capabilities": {
                            "tools": True,
                            "thinking": True,
                            "api_key": sentinel,
                        },
                        "roles": ["frontier", "https://provider.invalid/private-role"],
                        "lanes": ["core", "secret_lane"],
                        "endpoint": "https://provider.invalid/v1",
                    },
                    "runtime": {"last_error": f"provider failed with {sentinel}"},
                },
                {
                    "model_id": "https://provider.invalid/credential-card",
                    "label": sentinel,
                    "provider_key": "nvidia",
                },
            ],
        }

    monkeypatch.setattr(routes, "_fetch_model_cards_projection", fake_projection)
    response = client.get("/api/sage/v1/model-cards", headers=_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["catalogue_offers"] == 236
    assert set(payload) == {
        "schema",
        "projection_schema_version",
        "generated_at",
        "benchmark_contract",
        "summary",
        "models",
        "returned",
    }
    assert set(payload["benchmark_contract"]) == {
        "dimensions",
        "no_data",
        "policy_prior_is_not_benchmark",
    }
    assert set(payload["summary"]) == {
        "catalogue_offers",
        "cli_model_ids",
        "cli_visible_offers",
        "observed_healthy",
        "health_unverified",
        "unavailable",
        "rate_limited",
        "evidence_backed_offers",
        "configured_providers",
        "authenticated_providers",
    }
    assert payload["returned"] == 1

    model = payload["models"][0]
    assert model["model_id"] == "z-ai/glm-5.2"
    assert set(model) == {
        "model_id", "label", "provider_key", "routing", "health",
        "benchmarks", "policy_prior", "registry",
    }
    assert set(model["routing"]) == {
        "cli_visible", "cli_route_id", "eligible", "state",
    }
    assert set(model["health"]) == {
        "state", "raw_status", "observed", "latency_ms", "uptime_percent",
        "last_checked_at", "is_rate_limited",
    }
    assert set(model["benchmarks"]["dimensions"]) == {
        "quality", "code", "reasoning", "swe", "speed", "cost_efficiency",
    }
    assert model["benchmarks"]["sources"] == ["aa_coding"]
    assert model["benchmarks"]["coverage"] == ["quality", "code"]
    assert model["registry"]["capabilities"] == {"tools": True, "thinking": True}
    assert model["registry"]["roles"] == ["frontier"]
    assert model["registry"]["lanes"] == ["core"]
    assert sentinel not in response.text
    assert "https://" not in response.text
    assert "runtime" not in model
    assert "verdict" not in model["health"]
