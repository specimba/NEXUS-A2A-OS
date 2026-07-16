"""Focused security and forwarding tests for the NEXUS SAGE tunnel edge."""

from __future__ import annotations

import logging

from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
import httpx
import pytest

from nexus_os.sage_gateway import edge
from nexus_os.sage_gateway import routes
from nexus_os.sage_gateway.security import (
    SageBodyLimitMiddleware,
    sage_request_validation_handler,
)


_TEST_KEY = "sage-edge-unit-key-" + ("x" * 40)
_AUTHORIZATION = f"Bearer {_TEST_KEY}"


@pytest.fixture(autouse=True)
def _configured_sage_auth(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_SAGE_API_KEY", _TEST_KEY)
    monkeypatch.setenv("NEXUS_SAGE_GATEWAY_MODE", "observe_only")
    monkeypatch.setattr(
        edge,
        "_PROCESS_ABUSE_GUARD",
        edge._EdgeAbuseGuard(
            max_in_flight=4,
            max_requests=60,
            window_seconds=60,
        ),
    )


class _FakeClock:
    def __init__(self, now: float = 100.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _app(handler):
    return edge.create_sage_edge_app(transport=httpx.MockTransport(handler))


def _client(app, **kwargs):
    return TestClient(app, headers={"Authorization": _AUTHORIZATION}, **kwargs)


def test_abuse_control_defaults_are_bounded(monkeypatch) -> None:
    for name in (
        "NEXUS_SAGE_EDGE_MAX_IN_FLIGHT",
        "NEXUS_SAGE_EDGE_RATE_LIMIT_REQUESTS",
        "NEXUS_SAGE_EDGE_RATE_LIMIT_WINDOW_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    assert edge.edge_max_in_flight() == 4
    assert edge.edge_rate_limit_requests() == 60
    assert edge.edge_rate_limit_window_seconds() == 60


@pytest.mark.parametrize(
    ("name", "getter"),
    [
        ("NEXUS_SAGE_EDGE_MAX_IN_FLIGHT", edge.edge_max_in_flight),
        ("NEXUS_SAGE_EDGE_RATE_LIMIT_REQUESTS", edge.edge_rate_limit_requests),
        (
            "NEXUS_SAGE_EDGE_RATE_LIMIT_WINDOW_SECONDS",
            edge.edge_rate_limit_window_seconds,
        ),
    ],
)
@pytest.mark.parametrize(
    "value",
    ["", "0", "-1", "+1", "1.0", " 2", "2 ", "full", "999999"],
)
def test_abuse_control_env_rejects_ambiguous_or_unbounded_values(
    monkeypatch,
    name: str,
    getter,
    value: str,
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError):
        getter()


@pytest.mark.parametrize(
    ("name", "getter", "value"),
    [
        ("NEXUS_SAGE_EDGE_MAX_IN_FLIGHT", edge.edge_max_in_flight, "17"),
        (
            "NEXUS_SAGE_EDGE_RATE_LIMIT_REQUESTS",
            edge.edge_rate_limit_requests,
            "121",
        ),
        (
            "NEXUS_SAGE_EDGE_RATE_LIMIT_WINDOW_SECONDS",
            edge.edge_rate_limit_window_seconds,
            "9",
        ),
        (
            "NEXUS_SAGE_EDGE_RATE_LIMIT_WINDOW_SECONDS",
            edge.edge_rate_limit_window_seconds,
            "3601",
        ),
    ],
)
def test_abuse_control_env_enforces_each_bound(
    monkeypatch,
    name: str,
    getter,
    value: str,
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError):
        getter()


def test_process_global_rate_limit_ignores_forwarded_identity_and_recovers(
    monkeypatch,
) -> None:
    clock = _FakeClock()
    guard = edge._EdgeAbuseGuard(
        max_in_flight=2,
        max_requests=1,
        window_seconds=10,
        clock=clock,
    )
    monkeypatch.setattr(edge, "_PROCESS_ABUSE_GUARD", guard)
    calls = 0

    async def upstream(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"ok": True})

    first_app = _app(upstream)
    second_app = _app(upstream)
    with _client(first_app) as first_client:
        accepted = first_client.get(
            "/api/sage/v1/health",
            headers={"X-Forwarded-For": "203.0.113.10"},
        )
    with _client(second_app) as second_client:
        limited = second_client.get(
            "/api/sage/v1/health",
            headers={"X-Forwarded-For": "198.51.100.20"},
        )

    assert accepted.status_code == 200
    assert limited.status_code == 429
    assert limited.json() == {
        "detail": "SAGE edge request rate limit exceeded",
        "code": "sage_edge_rate_limited",
    }
    assert limited.headers["retry-after"] == "10"
    assert limited.headers["cache-control"] == "no-store, private"
    assert limited.headers["pragma"] == "no-cache"
    assert "198.51.100.20" not in limited.text
    assert calls == 1

    clock.advance(10)
    with _client(second_app) as second_client:
        recovered = second_client.get("/api/sage/v1/health")

    assert recovered.status_code == 200
    assert calls == 2


def test_concurrency_saturation_fails_closed_without_upstream_and_recovers(
    monkeypatch,
) -> None:
    guard = edge._EdgeAbuseGuard(
        max_in_flight=1,
        max_requests=10,
        window_seconds=10,
        clock=_FakeClock(),
    )
    guard.enter()
    monkeypatch.setattr(edge, "_PROCESS_ABUSE_GUARD", guard)
    calls = 0

    async def upstream(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"ok": True})

    app = _app(upstream)
    with _client(app) as client:
        saturated = client.get("/api/sage/v1/health")

    assert saturated.status_code == 503
    assert saturated.json() == {
        "detail": "SAGE edge concurrency limit is saturated",
        "code": "sage_edge_concurrency_saturated",
    }
    assert saturated.headers["retry-after"] == "1"
    assert saturated.headers["cache-control"] == "no-store, private"
    assert calls == 0

    guard.leave()
    with _client(app) as client:
        recovered = client.get("/api/sage/v1/health")

    assert recovered.status_code == 200
    assert calls == 1


def test_concurrency_slot_is_released_after_upstream_failure(monkeypatch) -> None:
    guard = edge._EdgeAbuseGuard(
        max_in_flight=1,
        max_requests=10,
        window_seconds=10,
        clock=_FakeClock(),
    )
    monkeypatch.setattr(edge, "_PROCESS_ABUSE_GUARD", guard)
    calls = 0

    async def upstream(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json={"ok": True})

    with _client(_app(upstream)) as client:
        failed = client.get("/api/sage/v1/health")
        recovered = client.get("/api/sage/v1/health")

    assert failed.status_code == 504
    assert recovered.status_code == 200
    assert calls == 2


def test_authentication_precedes_admission_body_and_upstream(monkeypatch) -> None:
    guard = edge._EdgeAbuseGuard(
        max_in_flight=1,
        max_requests=1,
        window_seconds=10,
        clock=_FakeClock(),
    )
    monkeypatch.setattr(edge, "_PROCESS_ABUSE_GUARD", guard)
    calls = 0

    async def upstream(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"ok": True})

    wrong_authorization = "Bearer " + ("wrong" * 16)
    body_sentinel = "BODY_SENTINEL_MUST_NOT_REFLECT"
    app = _app(upstream)
    with _client(app) as client:
        rejected = client.post(
            "/api/sage/v1/jobs",
            headers={
                "Authorization": wrong_authorization,
                "Content-Type": "text/plain",
            },
            content=body_sentinel,
        )
        accepted = client.get("/api/sage/v1/health")
        limited = client.get("/api/sage/v1/health")

    assert rejected.status_code == 401
    assert rejected.json()["code"] == "sage_edge_auth_rejected"
    assert body_sentinel not in rejected.text
    assert wrong_authorization not in rejected.text
    assert accepted.status_code == 200
    assert limited.status_code == 429
    assert calls == 1


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/sage/v1/health", None),
        ("GET", "/api/sage/v1/capabilities", None),
        ("GET", "/api/sage/v1/grounding", None),
        ("GET", "/api/sage/v1/model-cards?limit=7", None),
        ("POST", "/api/sage/v1/jobs", b"{}"),
        ("GET", f"/api/sage/v1/jobs/sage-job-{'a' * 32}", None),
    ],
)
def test_exact_six_operations_forward(
    method: str, path: str, body: bytes | None
) -> None:
    seen: list[httpx.Request] = []

    async def upstream(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    headers = {"Authorization": _AUTHORIZATION}
    if method == "POST":
        headers["Content-Type"] = "application/json"
    with _client(_app(upstream)) as client:
        response = client.request(method, path, headers=headers, content=body)

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["pragma"] == "no-cache"
    assert len(seen) == 1
    assert seen[0].method == method
    assert seen[0].url.host == "127.0.0.1"
    assert seen[0].url.port == 7352
    assert seen[0].headers["authorization"] == headers["Authorization"]
    if "?" in path:
        assert seen[0].url.query == b"limit=7"


def test_invalid_bearer_flood_never_reaches_brain_or_consumes_valid_lane() -> None:
    calls = 0

    async def upstream(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"ok": True})

    wrong_authorization = "Bearer " + ("wrong" * 16)
    with _client(_app(upstream)) as client:
        for _ in range(65):
            rejected = client.get(
                "/api/sage/v1/health",
                headers={"Authorization": wrong_authorization},
            )
            assert rejected.status_code == 401
            assert rejected.json()["code"] == "sage_edge_auth_rejected"
            assert rejected.headers["www-authenticate"] == "Bearer"

        accepted = client.get("/api/sage/v1/health")

    assert accepted.status_code == 200
    assert calls == 1


