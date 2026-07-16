"""Focused claim gates for the ChatGPT Actions SAGE contract exporter."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from scripts.export_sage_openapi import build_schema


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORTER = REPO_ROOT / "scripts" / "export_sage_openapi.py"
CHECKED_IN_CONTRACT = REPO_ROOT / "config" / "sage" / "nexus_sage_v1_1_openapi.json"
SAGE_PREFIX = "/api/sage/v1"
EXPECTED_OPERATIONS = {
    ("get", f"{SAGE_PREFIX}/health"),
    ("get", f"{SAGE_PREFIX}/capabilities"),
    ("get", f"{SAGE_PREFIX}/grounding"),
    ("get", f"{SAGE_PREFIX}/model-cards"),
    ("post", f"{SAGE_PREFIX}/jobs"),
    ("get", f"{SAGE_PREFIX}/jobs/{{job_id}}"),
}


def _operations(schema: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (method.lower(), path)
        for path, path_item in schema["paths"].items()
        for method in path_item
        if method.lower() in {"get", "post", "put", "patch", "delete"}
    }


def _url_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [url for nested in value.values() for url in _url_strings(nested)]
    if isinstance(value, list):
        return [url for nested in value for url in _url_strings(nested)]
    if isinstance(value, str) and value.lower().startswith(("http://", "https://")):
        return [value]
    return []


def _object_schemas_without_properties(value: Any, path: str = "$") -> list[str]:
    missing: list[str] = []
    if isinstance(value, dict):
        if value.get("type") == "object" and not value.get("properties"):
            missing.append(path)
        for key, nested in value.items():
            missing.extend(_object_schemas_without_properties(nested, f"{path}/{key}"))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            missing.extend(
                _object_schemas_without_properties(nested, f"{path}/{index}")
            )
    return missing


def test_actions_contract_has_six_operations_and_concrete_job_object() -> None:
    schema = build_schema()
    body = schema["paths"][f"{SAGE_PREFIX}/jobs"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]

    assert _operations(schema) == EXPECTED_OPERATIONS
    assert body["type"] == "object"
    assert "oneOf" not in body
    assert "discriminator" not in body
    assert body["additionalProperties"] is False
    assert set(body["required"]) == {
        "idempotency_key",
        "workflow_type",
        "parameters",
    }
    assert set(body["properties"]) == {
        "idempotency_key",
        "workflow_type",
        "parameters",
        "source_msg_id",
    }
    assert set(body["properties"]["workflow_type"]["enum"]) == {
        "grounding_audit",
        "evidence_search",
        "model_health_snapshot",
        "parallel_audit_proposal",
    }
    assert body["properties"]["parameters"]["type"] == "object"
    assert body["properties"]["parameters"]["additionalProperties"] is False


def test_actions_success_responses_have_explicit_object_properties() -> None:
    schema = build_schema()

    for method, path in EXPECTED_OPERATIONS:
        status = "202" if method == "post" else "200"
        response = schema["paths"][path][method]["responses"][status]["content"][
            "application/json"
        ]["schema"]
        assert response["type"] == "object"
        assert response["properties"]
    assert _object_schemas_without_properties(schema) == []


def test_actions_job_responses_publish_bounded_expiry() -> None:
    schema = build_schema()

    submitted = schema["paths"]["/api/sage/v1/jobs"]["post"]["responses"]["202"][
        "content"
    ]["application/json"]["schema"]
    status = schema["paths"]["/api/sage/v1/jobs/{job_id}"]["get"]["responses"][
        "200"
    ]["content"]["application/json"]["schema"]

    assert "expires_at" in submitted["required"]
    assert submitted["properties"]["expires_at"] == {"type": "string"}
    assert status["properties"]["expires_at"] == {"type": "string"}


def test_contract_is_secret_safe_and_uses_only_the_reserved_server() -> None:
    schema = build_schema()
    serialized = json.dumps(schema, sort_keys=True).lower()

    assert _url_strings(schema) == ["https://sage-gateway.invalid"]
    assert "localhost" not in serialized
    assert "127.0.0.1" not in serialized
    assert "nexus_sage_api_key" not in serialized
    assert ".sage_api_token" not in serialized
    assert "authorization" not in serialized
    assert "sk-" not in serialized


def test_export_is_deterministic_and_check_accepts_fresh_contract(
    tmp_path: Path,
) -> None:
    output = tmp_path / "sage-openapi.json"
    command = [sys.executable, str(EXPORTER), "--output", str(output)]

    subprocess.run(command, cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    first = output.read_bytes()
    subprocess.run(
        [*command, "--check"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(command, cwd=REPO_ROOT, check=True, capture_output=True, text=True)

    assert output.read_bytes() == first
    assert CHECKED_IN_CONTRACT.read_bytes() == first
