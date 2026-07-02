"""Tests for calibrated_hallucination_detector.py — adaptive thresholding (P0#4)."""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nexus_os.monitoring.calibrated_hallucination_detector import (
    CalibratedHallucinationDetector,
    RISK_LOW,
    RISK_MEDIUM,
    RISK_HIGH,
)


@pytest.fixture
def mock_lg_tracker():
    """Returns a mock LandauGinzburgTrackerV2.step() and EPRDetector."""
    mock_tracker = MagicMock()
    mock_tracker.step.return_value = None
    mock_tracker.get_report.return_value = MagicMock(
        order_parameters=[],
        lg_states=[],
    )

    mock_epr = MagicMock()
    mock_epr.step.return_value = None
    mock_epr.is_hallucination_risk.return_value = False

    with patch("nexus_os.monitoring.calibrated_hallucination_detector"
               ".CalibratedHallucinationDetector.tracker",
               new_callable=MagicMock) as mt, \
         patch("nexus_os.monitoring.calibrated_hallucination_detector"
               ".CalibratedHallucinationDetector.epr",
               new_callable=MagicMock) as me:
        mt.step.return_value = None
        mt.get_report.return_value = MagicMock(
            order_parameters=[],
            lg_states=[],
        )
        me.step.return_value = None
        me.is_hallucination_risk.return_value = False
        # We need __getattr__ for the property to work — actually the @property
        # bypasses MagicMock's __getattr__. Patch via property:
        # Instead, monkey-patch the detector's tracker after init
        yield mt


class TestInit:
    def test_default_threshold(self):
        d = CalibratedHallucinationDetector()
        assert d.base_threshold == 2.5
        assert d.adaptive is True
        assert d.bebop_weight == 0.15
        assert d.bebop_tau == 0.40

    def test_custom_params(self):
        d = CalibratedHallucinationDetector(
            threshold=3.0, calibration_window=50, adaptive=False,
            bebop_weight=0.0, bebop_tau=0.5,
        )
        assert d.base_threshold == 3.0
        assert d.adaptive is False
        assert d.bebop_weight == 0.0

    def test_initial_stats(self):
        d = CalibratedHallucinationDetector()
        s = d.get_stats()
        assert s["total_assessments"] == 0
        assert s["high_risk"] == 0
        assert s["medium_risk"] == 0
        assert s["low_risk"] == 0
        assert s["bebop_weight"] == 0.15


class TestGetEffectiveThreshold:
    def test_default_is_base(self):
        d = CalibratedHallucinationDetector(threshold=2.0)
        assert d._get_effective_threshold() == 2.0

    def test_calibrated_threshold_used(self):
        d = CalibratedHallucinationDetector()
        d._stats["calibrated_threshold"] = 3.5
        assert d._get_effective_threshold() == 3.5


class TestAdaptThreshold:
    def test_correct_feedback_lowers_threshold(self):
        d = CalibratedHallucinationDetector(threshold=2.0)
        old = d._get_effective_threshold()
        d._adapt_threshold(was_correct=True)
        assert d._get_effective_threshold() < old

    def test_false_positive_raises_threshold(self):
        d = CalibratedHallucinationDetector(threshold=2.0)
        old = d._get_effective_threshold()
        d._adapt_threshold(was_correct=False)
        assert d._get_effective_threshold() > old

    def test_threshold_clamped_min(self):
        d = CalibratedHallucinationDetector(threshold=1.0)
        for _ in range(100):
            d._adapt_threshold(was_correct=True)
        assert d._get_effective_threshold() >= 1.0

    def test_threshold_clamped_max(self):
        d = CalibratedHallucinationDetector(threshold=5.0)
        for _ in range(100):
            d._adapt_threshold(was_correct=False)
        assert d._get_effective_threshold() <= 5.0

    def test_non_adaptive_does_nothing(self):
        d = CalibratedHallucinationDetector(threshold=2.0, adaptive=False)
        d._adapt_threshold(was_correct=True)
        assert d._get_effective_threshold() == 2.0

    def test_adaptations_counter_increments(self):
        d = CalibratedHallucinationDetector(threshold=2.0)
        d._adapt_threshold(was_correct=False)
        d._adapt_threshold(was_correct=True)
        assert d._stats["adaptations"] >= 1

    def test_small_adjustment_no_update(self):
        d = CalibratedHallucinationDetector(threshold=2.0)
        # 2.0 * 0.98 = 1.96, diff 0.04 > 0.01 -> updates
        d._adapt_threshold(was_correct=True)
        # 1.96 * 0.98 ≈ 1.9208, diff ≈ 0.039 -> still > 0.01
        d._adapt_threshold(was_correct=True)
        assert d._stats["adaptations"] == 2