def test_non_ascii_bearer_is_uniform_401_and_never_reaches_brain() -> None:
    calls = 0

    async def upstream(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    with _client(_app(upstream)) as client:
        response = client.get(
            "/api/sage/v1/health",
            headers=[(b"authorization", b"Bearer \xff")],
        )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "valid SAGE bearer token required",
        "code": "sage_edge_auth_rejected",
    }
    assert calls == 0


def test_edge_and_brain_redact_rejected_secret_values(monkeypatch, tmp_path) -> None:
    sentinel = "DUMMY_SECRET_SENTINEL_MUST_NOT_RETURN"
    monkeypatch.setenv("NEXUS_SAGE_GATEWAY_MODE", "proposal_write")
    monkeypatch.setenv("NEXUS_SAGE_RUNTIME_DIR", str(tmp_path / "sage-state"))
    routes.reset_sage_stores_for_tests()

    brain = FastAPI()
    brain.add_middleware(SageBodyLimitMiddleware)
    brain.add_exception_handler(
        RequestValidationError,
        sage_request_validation_handler,
    )
    brain.include_router(routes.router)
    transport = httpx.ASGITransport(app=brain)
    try:
        with _client(edge.create_sage_edge_app(transport=transport)) as client:
            response = client.post(
                "/api/sage/v1/jobs",
                json={
                    "workflow_type": "grounding_audit",
                    "parameters": {
                        "files": ["NEXUS_MANIFEST.md"],
                        "api_key": sentinel,
                    },
                    "idempotency_key": "edge-secret-redaction-001",
                },
            )
    finally:
        routes.reset_sage_stores_for_tests()

    assert response.status_code == 422
    assert response.json()["code"] == "sage_validation_error"
    assert sentinel not in response.text
    assert all(set(item) == {"loc", "type"} for item in response.json()["detail"])


