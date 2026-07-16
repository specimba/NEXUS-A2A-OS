from __future__ import annotations

from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

import pytest

import scripts.verify_sage_runtime as runtime
from scripts.verify_sage_runtime import (
    ClaimFailure,
    EXPECTED_OPERATIONS,
    _enforce_surface,
    _openapi_operations,
    _pin_expected_host,
    _request,
    _validated_base_url,
)


def _valid_model_cards_response() -> dict:
    return {
        "schema": "nexus.sage-model-cards.v1",
        "projection_schema_version": 1,
        "generated_at": "2026-07-13T00:00:00Z",
        "benchmark_contract": {
            "dimensions": [
                "quality", "code", "reasoning", "swe", "speed", "cost_efficiency",
            ],
            "no_data": "null",
            "policy_prior_is_not_benchmark": True,
        },
        "summary": {
            "catalogue_offers": 1,
            "cli_model_ids": 1,
            "cli_visible_offers": 1,
            "observed_healthy": 0,
            "health_unverified": 1,
            "unavailable": 0,
            "rate_limited": 0,
            "evidence_backed_offers": 1,
            "configured_providers": 1,
            "authenticated_providers": 1,
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
                },
                "health": {
                    "state": "unverified",
                    "raw_status": "pending",
                    "observed": False,
                    "latency_ms": None,
                    "uptime_percent": None,
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
                    },
                    "coverage": ["quality", "code"],
                    "confidence": "high",
                    "sources": ["aa_coding"],
                    "as_of": "2026-07-08T00:00:00+00:00",
                    "catalogue_score": None,
                    "catalogue_score_label": None,
                    "matched_registry_id": "z-ai/glm-5.2",
                },
                "policy_prior": {
                    "registry_tier": 96.0,
                    "label": "registry_policy_tier",
                },
                "registry": {
                    "context_tokens": 1048576,
                    "capabilities": {"tools": True, "thinking": True},
                    "roles": ["frontier"],
                    "lanes": ["core"],
                },
            }
        ],
        "returned": 1,
    }


@pytest.mark.parametrize(
    "url",
    (
        "http://127.0.0.1:7352",
        "http://localhost:7352/",
        "https://sage.example.test",
    ),
)
def test_validated_base_url_accepts_loopback_http_or_https(url: str) -> None:
    assert _validated_base_url(url) == url.rstrip("/")


@pytest.mark.parametrize(
    "url",
    (
        "http://sage.example.test",
        "ftp://127.0.0.1:7352",
        "https://user:secret@sage.example.test",
        "https://sage.example.test?token=secret",
        "https://sage.example.test/unexpected-prefix",
    ),
)
def test_validated_base_url_rejects_unsafe_forms(url: str) -> None:
    with pytest.raises(ClaimFailure):
        _validated_base_url(url)


def test_openapi_operations_selects_only_the_six_sage_routes() -> None:
    paths: dict[str, dict[str, object]] = {}
    for method, path in EXPECTED_OPERATIONS:
        paths.setdefault(path, {})[method.lower()] = {}
    paths["/api/tasks"] = {"get": {}}
    paths["/api/sage/v1/health"]["parameters"] = []

    assert _openapi_operations({"paths": paths}) == EXPECTED_OPERATIONS


def test_openapi_operations_requires_paths_object() -> None:
    with pytest.raises(ClaimFailure, match="no paths"):
        _openapi_operations({})


def test_verify_recognizes_hardened_edge_without_requiring_openapi(monkeypatch, tmp_path) -> None:
    key_file = tmp_path / "sage.key"
    key_file.write_text("k" * 64, encoding="utf-8")

    def fake_request(base_url, path, key, *, method="GET", payload=None, expected=None):
        assert base_url == "http://127.0.0.1:17452"
        status, body = 200, {}
        if path == f"{runtime.SAGE_PREFIX}/health":
            if key.startswith("x"):
                status, body = 401, {"detail": "invalid"}
            else:
                body = {
                    "ok": True,
                    "plane": "brain-governance",
                    "execution_allowed": False,
                    "mode": "observe_only",
                }
        elif path == f"{runtime.SAGE_PREFIX}/capabilities":
            body = {
                "arbitrary_program_execution": False,
                "raw_memory_export": False,
                "self_approval": False,
            }
        elif path == f"{runtime.SAGE_PREFIX}/grounding":
            body = {"content_included": False, "files": [{"name": "AGENTS.md"}]}
        elif path == f"{runtime.SAGE_PREFIX}/model-cards?limit=1":
            body = _valid_model_cards_response()
        elif path == "/openapi.json":
            status, body = 404, {"code": "sage_edge_path_rejected"}
        elif path == "/_nexus/sage-edge/ready":
            body = {"ok": True, "service": "nexus-sage-edge"}
        elif path.endswith("sage-job-" + "0" * 32):
            status, body = 404, {"detail": "SAGE job not found"}
        elif path == f"{runtime.SAGE_PREFIX}/jobs" and method == "POST":
            status, body = 403, {"detail": "proposal writes disabled"}
        elif any(path == f"{runtime.SAGE_PREFIX}/{item}" for item in runtime.FORBIDDEN_PATHS):
            status, body = 404, {"code": "sage_edge_path_rejected"}
        else:
            raise AssertionError(f"unexpected probe: {method} {path}")
        assert expected is None or status in expected
        return status, body

    monkeypatch.setattr(runtime, "_request", fake_request)
    report = runtime.verify("http://127.0.0.1:17452", key_file)

    assert report["ok"] is True
    assert report["surface"] == "edge"
    assert report["operation_count"] == 6
    assert "internal_openapi_not_exposed" in report["checks"]


