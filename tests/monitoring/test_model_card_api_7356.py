"""Integration checks for the 7356 same-origin model-card projection API."""
from __future__ import annotations

import json
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
SERVER = REPO / "scripts" / "serve_dashboard_7356.js"
node = shutil.which("node")
pytestmark = pytest.mark.skipif(node is None, reason="node not available")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def model_card_server():
    request_paths: list[str] = []
    frontier_state = REPO / "tests" / "monitoring" / "fixtures"

    class RelayHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - stdlib handler contract
            request_paths.append(self.path)
            if self.path == "/api/models":
                payload = {
                    "models": [
                        {
                            "modelId": "z-ai/glm-5.2",
                            "label": "GLM-5.2",
                            "providerKey": "nvidia",
                            "status": "pending",
                            "pings": [],
                            "lastPingAt": 0,
                            "intell": None,
                            "isEstimatedScore": True,
                            "ctx": "1M",
                        },
                        {
                            "modelId": "labs-leanstral-1-5-1",
                            "label": "Leanstral 1.5",
                            "providerKey": "openai-compatible:mistral",
                            "status": "up",
                            "pings": [{"code": "200", "ms": 4853, "ts": int(time.time() * 1000)}],
                            "avg": 4853,
                            "intell": None,
                            "isEstimatedScore": True,
                            "ctx": "256k",
                        },
                    ]
                }
            elif self.path == "/v1/models":
                payload = {
                    "object": "list",
                    "data": [
                        {"id": "auto-fastest"},
                        {"id": "z-ai/glm-5.2"},
                        {"id": "labs-leanstral-1-5-1"},
                    ],
                }
            elif self.path == "/api/config":
                payload = [
                    {"key": "nvidia", "enabled": True, "hasKey": True},
                    {
                        "key": "openai-compatible:mistral",
                        "enabled": True,
                        "hasKey": True,
                    },
                ]
            else:
                self.send_error(404)
                return
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            return

    relay = ThreadingHTTPServer(("127.0.0.1", _free_port()), RelayHandler)
    relay_thread = threading.Thread(target=relay.serve_forever, daemon=True)
    relay_thread.start()

    dashboard_port = _free_port()
    env = {
        "PORT": str(dashboard_port),
        "HOST": "127.0.0.1",
        "PATH": str(Path(node).parent),
        "SystemRoot": "C:\\Windows",
        "MODELRELAY_BASE_URL": f"http://127.0.0.1:{relay.server_port}",
        "NEXUS_FRONTIER_SCANNER_STATE": str(frontier_state),
    }
    proc = subprocess.Popen(
        [node, str(SERVER)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=REPO,
    )
    url = f"http://127.0.0.1:{dashboard_port}"
    try:
        for _ in range(50):
            if proc.poll() is not None:
                output = proc.communicate(timeout=5)[0].decode("utf-8", errors="replace")
                pytest.fail(f"7356 test server exited before readiness: {output[:1000]}")
            try:
                urllib.request.urlopen(f"{url}/health", timeout=1)
                break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.1)
        else:
            proc.kill()
            pytest.fail("7356 test server did not start")
        yield url, request_paths
    finally:
        if proc.poll() is None:
            proc.kill()
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate(timeout=5)
        relay.shutdown()
        relay.server_close()
        relay_thread.join(timeout=5)


