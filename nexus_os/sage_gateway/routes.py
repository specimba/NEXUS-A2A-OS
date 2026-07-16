"""FastAPI routes for the governed NEXUS SAGE northbound client.

The router belongs to the Brain/governance plane.  It exposes bounded
observation and proposal-job operations only; execution remains HERMES-owned.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import Annotated, Any, Literal, Union
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx
from pydantic import BaseModel, ConfigDict, Field

from nexus_os.bridge.sage_governance import (
    build_sage_job_handoff,
    build_sage_job_proposal,
)
from nexus_os.sage_gateway.jobs import ALLOWED_WORKFLOWS, SageJob, SageJobStore
from nexus_os.sage_gateway.security import (
    contains_disallowed_persisted_content,
    SageSecurityContext,
    require_proposal_write,
    require_sage_auth,
)
_MODEL_CARD_URL = "http://127.0.0.1:7356/api/model-cards"
_MAX_MODEL_CARD_RESPONSE_BYTES = 1_048_576

_BENCHMARK_DIMENSIONS = (
    "quality",
    "code",
    "reasoning",
    "swe",
    "speed",
    "cost_efficiency",
)
_SUMMARY_FIELDS = (
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
)
_HEALTH_STATES = {
    "healthy", "unverified", "rate_limited", "auth_required",
    "unavailable", "excluded", "unknown",
}
_RAW_HEALTH_STATES = {
    "pending", "unknown", "up", "429", "rate_limited", "noauth",
    "unauthorized", "401", "403", "down", "timeout", "error",
    "banned", "disabled", "excluded",
}
_ROUTING_STATES = {"cli_visible", "offer_only", "excluded", "unknown"}
_BENCHMARK_STATUSES = {"evidence_backed", "catalogue_only", "no_data"}
_BENCHMARK_CONFIDENCE = {"low", "medium", "high", "unknown", "no_data"}
_REGISTRY_ROLES = {"code", "fast", "frontier", "intent", "judge", "reasoning", "teacher"}
_REGISTRY_LANES = {
    "core", "eval", "local", "logging_fallback", "memory_fallback",
    "quarantine", "specialist", "teacher", "visual",
}
_CAPABILITY_FIELDS = ("tools", "thinking", "thinkingBudget", "vision")
_MODEL_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+/-]{0,255}$")
_PROVIDER_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SOURCE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


router = APIRouter(prefix="/api/sage/v1", tags=["nexus-sage"])

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GROUNDING_FILES = (
    "NEXUS_MANIFEST.md",
    "01_PROJECT_STATE.md",
    "knowledge.md",
    "AGENTS.md",
    "docs/governance/NEXUS_OS_VISION_MANIFEST_2026.md",
    "docs/handbook/08_PORT_OWNERSHIP_RULESET.md",
)
_FORBIDDEN_PARAMETER_KEYS = {
    "api_key",
    "password",
    "secret",
    "authorization",
    "cookie",
    "bearer",
    "private_key",
    "access_token",
    "refresh_token",
    "program",
    "source_code",
    "shell",
    "command",
}
_job_store: SageJobStore | None = None
_job_store_path: Path | None = None


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _PublicRoutingEvidence(_StrictModel):
    cli_visible: bool
    cli_route_id: str | None
    eligible: bool
    state: Literal["cli_visible", "offer_only", "excluded", "unknown"]


class _PublicHealthEvidence(_StrictModel):
    state: Literal[
        "healthy", "unverified", "rate_limited", "auth_required",
        "unavailable", "excluded", "unknown",
    ]
    raw_status: Literal[
        "pending", "unknown", "up", "429", "rate_limited", "noauth",
        "unauthorized", "401", "403", "down", "timeout", "error",
        "banned", "disabled", "excluded",
    ]
    observed: bool
    latency_ms: float | None
    uptime_percent: float | None
    last_checked_at: str | None
    is_rate_limited: bool


class _PublicBenchmarkDimensions(_StrictModel):
    quality: float | None
    code: float | None
    reasoning: float | None
    swe: float | None
    speed: float | None
    cost_efficiency: float | None


class _PublicBenchmarkEvidence(_StrictModel):
    status: Literal["evidence_backed", "catalogue_only", "no_data"]
    dimensions: _PublicBenchmarkDimensions
    coverage: list[Literal[
        "quality", "code", "reasoning", "swe", "speed", "cost_efficiency",
    ]]
    confidence: Literal["low", "medium", "high", "unknown", "no_data"]
    sources: list[str]
    as_of: str | None
    catalogue_score: float | None
    catalogue_score_label: Literal["legacy_static_registry"] | None
    matched_registry_id: str | None


class _PublicPolicyPrior(_StrictModel):
    registry_tier: float | None
    label: Literal["none", "registry_policy_tier"]


class _PublicRegistryEvidence(_StrictModel):
    context_tokens: int | None
    capabilities: dict[str, bool]
    roles: list[Literal["code", "fast", "frontier", "intent", "judge", "reasoning", "teacher"]]
    lanes: list[Literal[
        "core", "eval", "local", "logging_fallback", "memory_fallback",
        "quarantine", "specialist", "teacher", "visual",
    ]]


class _PublicModelCard(_StrictModel):
    model_id: str
    label: str
    provider_key: str
    routing: _PublicRoutingEvidence
    health: _PublicHealthEvidence
    benchmarks: _PublicBenchmarkEvidence
    policy_prior: _PublicPolicyPrior
    registry: _PublicRegistryEvidence


class _PublicProjectionSummary(_StrictModel):
    catalogue_offers: int
    cli_model_ids: int
    cli_visible_offers: int
    observed_healthy: int
    health_unverified: int
    unavailable: int
    rate_limited: int
    evidence_backed_offers: int
    configured_providers: int
    authenticated_providers: int


class GroundingAuditParameters(_StrictModel):
    files: list[Literal[
        "NEXUS_MANIFEST.md",
        "01_PROJECT_STATE.md",
        "knowledge.md",
        "AGENTS.md",
    ]] = Field(min_length=1, max_length=4)
    verify_hashes: bool = True


class EvidenceSearchParameters(_StrictModel):
    query: str = Field(min_length=1, max_length=500)
    sources: list[Literal["grounding", "audit", "continuity", "archivist"]] = Field(
        default_factory=lambda: ["grounding", "audit"],
        max_length=4,
    )
    max_results: int = Field(default=10, ge=1, le=50)


class ModelHealthSnapshotParameters(_StrictModel):
    providers: list[str] = Field(default_factory=list, max_length=20)
    include_unverified: bool = True


class ParallelAuditProposalParameters(_StrictModel):
    objective: str = Field(min_length=1, max_length=4_000)
    domains: list[str] = Field(min_length=1, max_length=8)
    max_agents: int = Field(default=3, ge=1, le=4)


class _SageJobSubmissionBase(_StrictModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    source_msg_id: str | None = Field(default=None, max_length=128)


class GroundingAuditSubmission(_SageJobSubmissionBase):
    workflow_type: Literal["grounding_audit"]
    parameters: GroundingAuditParameters


class EvidenceSearchSubmission(_SageJobSubmissionBase):
    workflow_type: Literal["evidence_search"]
    parameters: EvidenceSearchParameters


class ModelHealthSnapshotSubmission(_SageJobSubmissionBase):
    workflow_type: Literal["model_health_snapshot"]
    parameters: ModelHealthSnapshotParameters


class ParallelAuditProposalSubmission(_SageJobSubmissionBase):
    workflow_type: Literal["parallel_audit_proposal"]
    parameters: ParallelAuditProposalParameters


SageJobSubmission = Annotated[
    Union[
        GroundingAuditSubmission,
        EvidenceSearchSubmission,
        ModelHealthSnapshotSubmission,
        ParallelAuditProposalSubmission,
    ],
    Field(discriminator="workflow_type"),
]

def _runtime_dir() -> Path:
    configured = (os.environ.get("NEXUS_SAGE_RUNTIME_DIR") or "").strip()
    return Path(configured).expanduser().resolve() if configured else Path.home() / ".nexus_pi" / "state" / "sage_gateway"


def _store() -> SageJobStore:
    global _job_store, _job_store_path
    root = _runtime_dir()
    jobs_path = root / "sage_jobs.sqlite3"
    if _job_store is None or _job_store_path != jobs_path:
        _job_store = SageJobStore(jobs_path)
        _job_store_path = jobs_path
    return _job_store


def reset_sage_stores_for_tests() -> None:
    """Drop cached handles; test databases remain isolated by environment."""

    global _job_store, _job_store_path
    _job_store = None
    _job_store_path = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_public_text(
    value: Any,
    *,
    max_length: int,
    pattern: re.Pattern[str] | None = None,
) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > max_length or not all(char.isprintable() for char in text):
        return None
    if pattern is not None and pattern.fullmatch(text) is None:
        return None
    if contains_disallowed_persisted_content(text):
        return None
    return text


def _safe_public_timestamp(value: Any) -> str | None:
    text = _safe_public_text(value, max_length=64)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return text if parsed.tzinfo is not None else None


def _safe_float(
    value: Any,
    *,
    minimum: float,
    maximum: float,
) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number < minimum or number > maximum:
        return None
    return number


def _safe_count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 0 <= value <= 10_000_000 else None


def _safe_context_tokens(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 1 <= value <= 100_000_000 else None


def _safe_allowlisted_strings(
    value: Any,
    *,
    allowed: set[str],
    maximum: int,
) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item in allowed and item not in result:
            result.append(item)
        if len(result) >= maximum:
            break
    return result


def _sanitize_projection_summary(value: Any) -> dict[str, int]:
    raw = _as_mapping(value)
    sanitized: dict[str, int] = {}
    for field in _SUMMARY_FIELDS:
        count = _safe_count(raw.get(field))
        if count is None:
            raise ValueError("canonical model-card summary has an invalid field")
        sanitized[field] = count
    return _PublicProjectionSummary.model_validate(sanitized).model_dump(mode="json")


def _sanitize_routing(value: Any) -> dict[str, Any]:
    raw = _as_mapping(value)
    route_id = _safe_public_text(
        raw.get("cli_route_id"),
        max_length=256,
        pattern=_MODEL_IDENTIFIER,
    )
    cli_visible = raw.get("cli_visible") is True and route_id is not None
    eligible = raw.get("eligible") is True
    state = raw.get("state") if raw.get("state") in _ROUTING_STATES else "unknown"
    if state == "cli_visible" and not cli_visible:
        state = "offer_only"
    if state == "excluded":
        eligible = False
    return _PublicRoutingEvidence(
        cli_visible=cli_visible,
        cli_route_id=route_id if cli_visible else None,
        eligible=eligible,
        state=state,
    ).model_dump(mode="json")


def _sanitize_health(value: Any) -> dict[str, Any]:
    raw = _as_mapping(value)
    state = raw.get("state") if raw.get("state") in _HEALTH_STATES else "unknown"
    raw_status = (
        raw.get("raw_status")
        if raw.get("raw_status") in _RAW_HEALTH_STATES
        else "unknown"
    )
    return _PublicHealthEvidence(
        state=state,
        raw_status=raw_status,
        observed=raw.get("observed") is True,
        latency_ms=_safe_float(raw.get("latency_ms"), minimum=0, maximum=86_400_000),
        uptime_percent=_safe_float(raw.get("uptime_percent"), minimum=0, maximum=100),
        last_checked_at=_safe_public_timestamp(raw.get("last_checked_at")),
        is_rate_limited=raw.get("is_rate_limited") is True,
    ).model_dump(mode="json")


def _sanitize_benchmark_sources(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    sources: list[str] = []
    for candidate in value:
        source = _safe_public_text(
            candidate,
            max_length=128,
            pattern=_SOURCE_IDENTIFIER,
        )
        if source is not None and source not in sources:
            sources.append(source)
        if len(sources) >= 32:
            break
    return sources


def _sanitize_benchmarks(value: Any) -> dict[str, Any]:
    raw = _as_mapping(value)
    raw_dimensions = _as_mapping(raw.get("dimensions"))
    dimensions = {
        name: _safe_float(raw_dimensions.get(name), minimum=0, maximum=1)
        for name in _BENCHMARK_DIMENSIONS
    }
    raw_coverage = raw.get("coverage") if isinstance(raw.get("coverage"), list) else []
    coverage = [
        name
        for name in _BENCHMARK_DIMENSIONS
        if name in raw_coverage and dimensions[name] is not None
    ]
    sources = _sanitize_benchmark_sources(raw.get("sources"))
    as_of = _safe_public_timestamp(raw.get("as_of"))
    catalogue_score = _safe_float(
        raw.get("catalogue_score"),
        minimum=0,
        maximum=1,
    )
    raw_status = raw.get("status") if raw.get("status") in _BENCHMARK_STATUSES else "no_data"
    evidence_backed = (
        raw_status == "evidence_backed"
        and bool(coverage)
        and bool(sources)
        and as_of is not None
    )
    if evidence_backed:
        status = "evidence_backed"
        confidence = (
            raw.get("confidence")
            if raw.get("confidence") in (_BENCHMARK_CONFIDENCE - {"no_data"})
            else "unknown"
        )
    else:
        status = "catalogue_only" if catalogue_score is not None else "no_data"
        dimensions = {name: None for name in _BENCHMARK_DIMENSIONS}
        coverage = []
        sources = []
        as_of = None
        confidence = "no_data"

    catalogue_label = (
        "legacy_static_registry"
        if catalogue_score is not None
        and raw.get("catalogue_score_label") == "legacy_static_registry"
        else None
    )
    matched_registry_id = _safe_public_text(
        raw.get("matched_registry_id"),
        max_length=256,
        pattern=_MODEL_IDENTIFIER,
    )
    return _PublicBenchmarkEvidence(
        status=status,
        dimensions=_PublicBenchmarkDimensions.model_validate(dimensions),
        coverage=coverage,
        confidence=confidence,
        sources=sources,
        as_of=as_of,
        catalogue_score=catalogue_score,
        catalogue_score_label=catalogue_label,
        matched_registry_id=matched_registry_id,
    ).model_dump(mode="json")


def _sanitize_policy_prior(value: Any) -> dict[str, Any]:
    raw = _as_mapping(value)
    tier = _safe_float(raw.get("registry_tier"), minimum=0, maximum=100)
    return _PublicPolicyPrior(
        registry_tier=tier,
        label="registry_policy_tier" if tier is not None else "none",
    ).model_dump(mode="json")


def _sanitize_registry(value: Any) -> dict[str, Any]:
    raw = _as_mapping(value)
    raw_capabilities = _as_mapping(raw.get("capabilities"))
    capabilities = {
        field: raw_capabilities[field]
        for field in _CAPABILITY_FIELDS
        if isinstance(raw_capabilities.get(field), bool)
    }
    return _PublicRegistryEvidence(
        context_tokens=_safe_context_tokens(raw.get("context_tokens")),
        capabilities=capabilities,
        roles=_safe_allowlisted_strings(
            raw.get("roles"),
            allowed=_REGISTRY_ROLES,
            maximum=16,
        ),
        lanes=_safe_allowlisted_strings(
            raw.get("lanes"),
            allowed=_REGISTRY_LANES,
            maximum=16,
        ),
    ).model_dump(mode="json")


def _sanitize_model_card(value: Any) -> dict[str, Any] | None:
    raw = _as_mapping(value)
    model_id = _safe_public_text(
        raw.get("model_id"),
        max_length=256,
        pattern=_MODEL_IDENTIFIER,
    )
    if model_id is None:
        return None
    label = _safe_public_text(raw.get("label"), max_length=200) or model_id
    provider_key = _safe_public_text(
        raw.get("provider_key"),
        max_length=128,
        pattern=_PROVIDER_IDENTIFIER,
    ) or "unknown"
    return _PublicModelCard(
        model_id=model_id,
        label=label,
        provider_key=provider_key,
        routing=_PublicRoutingEvidence.model_validate(_sanitize_routing(raw.get("routing"))),
        health=_PublicHealthEvidence.model_validate(_sanitize_health(raw.get("health"))),
        benchmarks=_PublicBenchmarkEvidence.model_validate(
            _sanitize_benchmarks(raw.get("benchmarks"))
        ),
        policy_prior=_PublicPolicyPrior.model_validate(
            _sanitize_policy_prior(raw.get("policy_prior"))
        ),
        registry=_PublicRegistryEvidence.model_validate(
            _sanitize_registry(raw.get("registry"))
        ),
    ).model_dump(mode="json")


def _sanitize_model_cards_projection(
    projection: dict[str, Any],
    *,
    limit: int,
) -> dict[str, Any]:
    if projection.get("schema_version") != 1:
        raise ValueError("canonical model-card projection schema is unsupported")
    generated_at = _safe_public_timestamp(projection.get("generated_at"))
    if generated_at is None:
        raise ValueError("canonical model-card projection timestamp is invalid")
    summary = _sanitize_projection_summary(projection.get("summary"))
    safe_models: list[dict[str, Any]] = []
    for raw_model in projection.get("models", []):
        model = _sanitize_model_card(raw_model)
        if model is not None:
            safe_models.append(model)
        if len(safe_models) >= limit:
            break
    return {
        "schema": "nexus.sage-model-cards.v1",
        "projection_schema_version": 1,
        "generated_at": generated_at,
        "benchmark_contract": {
            "dimensions": list(_BENCHMARK_DIMENSIONS),
            "no_data": "null",
            "policy_prior_is_not_benchmark": True,
        },
        "summary": summary,
        "models": safe_models,
        "returned": len(safe_models),
    }


def _forbidden_parameter_path(value: Any, path: str = "parameters") -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).strip().lower()
            child = f"{path}.{key}"
            if normalized in _FORBIDDEN_PARAMETER_KEYS:
                return child
            found = _forbidden_parameter_path(nested, child)
            if found:
                return found
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found = _forbidden_parameter_path(nested, f"{path}[{index}]")
            if found:
                return found
    return None


def _nexusclaw_handoff_for_pending_job(
    *,
    job_id: Any,
    principal: Any,
    workflow_type: Any,
    state: Any,
    parameters: Any,
    proposal: Any,
) -> dict[str, Any] | None:
    """Return the canonical dry-run handoff only for a valid pending receipt."""

    if state != "pending_review":
        return None
    try:
        return build_sage_job_handoff(
            job_id=job_id,
            principal=principal,
            workflow_type=workflow_type,
            state=state,
            parameters=parameters,
            proposal=proposal,
        ).to_dict()
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail="SAGE pending receipt is not eligible for a governed handoff",
            headers={"Cache-Control": "no-store"},
        ) from exc


def _serialize_job(job: SageJob) -> dict[str, Any]:
    payload = {
        "job_id": job.job_id,
        "workflow_type": job.workflow_type,
        "status": job.state,
        "proposal": job.proposal,
        "execution_allowed": False,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "expires_at": job.expires_at,
    }
    handoff = _nexusclaw_handoff_for_pending_job(
        job_id=job.job_id,
        principal=job.principal,
        workflow_type=job.workflow_type,
        state=job.state,
        parameters=job.parameters,
        proposal=job.proposal,
    )
    if handoff is not None:
        payload["nexusclaw_handoff"] = handoff
    return payload


def _serialize_submission_receipt(
    receipt: dict[str, Any],
    *,
    principal: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Attach the same governed handoff to created and idempotent replies."""

    payload = dict(receipt)
    handoff = _nexusclaw_handoff_for_pending_job(
        job_id=payload.get("job_id"),
        principal=principal,
        workflow_type=payload.get("workflow_type"),
        state=payload.get("status"),
        parameters=parameters,
        proposal=payload.get("proposal"),
    )
    if handoff is None:
        raise HTTPException(
            status_code=500,
            detail="SAGE proposal receipt has an invalid lifecycle state",
            headers={"Cache-Control": "no-store"},
        )
    payload["nexusclaw_handoff"] = handoff
    return payload