def test_non_loopback_verification_requires_exact_host_pin() -> None:
    with pytest.raises(ClaimFailure, match="requires --expected-host"):
        _pin_expected_host("https://sage.example.test", None)
    with pytest.raises(ClaimFailure, match="does not match"):
        _pin_expected_host("https://sage.example.test", "other.example.test")
    assert (
        _pin_expected_host("https://sage.example.test", "SAGE.EXAMPLE.TEST.")
        == "sage.example.test"
    )


def test_non_loopback_verification_requires_hardened_edge() -> None:
    with pytest.raises(ClaimFailure, match="requires the hardened SAGE edge"):
        _enforce_surface("sage.example.test", is_edge=False)

    _enforce_surface("sage.example.test", is_edge=True)
    _enforce_surface("127.0.0.1", is_edge=False)


def test_model_card_contract_validator_accepts_exact_typed_projection() -> None:
    runtime._validate_model_card_response(_valid_model_cards_response())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("projection_schema_version", True),
        ("generated_at", None),
    ],
)
def test_model_card_contract_validator_rejects_wrong_top_level_types(field, value) -> None:
    payload = deepcopy(_valid_model_cards_response())
    payload[field] = value

    with pytest.raises(ClaimFailure):
        runtime._validate_model_card_response(payload)


def test_model_card_contract_validator_rejects_arbitrary_nested_keys() -> None:
    payload = deepcopy(_valid_model_cards_response())
    payload["models"][0]["routing"]["endpoint"] = "https://provider.invalid/v1"

    with pytest.raises(ClaimFailure, match="routing keys"):
        runtime._validate_model_card_response(payload)


def test_model_card_contract_validator_rejects_sensitive_string_values() -> None:
    payload = deepcopy(_valid_model_cards_response())
    payload["models"][0]["benchmarks"]["sources"] = [
        "https://provider.invalid/private-score"
    ]

    with pytest.raises(ClaimFailure, match="benchmark sources"):
        runtime._validate_model_card_response(payload)


def test_model_card_contract_validator_rejects_wrong_nested_types() -> None:
    payload = deepcopy(_valid_model_cards_response())
    payload["models"][0]["health"]["observed"] = "false"

    with pytest.raises(ClaimFailure, match="health observed"):
        runtime._validate_model_card_response(payload)


def test_request_never_forwards_bearer_across_redirect() -> None:
    received_authorization: list[str | None] = []

    class SinkHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            received_authorization.append(self.headers.get("Authorization"))
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args) -> None:
            return

    sink = ThreadingHTTPServer(("127.0.0.1", 0), SinkHandler)
    sink_thread = threading.Thread(target=sink.serve_forever, daemon=True)
    sink_thread.start()

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(302)
            self.send_header(
                "Location",
                f"http://127.0.0.1:{sink.server_port}/credential-sink",
            )
            self.end_headers()

        def log_message(self, *_args) -> None:
            return

    redirector = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    redirect_thread = threading.Thread(target=redirector.serve_forever, daemon=True)
    redirect_thread.start()
    try:
        with pytest.raises(ClaimFailure, match="unexpected status"):
            _request(
                f"http://127.0.0.1:{redirector.server_port}",
                "/api/sage/v1/health",
                "s" * 64,
                expected={200},
            )
        assert received_authorization == []
    finally:
        redirector.shutdown()
        redirector.server_close()
        sink.shutdown()
        sink.server_close()
        redirect_thread.join(timeout=2)
        sink_thread.join(timeout=2)
