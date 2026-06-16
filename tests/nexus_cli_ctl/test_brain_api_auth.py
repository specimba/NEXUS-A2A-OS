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
    def test_verify_api_key_allows_anonymous(self):
        from nexus_os.api.brain_api import verify_api_key
        import asyncio
        result = asyncio.run(verify_api_key(None))
        assert result == "anonymous"

    def test_require_auth_rejects_missing(self):
        from nexus_os.api.brain_api import require_auth
        from fastapi import HTTPException
        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(require_auth(None))
        assert exc_info.value.status_code == 401

    def test_require_auth_accepts_nexus_prefix(self):
        from nexus_os.api.brain_api import require_auth
        import asyncio
        result = asyncio.run(require_auth("nexus-test-key"))
        assert result == "nexus-test-key"
