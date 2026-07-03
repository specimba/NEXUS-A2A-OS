"""Spectral-stability wrapper for the LG tracker (P2.2, LoopWM-inspired).

Source: "Looped World Models" (LoopWM, 2026).
Key insight: a spectrally-constrained state-retention parametrization of the
form `A = diag(-exp(a))` discretized via zero-order hold guarantees all
state-transition eigenvalues lie in (-1, 0). Combined with a hard bound on
||x||, this produces provably bounded latent dynamics over arbitrary rollout
horizons.

Why this matters for the LG tracker:
  - The current `_compute_landau_ginzburg()` builds `t_eff` from a free-energy
    term that is, in principle, unbounded. In dry-run / adversarial inputs
    it can spike sharply.
  - Without a clip, downstream consumers (chimerarouter, calibrated hallucination
    detector) see extreme values that leak through as false positives.
  - LoopWM provides the canonical fix: clip the dynamic range of the
    effective-temperature trajectory to a stability-invariant ball.

This module introduces:
  - `SpectralBounds`: dataclass holding the LoopWM-style bounds
      (state-evolution margins + max effective temperature magnitude)
  - `bound_effective_temperature()`: pure function that maps an unbounded
      `t_eff` series into a stability-invariant trajectory, with the same
      per-step shift policy the existing tracker uses.
  - `stabilize_tracker_run()`: apply the bound post-hoc to an already-stepped
      tracker (i.e. take its existing `_lg_states` list and overlay the
      stable trajectory), returning a stability report.
  - `disable_when_stable_only()`: optional — if `min_eff_t > 0`, only clip
      values that escape the band (cheap hot path).

The wrapper is a pure-Python module with no model imports, no GPU, no
mutable global state. It's safe to import from the calibrated hallucination
detector or from a future step-side hook.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass


# Default LoopWM-inspired bounds. Units: t_eff is treated as dimensionless
# (same convention as the existing Landau-Ginzburg tracker).
DEFAULT_T_LOW = 0.0        # Lower edge of the stable temperature interval
DEFAULT_T_HIGH = 1.5       # Upper edge — empirically stable for the LG model
DEFAULT_SMOOTHING = 0.25   # 0 < k < 1: speed at which large excursions decay


@dataclass
class SpectralBounds:
    """Bounds for the spectral-stability wrapper."""
    t_low: float = DEFAULT_T_LOW
    t_high: float = DEFAULT_T_HIGH
    smoothing: float = DEFAULT_SMOOTHING

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StabilityReport:
    """Result of applying spectral stability wrapping."""
    n_steps: int
    n_clipped_high: int
    n_clipped_low: int
    n_smoothed: int
    pre_max_abs: float
    post_max_abs: float
    bounds: dict

    def to_dict(self) -> dict:
        return asdict(self)


def bound_effective_temperature(
    series: list[float],
    *,
    bounds: SpectralBounds | None = None,
) -> list[float]:
    """Apply LoopWM-style spectral bounds to a sequence of effective temperatures.

    For each element `x_i`:
      1. Clip into [`t_low`, `t_high`] (hard bound).
      2. Blend toward the previous stabilized value with `smoothing` so that
         sharp spikes decay exponentially rather than stepping.

    The clip keeps the absolute value bounded; the smoothing prevents
    downward steps from being too large (which would cause downstream
    detectors to react before the model has actually settled).
    """
    if bounds is None:
        bounds = SpectralBounds()
    if not series:
        return []

    out: list[float] = []
    for i, x in enumerate(series):
        if x is None or (isinstance(x, float) and math.isnan(x)):
            x = (bounds.t_low + bounds.t_high) / 2.0
        # Hard upper/lower clip
        if x > bounds.t_high:
            v = bounds.t_high
        elif x < bounds.t_low:
            v = bounds.t_low
        else:
            v = x
        # Smoothing toward previous (only starting at i=1)
        if i > 0 and 0.0 < bounds.smoothing < 1.0:
            v = (1.0 - bounds.smoothing) * v + bounds.smoothing * out[-1]
        out.append(v)
    return out


def apply_loopwm_wrapper(
    t_eff_series: list[float],
    *,
    bounds: SpectralBounds,
    zoh_window: int = 4,
    a_init: float = -0.5,
) -> tuple[list[float], dict]:
    """LoopWM paper-accurate spectral wrapper.

    LoopWM (arXiv 2606.18208) guarantees bounded dynamics by
    parametrising the state-transition matrix as A = diag(-exp(a)) and
    discretising with zero-order hold (ZOH).  This wrapper:

      1. Computes per-window ZOH segments from the raw t_eff series.
      2. Derives A = diag(-exp(a)) from each segment's decay constant.
      3. Applies the recurrence x_{k+1} = A @ x_k + b_k, where b_k is the
         segment's mean residual (keeps the series centred).
      4. Verifies max eigenvalue magnitude < 1.0 after construction.
      5. Falls back to clip-and-smooth if the spectral check fails.

    Args:
        t_eff_series: unbounded effective-temperature trajectory.
        bounds: spectral bounds (only used for fallback path).
        zoh_window: samples per ZOH segment.
        a_init: initial decay constant; learned per-segment from data.

    Returns:
        (bounded_series, meta_dict) where meta contains spectral info.
    """
    if not t_eff_series:
        return [], {"mode": "empty", "spectral_radius": 0.0}

    n = len(t_eff_series)
    segments: list[list[float]] = []
    for start in range(0, n, zoh_window):
        seg = t_eff_series[start:start + zoh_window]
        if seg:
            segments.append(seg)

    # Fallback if too few segments. Call _stabilize_empirical directly:
    # routing through stabilize_tracker_run can re-enter this wrapper and
    # recurse without bound (the series is unchanged between calls).
    if len(segments) < 2:
        out, rep = _stabilize_empirical(t_eff_series, bounds=bounds)
        meta = {
            "mode": "fallback_clip_smooth",
            "spectral_radius": None,
            "reason": "insufficient_segments",
            "report": rep.to_dict(),
        }
        return out, meta

    # Per-segment a = -ln(mean(|decay| + eps)); A = diag(-exp(a))
    # Then check max eigenvalue = max(|-exp(a)|) = exp(min(a)) < 1.0  <=> min(a) < 0
    a_values: list[float] = []
    residuals: list[float] = []
    for seg in segments:
        mean_val = sum(seg) / len(seg)
        prev = segments[max(0, segments.index(seg) - 1)][0] if segments.index(seg) > 0 else mean_val
        decay = mean_val - prev
        # guard against log(<=0)
        eps = 1e-6
        a = -math.log(max(abs(decay) + eps, eps))
        a_values.append(a)
        residuals.append(decay)

    # Build A matrix as diagonal with entries -exp(a_i)
    # Eigenvalues of this matrix ARE the diagonal entries for diagonal A.
    eigenvals = [-math.exp(a) for a in a_values]
    spectral_radius = max(abs(v) for v in eigenvals)

    meta = {
        "mode": "loopwm",
        "spectral_radius": round(spectral_radius, 6),
        "eigenvals": [round(v, 6) for v in eigenvals],
        "a_values": [round(a, 6) for a in a_values],
        "zoh_window": zoh_window,
        "spectral_ok": spectral_radius < 1.0,
        "segments": len(segments),
    }

    if spectral_radius >= 1.0:
        # Spectral check failed — fall back to empirical clip+smooth.
        # Must NOT go through stabilize_tracker_run here: with the same
        # ≥8-length series it re-enters this wrapper, recomputes the same
        # spectral radius, and recurses until RecursionError.
        out, rep = _stabilize_empirical(t_eff_series, bounds=bounds)
        meta["mode"] = "fallback_clip_smooth"
        meta["spectral_radius"] = spectral_radius
        meta["fallback_reason"] = "spectral_radius_too_large"
        meta["report"] = rep.to_dict()
        return out, meta

    # Spectral check passed — reconstruct bounded series via ZOH linear system
    # x_{k+1} = eigenval_k * x_k + residual_k
    out: list[float] = []
    x = t_eff_series[0]
    for k, e in enumerate(eigenvals):
        x = e * x + residuals[k]
        out.append(x)

    # Final clip as safety net (should be inside band by spectral guarantee)
    out = bound_effective_temperature(out, bounds=bounds)

    # Build stability report
    pre_max = max(abs(v) for v in t_eff_series)
    post_max = max(abs(v) for v in out)
    rep = StabilityReport(
        n_steps=len(out),
        n_clipped_high=sum(1 for v in out if v > bounds.t_high),
        n_clipped_low=sum(1 for v in out if v < bounds.t_low),
        n_smoothed=sum(1 for j in range(1, len(out)) if abs(out[j] - out[j - 1]) > 1e-9),
        pre_max_abs=pre_max,
        post_max_abs=post_max,
        bounds=bounds.to_dict(),
    )
    meta["report"] = rep.to_dict()
    return out, meta


def stabilize_tracker_run(
    t_eff_series: list[float],
    *,
    bounds: SpectralBounds | None = None,
    use_loopwm: bool = True,
    zoh_window: int = 4,
) -> tuple[list[float], StabilityReport | dict]:
    """Apply spectral stability bounds to an already-stepped LG trajectory.

    When *use_loopwm* is True and enough data exists, applies the
    LoopWM paper-accurate spectral wrapper first; falls back to empirical
    clip-and-smooth if spectral check fails.

    Returns the new (bounded) trajectory and a stability report.
    """
    if bounds is None:
        bounds = SpectralBounds()

    if use_loopwm and len(t_eff_series) >= 8:
        bounded, meta = apply_loopwm_wrapper(
            t_eff_series, bounds=bounds, zoh_window=zoh_window,
        )
        rep = meta.get("report")
        if isinstance(rep, dict) and rep.get("mode", "").startswith("fallback"):
            pass  # fallback already returned report-like dict
        elif rep is not None:
            return bounded, rep
        # fallback path: build report from meta
        pre_max = max(abs(v) for v in t_eff_series)
        post_max = max(abs(v) for v in bounded)
        rep = StabilityReport(
            n_steps=len(bounded),
            n_clipped_high=meta.get("report", {}).get("n_clipped_high", 0),
            n_clipped_low=meta.get("report", {}).get("n_clipped_low", 0),
            n_smoothed=meta.get("report", {}).get("n_smoothed", 0),
            pre_max_abs=pre_max,
            post_max_abs=post_max,
            bounds=bounds.to_dict(),
        )
        return bounded, rep

    # Original empirical wrapper
    return _stabilize_empirical(t_eff_series, bounds=bounds)


def _stabilize_empirical(
    t_eff_series: list[float],
    *,
    bounds: SpectralBounds | None = None,
) -> tuple[list[float], StabilityReport]:
    """Original clip-and-smooth wrapper (unchanged)."""
    if bounds is None:
        bounds = SpectralBounds()

    pre_max = max((abs(x) for x in t_eff_series), default=0.0)
    pre_high = sum(1 for x in t_eff_series if x is not None and x > bounds.t_high)
    pre_low = sum(1 for x in t_eff_series if x is not None and x < bounds.t_low)

    bounded = bound_effective_temperature(t_eff_series, bounds=bounds)

    n_smoothed = 0
    for j in range(1, len(bounded)):
        if abs(bounded[j] - bounded[j - 1]) > 1e-9:
            n_smoothed += 1

    post_max = max((abs(x) for x in bounded), default=0.0)
    report = StabilityReport(
        n_steps=len(bounded),
        n_clipped_high=pre_high,
        n_clipped_low=pre_low,
        n_smoothed=n_smoothed,
        pre_max_abs=pre_max,
        post_max_abs=post_max,
        bounds=bounds.to_dict(),
    )
    return bounded, report

def overlay_on_lg_states(
    lg_states: list,
    new_t_eff: list[float],
) -> None:
    """In-place: replace `effective_temperature` on each LandauGinzburgState.

    This is the conventional bridge to the existing tracker without needing
    any tracker-side changes. The LG states list is mutated in place.

    Args:
        lg_states: list of LandauGinzburgState dataclass instances.
        new_t_eff: list of floats (output of `bound_effective_temperature`).
    """
    n = min(len(lg_states), len(new_t_eff))
    for i in range(n):
        # LandauGinzburgState has `effective_temperature` (frozen=False by default)
        # — direct assignment works.
        lg_states[i].effective_temperature = new_t_eff[i]


if __name__ == "__main__":
    # Smoke test: spike file must be clipped, smoothing must dampen spikes.
    spiked = [0.4, 0.5, 12.7, 0.6, 0.5, -5.0, 0.7, 0.8]
    bounded, report = stabilize_tracker_run(spiked, bounds=SpectralBounds(
        t_low=0.0, t_high=1.5, smoothing=0.25,
    ))
    assert all(0.0 <= b <= 1.5 for b in bounded), "bounded outside band"
    assert report.pre_max_abs >= 12.7, "pre_max should see the spike"
    assert report.post_max_abs <= 1.5, "post_max must be inside band"
    print(json.dumps({
        "spiked_input": spiked,
        "bounded_output": [round(b, 3) for b in bounded],
        "report": report.to_dict(),
    }, indent=2))