@router.get("/health")
async def sage_health(
    context: SageSecurityContext = Depends(require_sage_auth),
) -> dict[str, Any]:
    return {
        "ok": True,
        "service": "nexus-sage-ingress",
        "schema_version": "1.0",
        "timestamp": _now(),
        "plane": "brain-governance",
        "port_owner": 7352,
        "mode": context.mode,
        "principal": context.principal,
        "execution_allowed": False,
    }


@router.get("/capabilities")
async def sage_capabilities(
    context: SageSecurityContext = Depends(require_sage_auth),
) -> dict[str, Any]:
    return {
        "schema": "nexus.sage-capabilities.v1",
        "mode": context.mode,
        "authority": {
            "sage": ["sense", "propose", "witness"],
            "hermes": ["claim", "execute", "retry", "close"],
        },
        "observations": ["health", "capabilities", "grounding_manifest", "model_cards", "job_status"],
        "proposal_workflows": sorted(ALLOWED_WORKFLOWS),
        "proposal_writes_enabled": context.mode == "proposal_write",
        "arbitrary_program_execution": False,
        "raw_memory_export": False,
        "self_approval": False,
        "a2a_profile": "proposal-bound",
        "acp_profile": "future-editor-edge",
    }


@router.get("/grounding")
async def sage_grounding_manifest(
    _: SageSecurityContext = Depends(require_sage_auth),
) -> dict[str, Any]:
    files = []
    for relative in _GROUNDING_FILES:
        path = _REPO_ROOT / relative
        if not path.is_file():
            files.append({"name": relative, "available": False})
            continue
        payload = path.read_bytes()
        files.append(
            {
                "name": relative,
                "available": True,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "modified_at": datetime.fromtimestamp(
                    path.stat().st_mtime,
                    tz=timezone.utc,
                ).isoformat(),
            }
        )
    return {
        "schema": "nexus.sage-grounding-manifest.v1",
        "generated_at": _now(),
        "content_included": False,
        "files": files,
    }


