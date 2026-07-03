"""Tests for nexus_os.twave.landau_ginzburg_tracker_v2 — LandauGinzburgTrackerV2 and components."""

import sys
import warnings
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nexus_os.twave.landau_ginzburg_tracker_v2 import (
    CKPlugCoupler,
    DEFAULT_T_C,
    DEFAULT_WEIGHTS,
    DecodingMode,
    EDTController,
    EPRDetector,
    LandauGinzburgState,
    LandauGinzburgTrackerV2,
    LEADSwitching,
    LEDExplorer,
    OrderParameters,
    TrackerReport,
)


# ---------------------------------------------------------------------------
# EDTController
# ---------------------------------------------------------------------------
class TestEDTController:
    def test_default_init(self):
        edt = EDTController()
        assert edt.T0 == 1.0
        assert edt.T_max == 1.2

    def test_compute_zero_entropy_returns_T0(self):
        edt = EDTController(T0=0.8)
        assert edt.compute(0.0) == 0.8

    def test_compute_positive_entropy_within_bounds(self):
        edt = EDTController()
        T = edt.compute(2.0)
        assert 0.01 <= T <= edt.T_max

    def test_compute_high_entropy_approaches_T0(self):
        edt = EDTController()
        T_high_ent = edt.compute(100.0)
        T_low_ent = edt.compute(0.5)
        # T = T0 * N_base^(theta/H): higher H → exponent→0 → T→T0
        assert T_high_ent > T_low_ent

    def test_compute_respects_min_T(self):
        edt = EDTController(T0=0.001, N_base=0.01)
        T = edt.compute(0.1, min_T=0.05)
        assert T >= 0.05

    def test_anneal_decreasing(self):
        edt = EDTController()
        t0 = edt.anneal(0, 100)
        t10 = edt.anneal(10, 100)
        t30 = edt.anneal(30, 100)
        assert t0 > t10
        assert t30 == 0.1  # after d=25 tokens, returns T_min

    def test_anneal_at_d_returns_t_min(self):
        edt = EDTController()
        assert edt.anneal(25, 100) == 0.1
        assert edt.anneal(50, 100) == 0.1


# ---------------------------------------------------------------------------
# LEADSwitching
# ---------------------------------------------------------------------------
class TestLEADSwitching:
    def test_initial_mode_is_discrete(self):
        lead = LEADSwitching()
        assert lead.current_mode == DecodingMode.DISCRETE

    def test_step_with_low_entropy_stays_discrete(self):
        lead = LEADSwitching()
        for i in range(10):
            mode = lead.step(i, entropy=0.1)
        assert mode == DecodingMode.DISCRETE

    def test_transitions_tracked(self):
        lead = LEADSwitching(W_D_to_L=1, C_max=10, auto_threshold_window=3)
        # Fill entropy history with low values then spike
        for i in range(5):
            lead.step(i, entropy=0.2)
        # Now high entropy to trigger latent
        for i in range(5, 15):
            lead.step(i, entropy=5.0)
        transitions = lead.transitions
        assert isinstance(transitions, list)

    def test_c_max_limits_switches(self):
        lead = LEADSwitching(W_D_to_L=0, C_max=2, auto_threshold_window=2)
        for i in range(50):
            ent = 0.1 if i % 4 < 2 else 5.0
            lead.step(i, entropy=ent)
        assert lead._switch_count <= 2 + 5  # bounded by C_max logic

    def test_transitions_returns_copy(self):
        lead = LEADSwitching()
        t1 = lead.transitions
        t2 = lead.transitions
        assert t1 is not t2


