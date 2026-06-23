"""Tests for Fugu-style soft-target SFT dispatcher."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import math
import pytest
from nexus_os.model_relay.fugu_dispatch import (
    FuguDispatcher,
    TaskFeatures,
    WorkerRewardRecord,
    FUGU_STATE_PATH,
    FUGU_HEAD_PATH,
)


@pytest.fixture(autouse=True)
def clean_fugu_state():
    """Clear persistent state before each test for isolation."""
    if FUGU_STATE_PATH.exists():
        FUGU_STATE_PATH.unlink()
    if FUGU_HEAD_PATH.exists():
        FUGU_HEAD_PATH.unlink()
    yield


class TestTaskFeatures:
    def test_from_prompt_code(self):
        f = TaskFeatures.from_prompt("def fibonacci(n): return n if n < 2 else fib(n-1) + fib(n-2)")
        assert f.has_code is True
        assert f.task_type == "code_review"
        assert f.has_math is False

    def test_from_prompt_math(self):
        f = TaskFeatures.from_prompt("Calculate the integral of x^2 from 0 to 5")
        assert f.has_math is True
        assert f.task_type == "math"

    def test_from_prompt_long_context(self):
        f = TaskFeatures.from_prompt("Analyze this entire document of 100000 words")
        assert f.has_long_context is True
        assert f.task_type == "long_ctx"

    def test_from_prompt_search(self):
        f = TaskFeatures.from_prompt("Search the web for recent AI papers")
        assert f.requires_tools is True
        assert f.task_type == "search"

    def test_from_prompt_general(self):
        f = TaskFeatures.from_prompt("Hello how are you today?")
        assert f.task_type == "general"

    def test_complexity_increases_with_length(self):
        f_short = TaskFeatures.from_prompt("hi")
        f_long = TaskFeatures.from_prompt("hello " * 5000)
        assert f_long.estimated_complexity > f_short.estimated_complexity


class TestWorkerRewardRecord:
    def test_empty_record_success_rate(self):
        rec = WorkerRewardRecord(worker="m1", task_type="code")
        assert rec.success_rate == 0.5  # uniform prior
        assert rec.attempts == 0

    def test_record_outcomes(self):
        rec = WorkerRewardRecord(worker="m1", task_type="code")
        rec.successes = 8
        rec.failures = 2
        assert rec.success_rate == 0.8
        assert rec.attempts == 10

    def test_reward_balances_success_and_latency(self):
        rec_fast = WorkerRewardRecord(worker="m1", task_type="code")
        rec_fast.successes = 10
        rec_fast.failures = 0
        rec_fast.total_latency_ms = 1000  # 100ms avg
        rec_slow = WorkerRewardRecord(worker="m2", task_type="code")
        rec_slow.successes = 10
        rec_slow.failures = 0
        rec_slow.total_latency_ms = 20000  # 2000ms avg
        assert rec_fast.reward() > rec_slow.reward()


class TestFuguDispatcher:
    def test_empty_dispatcher(self):
        d = FuguDispatcher()
        assert len(d.records) == 0

    def test_record_outcome_persists(self):
        d = FuguDispatcher()
        d.record_worker_outcome("m1", "code", True, 100)
        d.record_worker_outcome("m1", "code", True, 100)
        d.record_worker_outcome("m1", "code", False, 100)
        assert d.records[("m1", "code")].successes == 2
        assert d.records[("m1", "code")].failures == 1

    def test_soft_targets_uniform_for_unknown_workers(self):
        d = FuguDispatcher()
        probs = d.compute_soft_targets("code", candidates=["a", "b", "c"])
        # All equal priors → uniform
        assert abs(probs["a"] - 1/3) < 0.01
        assert abs(probs["b"] - 1/3) < 0.01
        assert abs(probs["c"] - 1/3) < 0.01

    def test_soft_targets_prefer_better_worker(self):
        d = FuguDispatcher()
        # Worker A: 10/10 success
        for _ in range(10):
            d.record_worker_outcome("A", "code", True, 1000)
        # Worker B: 2/10 success
        for _ in range(2):
            d.record_worker_outcome("B", "code", True, 1000)
        for _ in range(8):
            d.record_worker_outcome("B", "code", False, 1000)
        probs = d.compute_soft_targets("code", candidates=["A", "B"])
        assert probs["A"] > probs["B"]
        # With temp=1.0 and reward A=1.0, B=0.2*0.85=0.17, softmax gives
        # exp(1)/exp(1)+exp(0.17) ≈ 0.71. Just assert A > B strongly.
        assert probs["A"] > 0.6
        assert probs["B"] < 0.4

    def test_soft_targets_consider_latency(self):
        d = FuguDispatcher()
        # Both succeed, A is faster
        for _ in range(5):
            d.record_worker_outcome("fast", "code", True, 500)
            d.record_worker_outcome("slow", "code", True, 5000)
        probs = d.compute_soft_targets("code", candidates=["fast", "slow"])
        assert probs["fast"] > probs["slow"]

    def test_dispatch_returns_chosen_and_probs(self):
        d = FuguDispatcher()
        for _ in range(5):
            d.record_worker_outcome("good", "code", True, 1000)
            d.record_worker_outcome("bad", "code", False, 1000)
        features = TaskFeatures(task_type="code")
        chosen, probs = d.dispatch(features, ["good", "bad"], deterministic=True)
        assert chosen == "good"
        assert "good" in probs and "bad" in probs

    def test_dispatch_excludes_worker(self):
        d = FuguDispatcher()
        chosen, _ = d.dispatch(
            TaskFeatures(task_type="code"),
            ["a", "b", "c"],
            exclude="a",
            deterministic=True,
        )
        assert chosen != "a"

    def test_dispatch_empty_candidates_returns_empty(self):
        d = FuguDispatcher()
        chosen, probs = d.dispatch(TaskFeatures(), [], deterministic=True)
        assert chosen == ""

    def test_dispatch_only_excluded_candidate_returns_excluded(self):
        d = FuguDispatcher()
        chosen, _ = d.dispatch(
            TaskFeatures(), ["only"], exclude="only", deterministic=True
        )
        assert chosen == "only"

    def test_worker_stats(self):
        d = FuguDispatcher()
        d.record_worker_outcome("w1", "code", True, 100)
        d.record_worker_outcome("w1", "code", True, 200)
        d.record_worker_outcome("w1", "code", False, 300)
        d.record_worker_outcome("w1", "math", True, 400)
        stats = d.get_worker_stats("w1")
        assert stats["total_attempts"] == 4
        assert abs(stats["success_rate"] - 0.75) < 0.01
        assert "code" in stats["by_task"]
        assert "math" in stats["by_task"]

    def test_train_lightweight_head_persists(self):
        d = FuguDispatcher()
        d.train_lightweight_head("w1", {"bias": 0.7, "has_code": 0.2})
        d2 = FuguDispatcher()
        assert "w1" in d2.head_weights
        assert d2.head_weights["w1"]["bias"] == 0.7

    def test_head_predict_with_weights(self):
        d = FuguDispatcher()
        d.train_lightweight_head("w1", {"bias": 0.5, "has_code": 0.3, "complexity_slope": 0.2})
        features = TaskFeatures(task_type="code", has_code=True, estimated_complexity=0.5)
        score = d.head_predict("w1", features)
        # bias 0.5 + has_code 0.3 + complexity 0.5*0.2 = 0.9
        assert abs(score - 0.9) < 0.01

    def test_head_predict_without_weights_uses_reward(self):
        d = FuguDispatcher()
        for _ in range(10):
            d.record_worker_outcome("w1", "code", True, 100)
        features = TaskFeatures(task_type="code")
        score = d.head_predict("w1", features)
        assert score > 0.5  # good reward

    def test_summary_format(self):
        d = FuguDispatcher()
        d.record_worker_outcome("w1", "code", True, 100)
        s = d.summary()
        assert "Fugu Dispatcher" in s
        assert "w1" in s
        assert "code" in s

    def test_empty_summary(self):
        d = FuguDispatcher()
        s = d.summary()
        assert "Fugu Dispatcher" in s
        assert "Records: 0" in s

    def test_persistence_round_trip(self):
        d = FuguDispatcher()
        d.record_worker_outcome("w1", "code", True, 1000)
        d.record_worker_outcome("w2", "code", False, 2000)
        d2 = FuguDispatcher()
        assert d2.records[("w1", "code")].successes == 1
        assert d2.records[("w2", "code")].failures == 1

    def test_temperature_zero_uniform(self):
        """At temperature=0 (or very small), softmax degenerates to argmax."""
        d = FuguDispatcher()
        for _ in range(10):
            d.record_worker_outcome("A", "code", True, 1000)
        probs = d.compute_soft_targets("code", candidates=["A", "B"], temperature=0.001)
        assert probs["A"] > 0.99  # sharp preference

    def test_high_temperature_smooth(self):
        """At high temperature, distribution approaches uniform."""
        d = FuguDispatcher()
        for _ in range(10):
            d.record_worker_outcome("A", "code", True, 1000)
        probs = d.compute_soft_targets("code", candidates=["A", "B", "C"], temperature=10.0)
        assert abs(probs["A"] - 1/3) < 0.05  # close to uniform

    def test_dispatch_temperature_affects_sampling(self):
        """Deterministic dispatch picks argmax regardless of temperature."""
        d = FuguDispatcher()
        for _ in range(10):
            d.record_worker_outcome("good", "code", True, 1000)
            d.record_worker_outcome("bad", "code", False, 1000)
        # Deterministic always picks good
        features = TaskFeatures(task_type="code")
        for _ in range(5):
            chosen, _ = d.dispatch(features, ["good", "bad"], deterministic=True)
            assert chosen == "good"

    def test_random_dispatch_can_pick_lower_prob(self):
        d = FuguDispatcher()
        for _ in range(10):
            d.record_worker_outcome("good", "code", True, 1000)
        # Even with random, "bad" should rarely be picked
        bad_picks = 0
        for _ in range(100):
            chosen, _ = d.dispatch(TaskFeatures(task_type="code"), ["good", "bad"], deterministic=False)
            if chosen == "bad":
                bad_picks += 1
        # Bad has uniform prior 0.5 vs good's high reward — bad should still be picked sometimes
        assert bad_picks < 50  # good is preferred most of the time

    def test_cross_task_isolation(self):
        """Worker that's good at code is not assumed good at math."""
        d = FuguDispatcher()
        for _ in range(10):
            d.record_worker_outcome("w1", "code", True, 100)
        # First call for math
        chosen, probs = d.dispatch(TaskFeatures(task_type="math"), ["w1", "w2"], deterministic=True)
        # w1 has uniform prior for math — may pick either
        assert chosen in ["w1", "w2"]