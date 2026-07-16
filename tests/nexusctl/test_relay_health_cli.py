"""Read-only contract tests for ``nexusctl relay-health``."""
from __future__ import annotations

import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from nexusctl.cli import main
from nexusctl.relay_health import _offer_projection, _sampler_projection


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_health_server() -> tuple[ThreadingHTTPServer, list[tuple[str, str]]]:
    requests: list[tuple[str, str]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
            requests.append((self.command, self.path))
            payload: dict[str, object]
            if self.path == "/api/health-sampler":
                payload = {
                    "policy": "bounded_provider_aware_canary_v1",
                    "globalLimitPerWindow": 6,
                    "windowSeconds": 3600,
                    "minimumSpacingSeconds": 600,
                    "usedInWindow": 2,
                    "remainingInWindow": 4,
                    "persistedObservations": 3,
                    "activePersistedCooldowns": 1,
                    "activePersistedAccessBlocks": 0,
                    # The sampler most recently scheduled a retired route,
                    # but the arena has a newer successful observation for
                    # the canonical GLM route.  These must remain distinct.
                    "lastObservedAt": "2026-07-15T10:05:00.000Z",
                    "nextEligibleAt": "2026-07-15T10:10:00.000Z",
                    "lastEvent": {
                        "at": 1_784_106_000_000,
                        "providerKey": "nvidia",
                        "modelId": "z-ai/glm5",
                        "source": "scheduled",
                        "outcome": "failed",
                        "status": 410,
                        "latencyMs": 369,
                        "accountKey": "must-not-leak",
                    },
                }
            elif self.path == "/api/models":
                payload = {
                    "models": [
                        {
                            "providerKey": "nvidia",
                            "modelId": "z-ai/glm-5.2",
                            "status": "down",
                            "httpCode": "429",
                            "isRateLimited": True,
                            "lastPingAt": "2026-07-15T10:07:00.000Z",
                            # The sampler count cannot be attributed to this
                            # offer without a route-level expiry in /api/models.
                            "cooldownUntil": None,
                            "lastError": "must-not-leak",
                        },
                        {
                            "providerKey": "openai-compatible:mistral",
                            "modelId": "labs-leanstral-1-5-1",
                            "status": "pending",
                        },
                    ]
                }
            elif self.path == "/api/model-cards":
                payload = {
                    "models": [
                        {
                            "model_id": "z-ai/glm-5.2",
                            "provider_key": "nvidia",
                            "runtime": {"last_error": "must-not-leak"},
                            "health": {
                                "state": "healthy",
                                "observed": True,
                                "fresh": True,
                                "last_checked_at": "2026-07-15T10:04:00.000Z",
                                "latency_ms": 941,
                            },
                        },
                        {
                            "model_id": "labs-leanstral-1-5-1",
                            "provider_key": "openai-compatible:mistral",
                            "health": {
                                "state": "stale",
                                "observed": True,
                                "fresh": False,
                                "last_checked_at": "2026-07-15T10:06:00.000Z",
                                "latency_ms": 942,
                            },
                        },
                        {
                            "model_id": "minimax-m3",
                            "provider_key": "nvidia",
                            "health": {"state": "unverified", "observed": False, "fresh": False},
                        },
                        {
                            "model_id": "not-fresh",
                            "provider_key": "nvidia",
                            "health": {"state": "healthy", "observed": True, "fresh": False},
                        },
                        {
                            "model_id": "z-ai/glm5",
                            "provider_key": "nvidia",
                            "health": {
                                "state": "unavailable",
                                "observed": True,
                                "fresh": True,
                                "last_checked_at": "2026-07-15T10:03:00.000Z",
                                "latency_ms": 369,
                            },
                        },
                    ]
                }
            else:
                self.send_error(404)
                return

            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", _free_port()), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, requests


def test_relay_health_reports_only_safe_live_fields_and_never_infers(capsys, monkeypatch):
    server, requests = _start_health_server()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "nexusctl",
                "relay-health",
                "--relay-url",
                base_url,
                "--arena-url",
                base_url,
            ],
        )

        assert main() == 0
        payload = json.loads(capsys.readouterr().out)
    finally:
        server.shutdown()
        server.server_close()

    assert payload["status"] == "ok"
    assert payload["read_only"] is True
    assert payload["provider_inference"] is False
    assert payload["modelrelay"]["sampler"]["remaining_in_window"] == 4
    assert payload["modelrelay"]["sampler"]["latest_event"] == {
        "at": "2026-07-15T09:00:00+00:00",
        "provider_key": "nvidia",
        "model_id": "z-ai/glm5",
        "source": "scheduled",
        "outcome": "failed",
        "http_status": 410,
        "latency_ms": 369,
    }
    assert payload["modelrelay"]["sampler"]["last_sampler_observation_at"] == "2026-07-15T10:05:00+00:00"
    assert payload["modelrelay"]["sampler"]["latest_scheduled_canary_event"] == {
        "at": "2026-07-15T09:00:00+00:00",
        "provider_key": "nvidia",
        "model_id": "z-ai/glm5",
        "source": "scheduled",
        "outcome": "failed",
        "http_status": 410,
        "latency_ms": 369,
    }
    assert payload["modelrelay"]["offers"] == {
        "total": 2,
        "providers": 2,
        "status_counts": {"down": 1, "pending": 1},
        "rate_limit_evidence_total": 1,
        "rate_limit_evidence": [
            {
                "offer_id": "nvidia/z-ai/glm-5.2",
                "provider_key": "nvidia",
                "model_id": "z-ai/glm-5.2",
                "failure_class": "rate_limited",
                "http_status": 429,
                "observed_at": "2026-07-15T10:07:00+00:00",
                "cooldown_active": False,
                "cooldown_expires_at": None,
                "cooldown_remaining_seconds": None,
            }
        ],
    }
    assert payload["model_arena"]["summary"] == {
        "catalogue_offers": 5,
        "fresh_healthy": 1,
        "stale": 1,
        "unverified": 1,
        "unavailable": 1,
        "rate_limited": 0,
    }
    assert payload["model_arena"]["fresh_healthy_offers"] == [
        {
            "offer_id": "nvidia/z-ai/glm-5.2",
            "provider_key": "nvidia",
            "model_id": "z-ai/glm-5.2",
            "last_checked_at": "2026-07-15T10:04:00+00:00",
            "latency_ms": 941,
        }
    ]
    assert payload["model_arena"]["latest_observed_healthy_evidence"] == {
        "offer_id": "nvidia/z-ai/glm-5.2",
        "provider_key": "nvidia",
        "model_id": "z-ai/glm-5.2",
        "state": "healthy",
        "observed": True,
        "fresh": True,
        "last_checked_at": "2026-07-15T10:04:00+00:00",
        "latency_ms": 941,
    }
    assert payload["model_arena"]["latest_observed_unhealthy_evidence"] == {
        "offer_id": "nvidia/z-ai/glm5",
        "provider_key": "nvidia",
        "model_id": "z-ai/glm5",
        "state": "unavailable",
        "observed": True,
        "fresh": True,
        "last_checked_at": "2026-07-15T10:03:00+00:00",
        "latency_ms": 369,
    }
    assert {path for _method, path in requests} == {
        "/api/health-sampler",
        "/api/models",
        "/api/model-cards",
    }
    assert {method for method, _path in requests} == {"GET"}
    assert "must-not-leak" not in json.dumps(payload)