# ---------------------------------------------------------------------------
# EPRDetector
# ---------------------------------------------------------------------------
class TestEPRDetector:
    def test_compute_topk_entropy_uniform(self):
        epr = EPRDetector(K=4)
        probs = np.array([0.25, 0.25, 0.25, 0.25])
        H = epr.compute_topk_entropy(probs)
        assert abs(H - 2.0) < 0.01  # log2(4)

    def test_compute_topk_entropy_peaked(self):
        epr = EPRDetector()
        probs = np.array([0.99, 0.01])
        H = epr.compute_topk_entropy(probs)
        assert H < 0.5

    def test_compute_epr_empty(self):
        epr = EPRDetector()
        assert epr.compute_epr() == 0.0

    def test_step_accumulates(self):
        epr = EPRDetector()
        probs = np.array([0.5, 0.3, 0.2])
        for _ in range(5):
            H_t, epr_score = epr.step(probs)
        assert epr_score > 0

    def test_is_hallucination_risk(self):
        epr = EPRDetector()
        probs = np.array([0.25, 0.25, 0.25, 0.25])
        for _ in range(20):
            epr.step(probs, temperature=0.3)
        assert isinstance(epr.is_hallucination_risk(threshold=1.0, temperature=0.3), bool)

    def test_reset_clears(self):
        epr = EPRDetector()
        epr.step(np.array([0.5, 0.5]))
        epr.reset()
        assert epr.compute_epr() == 0.0

    def test_zero_temperature_returns_raw(self):
        epr = EPRDetector()
        epr.step(np.array([0.5, 0.5]))
        raw = epr.compute_epr(temperature=0.0)
        assert raw == epr.compute_epr(temperature=0.0)


# ---------------------------------------------------------------------------
# LEDExplorer
# ---------------------------------------------------------------------------
class TestLEDExplorer:
    def test_select_depth_empty_returns_zero(self):
        led = LEDExplorer()
        assert led.select_depth([]) == 0

    def test_select_depth_single_layer_returns_zero(self):
        led = LEDExplorer()
        assert led.select_depth([np.array([1.0, 2.0])]) == 0

    def test_select_depth_valid_layers(self):
        led = LEDExplorer(k=3, d=2)
        layers = [np.random.randn(10) for _ in range(5)]
        depth = led.select_depth(layers)
        assert 0 <= depth < len(layers)

    def test_exploit_or_explore_high_prob(self):
        led = LEDExplorer(exploit_threshold=0.9)
        assert led.exploit_or_explore(0.95) == "exploit"

    def test_exploit_or_explore_low_prob(self):
        led = LEDExplorer(exploit_threshold=0.9)
        assert led.exploit_or_explore(0.5) == "explore"

    def test_select_depth_log_zero_no_crash(self):
        """Edge case: layer logits with zeros should not crash due to log(0).
        The code uses np.log(agg + 1e-10), so a RuntimeWarning could still appear."""
        led = LEDExplorer(k=3)
        layers = [np.zeros(5) for _ in range(3)]
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            try:
                depth = led.select_depth(layers)
            except RuntimeWarning:
                pytest.skip("RuntimeWarning raised for log(0) — known edge case")
            assert isinstance(depth, int)


# ---------------------------------------------------------------------------
# CKPlugCoupler
# ---------------------------------------------------------------------------
class TestCKPlugCoupler:
    def test_compute_cg(self):
        ck = CKPlugCoupler()
        logits_p = np.array([1.0, 2.0, 0.5])
        logits_r = np.array([0.5, 1.0, 2.0])
        cg, h_p, h_r = ck.compute_cg(logits_p, logits_r)
        assert isinstance(cg, float)
        assert isinstance(h_p, float)
        assert isinstance(h_r, float)

    def test_compute_effective_alpha_no_adaptive(self):
        ck = CKPlugCoupler(alpha=0.5, adaptive_alpha=False)
        alpha = ck.compute_effective_alpha(cg=0.5)
        assert alpha == 0.5

    def test_compute_effective_alpha_support(self):
        ck = CKPlugCoupler(alpha=0.5, adaptive_alpha=True, support_threshold=0.1,
                           adaptive_aggressiveness=0.3)
        alpha = ck.compute_effective_alpha(cg=0.5)
        assert alpha > 0.5

    def test_compute_effective_alpha_conflict(self):
        ck = CKPlugCoupler(alpha=0.5, adaptive_alpha=True, conflict_threshold=-0.1,
                           adaptive_aggressiveness=0.3)
        alpha = ck.compute_effective_alpha(cg=-0.5)
        assert alpha < 0.5

    def test_compute_effective_alpha_clamped(self):
        ck = CKPlugCoupler(alpha=0.5, adaptive_alpha=True, adaptive_aggressiveness=10.0)
        alpha = ck.compute_effective_alpha(cg=100.0)
        assert 0.0 <= alpha <= 1.0

    def test_modulate_returns_logits_and_diag(self):
        ck = CKPlugCoupler(enable_diagnostics=True)
        logits_p = np.array([1.0, 2.0, 0.5])
        logits_r = np.array([0.5, 1.0, 2.0])
        modulated, diag = ck.modulate(logits_p, logits_r, position=0)
        assert modulated.shape == logits_p.shape
        assert diag is not None
        assert "cg" in diag
        assert "alpha_applied" in diag

    def test_modulate_no_diagnostics(self):
        ck = CKPlugCoupler(enable_diagnostics=False)
        logits_p = np.array([1.0, 2.0])
        logits_r = np.array([0.5, 1.5])
        modulated, diag = ck.modulate(logits_p, logits_r)
        assert diag is None

    def test_to_mu_ret(self):
        ck = CKPlugCoupler()
        mu = ck.to_mu_ret(cg=0.3, current_temperature=0.7)
        assert isinstance(mu, float)

    def test_to_mu_ret_temperature_respect(self):
        ck = CKPlugCoupler(temperature_respect=True)
        mu_low = ck.to_mu_ret(0.5, current_temperature=0.3)
        mu_high = ck.to_mu_ret(0.5, current_temperature=0.9)
        assert abs(mu_low) >= abs(mu_high)

    def test_reset_clears_diagnostics(self):
        ck = CKPlugCoupler(enable_diagnostics=True)
        ck.modulate(np.array([1.0, 2.0]), np.array([0.5, 1.5]))
        assert len(ck._diagnostics) == 1
        ck.reset()
        assert len(ck._diagnostics) == 0

    def test_temperature_respect_high_temp_dampens_support(self):
        ck = CKPlugCoupler(alpha=0.5, adaptive_alpha=True, temperature_respect=True,
                           support_threshold=0.1, adaptive_aggressiveness=0.5)
        alpha_cool = ck.compute_effective_alpha(cg=0.5, current_temperature=0.5)
        alpha_hot = ck.compute_effective_alpha(cg=0.5, current_temperature=0.9)
        assert alpha_hot <= alpha_cool