@pytest.mark.parametrize(
    "method", ["HEAD", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"]
)
def test_methods_outside_operation_contract_never_reach_brain(method: str) -> None:
    calls = 0

    async def upstream(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    with _client(_app(upstream)) as client:
        response = client.request(method, "/api/sage/v1/health")

    assert response.status_code == 405
    if method != "HEAD":
        assert response.json()["code"] == "sage_edge_method_rejected"
    assert calls == 0


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/docs",
        "/api/sage/v1",
        "/api/sage/v1/health/",
        "/api/sage/v1//health",
        "/api/sage/v1/jobs/not-a-real-job-id",
        "/api/sage/v1/program",
        "/api/sage/v1/memory",
        "/api/sage/v1/swarm",
        "/api/sage/v1/execute",
    ],
)
def test_non_allowlisted_paths_never_reach_brain(path: str) -> None:
    calls = 0

    async def upstream(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    with _client(_app(upstream)) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert response.json()["code"] == "sage_edge_path_rejected"
    assert calls == 0


@pytest.mark.parametrize(
    "path",
    [
        "/api/sage/v1/%2e%2e/health",
        "/api/sage/v1/%2E%2E%2Fjobs",
        "/api/sage/v1/health%2f..%2fjobs",
        "/api/sage/v1/jobs/%2e%2e%2fhealth",
        "/api/sage/v1/%68ealth",
        "/api/sage/v1%2fhealth",
        "/api/sage/v1/%5chealth",
    ],
)
def test_encoded_and_traversal_paths_are_rejected_before_upstream(path: str) -> None:
    calls = 0

    async def upstream(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    with _client(_app(upstream)) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert response.json()["code"] == "sage_edge_path_rejected"
    assert calls == 0


@pytest.mark.parametrize(
    "path",
    [
        "/api/sage/v1/health?debug=1",
        "/api/sage/v1/model-cards?limit=0",
        "/api/sage/v1/model-cards?limit=101",
        "/api/sage/v1/model-cards?limit=2&limit=3",
        "/api/sage/v1/model-cards?url=http%3A%2F%2Fevil.example",
    ],
)
def test_query_contract_cannot_turn_edge_into_generic_target(path: str) -> None:
    calls = 0

    async def upstream(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    with _client(_app(upstream)) as client:
        response = client.get(path)

    assert response.status_code == 400
    assert response.json()["code"] == "sage_edge_query_rejected"
    assert calls == 0


def test_actual_body_bytes_are_bounded_even_with_false_content_length(
    monkeypatch,
) -> None:
    monkeypatch.setenv("NEXUS_SAGE_MAX_BODY_BYTES", "1024")
    monkeypatch.setenv("NEXUS_SAGE_EDGE_MAX_BODY_BYTES", "99999")
    calls = 0

    async def upstream(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    payload = b"{" + (b'"x":"' + b"a" * 1_100 + b'"}')
    with _client(_app(upstream)) as client:
        response = client.post(
            "/api/sage/v1/jobs",
            headers={"Content-Type": "application/json", "Content-Length": "1"},
            content=payload,
        )

    assert edge.edge_body_limit() == 1024
    assert response.status_code == 413
    assert response.json()["code"] == "sage_edge_payload_too_large"
    assert calls == 0


def test_post_requires_json_and_get_rejects_body() -> None:
    calls = 0

    async def upstream(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    with _client(_app(upstream)) as client:
        bad_post = client.post("/api/sage/v1/jobs", content=b"plain text")
        bad_get = client.request("GET", "/api/sage/v1/health", content=b"unexpected")

    assert bad_post.status_code == 415
    assert bad_get.status_code == 400
    assert calls == 0


def test_authorization_is_preserved_while_hop_and_ambient_headers_are_stripped() -> (
    None
):
    captured: dict[str, str] = {}

    async def upstream(request: httpx.Request) -> httpx.Response:
        captured.update(request.headers)
        return httpx.Response(
            202,
            json={"status": "pending_review"},
            headers={
                "Connection": "X-Upstream-Hop",
                "X-Upstream-Hop": "remove-me",
                "Keep-Alive": "timeout=5",
                "Set-Cookie": "edge-must-not-forward=1",
                "Server": "brain-internal",
                "X-NEXUS-Idempotency": "created",
                "Cache-Control": "no-store",
            },
        )

    secret = _AUTHORIZATION
    with _client(_app(upstream)) as client:
        response = client.post(
            "/api/sage/v1/jobs",
            headers={
                "Authorization": secret,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Connection": "X-Hop",
                "X-Hop": "remove-me",
                "Proxy-Authorization": "remove-me",
                "Cookie": "remove-me",
                "X-Forwarded-For": "203.0.113.7",
                "X-Api-Key": "remove-me",
            },
            content=b"{}",
        )

    assert response.status_code == 202
    assert captured["authorization"] == secret
    for forbidden in (
        "connection",
        "x-hop",
        "proxy-authorization",
        "cookie",
        "x-forwarded-for",
        "x-api-key",
    ):
        assert forbidden not in captured
    assert response.headers["x-nexus-idempotency"] == "created"
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["pragma"] == "no-cache"
    for forbidden in (
        "connection",
        "x-upstream-hop",
        "keep-alive",
        "set-cookie",
        "server",
    ):
        assert forbidden not in response.headers


def test_upstream_connection_failure_returns_safe_502_without_secret(caplog) -> None:
    secret = _AUTHORIZATION

    async def upstream(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "sensitive internal connection detail", request=request
        )

    with caplog.at_level(logging.DEBUG):
        with _client(_app(upstream)) as client:
            response = client.get(
                "/api/sage/v1/health",
                headers={"Authorization": secret},
            )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Brain SAGE upstream is unavailable",
        "code": "sage_edge_upstream_unavailable",
    }
    assert secret not in caplog.text
    assert "sensitive internal connection detail" not in response.text


def test_upstream_timeout_returns_504() -> None:
    async def upstream(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with _client(_app(upstream)) as client:
        response = client.get("/api/sage/v1/health")

    assert response.status_code == 504
    assert response.json()["code"] == "sage_edge_upstream_timeout"


def test_upstream_redirect_is_not_followed_or_exposed() -> None:
    calls = 0

    async def upstream(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(307, headers={"Location": "https://evil.example/collect"})

    with _client(_app(upstream), follow_redirects=False) as client:
        response = client.get("/api/sage/v1/health")

    assert calls == 1
    assert response.status_code == 502
    assert response.json()["code"] == "sage_edge_upstream_redirect_rejected"
    assert "location" not in response.headers
    assert "evil.example" not in response.text


def test_fixed_upstream_ignores_environment_target_override(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_SAGE_EDGE_UPSTREAM", "http://evil.example:9999")
    seen: list[httpx.Request] = []

    async def upstream(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200)

    with _client(_app(upstream)) as client:
        assert client.get("/api/sage/v1/health").status_code == 200

    assert len(seen) == 1
    assert str(seen[0].url).startswith("http://127.0.0.1:7352/")


def test_upstream_client_disables_environment_proxies_and_redirects(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}
    real_client = httpx.AsyncClient

    def recording_client(*args, **kwargs):
        captured.update(kwargs)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(edge.httpx, "AsyncClient", recording_client)
    client = edge._make_upstream_client(
        httpx.MockTransport(lambda _: httpx.Response(200))
    )
    try:
        assert captured["base_url"] == "http://127.0.0.1:7352"
        assert captured["trust_env"] is False
        assert captured["follow_redirects"] is False
    finally:
        import asyncio

        asyncio.run(client.aclose())


def test_liveness_and_privacy_are_explicit_safe_local_documents() -> None:
    async def should_not_run(_: httpx.Request) -> httpx.Response:
        raise AssertionError("local edge documents must not call Brain")

    with _client(_app(should_not_run)) as client:
        liveness = client.get(edge.LIVENESS_PATH)
        privacy = client.get(edge.PRIVACY_PATH)
        privacy_post = client.post(edge.PRIVACY_PATH)

    assert liveness.status_code == 200
    assert liveness.json() == {
        "ok": True,
        "service": "nexus-sage-edge",
        "check": "liveness",
        "upstream_checked": False,
    }
    notice = " ".join(privacy.text.lower().split())
    assert "exactly six allowlisted sage operations" in notice
    assert "edge itself does not persist bearer credentials or request bodies" in notice
    assert "openai and the tunnel provider may process" in notice
    assert "brain may persist submitted proposal-job data" in notice
    assert "no user-facing deletion api" in notice
    assert "not a public-production service" in notice
    assert "encryption" not in notice
    assert "backup" not in notice
    assert privacy_post.status_code == 405
    assert privacy_post.headers["cache-control"] == "no-store, private"
    assert privacy_post.headers["pragma"] == "no-cache"


def test_readiness_requires_bearer_and_validates_brain_sage_health() -> None:
    seen: list[httpx.Request] = []

    async def upstream(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "ok": True,
                "service": "nexus-sage-ingress",
                "mode": "observe_only",
                "execution_allowed": False,
            },
        )

    app = _app(upstream)
    with TestClient(app) as unauthenticated_client:
        unauthorized = unauthenticated_client.get(edge.READINESS_PATH)
    with _client(app) as authenticated_client:
        ready = authenticated_client.get(edge.READINESS_PATH)

    assert unauthorized.status_code == 401
    assert unauthorized.json()["code"] == "sage_edge_auth_rejected"
    assert unauthorized.headers["www-authenticate"] == "Bearer"
    assert ready.status_code == 200
    assert ready.json() == {
        "ok": True,
        "service": "nexus-sage-edge",
        "check": "readiness",
        "upstream_checked": True,
        "mode": "observe_only",
        "execution_allowed": False,
    }
    assert len(seen) == 1
    assert seen[0].method == "GET"
    assert seen[0].url.host == "127.0.0.1"
    assert seen[0].url.port == 7352
    assert seen[0].url.path == "/api/sage/v1/health"
    assert seen[0].headers["authorization"] == _AUTHORIZATION


def test_readiness_fails_closed_when_brain_health_contract_is_invalid() -> None:
    sentinel = "BRAIN_FAILURE_DETAIL_MUST_NOT_RETURN"

    async def upstream(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={"detail": sentinel, "execution_allowed": True},
        )

    with _client(_app(upstream)) as client:
        response = client.get(edge.READINESS_PATH)

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Brain SAGE upstream is not ready",
        "code": "sage_edge_upstream_not_ready",
    }
    assert sentinel not in response.text


@pytest.mark.parametrize(
    "host", ["0.0.0.0", "::", "192.168.1.10", "localhost", "example.com"]
)
def test_startup_rejects_every_nonliteral_or_nonloopback_host(host: str) -> None:
    with pytest.raises(ValueError):
        edge.validate_edge_bind_host(host)


@pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.2", "::1"])
def test_startup_accepts_only_literal_loopback_hosts(host: str) -> None:
    assert edge.validate_edge_bind_host(host) == host


@pytest.mark.parametrize("port", [7350, 7352, 7354, 7355, 7356, 7357, 8000, 11434])
def test_startup_rejects_nexus_reserved_ports(port: int) -> None:
    with pytest.raises(ValueError, match="reserved"):
        edge.validate_edge_port(port)


def test_default_edge_port_is_unreserved() -> None:
    assert edge.DEFAULT_EDGE_PORT == 17_452
    assert edge.validate_edge_port(edge.DEFAULT_EDGE_PORT) == edge.DEFAULT_EDGE_PORT
    assert edge.DEFAULT_EDGE_PORT not in edge.PortRegistry.CANONICAL_PORTS


def test_runner_uses_only_loopback_safe_uvicorn_options(monkeypatch) -> None:
    from scripts import serve_sage_edge

    captured: dict[str, object] = {}

    def fake_run(app_path: str, **kwargs) -> None:
        captured["app_path"] = app_path
        captured.update(kwargs)

    monkeypatch.setenv("NEXUS_SAGE_EDGE_HOST", "127.0.0.2")
    monkeypatch.setenv("NEXUS_SAGE_EDGE_PORT", "17453")
    monkeypatch.setattr(serve_sage_edge.uvicorn, "run", fake_run)

    serve_sage_edge.main()

    assert captured == {
        "app_path": "nexus_os.sage_gateway.edge:app",
        "host": "127.0.0.2",
        "port": 17_453,
        "access_log": False,
        "proxy_headers": False,
        "server_header": False,
        "log_level": "warning",
    }
