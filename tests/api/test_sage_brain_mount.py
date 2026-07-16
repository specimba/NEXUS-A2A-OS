"""Contract tests for the NEXUS SAGE Brain ingress and Actions schema."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.routing import APIRoute

from nexus_os.api.brain_api import brain_app
from nexus_os.sage_gateway.security import SageBodyLimitMiddleware

from scripts.export_sage_openapi import build_schema

SAGE_PREFIX = "/api/sage/v1"
EXPECTED_OPERATIONS = {
    ("GET", f"{SAGE_PREFIX}/health"),
    ("GET", f"{SAGE_PREFIX}/capabilities"),
    ("GET", f"{SAGE_PREFIX}/grounding"),
    ("GET", f"{SAGE_PREFIX}/model-cards"),
    ("POST", f"{SAGE_PREFIX}/jobs"),
    ("GET", f"{SAGE_PREFIX}/jobs/{{job_id}}"),
}
FORBIDDEN_PATH_SEGMENTS = ("program", "memory", "swarm", "execute")
CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "sage"
    / "nexus_sage_v1_1_openapi.json"
)


def _mounted_sage_operations() -> set[tuple[str, str]]:
    operations: set[tuple[str, str]] = set()
    for route in brain_app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith(SAGE_PREFIX):
            continue
        operations.update((method, route.path) for method in route.methods or set())
    return operations


def _schema_operations(schema: dict) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, path_item in schema["paths"].items()
        for method in path_item
        if method.lower() in {"get", "post", "put", "patch", "delete"}
    }


def test_brain_mount_exposes_only_the_six_governed_sage_operations() -> None:
    operations = _mounted_sage_operations()

    assert operations == EXPECTED_OPERATIONS
    assert all(
        segment not in path.lower()
        for _, path in operations
        for segment in FORBIDDEN_PATH_SEGMENTS
    )


def test_brain_mount_has_exactly_one_sage_body_limit_middleware() -> None:
    mounted = [
        middleware
        for middleware in brain_app.user_middleware
        if middleware.cls is SageBodyLimitMiddleware
    ]

    assert len(mounted) == 1


def test_exported_actions_schema_matches_the_governed_mount() -> None:
    schema = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert schema == build_schema()

    assert _schema_operations(schema) == EXPECTED_OPERATIONS
    assert schema["servers"] == [
        {
            "description": "Replace only after the governed HTTPS ingress is approved",
            "url": "https://sage-gateway.invalid",
        }
    ]
    assert schema["components"]["securitySchemes"]["SageBearerAuth"] == {
        "bearerFormat": "opaque",
        "description": "Operator-provisioned NEXUS SAGE credential",
        "scheme": "bearer",
        "type": "http",
    }

    operation_ids: set[str] = set()
    for path, path_item in schema["paths"].items():
        assert not any(segment in path.lower() for segment in FORBIDDEN_PATH_SEGMENTS)
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            assert operation["security"] == [{"SageBearerAuth": []}]
            assert not any(
                parameter.get("in") == "header"
                and parameter.get("name", "").lower() == "authorization"
                for parameter in operation.get("parameters", [])
            )
            operation_id = operation["operationId"]
            assert operation_id not in operation_ids
            operation_ids.add(operation_id)

    serialized = json.dumps(schema, sort_keys=True).lower()
    assert "localhost" not in serialized
    assert "127.0.0.1" not in serialized

