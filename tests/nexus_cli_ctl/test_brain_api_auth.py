"""Tests for Brain API auth and rate limiting."""
import time
import sys
from pathlib import Path

import pytest

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