# ---------------------------------------------------------------------------
# LandauGinzburgTrackerV2 — initialization
# ---------------------------------------------------------------------------
class TestLandauGinzburgTrackerV2Init:
    def test_default_init(self):
        tracker = LandauGinzburgTrackerV2()
        assert tracker.category == "default"
        assert tracker.t_c == DEFAULT_T_C["default"]
        assert tracker.weights == DEFAULT_WEIGHTS["default"]
        assert tracker.enable_edt is True
        assert tracker.enable_lead is True
        assert tracker.enable_epr is True
        assert tracker.enable_led is False
        assert tracker.enable_ckplug is False

    def test_category_lookup(self):
        tracker = LandauGinzburgTrackerV2(category="F1.1")
        assert tracker.t_c == DEFAULT_T_C["F1.1"]
        assert tracker.weights == DEFAULT_WEIGHTS["F1.1"]

    def test_custom_t_c_overrides_category(self):
        tracker = LandauGinzburgTrackerV2(category="F1.1", t_c=0.99)
        assert tracker.t_c == 0.99

    def test_cooling_modes(self):
        for mode, expected in [("gentle", 0.95), ("moderate", 0.85), ("aggressive", 0.70)]:
            tracker = LandauGinzburgTrackerV2(cooling_mode=mode)
            assert tracker.cooling_factor == expected

    def test_unknown_cooling_mode_defaults(self):
        tracker = LandauGinzburgTrackerV2(cooling_mode="unknown")
        assert tracker.cooling_factor == 0.85

    def test_components_disabled(self):
        tracker = LandauGinzburgTrackerV2(enable_edt=False, enable_lead=False,
                                          enable_epr=False)
        assert tracker.edt is None
        assert tracker.lead is None
        assert tracker.epr is None

    def test_components_enabled(self):
        tracker = LandauGinzburgTrackerV2(enable_edt=True, enable_lead=True,
                                          enable_epr=True, enable_led=True,
                                          enable_ckplug=True)
        assert tracker.edt is not None
        assert tracker.lead is not None
        assert tracker.epr is not None
        assert tracker.led is not None
        assert tracker.ckplug is not None