def test_model_card_api_projects_live_routes_health_and_benchmarks(model_card_server):
    server_url, request_paths = model_card_server
    with urllib.request.urlopen(f"{server_url}/api/model-cards", timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
        cache_control = response.headers.get("Cache-Control")

    assert response.status == 200
    assert cache_control == "no-store"
    assert payload["schema_version"] == 1
    assert payload["summary"]["catalogue_offers"] == 2
    assert payload["summary"]["relay_route_ids"] == 3
    assert payload["summary"]["automatic_route_ids"] == 1
    assert payload["summary"]["observed_stale"] == 0
    assert payload["summary"]["cli_model_ids"] == 2
    assert payload["summary"]["observed_healthy"] == 1
    assert payload["summary"]["health_unverified"] == 1
    assert payload["summary"]["evidence_backed_offers"] == 1

    glm = next(model for model in payload["models"] if model["model_id"] == "z-ai/glm-5.2")
    assert glm["health"]["state"] == "unverified"
    assert glm["routing"]["cli_visible"] is True
    assert glm["benchmarks"]["status"] == "evidence_backed"
    assert glm["benchmarks"]["dimensions"]["quality"] == 0.7161
    assert glm["benchmarks"]["dimensions"]["swe"] is None

    leanstral = next(
        model for model in payload["models"] if model["model_id"] == "labs-leanstral-1-5-1"
    )
    assert leanstral["health"]["state"] == "healthy"
    assert leanstral["health"]["latest_http_code"] == 200
    assert leanstral["benchmarks"]["status"] == "no_data"

    assert set(request_paths) == {"/api/models", "/v1/models", "/api/config"}
    serialized = json.dumps(payload)
    assert "apiKey" not in serialized
    assert "apiKeys" not in serialized
    assert "/chat/completions" not in serialized


def test_client_manifest_is_live_canonical_and_safe_for_cli_consumers(model_card_server):
    server_url, request_paths = model_card_server
    with urllib.request.urlopen(f"{server_url}/api/client-manifest", timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
        cache_control = response.headers.get("Cache-Control")

    assert response.status == 200
    assert cache_control == "no-store"
    assert payload["schema_version"] == 1
    assert payload["contract"]["source"] == "nexus-model-arena-live-projection"
    assert payload["contract"]["relay_base_url"].endswith("/v1")
    assert payload["automatic_route"]["id"] == "auto-fastest"
    assert payload["summary"]["canonical_cli_routes"] == 2
    assert payload["summary"]["canonical_providers"] == 2
    assert payload["summary"]["observed_healthy_routes"] == 1
    assert payload["recommendation"]["id"] == "labs-leanstral-1-5-1"

    glm = next(model for model in payload["models"] if model["id"] == "z-ai/glm-5.2")
    assert glm["health"]["state"] == "unverified"
    assert glm["benchmarks"]["status"] == "evidence_backed"
    assert glm["benchmarks"]["dimensions"]["quality"] == 0.7161
    assert set(request_paths) == {"/api/models", "/v1/models", "/api/config"}
    serialized = json.dumps(payload)
    assert "apiKey" not in serialized
    assert "last_error" not in serialized


def test_frontier_intelligence_endpoint_is_candidate_only_and_safe(model_card_server):
    server_url, request_paths = model_card_server
    before = len(request_paths)
    with urllib.request.urlopen(f"{server_url}/api/frontier-intelligence", timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
        cache_control = response.headers.get("Cache-Control")

    assert response.status == 200
    assert cache_control == "no-store"
    assert payload["schema_version"] == 1
    # The fixture is intentionally checked into source control, so its mtime
    # may age between test runs; validity and candidate-only semantics matter
    # here, while the Node unit test covers a fresh timestamp deterministically.
    assert payload["state"] in {"fresh", "stale"}
    assert payload["candidate_count"] == 2
    assert payload["baseline_established_count"] == 1
    assert payload["providers"] == [
        {"provider": "nvidia", "candidate_count": 1},
        {"provider": "openrouter", "candidate_count": 1},
    ]
    assert payload["policy"] == {
        "candidate_only": True,
        "automatic_registration": False,
        "automatic_routing": False,
        "automatic_probing": False,
    }
    assert payload["review_contract"] == {
        "mode": "operator_review_only",
        "admission_state": "awaiting_operator_review",
        "required_evidence": [
            "confirm provider entitlement and endpoint contract",
            "perform one explicit bounded health probe after review",
            "attach compatible benchmark evidence or retain UNSCORED",
        ],
        "promotion": "separate explicit operator change; this endpoint cannot register, route, or probe a candidate",
    }
    assert payload["review_queue"] == {
        "total_candidates": 2,
        "emitted_candidates": 2,
        "truncated": False,
        "items": [
            {
                "candidate_id": "frontier-discovery::nvidia::z-ai%2Fglm-5.2",
                "provider": "nvidia",
                "model_id": "z-ai/glm-5.2",
                "discovery_class": "baseline_established",
                "review_state": "awaiting_operator_review",
                "registration_state": "not_registered",
                "routing_state": "not_routable",
                "evidence_state": "catalogue_delta_only",
            },
            {
                "candidate_id": "frontier-discovery::openrouter::example%2Ffrontier-free",
                "provider": "openrouter",
                "model_id": "example/frontier-free",
                "discovery_class": "catalogue_delta",
                "review_state": "awaiting_operator_review",
                "registration_state": "not_registered",
                "routing_state": "not_routable",
                "evidence_state": "catalogue_delta_only",
            },
        ],
    }
    serialized = json.dumps(payload)
    assert "must-not-leak" not in serialized
    assert "source_metadata" not in serialized
    assert "baseline_established:missing" not in serialized
    assert len(request_paths) == before
