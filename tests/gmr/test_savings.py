"""tests/gmr/test_savings.py — SavingsTracker and TokenSavings tests"""
import json
import pytest

from nexus_os.gmr.savings import SavingsTracker, TokenSavings


class TestSavingsTracker:
    def test_initial_state(self):
        tracker = SavingsTracker()
        assert tracker.total_tokens_used == 0
        assert tracker.total_tokens_saved == 0
        assert tracker.total_cost_saved == 0.0
        assert tracker.savings == []

    def test_record_single_saving(self):
        tracker = SavingsTracker()
        tracker.record(
            task_type="code", primary="model-a", fallback="model-b",
            tokens_used=1000, tokens_saved=500, cost_saved=0.05, reason="test",
        )
        assert len(tracker.savings) == 1
        assert tracker.total_tokens_used == 1000
        assert tracker.total_tokens_saved == 500
        assert tracker.total_cost_saved == 0.05

    def test_record_multiple_savings_accumulate(self):
        tracker = SavingsTracker()
        tracker.record("code", "a", "b", 1000, 500, 0.05, "r1")
        tracker.record("research", "c", "d", 2000, 800, 0.10, "r2")
        assert tracker.total_tokens_used == 3000
        assert tracker.total_tokens_saved == 1300
        assert abs(tracker.total_cost_saved - 0.15) < 1e-9

    def test_get_report_structure(self):
        tracker = SavingsTracker()
        tracker.record("code", "a", "b", 1000, 500, 0.05, "r1")
        report = tracker.get_report()
        assert "timestamp" in report
        assert "summary" in report
        assert "recent" in report
        assert report["summary"]["total_tokens_used"] == 1000
        assert report["summary"]["total_tokens_saved"] == 500

    def test_savings_rate_calculation(self):
        tracker = SavingsTracker()
        tracker.record("code", "a", "b", 1000, 500, 0.05, "r1")
        report = tracker.get_report()
        assert report["summary"]["savings_rate"] == 50.0

    def test_savings_rate_zero_when_no_usage(self):
        tracker = SavingsTracker()
        report = tracker.get_report()
        assert report["summary"]["savings_rate"] == 0.0

    def test_recent_limited_to_10(self):
        tracker = SavingsTracker()
        for i in range(15):
            tracker.record("code", "a", "b", 100, 50, 0.01, f"r{i}")
        report = tracker.get_report()
        assert len(report["recent"]) == 10

    def test_save_report_to_file(self, tmp_path):
        tracker = SavingsTracker()
        tracker.record("code", "a", "b", 1000, 500, 0.05, "r1")
        path = str(tmp_path / "report.json")
        tracker.save_report(path)
        with open(path) as f:
            data = json.load(f)
        assert data["summary"]["total_tokens_used"] == 1000


class TestTokenSavings:
    def test_dataclass_fields(self):
        ts = TokenSavings(
            timestamp="2024-01-01T00:00:00Z", task_type="code",
            primary_model="a", fallback_model="b",
            tokens_used=100, tokens_saved=50, cost_saved=0.01, reason="test",
        )
        assert ts.task_type == "code"
        assert ts.tokens_used == 100