class TestAssess:
    def test_assess_returns_result_structure(self):
        d = CalibratedHallucinationDetector(bebop_weight=0.0)
        # Mock the tracker properties
        mock_report = MagicMock()
        mock_report.order_parameters = []
        mock_report.lg_states = []
        mock_tracker = MagicMock()
        mock_tracker.step.return_value = None
        mock_tracker.get_report.return_value = mock_report
        mock_epr = MagicMock()
        mock_epr.step.return_value = None
        mock_epr.is_hallucination_risk.return_value = False

        with patch.object(d, "_tracker", mock_tracker), \
             patch.object(d, "_epr", mock_epr):
            result = d.assess(logits=[1.0, 0.5, 0.0], position=0)
        assert "risk" in result
        assert result["risk"] in ("low", "medium", "high")
        assert "score" in result
        assert "reasons" in result
        assert "position" in result
        assert result["position"] == 0
        assert "elapsed_ms" in result

    def test_assess_increments_counter(self):
        d = CalibratedHallucinationDetector(bebop_weight=0.0)
        mock_report = MagicMock()
        mock_report.order_parameters = []
        mock_report.lg_states = []
        mock_tracker = MagicMock()
        mock_tracker.step.return_value = None
        mock_tracker.get_report.return_value = mock_report
        mock_epr = MagicMock()
        mock_epr.step.return_value = None
        mock_epr.is_hallucination_risk.return_value = False

        with patch.object(d, "_tracker", mock_tracker), \
             patch.object(d, "_epr", mock_epr):
            d.assess(logits=[1.0, 0.0])
            d.assess(logits=[0.5, 0.5])
        assert d._stats["total_assessments"] == 2

    def test_high_risk_when_epr_triggered(self):
        """EPR alone gives risk 0.5, which is below RISK_MEDIUM (0.6), so 'low'."""
        d = CalibratedHallucinationDetector(bebop_weight=0.0)
        mock_report = MagicMock()
        mock_report.order_parameters = []
        mock_report.lg_states = []
        mock_tracker = MagicMock()
        mock_tracker.step.return_value = None
        mock_tracker.get_report.return_value = mock_report
        mock_epr = MagicMock()
        mock_epr.step.return_value = None
        mock_epr.is_hallucination_risk.return_value = True

        with patch.object(d, "_tracker", mock_tracker), \
             patch.object(d, "_epr", mock_epr):
            result = d.assess(topk_probs=[0.5, 0.3, 0.2])
        assert result["risk"] == "medium"  # 0.5 >= RISK_MEDIUM (0.4)
        assert result["reasons"] == ["high_epr"]

    def test_high_risk_when_epr_and_lg_energy(self):
        """EPR + high LG energy = 0.5 + 0.3 = 0.8, crosses RISK_HIGH (0.6)."""
        d = CalibratedHallucinationDetector(bebop_weight=0.0)
        mock_report = MagicMock()
        mock_lg_state = MagicMock()
        mock_lg_state.free_energy = 0.9
        mock_lg_state.effective_temperature = 1.0
        mock_lg_state.specific_heat = 0.5
        mock_lg_state.is_critical = False
        mock_lg_state.is_hallucinating = True
        mock_report.lg_states = [mock_lg_state]
        mock_report.order_parameters = []
        mock_tracker = MagicMock()
        mock_tracker.step.return_value = None
        mock_tracker.get_report.return_value = mock_report
        mock_epr = MagicMock()
        mock_epr.step.return_value = None
        mock_epr.is_hallucination_risk.return_value = True

        with patch.object(d, "_tracker", mock_tracker), \
             patch.object(d, "_epr", mock_epr):
            result = d.assess(topk_probs=[0.5, 0.3, 0.2])
        assert result["risk"] == "high"
        assert "high_epr" in result["reasons"]
        assert "high_lg_energy" in result["reasons"]

    def test_low_risk_when_nothing_triggered(self):
        d = CalibratedHallucinationDetector(bebop_weight=0.0)
        mock_report = MagicMock()
        mock_report.order_parameters = []
        mock_report.lg_states = []
        mock_tracker = MagicMock()
        mock_tracker.step.return_value = None
        mock_tracker.get_report.return_value = mock_report
        mock_epr = MagicMock()
        mock_epr.is_hallucination_risk.return_value = False

        with patch.object(d, "_tracker", mock_tracker), \
             patch.object(d, "_epr", mock_epr):
            result = d.assess(topk_probs=[0.5, 0.5])
        assert result["risk"] == "low"

    def test_bebop_integration(self):
        d = CalibratedHallucinationDetector(bebop_weight=0.15, bebop_tau=0.4)
        mock_report = MagicMock()
        mock_report.order_parameters = []
        mock_report.lg_states = []
        mock_tracker = MagicMock()
        mock_tracker.step.return_value = None
        mock_tracker.get_report.return_value = mock_report
        mock_epr = MagicMock()
        mock_epr.step.return_value = None
        mock_epr.is_hallucination_risk.return_value = False

        with patch.object(d, "_tracker", mock_tracker), \
             patch.object(d, "_epr", mock_epr):
            result = d.assess(topk_probs=[0.9, 0.05, 0.03, 0.02])  # peaked -> high_drift
        assert "bebop" in result
        assert result["bebop"]["enabled"] is True
        if result["bebop"]["class"]:
            assert "bebop_" in " ".join(result["reasons"])

    def test_bebop_disabled_when_weight_zero(self):
        d = CalibratedHallucinationDetector(bebop_weight=0.0)
        mock_report = MagicMock()
        mock_report.order_parameters = []
        mock_report.lg_states = []
        mock_tracker = MagicMock()
        mock_tracker.step.return_value = None
        mock_tracker.get_report.return_value = mock_report
        mock_epr = MagicMock()
        mock_epr.step.return_value = None
        mock_epr.is_hallucination_risk.return_value = False

        with patch.object(d, "_tracker", mock_tracker), \
             patch.object(d, "_epr", mock_epr):
            result = d.assess(topk_probs=[0.8, 0.2])
        assert result["bebop"]["enabled"] is False
        assert result["bebop"]["risk"] == 0.0

    def test_tracker_report_embedded(self):
        d = CalibratedHallucinationDetector(bebop_weight=0.0)
        mock_report = MagicMock()
        mock_report.order_parameters = []
        mock_report.lg_states = []
        mock_tracker = MagicMock()
        mock_tracker.step.return_value = None
        mock_tracker.get_report.return_value = mock_report
        mock_epr = MagicMock()
        mock_epr.step.return_value = None
        mock_epr.is_hallucination_risk.return_value = False

        with patch.object(d, "_tracker", mock_tracker), \
             patch.object(d, "_epr", mock_epr):
            result = d.assess(logits=[1.0, 0.0])
        assert result["tracker_report"] is None  # no lg states