async def _fetch_model_cards_projection(
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    async with httpx.AsyncClient(
        timeout=6.0,
        trust_env=False,
        follow_redirects=False,
        transport=transport,
    ) as client:
        async with client.stream(
            "GET",
            _MODEL_CARD_URL,
            headers={"Accept": "application/json"},
        ) as response:
            if 300 <= response.status_code < 400:
                raise ValueError("canonical model-card projection redirected")
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > _MAX_MODEL_CARD_RESPONSE_BYTES:
                    raise ValueError("canonical model-card projection exceeded size limit")
    payload = json.loads(body)
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        raise ValueError("canonical model-card projection returned an invalid contract")
    return payload


@router.get("/model-cards")
async def sage_model_cards(
    limit: int = Query(default=20, ge=1, le=100),
    _: SageSecurityContext = Depends(require_sage_auth),
) -> dict[str, Any]:
    try:
        projection = await _fetch_model_cards_projection()
        return _sanitize_model_cards_projection(projection, limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"canonical model-card projection unavailable: {type(exc).__name__}",
        ) from exc


@router.post("/jobs", status_code=202)
async def submit_sage_job(
    submission: SageJobSubmission,
    context: SageSecurityContext = Depends(require_sage_auth),
) -> JSONResponse:
    require_proposal_write(context)
    parameters = submission.parameters.model_dump(mode="json")
    forbidden_path = _forbidden_parameter_path(parameters)
    if forbidden_path:
        raise HTTPException(status_code=422, detail=f"forbidden parameter field: {forbidden_path}")
    persisted_values = {
        "parameters": parameters,
        "source_msg_id": submission.source_msg_id,
        "idempotency_key": submission.idempotency_key,
    }
    if contains_disallowed_persisted_content(persisted_values):
        raise HTTPException(
            status_code=422,
            detail="SAGE proposal content was rejected by persistence policy",
            headers={"Cache-Control": "no-store"},
        )

    encoded_parameters = json.dumps(
        parameters,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    if len(encoded_parameters) > 20_000:
        raise HTTPException(status_code=413, detail="SAGE job parameters are too large")

    proposal_id = f"sage-proposal-{uuid.uuid4().hex}"
    proposal = build_sage_job_proposal(
        task_id=proposal_id,
        workflow_type=submission.workflow_type,
        parameters=parameters,
    )
    result = await asyncio.to_thread(
        _store().submit_idempotent,
        principal=context.principal,
        workflow_type=submission.workflow_type,
        parameters=parameters,
        proposal=proposal,
        idempotency_key=submission.idempotency_key,
        source_msg_id=submission.source_msg_id,
    )
    if result.state == "conflict":
        raise HTTPException(
            status_code=409,
            detail="idempotency key reused with a different payload",
        )
    if result.response is None:
        raise HTTPException(status_code=500, detail="SAGE proposal receipt was not created")
    response_payload = _serialize_submission_receipt(
        result.response,
        principal=context.principal,
        parameters=parameters,
    )
    if result.state == "duplicate":
        return JSONResponse(
            status_code=result.http_status or 202,
            content=response_payload,
            headers={"X-NEXUS-Idempotency": "duplicate"},
        )
    return JSONResponse(
        status_code=202,
        content=response_payload,
        headers={"X-NEXUS-Idempotency": "created"},
    )


@router.get("/jobs/{job_id}")
async def get_sage_job(
    job_id: str,
    context: SageSecurityContext = Depends(require_sage_auth),
) -> dict[str, Any]:
    if len(job_id) > 96 or not job_id.startswith("sage-job-"):
        raise HTTPException(status_code=404, detail="SAGE job not found")
    job_store = _store()
    job = await asyncio.to_thread(job_store.get, job_id, principal=context.principal)
    if job is None:
        raise HTTPException(status_code=404, detail="SAGE job not found")
    return _serialize_job(job)