def test_relay_health_only_labels_scheduled_sampler_events_as_canaries():
    projection = _sampler_projection(
        {
            "lastEvent": {
                "at": "2026-07-15T10:00:00.000Z",
                "providerKey": "nvidia",
                "modelId": "z-ai/glm-5.2",
                "source": "manual",
                "outcome": "success",
                "status": 200,
                "latencyMs": 941,
            }
        }
    )

    assert projection["latest_event"]["source"] == "manual"
    assert projection["latest_scheduled_canary_event"] is None


def test_relay_health_exposes_an_explicit_offer_cooldown_without_inferring_one():
    projection = _offer_projection(
        {
            "models": [
                {
                    "providerKey": "nvidia",
                    "modelId": "z-ai/glm-5.2",
                    "status": "down",
                    "httpCode": "429",
                    "lastPingAt": "2026-07-15T10:00:00.000Z",
                    "cooldownUntil": "2099-01-01T00:00:00.000Z",
                },
                {
                    "providerKey": "nvidia",
                    "modelId": "z-ai/glm5",
                    "status": "down",
                    "httpCode": "410",
                    "lastPingAt": "2026-07-15T10:01:00.000Z",
                },
            ]
        }
    )

    assert projection is not None
    assert projection["rate_limit_evidence_total"] == 1
    evidence = projection["rate_limit_evidence"][0]
    assert evidence["offer_id"] == "nvidia/z-ai/glm-5.2"
    assert evidence["cooldown_active"] is True
    assert evidence["cooldown_expires_at"] == "2099-01-01T00:00:00+00:00"
    assert evidence["cooldown_remaining_seconds"] > 0
    assert "z-ai/glm5" not in json.dumps(projection)


def test_relay_health_fails_closed_when_contract_endpoints_are_unreachable(capsys, monkeypatch):
    dead_url = f"http://127.0.0.1:{_free_port()}"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "nexusctl",
            "relay-health",
            "--relay-url",
            dead_url,
            "--arena-url",
            dead_url,
            "--timeout",
            "0.1",
        ],
    )

    assert main() == 2
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "unavailable"
    assert payload["modelrelay"]["reachable"] is False
    assert payload["model_arena"]["reachable"] is False
    assert payload["modelrelay"]["errors"] == {
        "sampler": "url_unreachable",
        "models": "url_unreachable",
    }
    assert payload["model_arena"]["errors"] == {"model_cards": "url_unreachable"}


def test_relay_health_rejects_non_loopback_targets_without_requesting_them(capsys, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "nexusctl",
            "relay-health",
            "--relay-url",
            "https://example.invalid",
            "--arena-url",
            "https://example.invalid",
        ],
    )

    assert main() == 2
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "unavailable"
    assert payload["modelrelay"]["errors"] == {
        "sampler": "unsafe_base_url",
        "models": "unsafe_base_url",
    }
    assert payload["model_arena"]["errors"] == {"model_cards": "unsafe_base_url"}
