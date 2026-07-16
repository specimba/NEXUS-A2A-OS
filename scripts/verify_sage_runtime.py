#!/usr/bin/env python3
"""Secret-safe live claim gate for the governed NEXUS SAGE ingress."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


SAGE_PREFIX = "/api/sage/v1"
EXPECTED_OPERATIONS = {
    ("GET", f"{SAGE_PREFIX}/health"),
    ("GET", f"{SAGE_PREFIX}/capabilities"),
    ("GET", f"{SAGE_PREFIX}/grounding"),
    ("GET", f"{SAGE_PREFIX}/model-cards"),
    ("POST", f"{SAGE_PREFIX}/jobs"),
    ("GET", f"{SAGE_PREFIX}/jobs/{{job_id}}"),
}
FORBIDDEN_PATHS = ("program", "memory", "swarm", "execute")
DEFAULT_KEY_FILE = Path.home() / ".nexus_pi" / "state" / ".sage_api_token"

_BENCHMARK_DIMENSIONS = (
    "quality", "code", "reasoning", "swe", "speed", "cost_efficiency",
)
_SUMMARY_FIELDS = {
    "catalogue_offers", "cli_model_ids", "cli_visible_offers",
    "observed_healthy", "health_unverified", "unavailable", "rate_limited",
    "evidence_backed_offers", "configured_providers", "authenticated_providers",
}
_MODEL_CARD_FIELDS = {
    "model_id", "label", "provider_key", "routing", "health", "benchmarks",
    "policy_prior", "registry",
}
_ROUTING_FIELDS = {"cli_visible", "cli_route_id", "eligible", "state"}
_HEALTH_FIELDS = {
    "state", "raw_status", "observed", "latency_ms", "uptime_percent",
    "last_checked_at", "is_rate_limited",
}
_BENCHMARK_FIELDS = {
    "status", "dimensions", "coverage", "confidence", "sources", "as_of",
    "catalogue_score", "catalogue_score_label", "matched_registry_id",
}
_HEALTH_STATES = {
    "healthy", "unverified", "rate_limited", "auth_required", "unavailable",
    "excluded", "unknown",
}
_RAW_HEALTH_STATES = {
    "pending", "unknown", "up", "429", "rate_limited", "noauth",
    "unauthorized", "401", "403", "down", "timeout", "error", "banned",
    "disabled", "excluded",
}
_ROUTING_STATES = {"cli_visible", "offer_only", "excluded", "unknown"}
_BENCHMARK_STATUSES = {"evidence_backed", "catalogue_only", "no_data"}
_BENCHMARK_CONFIDENCE = {"low", "medium", "high", "unknown", "no_data"}
_CAPABILITY_FIELDS = {"tools", "thinking", "thinkingBudget", "vision"}
_REGISTRY_ROLES = {"code", "fast", "frontier", "intent", "judge", "reasoning", "teacher"}
_REGISTRY_LANES = {
    "core", "eval", "local", "logging_fallback", "memory_fallback",
    "quarantine", "specialist", "teacher", "visual",
}
_MODEL_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+/-]{0,255}$")
_PROVIDER_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SOURCE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SENSITIVE_PUBLIC_TEXT = re.compile(
    r"(?i)(?:\b(?:api[-_ ]?key|access[-_ ]?token|refresh[-_ ]?token|"
    r"client[-_ ]?secret|password|passwd|authorization)\b\s*[:=]\s*\S+|"
    r"\bbearer\s+\S{8,}|\bsk-[A-Za-z0-9_-]{16,}|"
    r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----)"
)


class _NoRedirectHandler(HTTPRedirectHandler):
    """Return 30x responses to the verifier without forwarding credentials."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


_NO_REDIRECT_OPENER = build_opener(_NoRedirectHandler())


class ClaimFailure(RuntimeError):
    """A runtime property failed its SAGE claim gate."""