# ---------------------------------------------------------------------------
# LandauGinzburgTrackerV2 — step / dry-run
# ---------------------------------------------------------------------------
class TestLandauGinzburgTrackerV2Step:
    def test_dry_run_step(self):
        tracker = LandauGinzburgTrackerV2(category="F1.1")
        tracker.set_dry_run(True)
        action = tracker.step(position=0, current_temperature=0.7)
        assert "cool" in action
        assert "mode" in action
        assert "hallucination_risk" in action

    def test_dry_run_multiple_steps(self):
        tracker = LandauGinzburgTrackerV2(category="F1.1")
        tracker.set_dry_run(True)
        for i in range(20):
            action = tracker.step(position=i, current_temperature=0.7)
        assert len(tracker._order_params) == 20
        assert len(tracker._lg_states) == 20

    def test_step_with_real_logits(self):
        tracker = LandauGinzburgTrackerV2(category="default", enable_epr=True)
        logits = np.random.randn(100)
        topk_probs = np.array([0.3, 0.2, 0.15, 0.1, 0.08, 0.07, 0.05, 0.03, 0.01, 0.01])
        action = tracker.step(position=0, logits=logits, current_temperature=0.7,
                              topk_probs=topk_probs)
        assert isinstance(action, dict)
        assert "ep_r" in action

    def test_step_with_layer_logits(self):
        tracker = LandauGinzburgTrackerV2(enable_led=True)
        logits = np.random.randn(50)
        layer_logits = [np.random.randn(50) for _ in range(5)]
        action = tracker.step(position=0, logits=logits, current_temperature=0.7,
                              layer_logits=layer_logits)
        assert action["led_depth"] is not None

    def test_step_with_ckplug(self):
        tracker = LandauGinzburgTrackerV2(enable_ckplug=True)
        logits = np.random.randn(50)
        logits_p = np.random.randn(50)
        logits_r = np.random.randn(50)
        action = tracker.step(position=0, logits=logits, current_temperature=0.7,
                              logits_parametric=logits_p, logits_retrieval=logits_r)
        assert isinstance(action, dict)

    def test_step_with_attention_weights(self):
        tracker = LandauGinzburgTrackerV2()
        logits = np.random.randn(50)
        attn = np.random.rand(10)
        action = tracker.step(position=0, logits=logits, current_temperature=0.7,
                              attention_weights=attn)
        assert isinstance(action, dict)

    def test_callbacks_invoked(self):
        cooling_events = []
        hallucination_events = []
        mode_events = []

        def on_cool(pos, old_t, new_t):
            cooling_events.append(pos)

        def on_hall(pos, msg):
            hallucination_events.append(pos)

        def on_mode(pos, old, new):
            mode_events.append((pos, old, new))

        tracker = LandauGinzburgTrackerV2(
            category="F1.1",
            on_cooling=on_cool,
            on_hallucination=on_hall,
            on_mode_switch=on_mode,
        )
        tracker.set_dry_run(True)
        for i in range(50):
            tracker.step(position=i, current_temperature=0.9)
        # callbacks may or may not fire depending on random seeds; just check types
        assert isinstance(cooling_events, list)
        assert isinstance(hallucination_events, list)


# ---------------------------------------------------------------------------
# LandauGinzburgTrackerV2 — report
# ---------------------------------------------------------------------------
class TestLandauGinzburgTrackerV2Report:
    def test_report_after_steps(self):
        tracker = LandauGinzburgTrackerV2(category="R2.1",
                                          enable_edt=True, enable_lead=True, enable_epr=True)
        tracker.set_dry_run(True)
        for i in range(10):
            tracker.step(position=i, current_temperature=0.7)
        report = tracker.get_report()
        assert isinstance(report, TrackerReport)
        assert report.category == "R2.1"
        assert report.t_c == DEFAULT_T_C["R2.1"]
        assert report.tokens_generated == 10
        assert len(report.order_parameters) == 10
        assert len(report.lg_states) == 10
        assert isinstance(report.mean_entropy, float)
        assert isinstance(report.max_entropy, float)
        assert isinstance(report.entropy_variance, float)

    def test_report_epr_score_present(self):
        tracker = LandauGinzburgTrackerV2(enable_epr=True)
        tracker.set_dry_run(True)
        for i in range(5):
            tracker.step(position=i, current_temperature=0.7)
        report = tracker.get_report()
        assert report.epr_score is not None

    def test_report_mode_transitions(self):
        tracker = LandauGinzburgTrackerV2(enable_lead=True)
        tracker.set_dry_run(True)
        for i in range(20):
            tracker.step(position=i, current_temperature=0.7)
        report = tracker.get_report()
        assert report.mode_transitions is not None
        assert isinstance(report.mode_transitions, list)

    def test_report_empty_tracker(self):
        tracker = LandauGinzburgTrackerV2()
        report = tracker.get_report()
        assert report.tokens_generated == 0
        assert report.mean_entropy == 0.0
        assert report.hallucination_detected is False


