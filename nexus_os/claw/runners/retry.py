"""RetryMixin with AWS full-jitter exponential back-off.

Formula: delay = random.uniform(0, min(max_delay, base_delay * 2^attempt))

Respects ``retry_after`` headers from servers when available.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar

from nexus_os.claw.exceptions import RetryableError

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")
RetryableFn = Callable[P, Awaitable[R]]


class RetryMixin:
    """AWS full-jitter back-off mixin for async callables.

    Configuration is per-instance; caller may override on individual calls
    via keyword arguments prefixed with ``retry_``.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    async def with_retry(
        self,
        fn: RetryableFn[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        """Execute *fn* with automatic retry on ``RetryableError``.

        Per-call overrides are extracted from ``**kwargs``:
          - ``retry_max_attempts``
          - ``retry_base_delay``
          - ``retry_max_delay``
        """
        attempts = kwargs.pop("retry_max_attempts", self.max_attempts)
        base = kwargs.pop("retry_base_delay", self.base_delay)
        mx = kwargs.pop("retry_max_delay", self.max_delay)

        last_exc: RetryableError | None = None
        for attempt in range(attempts):
            try:
                return await fn(*args, **kwargs)
            except RetryableError as exc:
                last_exc = exc
                if attempt == attempts - 1:
                    raise

                retry_after = exc.context.get("retry_after")
                if retry_after is not None and isinstance(retry_after, (int, float)):
                    delay = float(retry_after)
                else:
                    cap = min(mx, base * (2**attempt))
                    delay = random.uniform(0, cap)

                logger.info(
                    "RetryableError (attempt %d/%d): sleeping %.2fs — %s",
                    attempt + 1,
                    attempts,
                    delay,
                    exc.message,
                )
                await asyncio.sleep(delay)

        raise AssertionError("unreachable")  # nosec

    def deferred(
        self,
        fn: RetryableFn[P, R],
        *,
        max_attempts: int | None = None,
        base_delay: float | None = None,
        max_delay: float | None = None,
    ) -> Callable[P, Awaitable[R]]:
        """Return a bound wrapper binding overrides for later calls."""
        overrides: dict[str, Any] = {}
        if max_attempts is not None:
            overrides["retry_max_attempts"] = max_attempts
        if base_delay is not None:
            overrides["retry_base_delay"] = base_delay
        if max_delay is not None:
            overrides["retry_max_delay"] = max_delay

        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            merged = {**overrides, **kwargs}
            return await self.with_retry(fn, *args, **merged)

        return wrapper


class NoRetry(RetryMixin):
    """A retry policy that passes through without any retry logic."""

    def __init__(self) -> None:
        super().__init__(max_attempts=1)

    async def with_retry(
        self,
        fn: RetryableFn[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        return await fn(*args, **kwargs)
