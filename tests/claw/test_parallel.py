"""tests/claw/test_parallel.py — Parallel runner tests."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from nexus_os.claw.exceptions import RetryableError
from nexus_os.claw.runners.runner import BatchResult, ParallelRunner


async def _ok(value: str = "ok") -> str:
    return value


async def _slow(value: str = "slow") -> str:
    import asyncio
    await asyncio.sleep(0.05)
    return value


async def _failing(value: str = "fail") -> str:
    raise ValueError(value)


async def _retryable_once() -> str:
    if not hasattr(_retryable_once, "_called"):
        _retryable_once._called = True
        raise RetryableError("transient")
    return "recovered"


class TestParallelRunner:
    @pytest.mark.asyncio
    async def test_batch_single_task(self) -> None:
        runner = ParallelRunner(max_concurrency=3)
        tasks = [(_ok, ["hello"], {})]
        result = await runner.batch(tasks)
        assert result.success_count == 1
        assert result.all_successful
        assert result.results[0] == "hello"

    @pytest.mark.asyncio
    async def test_batch_all_succeed(self) -> None:
        runner = ParallelRunner(max_concurrency=3)
        tasks = [(_ok, [f"task-{i}"], {}) for i in range(5)]
        result = await runner.batch(tasks)
        assert result.success_count == 5
        assert result.all_successful
        assert result.results[4] == "task-4"

    @pytest.mark.asyncio
    async def test_batch_max_concurrency_respected(self) -> None:
        runner = ParallelRunner(max_concurrency=2)
        tasks = [(_slow, [f"t-{i}"], {}) for i in range(10)]
        result = await runner.batch(tasks, max_concurrency=2)
        assert result.success_count == 10
        assert result.all_successful

    @pytest.mark.asyncio
    async def test_batch_partial_failure(self) -> None:
        runner = ParallelRunner(max_concurrency=3)
        tasks = [(_ok, ["good"], {}), (_failing, ["bad"], {})]
        result = await runner.batch(tasks)
        assert result.success_count == 1
        assert result.failure_count == 1
        assert not result.all_successful
        assert isinstance(result.errors[1], ValueError)

    @pytest.mark.asyncio
    async def test_batch_concurrency_at_least_1(self) -> None:
        runner = ParallelRunner(max_concurrency=0)
        assert runner.effective_concurrency >= 1

    @pytest.mark.asyncio
    async def test_batch_all_tasks_fail(self) -> None:
        runner = ParallelRunner(max_concurrency=3)
        tasks = [(_failing, [f"err-{i}"], {}) for i in range(3)]
        result = await runner.batch(tasks)
        assert result.success_count == 0
        assert result.failure_count == 3
        assert result.total == 3

    @pytest.mark.asyncio
    async def test_batch_empty_task_list(self) -> None:
        runner = ParallelRunner(max_concurrency=3)
        result = await runner.batch([])
        assert result.total == 0
        assert result.all_successful

    @pytest.mark.asyncio
    async def test_run_single_success(self) -> None:
        runner = ParallelRunner()
        result = await runner.run_single(_ok, "single")
        assert result == "single"

    @pytest.mark.asyncio
    async def test_run_single_failure(self) -> None:
        runner = ParallelRunner()
        with pytest.raises(ValueError):
            await runner.run_single(_failing, "boom")

    @pytest.mark.asyncio
    async def test_batch_result_properties(self) -> None:
        br = BatchResult(3)
        br.record(0, "a")
        br.record_error(1, ValueError("err"))
        assert br.success_count == 1
        assert br.failure_count == 1
        assert br.total == 3
        assert not br.all_successful


if __name__ == "__main__":
    pytest.main([__file__])