def _validated_base_url(value: str) -> str:
    parsed = urlparse(value.rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ClaimFailure("base URL must be an absolute HTTP(S) URL")
    if parsed.path not in {"", "/"}:
        raise ClaimFailure("base URL must not contain a path")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ClaimFailure("base URL must not contain credentials, query, or fragment")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ClaimFailure("non-loopback SAGE verification requires HTTPS")
    return value.rstrip("/")


def _pin_expected_host(base_url: str, expected_host: str | None) -> str:
    hostname = urlparse(base_url).hostname or ""
    loopback = hostname in {"127.0.0.1", "localhost", "::1"}
    normalized_expected = (expected_host or "").strip().rstrip(".").casefold()
    normalized_actual = hostname.rstrip(".").casefold()
    if not loopback and not normalized_expected:
        raise ClaimFailure("non-loopback verification requires --expected-host")
    if normalized_expected and normalized_expected != normalized_actual:
        raise ClaimFailure("base URL host does not match the expected host pin")
    return normalized_actual
def _enforce_surface(verified_host: str, *, is_edge: bool) -> None:
    loopback = verified_host in {"127.0.0.1", "localhost", "::1"}
    if not loopback and not is_edge:
        raise ClaimFailure(
            "non-loopback verification requires the hardened SAGE edge surface"
        )




def _read_key(path: Path) -> str:
    try:
        key = path.expanduser().read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ClaimFailure("SAGE key file is unavailable") from exc
    if len(key) < 32:
        raise ClaimFailure("SAGE key file does not contain a strong credential")
    return key


def _request(
    base_url: str,
    path: str,
    key: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    expected: set[int] | None = None,
) -> tuple[int, dict[str, Any]]:
    body = None
    headers = {"Accept": "application/json", "Authorization": f"Bearer {key}"}
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(base_url + path, data=body, headers=headers, method=method)
    status = 0
    raw = b""
    try:
        with _NO_REDIRECT_OPENER.open(request, timeout=8) as response:
            status = response.status
            raw = response.read(2_000_000)
    except HTTPError as exc:
        status = exc.code
        raw = exc.read(2_000_000)
    except (OSError, URLError) as exc:
        raise ClaimFailure(f"request failed for {path}: {type(exc).__name__}") from exc
    if expected is not None and status not in expected:
        raise ClaimFailure(f"unexpected status for {path}: {status}")
    try:
        decoded = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise ClaimFailure(f"non-JSON response for {path}") from exc
    if not isinstance(decoded, dict):
        raise ClaimFailure(f"non-object response for {path}")
    return status, decoded


def _openapi_operations(schema: dict[str, Any]) -> set[tuple[str, str]]:
    operations: set[tuple[str, str]] = set()
    paths = schema.get("paths")
    if not isinstance(paths, dict):
        raise ClaimFailure("OpenAPI document has no paths object")
    for path, path_item in paths.items():
        if not str(path).startswith(SAGE_PREFIX) or not isinstance(path_item, dict):
            continue
        for method in path_item:
            normalized = str(method).upper()
            if normalized in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                operations.add((normalized, str(path)))
    return operations


def _exact_mapping(
    value: Any,
    expected_keys: set[str],
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise ClaimFailure(f"{label} keys are invalid")
    return value


def _require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ClaimFailure(f"{label} is invalid")
    return value


def _require_optional_number(
    value: Any,
    label: str,
    *,
    minimum: float,
    maximum: float,
) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ClaimFailure(f"{label} is invalid")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ClaimFailure(f"{label} is invalid")
    return number


def _require_count(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ClaimFailure(f"{label} is invalid")
    if not 0 <= value <= 10_000_000:
        raise ClaimFailure(f"{label} is invalid")
    return value


def _require_safe_text(value: Any, label: str, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise ClaimFailure(f"{label} is invalid")
    if not value or len(value) > max_length or not all(char.isprintable() for char in value):
        raise ClaimFailure(f"{label} is invalid")
    lowered = value.casefold()
    if "://" in lowered or _SENSITIVE_PUBLIC_TEXT.search(value):
        raise ClaimFailure(f"{label} is invalid")
    if re.search(
        r"(?i)(?:[A-Z]:[\\/]|/(?:home|users|root|etc|var|tmp|data|opt|srv)(?:/|$))",
        value,
    ):
        raise ClaimFailure(f"{label} is invalid")
    return value


def _require_identifier(
    value: Any,
    label: str,
    *,
    pattern: re.Pattern[str],
    max_length: int,
) -> str:
    text = _require_safe_text(value, label, max_length=max_length)
    if pattern.fullmatch(text) is None:
        raise ClaimFailure(f"{label} is invalid")
    return text


def _require_optional_identifier(
    value: Any,
    label: str,
    *,
    pattern: re.Pattern[str],
    max_length: int,
) -> str | None:
    if value is None:
        return None
    return _require_identifier(
        value,
        label,
        pattern=pattern,
        max_length=max_length,
    )


def _require_optional_timestamp(value: Any, label: str) -> str | None:
    if value is None:
        return None
    text = _require_safe_text(value, label, max_length=64)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ClaimFailure(f"{label} is invalid") from exc
    if parsed.tzinfo is None:
        raise ClaimFailure(f"{label} is invalid")
    return text


def _require_allowlisted_list(
    value: Any,
    label: str,
    *,
    allowed: set[str],
    maximum: int,
) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise ClaimFailure(f"{label} is invalid")
    if any(not isinstance(item, str) or item not in allowed for item in value):
        raise ClaimFailure(f"{label} is invalid")
    if len(set(value)) != len(value):
        raise ClaimFailure(f"{label} is invalid")
    return value


def _validate_model_card(card: Any) -> None:
    model = _exact_mapping(card, _MODEL_CARD_FIELDS, "model-card")
    _require_identifier(
        model["model_id"],
        "model-card model id",
        pattern=_MODEL_IDENTIFIER,
        max_length=256,
    )
    _require_safe_text(model["label"], "model-card label", max_length=200)
    _require_identifier(
        model["provider_key"],
        "model-card provider",
        pattern=_PROVIDER_IDENTIFIER,
        max_length=128,
    )

    routing = _exact_mapping(model["routing"], _ROUTING_FIELDS, "model-card routing")
    cli_visible = _require_bool(routing["cli_visible"], "model-card routing visibility")
    route_id = _require_optional_identifier(
        routing["cli_route_id"],
        "model-card route id",
        pattern=_MODEL_IDENTIFIER,
        max_length=256,
    )
    _require_bool(routing["eligible"], "model-card routing eligibility")
    if routing["state"] not in _ROUTING_STATES:
        raise ClaimFailure("model-card routing state is invalid")
    if cli_visible != (route_id is not None):
        raise ClaimFailure("model-card routing visibility is inconsistent")

    health = _exact_mapping(model["health"], _HEALTH_FIELDS, "model-card health")
    if health["state"] not in _HEALTH_STATES:
        raise ClaimFailure("model-card health state is invalid")
    if health["raw_status"] not in _RAW_HEALTH_STATES:
        raise ClaimFailure("model-card health raw status is invalid")
    _require_bool(health["observed"], "model-card health observed")
    _require_optional_number(
        health["latency_ms"],
        "model-card health latency",
        minimum=0,
        maximum=86_400_000,
    )
    _require_optional_number(
        health["uptime_percent"],
        "model-card health uptime",
        minimum=0,
        maximum=100,
    )
    _require_optional_timestamp(health["last_checked_at"], "model-card health timestamp")
    _require_bool(health["is_rate_limited"], "model-card rate-limit flag")

    benchmarks = _exact_mapping(
        model["benchmarks"],
        _BENCHMARK_FIELDS,
        "model-card benchmarks",
    )
    if benchmarks["status"] not in _BENCHMARK_STATUSES:
        raise ClaimFailure("model-card benchmark status is invalid")
    dimensions = _exact_mapping(
        benchmarks["dimensions"],
        set(_BENCHMARK_DIMENSIONS),
        "model-card benchmark dimensions",
    )
    normalized_dimensions = {
        name: _require_optional_number(
            dimensions[name],
            f"model-card benchmark {name}",
            minimum=0,
            maximum=1,
        )
        for name in _BENCHMARK_DIMENSIONS
    }
    coverage = _require_allowlisted_list(
        benchmarks["coverage"],
        "model-card benchmark coverage",
        allowed=set(_BENCHMARK_DIMENSIONS),
        maximum=len(_BENCHMARK_DIMENSIONS),
    )
    if any(normalized_dimensions[name] is None for name in coverage):
        raise ClaimFailure("model-card benchmark coverage is inconsistent")
    if benchmarks["confidence"] not in _BENCHMARK_CONFIDENCE:
        raise ClaimFailure("model-card benchmark confidence is invalid")
    sources = benchmarks["sources"]
    if not isinstance(sources, list) or len(sources) > 32:
        raise ClaimFailure("model-card benchmark sources are invalid")
    checked_sources = [
        _require_identifier(
            source,
            "model-card benchmark sources",
            pattern=_SOURCE_IDENTIFIER,
            max_length=128,
        )
        for source in sources
    ]
    if len(set(checked_sources)) != len(checked_sources):
        raise ClaimFailure("model-card benchmark sources are invalid")
    as_of = _require_optional_timestamp(benchmarks["as_of"], "model-card benchmark timestamp")
    catalogue_score = _require_optional_number(
        benchmarks["catalogue_score"],
        "model-card catalogue score",
        minimum=0,
        maximum=1,
    )
    if benchmarks["catalogue_score_label"] not in {None, "legacy_static_registry"}:
        raise ClaimFailure("model-card catalogue label is invalid")
    if benchmarks["catalogue_score_label"] is not None and catalogue_score is None:
        raise ClaimFailure("model-card catalogue label is inconsistent")
    _require_optional_identifier(
        benchmarks["matched_registry_id"],
        "model-card matched registry id",
        pattern=_MODEL_IDENTIFIER,
        max_length=256,
    )
    if benchmarks["status"] == "evidence_backed":
        if not coverage or not checked_sources or as_of is None:
            raise ClaimFailure("model-card benchmark evidence is incomplete")
        if benchmarks["confidence"] == "no_data":
            raise ClaimFailure("model-card benchmark confidence is inconsistent")
    else:
        if coverage or checked_sources or as_of is not None:
            raise ClaimFailure("model-card benchmark evidence is inconsistent")
        if any(value is not None for value in normalized_dimensions.values()):
            raise ClaimFailure("model-card benchmark dimensions are inconsistent")
        if benchmarks["confidence"] != "no_data":
            raise ClaimFailure("model-card benchmark confidence is inconsistent")
        if benchmarks["status"] == "catalogue_only" and catalogue_score is None:
            raise ClaimFailure("model-card catalogue status is inconsistent")
        if benchmarks["status"] == "no_data" and catalogue_score is not None:
            raise ClaimFailure("model-card catalogue status is inconsistent")

    policy = _exact_mapping(
        model["policy_prior"],
        {"registry_tier", "label"},
        "model-card policy prior",
    )
    tier = _require_optional_number(
        policy["registry_tier"],
        "model-card policy tier",
        minimum=0,
        maximum=100,
    )
    expected_policy_label = "registry_policy_tier" if tier is not None else "none"
    if policy["label"] != expected_policy_label:
        raise ClaimFailure("model-card policy label is inconsistent")

    registry = _exact_mapping(
        model["registry"],
        {"context_tokens", "capabilities", "roles", "lanes"},
        "model-card registry",
    )
    context_tokens = registry["context_tokens"]
    if context_tokens is not None:
        if isinstance(context_tokens, bool) or not isinstance(context_tokens, int):
            raise ClaimFailure("model-card context size is invalid")
        if not 1 <= context_tokens <= 100_000_000:
            raise ClaimFailure("model-card context size is invalid")
    capabilities = registry["capabilities"]
    if not isinstance(capabilities, dict) or not set(capabilities) <= _CAPABILITY_FIELDS:
        raise ClaimFailure("model-card capability keys are invalid")
    if any(not isinstance(value, bool) for value in capabilities.values()):
        raise ClaimFailure("model-card capability values are invalid")
    _require_allowlisted_list(
        registry["roles"],
        "model-card roles",
        allowed=_REGISTRY_ROLES,
        maximum=16,
    )
    _require_allowlisted_list(
        registry["lanes"],
        "model-card lanes",
        allowed=_REGISTRY_LANES,
        maximum=16,
    )


def _validate_model_card_response(cards: dict[str, Any]) -> None:
    response = _exact_mapping(
        cards,
        {
            "schema", "projection_schema_version", "generated_at",
            "benchmark_contract", "summary", "models", "returned",
        },
        "model-card response",
    )
    if response["schema"] != "nexus.sage-model-cards.v1":
        raise ClaimFailure("model-card projection schema mismatch")
    if type(response["projection_schema_version"]) is not int or response["projection_schema_version"] != 1:
        raise ClaimFailure("model-card source schema mismatch")
    if _require_optional_timestamp(
        response["generated_at"], "model-card generation timestamp"
    ) is None:
        raise ClaimFailure("model-card generation timestamp is invalid")
    contract = _exact_mapping(
        response["benchmark_contract"],
        {"dimensions", "no_data", "policy_prior_is_not_benchmark"},
        "model-card benchmark contract",
    )
    if contract["dimensions"] != list(_BENCHMARK_DIMENSIONS):
        raise ClaimFailure("model-card benchmark contract dimensions are invalid")
    if contract["no_data"] != "null" or contract["policy_prior_is_not_benchmark"] is not True:
        raise ClaimFailure("model-card benchmark contract is invalid")
    summary = _exact_mapping(response["summary"], _SUMMARY_FIELDS, "model-card summary")
    counts = {field: _require_count(summary[field], f"model-card summary {field}") for field in _SUMMARY_FIELDS}
    if counts["authenticated_providers"] > counts["configured_providers"]:
        raise ClaimFailure("model-card provider counts are inconsistent")
    for field in (
        "cli_visible_offers", "observed_healthy", "health_unverified",
        "unavailable", "rate_limited", "evidence_backed_offers",
    ):
        if counts[field] > counts["catalogue_offers"]:
            raise ClaimFailure("model-card catalogue counts are inconsistent")
    models = response["models"]
    returned = _require_count(response["returned"], "model-card returned count")
    if not isinstance(models, list) or returned != len(models) or len(models) > 1:
        raise ClaimFailure("model-card returned count is inconsistent")
    if counts["catalogue_offers"] > 0 and returned == 0:
        raise ClaimFailure("model-card response omitted all catalogue evidence")
    for card in models:
        _validate_model_card(card)


def verify(base_url: str, key_file: Path, *, expected_host: str | None = None) -> dict[str, Any]:
    base_url = _validated_base_url(base_url)
    verified_host = _pin_expected_host(base_url, expected_host)
    key = _read_key(key_file)
    checks: list[str] = []

    _, health = _request(base_url, f"{SAGE_PREFIX}/health", key, expected={200})
    if not health.get("ok") or health.get("plane") != "brain-governance":
        raise ClaimFailure("health response is not the Brain governance plane")
    if health.get("execution_allowed") is not False:
        raise ClaimFailure("health response did not deny execution")
    mode = health.get("mode")
    if mode not in {"observe_only", "proposal_write"}:
        raise ClaimFailure(f"unexpected SAGE mode: {mode!r}")
    checks.append("brain_plane_health")

    _, capabilities = _request(
        base_url, f"{SAGE_PREFIX}/capabilities", key, expected={200}
    )
    if capabilities.get("arbitrary_program_execution") is not False:
        raise ClaimFailure("capability fence permits arbitrary programs")
    if capabilities.get("raw_memory_export") is not False:
        raise ClaimFailure("capability fence permits raw memory export")
    if capabilities.get("self_approval") is not False:
        raise ClaimFailure("capability fence permits self-approval")
    checks.append("sense_propose_witness_fence")

    _, grounding = _request(base_url, f"{SAGE_PREFIX}/grounding", key, expected={200})
    if grounding.get("content_included") is not False:
        raise ClaimFailure("grounding endpoint returned file content")
    for entry in grounding.get("files", []):
        if not isinstance(entry, dict) or Path(str(entry.get("name", ""))).is_absolute():
            raise ClaimFailure("grounding endpoint exposed an absolute path")
    checks.append("metadata_only_grounding")

    _, cards = _request(
        base_url, f"{SAGE_PREFIX}/model-cards?limit=1", key, expected={200}
    )
    _validate_model_card_response(cards)
    checks.append("sanitized_model_cards")

    openapi_status, schema = _request(
        base_url, "/openapi.json", key, expected={200, 404}
    )
    is_edge = openapi_status == 404
    _enforce_surface(verified_host, is_edge=is_edge)
    if is_edge:
        _, readiness = _request(
            base_url, "/_nexus/sage-edge/ready", key, expected={200}
        )
        if readiness.get("service") != "nexus-sage-edge":
            raise ClaimFailure("OpenAPI is absent but the endpoint is not a SAGE edge")
        _, missing_job = _request(
            base_url,
            f"{SAGE_PREFIX}/jobs/sage-job-{'0' * 32}",
            key,
            expected={404},
        )
        if missing_job.get("detail") != "SAGE job not found" or missing_job.get("code"):
            raise ClaimFailure("valid job-status operation did not reach Brain")
        operations = EXPECTED_OPERATIONS
        checks.append("six_operation_edge_contract")
        checks.append("internal_openapi_not_exposed")
    else:
        operations = _openapi_operations(schema)
        if operations != EXPECTED_OPERATIONS:
            raise ClaimFailure(
                f"SAGE OpenAPI drift: expected {len(EXPECTED_OPERATIONS)} operations, "
                f"found {len(operations)}"
            )
        checks.append("six_operation_openapi")

    bad_key = "x" * max(32, len(key))
    _request(base_url, f"{SAGE_PREFIX}/health", bad_key, expected={401})
    checks.append("invalid_bearer_rejected")

    for segment in FORBIDDEN_PATHS:
        _request(base_url, f"{SAGE_PREFIX}/{segment}", key, expected={404})
    checks.append("forbidden_routes_absent")

    if mode == "observe_only":
        _request(
            base_url,
            f"{SAGE_PREFIX}/jobs",
            key,
            method="POST",
            payload={
                "workflow_type": "model_health_snapshot",
                "idempotency_key": "runtime-claim-gate",
                "parameters": {"providers": [], "include_unverified": True},
            },
            expected={403},
        )
        checks.append("proposal_write_denied")
    else:
        if capabilities.get("proposal_writes_enabled") is not True:
            raise ClaimFailure("proposal-write mode is not reflected in capabilities")
        checks.append("proposal_write_enabled_not_mutation_probed")

    return {
        "ok": True,
        "service": "nexus-sage-runtime-claim-gate",
        "base_url": base_url,
        "verified_host": verified_host,
        "mode": mode,
        "surface": "edge" if is_edge else "brain",
        "checks": checks,
        "operation_count": len(operations),
        "secret_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:7352")
    parser.add_argument("--key-file", type=Path, default=DEFAULT_KEY_FILE)
    parser.add_argument(
        "--expected-host",
        help="required hostname pin for every non-loopback HTTPS verification",
    )
    args = parser.parse_args()
    try:
        report = verify(
            args.base_url, args.key_file, expected_host=args.expected_host
        )
    except ClaimFailure as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