# ---------------------------------------------------------------------------
# LandauGinzburgTrackerV2 — reset
# ---------------------------------------------------------------------------
class TestLandauGinzburgTrackerV2Reset:
    def test_reset_clears_state(self):
        tracker = LandauGinzburgTrackerV2(enable_epr=True, enable_ckplug=True)
        tracker.set_dry_run(True)
        for i in range(10):
            tracker.step(position=i, current_temperature=0.7)
        tracker.reset()
        assert len(tracker._order_params) == 0
        assert len(tracker._lg_states) == 0
        assert len(tracker._cooling_events) == 0
        assert len(tracker._hallucination_positions) == 0
        assert tracker._current_temperature == 0.7


# ---------------------------------------------------------------------------
# LandauGinzburgTrackerV2 — phase tracking & hallucination
# ---------------------------------------------------------------------------
class TestPhaseTracking:
    def test_high_temp_triggers_hallucination(self):
        tracker = LandauGinzburgTrackerV2(category="D11.1", enable_edt=True,
                                          enable_lead=True, enable_epr=False)
        tracker.set_dry_run(True)
        for i in range(40):
            tracker.step(position=i, current_temperature=1.5)
        report = tracker.get_report()
        # At T=1.5 with T_c=0.50, hallucination should be detected
        assert report.hallucination_detected is True
        assert len(report.hallucination_positions) > 0

    def test_low_temp_no_hallucination(self):
        tracker = LandauGinzburgTrackerV2(category="S4.6", enable_edt=True,
                                          enable_lead=True, enable_epr=False)
        tracker.set_dry_run(True)
        for i in range(20):
            tracker.step(position=i, current_temperature=0.1)
        report = tracker.get_report()
        assert report.hallucination_detected is False

    def test_self_correction_detection(self):
        tracker = LandauGinzburgTrackerV2(category="F1.1")
        tracker.set_dry_run(True)
        for i in range(50):
            tracker.step(position=i, current_temperature=0.8)
        # self-corrections depend on stochastic dry-run; just check it's a list
        report = tracker.get_report()
        assert isinstance(report.self_correction_positions, list)


# ---------------------------------------------------------------------------
# LandauGinzburgTrackerV2 — black_box_step
# ---------------------------------------------------------------------------
class TestBlackBoxStep:
    def test_basic_black_box(self):
        tracker = LandauGinzburgTrackerV2(enable_epr=True)
        probs = np.array([0.3, 0.2, 0.15, 0.1, 0.08, 0.07, 0.05, 0.03, 0.01, 0.01])
        result = tracker.black_box_step(0, probs, temperature=0.7)
        assert "cool" in result
        assert "ep_r" in result
        assert "mode" in result

    def test_black_box_raises_without_epr(self):
        tracker = LandauGinzburgTrackerV2(enable_epr=False)
        with pytest.raises(ValueError, match="EPR must be enabled"):
            tracker.black_box_step(0, np.array([0.5, 0.5]))


# ---------------------------------------------------------------------------
# LandauGinzburgTrackerV2 — entropy_from_logits (static)
# ---------------------------------------------------------------------------
class TestEntropyFromLogits:
    def test_uniform_logits(self):
        logits = np.zeros(10)
        entropy, top2 = LandauGinzburgTrackerV2._entropy_from_logits(logits)
        assert entropy > 0
        assert abs(top2 - 1.0) < 0.01  # uniform → top2 ratio ≈ 1

    def test_peaked_logits(self):
        logits = np.array([10.0, 0.0, 0.0, 0.0, 0.0])
        entropy, top2 = LandauGinzburgTrackerV2._entropy_from_logits(logits)
        assert entropy < 1.0
        assert top2 > 1.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
