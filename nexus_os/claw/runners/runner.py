"""Parallel task execution runner for NEXUSCLAW.

Supports concurrent batch execution with configurable concurrency limits,
result aggregation, and partial failure handling.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, TypeVar

from nexus_os.claw.runners.retry import RetryMixin

logger = logging.getLogger(__name__)

T = TypeVar("T")
TaskFn = Callable[..., Awaitable[T]]


class BatchResult:
    """Collects results from a batch of parallel tasks."""

    def __init__(self, tasks: int) -> None:
        self._total = tasks
        self._results: dict[int, Any] = {}
        self._errors: dict[int, Exception] = {}

    def record(self, index: int, result: Any) -> None:
        self._results[index] = result

    def record_error(self, index: int, error: Exception) -> None:
        self._errors[index] = error

    @property
    def success_count(self) -> int:
        return len(self._results)

    @property
    def failure_count(self) -> int:
        return len(self._errors)

    @property
    def total(self) -> int:
        return self._total

    @property
    def all_successful(self) -> bool:
        return len(self._errors) == 0 and len(self._results) == self._total

    @property
    def results(self) -> dict[int, Any]:
        return dict(self._results)

    @property
    def errors(self) -> dict[int, Exception]:
        return dict(self._errors)


class ParallelRunner(RetryMixin):
    """Execute multiple tasks concurrently with a semaphore cap."""

    def __init__(
        self,
        max_concurrency: int = 3,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ) -> None:
        super().__init__(max_attempts=max_attempts, base_delay=base_delay, max_delay=max_delay)
        self.max_concurrency = max_concurrency

    @property
    def effective_concurrency(self) -> int:
        return max(1, self.max_concurrency)

    async def batch(
        self,
        tasks: list[tuple[TaskFn[Any], list[Any], dict[str, Any]]],
        *,
        max_concurrency: int | None = None,
    ) -> BatchResult:
        """Execute *tasks* with up to *max_concurrency* in parallel.

        Each task is ``(fn, args, kwargs)``. Returns a ``BatchResult``
        with per-task results and errors.
        """
        concurrency = max(1, max_concurrency or self.max_concurrency)
        semaphore = asyncio.Semaphore(concurrency)
        result = BatchResult(len(tasks))

        async def _worker(index: int, fn: TaskFn[Any], args: list[Any], kwargs: dict[str, Any]) -> None:
            async with semaphore:
                try:
                    value = await self.with_retry(fn, *args, **kwargs)
                    result.record(index, value)
                except Exception as exc:
                    result.record_error(index, exc)
                    logger.warning("Task %d failed: %s", index, exc)

        workers = [
            _worker(i, fn, args, kwargs) for i, (fn, args, kwargs) in enumerate(tasks)
        ]
        await asyncio.gather(*workers)
        return result

    async def run_single(
        self,
        fn: TaskFn[T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Convenience wrapper: run a single task through the batch path."""
        batch_result = await self.batch([(fn, list(args), kwargs)])
        if batch_result.failure_count > 0:
            raise list(batch_result.errors.values())[0]
        return batch_result.results[0]
