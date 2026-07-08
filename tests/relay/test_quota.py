"""Tests for relay quota guards: SlidingWindowRPMTracker and context-fit helpers.

Covers audit findings on the Phase 7 relay resilience work:
- proactive backoff at 80% utilization (NIM defaults to conservative 8 RPM)
- hard stop with retry hint when the window is exhausted
- context-window clamping / hard failover budgets
"""
from __future__ import annotations

import pytest

from nexus_os.relay.quota import (
    CONTEXT_SAFETY_MARGIN,
    KNOWN_CONTEXT_LIMITS,
    SlidingWindowRPMTracker,
    check_context_fit,
    max_completion_budget,
)


class TestSlidingWindowRPMTracker:
    def test_default_tracker_uses_conservative_nim_limit(self):
        tracker = SlidingWindowRPMTracker()
        assert tracker.state()["rpm_limit"] == 8

    def test_fresh_tracker_allows_immediately(self):
        tracker = SlidingWindowRPMTracker(rpm_limit=40)
        allowed, backoff, util = tracker.can_proceed()
        assert allowed is True
        assert backoff == 0.0
        assert util == 0.0

    def test_below_threshold_no_backoff(self):
        tracker = SlidingWindowRPMTracker(rpm_limit=10, backoff_threshold=0.8)
        for _ in range(7):  # 70% < 80%
            tracker.record_request()
        allowed, backoff, util = tracker.can_proceed()
        assert allowed is True
        assert backoff == 0.0
        assert util == pytest.approx(0.7)

    def test_at_threshold_proactive_backoff(self):
        tracker = SlidingWindowRPMTracker(rpm_limit=10, backoff_threshold=0.8)
        for _ in range(8):  # exactly 80%
            tracker.record_request()
        allowed, backoff, util = tracker.can_proceed()
        assert allowed is True
        assert backoff > 0.0
        assert util == pytest.approx(0.8)

    def test_exhausted_window_blocks_with_wait(self):
        tracker = SlidingWindowRPMTracker(rpm_limit=5, window_seconds=60.0)
        for _ in range(5):
            tracker.record_request()
        allowed, backoff, util = tracker.can_proceed()
        assert allowed is False
        assert 0.0 < backoff <= 60.0
        assert util >= 1.0

    def test_window_pruning_frees_slots(self, monkeypatch):
        tracker = SlidingWindowRPMTracker(rpm_limit=5, window_seconds=60.0)
        base = 1_000_000.0
        now = {"t": base}
        monkeypatch.setattr("nexus_os.relay.quota.time.time", lambda: now["t"])
        for _ in range(5):
            tracker.record_request()
        allowed, _, _ = tracker.can_proceed()
        assert allowed is False
        now["t"] = base + 61.0  # window rolls over
        allowed, backoff, util = tracker.can_proceed()
        assert allowed is True
        assert backoff == 0.0
        assert util == 0.0

    def test_state_reporting(self):
        tracker = SlidingWindowRPMTracker(rpm_limit=40)
        tracker.record_request()
        tracker.update_from_headers(remaining=38)
        state = tracker.state()
        assert state["current_count"] == 1
        assert state["rpm_limit"] == 40
        assert state["header_remaining"] == 38
        assert state["backoff_active"] is False


class TestContextFit:
    MODEL = "z-ai/glm-5.1"  # 202,752 window (the live-observed NIM failure mode)
    LIMIT = KNOWN_CONTEXT_LIMITS[MODEL]

    def test_unknown_model_never_clamped(self):
        assert max_completion_budget("some/unknown-model", 10**9) is None
        fits, advice = check_context_fit("some/unknown-model", 10**9, 10**9)
        assert fits is True
        assert advice == ""

    def test_fits_comfortably(self):
        fits, advice = check_context_fit(self.MODEL, 1000, 512)
        assert fits is True
        assert advice == ""

    def test_completion_budget_clamped(self):
        # The live incident: compaction leaves ~173K input, 32K completion
        # pushes the total over the 202,752 window.
        input_tokens = 173_000
        fits, advice = check_context_fit(self.MODEL, input_tokens, 32_000)
        assert fits is False
        assert "Reduce completion budget" in advice
        cap = max_completion_budget(self.MODEL, input_tokens)
        assert cap == self.LIMIT - input_tokens - CONTEXT_SAFETY_MARGIN
        assert input_tokens + cap < self.LIMIT

    def test_input_alone_overflows(self):
        input_tokens = self.LIMIT + 1
        fits, advice = check_context_fit(self.MODEL, input_tokens, 1)
        assert fits is False
        assert "Fail over" in advice
        assert max_completion_budget(self.MODEL, input_tokens) == 0

    def test_budget_never_negative(self):
        assert max_completion_budget(self.MODEL, self.LIMIT * 2) == 0