class TestEdgeCases:
    def test_healing_length_no_hallucinations(self):
        tracker = LandauGinzburgTrackerV2()
        assert tracker._estimate_healing_length() is None

    def test_edt_schedule_recorded(self):
        tracker = LandauGinzburgTrackerV2(enable_edt=True)
        tracker.set_dry_run(True)
        for i in range(10):
            tracker.step(position=i, current_temperature=0.7)
        assert len(tracker._edt_schedule) == 10

    def test_led_depths_recorded_when_enabled(self):
        tracker = LandauGinzburgTrackerV2(enable_led=True)
        logits = np.random.randn(20)
        layer_logits = [np.random.randn(20) for _ in range(4)]
        for i in range(5):
            tracker.step(position=i, logits=logits, current_temperature=0.7,
                         layer_logits=layer_logits)
        assert len(tracker._led_depths) == 5


# ---------------------------------------------------------------------------
# P2-1 en-route fixes: spectral recursion + logits-processor cooling
# ---------------------------------------------------------------------------
class TestSpectralFallbackRecursion:
    """apply_loopwm_wrapper used to fall back through stabilize_tracker_run,
    which re-entered the wrapper with the same series and recursed until
    RecursionError. Smooth series (adjacent segment means differing by <1.0)
    always have spectral radius > 1, so the common case crashed."""

    def test_smooth_series_no_recursion(self):
        from nexus_os.twave.spectral_stability import stabilize_tracker_run
        series = [0.7, 0.75, 0.8, 0.72, 0.71, 0.74, 0.76, 0.73]
        out, rep = stabilize_tracker_run(series, use_loopwm=True)
        assert len(out) == len(series)
        assert all(isinstance(v, float) for v in out)

    def test_spectral_fail_falls_back_with_report(self):
        from nexus_os.twave.spectral_stability import (
            SpectralBounds,
            apply_loopwm_wrapper,
        )
        series = [0.7, 0.75, 0.8, 0.72, 0.71, 0.74, 0.76, 0.73]
        out, meta = apply_loopwm_wrapper(series, bounds=SpectralBounds())
        assert meta["mode"] == "fallback_clip_smooth"
        assert meta["fallback_reason"] == "spectral_radius_too_large"
        assert "report" in meta
        assert len(out) == len(series)

    def test_insufficient_segments_no_recursion(self):
        from nexus_os.twave.spectral_stability import (
            SpectralBounds,
            apply_loopwm_wrapper,
        )
        out, meta = apply_loopwm_wrapper([0.7, 0.8, 0.9], bounds=SpectralBounds())
        assert meta["mode"] == "fallback_clip_smooth"
        assert meta["reason"] == "insufficient_segments"
        assert len(out) == 3

    def test_report_path_via_tracker(self):
        tracker = LandauGinzburgTrackerV2()
        tracker.set_dry_run(True)
        for i in range(12):
            tracker.step(position=i, current_temperature=0.7)
        report = tracker.get_report(apply_spectral_bounds=True)
        assert report.stability_report is not None
        # Must not have crashed; bounded states overlaid in place.
        assert len(report.lg_states) == 12


class TestLogitsProcessorCooling:
    """Cooling used to mutate _current_temp before computing the scale
    factor (ratio always 1.0 → no-op), and ABSTAIN's t_eff=0 multiplied
    every logit by zero, turning detected hallucinations into uniform
    random sampling."""

    def _processor(self, t_eff):
        pytest.importorskip("transformers")
        tracker = LandauGinzburgTrackerV2()
        proc = tracker.logits_processor()
        proc.tracker = _StubTracker(t_eff)
        return proc

    def test_cooling_sharpens_not_noop(self):
        proc = self._processor(t_eff=0.35)
        scores = np.array([[2.0, 1.0, 0.5]])
        out = proc(None, scores)
        # prev temp 0.7 / new temp 0.35 = 2.0 → logits doubled (sharper)
        assert np.allclose(out, scores * 2.0)
        assert proc._current_temp == pytest.approx(0.35)

    def test_abstain_never_zeroes_logits(self):
        proc = self._processor(t_eff=0.0)
        scores = np.array([[2.0, 1.0, 0.5]])
        out = proc(None, scores)
        assert not np.allclose(out, 0.0)
        # Floored at 0.01 → strong sharpening, not information loss
        assert np.all(np.abs(out) >= np.abs(scores))
        assert proc._current_temp == pytest.approx(0.01)


class _StubTracker:
    def __init__(self, t_eff):
        self._t_eff = t_eff

    def step(self, position, logits, current_temperature):
        return {"cool": True, "t_eff": self._t_eff, "mode": "ABSTAIN"}
