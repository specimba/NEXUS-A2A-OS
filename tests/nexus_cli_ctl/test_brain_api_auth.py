"""Tests for Brain API auth and rate limiting."""
import time
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.api.brain_api import SimpleRateLimiter, rate_limiter


class TestSimpleRateLimiter:
    def test_allows_normal_traffic(self):
        limiter = SimpleRateLimiter(max_requests=5, window_seconds=60)
        for i in range(5):
            assert limiter.is_allowed("client1") is True

    def test_blocks_excess_traffic(self):
        limiter = SimpleRateLimiter(max_requests=3, window_seconds=60)
        for i in range(3):
            limiter.is_allowed("client1")
        assert limiter.is_allowed("client1") is False

    def test_separate_clients_independent(self):
        limiter = SimpleRateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("client1")
        limiter.is_allowed("client1")
        assert limiter.is_allowed("client2") is True
        assert limiter.is_allowed("client1") is False

    def test_remaining_count(self):
        limiter = SimpleRateLimiter(max_requests=10, window_seconds=60)
        assert limiter.remaining("client1") == 10
        limiter.is_allowed("client1")
        assert limiter.remaining("client1") == 9

    def test_window_expiry(self):
        limiter = SimpleRateLimiter(max_requests=2, window_seconds=0.05)
        limiter.is_allowed("client1")
        limiter.is_allowed("client1")
        assert limiter.is_allowed("client1") is False
        time.sleep(0.1)
        assert limiter.is_allowed("client1") is True

    def test_global_limiter_instance(self):
        assert rate_limiter is not None
        assert rate_limiter.max_requests > 0


class TestBrainAPIAuth:
    """Audit CRITICAL: reads accepted anonymous, mutations accepted any
    'nexus-'-prefixed key. Both now verify the real shared secret."""

    def test_verify_api_key_rejects_anonymous(self, monkeypatch):
        monkeypatch.setenv("NEXUS_BRAIN_TOKEN", "secret-token")
        from nexus_os.api.brain_api import verify_api_key
        from fastapi import HTTPException
        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(verify_api_key(None))
        assert exc_info.value.status_code == 401

    def test_require_auth_rejects_missing(self, monkeypatch):
        monkeypatch.setenv("NEXUS_BRAIN_TOKEN", "secret-token")
        from nexus_os.api.brain_api import require_auth
        from fastapi import HTTPException
        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(require_auth(None))
        assert exc_info.value.status_code == 401

    def test_require_auth_rejects_guessable_nexus_prefix(self, monkeypatch):
        monkeypatch.setenv("NEXUS_BRAIN_TOKEN", "secret-token")
        from nexus_os.api.brain_api import require_auth
        from fastapi import HTTPException
        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(require_auth("nexus-anything"))
        assert exc_info.value.status_code == 401

    def test_correct_token_accepted_for_read_and_mutation(self, monkeypatch):
        monkeypatch.setenv("NEXUS_BRAIN_TOKEN", "secret-token")
        from nexus_os.api.brain_api import require_auth, verify_api_key
        import asyncio
        assert asyncio.run(verify_api_key("secret-token")) == "authenticated"
        assert asyncio.run(require_auth("secret-token")) == "authenticated"

    def test_token_autogenerates_local_file(self, tmp_path, monkeypatch):
        import nexus_os.api.brain_api as brain_api
        monkeypatch.delenv("NEXUS_BRAIN_TOKEN", raising=False)
        monkeypatch.setattr(brain_api, "BRAIN_TOKEN_FILE", tmp_path / ".brain_api_token")
        t1 = brain_api.get_brain_api_token()
        t2 = brain_api.get_brain_api_token()
        assert t1 == t2 and len(t1) >= 32


class TestBrainAPIServerBinding:
    def test_direct_runner_defaults_to_loopback(self, monkeypatch):
        import nexus_os.api.brain_api as brain_api
        import uvicorn

        calls = []
        monkeypatch.delenv(
            "NEXUS_UNSAFE_ALLOW_NON_LOOPBACK_BRAIN_BIND",
            raising=False,
        )
        monkeypatch.setattr(
            uvicorn,
            "run",
            lambda app, *, host, port: calls.append((app, host, port)),
        )

        brain_api.run_brain_api()

        assert calls == [(brain_api.brain_app, "127.0.0.1", 7352)]

    def test_non_loopback_bind_fails_closed_without_unsafe_opt_in(self, monkeypatch):
        import nexus_os.api.brain_api as brain_api
        import uvicorn

        monkeypatch.delenv(
            "NEXUS_UNSAFE_ALLOW_NON_LOOPBACK_BRAIN_BIND",
            raising=False,
        )
        run_called = False

        def fake_run(*args, **kwargs):
            nonlocal run_called
            run_called = True

        monkeypatch.setattr(uvicorn, "run", fake_run)

        with pytest.raises(
            RuntimeError,
            match="NEXUS_UNSAFE_ALLOW_NON_LOOPBACK_BRAIN_BIND=1",
        ):
            brain_api.run_brain_api(host="0.0.0.0")
        assert run_called is False

    def test_non_loopback_bind_requires_exact_unsafe_opt_in(self, monkeypatch):
        import nexus_os.api.brain_api as brain_api
        import uvicorn

        calls = []
        monkeypatch.setenv(
            "NEXUS_UNSAFE_ALLOW_NON_LOOPBACK_BRAIN_BIND",
            "1",
        )
        monkeypatch.setattr(
            uvicorn,
            "run",
            lambda app, *, host, port: calls.append((app, host, port)),
        )

        brain_api.run_brain_api(host="0.0.0.0", port=7352)

        assert calls == [(brain_api.brain_app, "0.0.0.0", 7352)]


class TestBrainAPIWebSocketAuth:
    def test_websocket_rejects_anonymous_before_accept(self, monkeypatch):
        import nexus_os.api.brain_api as brain_api

        monkeypatch.setenv("NEXUS_BRAIN_TOKEN", "secret-token")

        with TestClient(brain_api.brain_app) as client:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect("/ws"):
                    pass

        assert exc_info.value.code == 1008

    def test_websocket_rejects_credentials_in_query_string(self, monkeypatch):
        import nexus_os.api.brain_api as brain_api

        monkeypatch.setenv("NEXUS_BRAIN_TOKEN", "secret-token")

        with TestClient(brain_api.brain_app) as client:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect("/ws?token=secret-token"):
                    pass

        assert exc_info.value.code == 1008

    @pytest.mark.parametrize(
        ("path", "headers"),
        [
            ("/ws", {"X-Api-Key": "secret-token"}),
            ("/ws", {"Authorization": "Bearer secret-token"}),
        ],
    )
    def test_websocket_accepts_existing_brain_credentials(
        self,
        monkeypatch,
        path,
        headers,
    ):
        import nexus_os.api.brain_api as brain_api

        monkeypatch.setenv("NEXUS_BRAIN_TOKEN", "secret-token")

        with TestClient(brain_api.brain_app) as client:
            with client.websocket_connect(path, headers=headers) as websocket:
                message = websocket.receive_json()

        assert message["type"] == "connected"
        assert message["connection_id"].startswith("ws-")
