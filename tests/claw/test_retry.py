"""tests/claw/test_retry.py — RetryMixin with full jitter."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from nexus_os.claw.exceptions import RetryableError
from nexus_os.claw.runners.retry import NoRetry, RetryMixin


async def _ok_fn(value: str = "ok") -> str:
    return value


async def _fail_fn(times: int = 2) -> str:
    """Fail *times* times with RetryableError, then succeed."""
    if not hasattr(_fail_fn, "_call_count"):
        _fail_fn._call_count = 0
    _fail_fn._call_count += 1
    if _fail_fn._call_count <= times:
        raise RetryableError("transient failure", http_status=429)
    return "recovered"


async def _always_fail_fn() -> str:
    raise RetryableError("always failing", http_status=503)


async def _non_retryable_fn() -> str:
    raise ValueError("not retryable")


class TestRetryMixin:
    """Container for retry mixin tests."""

    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self) -> None:
        mixin = RetryMixin(max_attempts=3)
        result = await mixin.with_retry(_ok_fn, value="hello")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_retry_success_after_failure(self) -> None:
        _fail_fn._call_count = 0  # reset
        mixin = RetryMixin(max_attempts=5, base_delay=0.01)
        result = await mixin.with_retry(_fail_fn, times=2)
        assert result == "recovered"

    @pytest.mark.asyncio
    async def test_retry_exhaustion_raises(self) -> None:
        mixin = RetryMixin(max_attempts=3, base_delay=0.01)
        with pytest.raises(RetryableError):
            await mixin.with_retry(_always_fail_fn)

    @pytest.mark.asyncio
    async def test_retry_non_retryable_propagates(self) -> None:
        mixin = RetryMixin(max_attempts=3)
        with pytest.raises(ValueError):
            await mixin.with_retry(_non_retryable_fn)

    @pytest.mark.asyncio
    async def test_retry_respects_retry_after_header(self) -> None:
        call_count = 0

        async def _respect_fn() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RetryableError("rate limited", http_status=429, retry_after=0.01)
            return "ok"

        mixin = RetryMixin(max_attempts=3, base_delay=10.0)
        result = await mixin.with_retry(_respect_fn)
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_custom_delays(self) -> None:
        mixin = RetryMixin(max_attempts=3, base_delay=10.0)
        result = await mixin.with_retry(
            _ok_fn, retry_max_attempts=1, retry_base_delay=0.0
        )
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_retry_deferred_binds_overrides(self) -> None:
        mixin = RetryMixin(max_attempts=3)
        wrapped = mixin.deferred(_ok_fn, max_attempts=1)
        result = await wrapped()
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_no_retry_passthrough(self) -> None:
        no_retry = NoRetry()
        result = await no_retry.with_retry(_ok_fn)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_no_retry_does_not_catch_retryable(self) -> None:
        no_retry = NoRetry()
        with pytest.raises(RetryableError):
            await no_retry.with_retry(_always_fail_fn)


if __name__ == "__main__":
    pytest.main([__file__])
