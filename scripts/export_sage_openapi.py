#!/usr/bin/env python3
"""Export the bounded NEXUS SAGE contract for ChatGPT Actions.

The generated document intentionally uses the reserved ``.invalid`` TLD.  An
operator must replace that server only after the governed HTTPS ingress and
credential-rotation gates are satisfied.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any

from fastapi import FastAPI


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from nexus_os.sage_gateway.routes import router as sage_router  # noqa: E402


SAGE_PREFIX = "/api/sage/v1"
SAFE_SERVER = "https://sage-gateway.invalid"
DEFAULT_OUTPUT = REPO_ROOT / "config" / "sage" / "nexus_sage_v1_1_openapi.json"
EXPECTED_OPERATIONS = {
    ("get", f"{SAGE_PREFIX}/health"),
    ("get", f"{SAGE_PREFIX}/capabilities"),
    ("get", f"{SAGE_PREFIX}/grounding"),
    ("get", f"{SAGE_PREFIX}/model-cards"),
    ("post", f"{SAGE_PREFIX}/jobs"),
    ("get", f"{SAGE_PREFIX}/jobs/{{job_id}}"),
}
OPERATION_COPY = {
    ("get", f"{SAGE_PREFIX}/health"): (
        "Check SAGE ingress health",
        "Confirm the separately authenticated Brain-plane ingress is available. "
        "This operation does not grant execution authority.",
    ),
    ("get", f"{SAGE_PREFIX}/capabilities"): (
        "Read governed SAGE capabilities",
        "Return the Sense/Propose/Witness boundary and explicitly denied powers.",
    ),
    ("get", f"{SAGE_PREFIX}/grounding"): (
        "Read grounding metadata",
        "Return allowlisted file names, sizes, timestamps, and hashes without file bodies or absolute paths.",
    ),
    ("get", f"{SAGE_PREFIX}/model-cards"): (
        "Read sanitized model evidence",
        "Return the canonical Model Arena projection without provider errors, credentials, or routing secrets.",
    ),
    ("post", f"{SAGE_PREFIX}/jobs"): (
        "Submit a governed proposal job",
        "Create an idempotent proposal receipt in pending_review state. "
        "This operation cannot execute, approve, retry, or close work.",
    ),
    ("get", f"{SAGE_PREFIX}/jobs/{{job_id}}"): (
        "Read a proposal job receipt",
        "Return a receipt owned by the authenticated SAGE principal without raw execution state.",
    ),
}
FORBIDDEN_PATH_SEGMENTS = ("program", "memory", "swarm", "execute")

# ChatGPT Actions currently requires a concrete object at the request-body
# root. FastAPI correctly emits the runtime Pydantic discriminated union as a
# top-level ``oneOf``, but the Builder skips that operation. This projection
# deliberately narrows only the exported Actions contract; the Brain route
# continues to validate the authoritative discriminated union.
ACTIONS_JOB_BODY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "title": "Governed SAGE proposal job",
    "description": (
        "Submit exactly one allowlisted proposal workflow. Match parameters to "
        "workflow_type and do not mix fields between workflows: grounding_audit "
        "requires files and optionally accepts verify_hashes; evidence_search "
        "requires query and optionally accepts sources and max_results; "
        "model_health_snapshot optionally accepts providers and include_unverified; "
        "parallel_audit_proposal requires objective and domains and optionally "
        "accepts max_agents. The server rejects mismatched or extra fields."
    ),
    "additionalProperties": False,
    "required": ["idempotency_key", "workflow_type", "parameters"],
    "properties": {
        "idempotency_key": {
            "type": "string",
            "minLength": 8,
            "maxLength": 128,
            "description": (
                "Caller-generated stable key. Reuse only when replaying the exact same proposal payload."
            ),
        },
        "workflow_type": {
            "type": "string",
            "enum": [
                "grounding_audit",
                "evidence_search",
                "model_health_snapshot",
                "parallel_audit_proposal",
            ],
            "description": "The allowlisted proposal workflow whose parameter rules apply.",
        },
        "parameters": {
            "type": "object",
            "description": (
                "Workflow-specific parameters. grounding_audit: files (required), "
                "verify_hashes. evidence_search: query (required), sources, max_results. "
                "model_health_snapshot: providers, include_unverified. "
                "parallel_audit_proposal: objective and domains (required), max_agents."
            ),
            "additionalProperties": False,
            "properties": {
                "files": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 4,
                    "items": {
                        "type": "string",
                        "enum": [
                            "NEXUS_MANIFEST.md",
                            "01_PROJECT_STATE.md",
                            "knowledge.md",
                            "AGENTS.md",
                        ],
                    },
                    "description": "Required only for grounding_audit.",
                },
                "verify_hashes": {
                    "type": "boolean",
                    "default": True,
                    "description": "Optional for grounding_audit.",
                },
                "query": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 500,
                    "description": "Required only for evidence_search.",
                },
                "sources": {
                    "type": "array",
                    "maxItems": 4,
                    "items": {
                        "type": "string",
                        "enum": ["grounding", "audit", "continuity", "archivist"],
                    },
                    "description": "Optional for evidence_search.",
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10,
                    "description": "Optional for evidence_search.",
                },
                "providers": {
                    "type": "array",
                    "maxItems": 20,
                    "items": {"type": "string"},
                    "description": "Optional for model_health_snapshot.",
                },
                "include_unverified": {
                    "type": "boolean",
                    "default": True,
                    "description": "Optional for model_health_snapshot.",
                },
                "objective": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 4000,
                    "description": "Required only for parallel_audit_proposal.",
                },
                "domains": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 8,
                    "items": {"type": "string"},
                    "description": "Required only for parallel_audit_proposal.",
                },
                "max_agents": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 4,
                    "default": 3,
                    "description": "Optional for parallel_audit_proposal.",
                },
            },
        },
        "source_msg_id": {
            "type": "string",
            "maxLength": 128,
            "description": "Optional external correlation identifier; omit when unavailable.",
        },
    },
}

# Response projections enumerate stable, non-secret fields so the Builder can
# interpret results instead of warning about FastAPI's generic object schemas.
# Additional fields remain allowed for forward-compatible evidence metadata.
ACTIONS_SUCCESS_RESPONSE_SCHEMAS: dict[tuple[str, str], dict[str, Any]] = {
    ("get", f"{SAGE_PREFIX}/health"): {
        "type": "object",
        "additionalProperties": True,
        "required": ["ok", "service", "plane", "mode", "execution_allowed"],
        "properties": {
            "ok": {"type": "boolean"},
            "service": {"type": "string"},
            "plane": {"type": "string", "enum": ["brain-governance"]},
            "mode": {"type": "string", "enum": ["observe_only", "proposal_write"]},
            "execution_allowed": {"type": "boolean"},
        },
    },
    ("get", f"{SAGE_PREFIX}/capabilities"): {
        "type": "object",
        "additionalProperties": True,
        "required": [
            "schema",
            "mode",
            "proposal_writes_enabled",
            "arbitrary_program_execution",
            "raw_memory_export",
            "self_approval",
        ],
        "properties": {
            "schema": {"type": "string"},
            "mode": {"type": "string", "enum": ["observe_only", "proposal_write"]},
            "proposal_writes_enabled": {"type": "boolean"},
            "arbitrary_program_execution": {"type": "boolean"},
            "raw_memory_export": {"type": "boolean"},
            "self_approval": {"type": "boolean"},
        },
    },
    ("get", f"{SAGE_PREFIX}/grounding"): {
        "type": "object",
        "additionalProperties": True,
        "required": ["schema", "generated_at", "content_included", "files"],
        "properties": {
            "schema": {"type": "string"},
            "generated_at": {"type": "string"},
            "content_included": {"type": "boolean"},
            "files": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["name", "available"],
                    "properties": {
                        "name": {"type": "string"},
                        "available": {"type": "boolean"},
                        "bytes": {"type": "integer"},
                        "sha256": {"type": "string"},
                        "modified_at": {"type": "string"},
                    },
                },
            },
        },
    },
    ("get", f"{SAGE_PREFIX}/model-cards"): {
        "type": "object",
        "additionalProperties": True,
        "required": ["schema", "models", "returned"],
        "properties": {
            "schema": {"type": "string"},
            "projection_schema_version": {"type": "string"},
            "generated_at": {"type": "string"},
            "returned": {"type": "integer"},
            "models": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": True,
                    "properties": {
                        "model_id": {"type": "string"},
                        "label": {"type": "string"},
                        "provider_key": {"type": "string"},
                    },
                },
            },
        },
    },
    ("post", f"{SAGE_PREFIX}/jobs"): {
        "type": "object",
        "additionalProperties": True,
        "required": [
            "receipt_id",
            "job_id",
            "workflow_type",
            "status",
            "proposal_only",
            "execution_allowed",
            "approval_state",
            "created_at",
            "updated_at",
            "expires_at",
        ],
        "properties": {
            "receipt_id": {"type": "string"},
            "job_id": {"type": "string"},
            "workflow_type": {"type": "string"},
            "status": {"type": "string"},
            "proposal_only": {"type": "boolean"},
            "execution_allowed": {"type": "boolean"},
            "approval_state": {"type": "string"},
            "created_at": {"type": "string"},
            "updated_at": {"type": "string"},
            "expires_at": {"type": "string"},
        },
    },
    ("get", f"{SAGE_PREFIX}/jobs/{{job_id}}"): {
        "type": "object",
        "additionalProperties": True,
        "required": ["job_id", "workflow_type", "status", "execution_allowed"],
        "properties": {
            "job_id": {"type": "string"},
            "workflow_type": {"type": "string"},
            "status": {"type": "string"},
            "execution_allowed": {"type": "boolean"},
            "created_at": {"type": "string"},
            "updated_at": {"type": "string"},
            "expires_at": {"type": "string"},
        },
    },
}


def _iter_operations(schema: dict[str, Any]):
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method.lower() in {"get", "post", "put", "patch", "delete"}:
                yield method.lower(), path, operation


def _project_actions_job_body(operation: dict[str, Any]) -> None:
    """Replace only the Actions-facing POST body with a concrete object."""

    operation["requestBody"]["content"]["application/json"]["schema"] = deepcopy(
        ACTIONS_JOB_BODY_SCHEMA
    )


def _project_actions_success_response(
    operation: dict[str, Any], method: str, path: str
) -> None:
    """Replace an inferred success response with stable, explicit properties."""

    status = "202" if method == "post" else "200"
    operation["responses"][status]["content"]["application/json"]["schema"] = deepcopy(
        ACTIONS_SUCCESS_RESPONSE_SCHEMAS[(method, path)]
    )


def _strip_inferred_validation_context(schema: dict[str, Any]) -> None:
    """Remove generic Pydantic error fields that Actions cannot interpret."""

    validation_error = (
        schema.get("components", {}).get("schemas", {}).get("ValidationError", {})
    )
    properties = validation_error.get("properties", {})
    properties.pop("ctx", None)
    properties.pop("input", None)


def build_schema() -> dict[str, Any]:
    app = FastAPI(
        title="NEXUS SAGE Governed Actions API",
        summary="Sense, propose, and witness through the NEXUS Brain governance plane.",
        description=(
            "NEXUS SAGE is an external reasoning client. It may observe bounded "
            "evidence and submit proposal-only jobs; HERMES retains claim, execution, "
            "retry, and closure authority. Replace the reserved server only after "
            "operator approval of the public HTTPS ingress."
        ),
        version="1.1.0",
        servers=[
            {
                "url": SAFE_SERVER,
                "description": "Replace only after the governed HTTPS ingress is approved",
            }
        ],
    )
    app.include_router(sage_router)
    schema = app.openapi()
    _strip_inferred_validation_context(schema)

    schema["components"].setdefault("securitySchemes", {})["SageBearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "opaque",
        "description": "Operator-provisioned NEXUS SAGE credential",
    }
    for method, path, operation in _iter_operations(schema):
        summary, description = OPERATION_COPY[(method, path)]
        operation["summary"] = summary
        operation["description"] = description
        operation["security"] = [{"SageBearerAuth": []}]
        parameters = [
            parameter
            for parameter in operation.get("parameters", [])
            if not (
                parameter.get("in") == "header"
                and parameter.get("name", "").lower() == "authorization"
            )
        ]
        if parameters:
            operation["parameters"] = parameters
        else:
            operation.pop("parameters", None)
        operation["x-nexus-authority"] = "sense-propose-witness"
        operation["x-nexus-execution-allowed"] = False
        _project_actions_success_response(operation, method, path)
        if (method, path) == ("post", f"{SAGE_PREFIX}/jobs"):
            _project_actions_job_body(operation)

    schema["x-nexus-contract"] = "sage-governed-actions-v1.1"
    schema["x-nexus-server-requires-operator-replacement"] = True
    _validate(schema)
    return schema


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


def _validate(schema: dict[str, Any]) -> None:
    operations = {(method, path) for method, path, _ in _iter_operations(schema)}
    if operations != EXPECTED_OPERATIONS:
        raise RuntimeError(
            f"SAGE route drift: expected {sorted(EXPECTED_OPERATIONS)}, got {sorted(operations)}"
        )
    for _, path in operations:
        if any(segment in path.lower() for segment in FORBIDDEN_PATH_SEGMENTS):
            raise RuntimeError(f"forbidden SAGE capability in exported path: {path}")
    if schema.get("servers") != [
        {
            "url": SAFE_SERVER,
            "description": "Replace only after the governed HTTPS ingress is approved",
        }
    ]:
        raise RuntimeError("export must contain only the reserved non-routable server")

    serialized = json.dumps(schema, sort_keys=True).lower()
    if "localhost" in serialized or "127.0.0.1" in serialized:
        raise RuntimeError("local or live endpoint leaked into SAGE Actions schema")
    submission_schema = schema["paths"][f"{SAGE_PREFIX}/jobs"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    if submission_schema.get("type") != "object" or "oneOf" in submission_schema:
        raise RuntimeError("SAGE Actions job body must have a concrete object root")
    if submission_schema.get("additionalProperties") is not False:
        raise RuntimeError("SAGE Actions job body must reject extra top-level fields")
    if set(submission_schema.get("properties", {})) != {
        "idempotency_key",
        "workflow_type",
        "parameters",
        "source_msg_id",
    }:
        raise RuntimeError("SAGE Actions job body field set drifted")

    for method, path, operation in _iter_operations(schema):
        status = "202" if method == "post" else "200"
        response_schema = operation["responses"][status]["content"]["application/json"][
            "schema"
        ]
        if response_schema.get("type") != "object":
            raise RuntimeError(
                f"SAGE Actions response is not an object: {method} {path}"
            )
        if not response_schema.get("properties"):
            raise RuntimeError(
                f"SAGE Actions response has no explicit properties: {method} {path}"
            )

    missing_properties = _object_schemas_without_properties(schema)
    if missing_properties:
        raise RuntimeError(
            f"SAGE Actions object schemas lack properties: {missing_properties}"
        )


def _render(schema: dict[str, Any]) -> str:
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the checked-in contract differs from a fresh export",
    )
    args = parser.parse_args()

    output = args.output.expanduser().resolve()
    rendered = _render(build_schema())
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            print(f"SAGE OpenAPI contract is stale: {output}", file=sys.stderr)
            return 1
        print(f"SAGE OpenAPI contract is current: {output}")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"Exported governed SAGE OpenAPI contract: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