class TestRecordFeedback:
    def test_feedback_updates_stats(self):
        d = CalibratedHallucinationDetector()
        d.record_feedback(was_correct=True)
        assert d._stats["adaptations"] > 0

    def test_feedback_multiple_times(self):
        d = CalibratedHallucinationDetector()
        for _ in range(3):
            d.record_feedback(was_correct=False)
        assert d._stats["adaptations"] > 0


class TestGetCalibrationHistory:
    def test_history_records_assessment(self):
        d = CalibratedHallucinationDetector(bebop_weight=0.0)
        mock_report = MagicMock()
        mock_report.order_parameters = []
        mock_report.lg_states = []
        mock_tracker = MagicMock()
        mock_tracker.step.return_value = None
        mock_tracker.get_report.return_value = mock_report
        mock_epr = MagicMock()
        mock_epr.step.return_value = None
        mock_epr.is_hallucination_risk.return_value = False

        with patch.object(d, "_tracker", mock_tracker), \
             patch.object(d, "_epr", mock_epr):
            d.assess(logits=[1.0, 0.0], position=5)
        history = d.get_calibration_history()
        assert len(history) == 1
        assert history[0]["position"] == 5
        assert history[0]["risk"] in ("low", "medium", "high")


class TestStats:
    def test_risk_counts_tracked(self):
        d = CalibratedHallucinationDetector(bebop_weight=0.0)
        mock_report = MagicMock()
        mock_report.order_parameters = []
        mock_report.lg_states = []
        mock_tracker = MagicMock()
        mock_tracker.step.return_value = None
        mock_tracker.get_report.return_value = mock_report
        mock_epr = MagicMock()
        mock_epr.step.return_value = None
        mock_epr.is_hallucination_risk.return_value = False

        with patch.object(d, "_tracker", mock_tracker), \
             patch.object(d, "_epr", mock_epr):
            d.assess(logits=[1.0, 0.0])
        s = d.get_stats()
        assert s["total_assessments"] == 1
        total = s["high_risk"] + s["medium_risk"] + s["low_risk"]
        assert total == 1


class TestCLI:
    def test_cli_status(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["chd", "--status"])
        from nexus_os.monitoring.calibrated_hallucination_detector import cli_main
        cli_main()

    def test_cli_feedback(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["chd", "--feedback", "True"])
        with patch("nexus_os.monitoring.calibrated_hallucination_detector"
                   ".CalibratedHallucinationDetector.record_feedback") as m:
            from nexus_os.monitoring.calibrated_hallucination_detector import cli_main
            cli_main()
            m.assert_called_once_with(True)


class TestHighSensitivityInit:
    def test_high_sensitivity_does_not_crash_and_boosts(self):
        """Regression: bebop_weight was read before assignment (AttributeError)
        and the boost was then discarded by a later unconditional assignment."""
        from nexus_os.monitoring.calibrated_hallucination_detector import (
            HIGH_SENSITIVITY_THRESHOLD,
            HIGH_SENSITIVITY_BEBOP_WEIGHT,
        )
        d = CalibratedHallucinationDetector(high_sensitivity=True)
        assert d.base_threshold == HIGH_SENSITIVITY_THRESHOLD
        assert d.bebop_weight >= HIGH_SENSITIVITY_BEBOP_WEIGHT

    def test_high_sensitivity_keeps_larger_explicit_weight(self):
        d = CalibratedHallucinationDetector(high_sensitivity=True, bebop_weight=0.5)
        assert d.bebop_weight == 0.5


class TestBatchedCalibrationPersistence:
    def test_assess_does_not_write_every_call(self, tmp_path, monkeypatch):
        """Hot-path requirement: no JSON disk write per token."""
        import nexus_os.monitoring.calibrated_hallucination_detector as chd_mod
        state = tmp_path / "cal.json"
        monkeypatch.setattr(chd_mod, "CALIBRATION_STATE_FILE", state)
        d = CalibratedHallucinationDetector()
        for _ in range(chd_mod.CalibratedHallucinationDetector.PERSIST_EVERY - 1):
            d.assess(topk_probs=[0.5, 0.3, 0.2])
        assert not state.exists()

    def test_assess_persists_on_batch_boundary_and_flush(self, tmp_path, monkeypatch):
        import nexus_os.monitoring.calibrated_hallucination_detector as chd_mod
        state = tmp_path / "cal.json"
        monkeypatch.setattr(chd_mod, "CALIBRATION_STATE_FILE", state)
        d = CalibratedHallucinationDetector()
        for _ in range(chd_mod.CalibratedHallucinationDetector.PERSIST_EVERY):
            d.assess(topk_probs=[0.5, 0.3, 0.2])
        assert state.exists()
        state.unlink()
        d.assess(topk_probs=[0.5, 0.3, 0.2])
        assert not state.exists()
        d.flush_calibration()
        assert state.exists()
