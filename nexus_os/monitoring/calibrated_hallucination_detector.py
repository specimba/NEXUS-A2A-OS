"""Calibrated Hallucination Detector — wraps LG tracker with adaptive thresholds.

Adds calibration layer on top of LandauGinzburgTrackerV2's existing
EPRDetector (entropy production rate) and LG order parameters:
  1. Tracks FP/FN rates across sessions to calibrate thresholds
  2. Adaptive threshold adjustment based on calibration history
  3. Cross-session learning via A2A channel emit (Plan 20)
  4. Self-correction signal for re-generation when hallucination detected

Usage:
    detector = CalibratedHallucinationDetector()
    result = detector.assess(logits, position=0, temperature=1.0)
    # {"risk": "low"|"medium"|"high", "calibrated": True, ...}
"""
from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CALIBRATION_STATE_FILE = Path(os.path.expanduser("~")) / ".nexus" / "calibration_state.json"

# Default calibration thresholds (Plan 18 quota-style: yellow/orange/red)
RISK_LOW = 0.25
RISK_MEDIUM = 0.40
RISK_HIGH = 0.60
HIGH_SENSITIVITY_THRESHOLD = 0.40
HIGH_SENSITIVITY_BEBOP_WEIGHT = 0.30


class CalibratedHallucinationDetector:
    """Calibrated hallucination risk detector.

    Wraps the LG tracker's EPR detector with adaptive thresholds,
    calibration tracking, and cross-session learning.
    """

    def __init__(
        self,
        threshold: float = 2.5,
        calibration_window: int = 100,
        a2a_channel: str | None = None,
        adaptive: bool = True,
        bebop_weight: float = 0.15,
        bebop_tau: float = 0.40,
        high_sensitivity: bool = False,
    ):
        """
        Args:
            bebop_weight: 0.0 disables the Bebop TV-distribution signal (default).
                         Recommended range: 0.1 — 0.25. Anything >= 0.5 may
                         double-count a high-drift case alongside the EPR.
            bebop_tau: TV-distance threshold that maps to ~0.5 risk score.
            high_sensitivity: If True, tightens thresholds for more aggressive detection.
        """
        self.base_threshold = threshold
        self.bebop_weight = float(bebop_weight)
        self.bebop_tau = float(bebop_tau)
        if high_sensitivity:
            # Order matters: bebop_weight must exist before this max() (the
            # old code read it pre-assignment -> AttributeError, and the
            # later unconditional assignment silently discarded the boost).
            self.base_threshold = HIGH_SENSITIVITY_THRESHOLD
            self.bebop_weight = max(self.bebop_weight, HIGH_SENSITIVITY_BEBOP_WEIGHT)
        self.calibration_window = calibration_window
        self.a2a_channel = a2a_channel
        self.adaptive = adaptive

        self._tracker = None
        self._epr = None
        self._calibration_history: deque[dict[str, Any]] = deque(maxlen=calibration_window)
        self._stats: dict[str, Any] = {
            "total_assessments": 0,
            "high_risk": 0,
            "medium_risk": 0,
            "low_risk": 0,
            "calibrated_threshold": threshold,
            "adaptations": 0,
            "bebop_weight": self.bebop_weight,
            "bebop_tau": self.bebop_tau,
            "bebop_contributions": 0,
        }
        self._load_calibration()

    @property
    def tracker(self):
        if self._tracker is None:
            from nexus_os.twave.landau_ginzburg_tracker_v2 import LandauGinzburgTrackerV2
            self._tracker = LandauGinzburgTrackerV2()
        return self._tracker

    @property
    def epr(self):
        if self._epr is None:
            from nexus_os.twave.landau_ginzburg_tracker_v2 import EPRDetector
            self._epr = EPRDetector()
        return self._epr

    def _load_calibration(self):
        if CALIBRATION_STATE_FILE.exists():
            try:
                data = json.loads(CALIBRATION_STATE_FILE.read_text(encoding="utf-8"))
                self._calibration_history.extend(data.get("history", []))
                cal_threshold = data.get("calibrated_threshold")
                if cal_threshold and self.adaptive:
                    self._stats["calibrated_threshold"] = cal_threshold
                self._stats["adaptations"] = data.get("adaptations", 0)
            except Exception:
                pass

    #: Persist calibration every N assessments. assess() used to write the
    #: JSON state file on EVERY call — a disk write per token, unusable on
    #: the hot inference path.
    PERSIST_EVERY = 25

    def _save_calibration(self, force: bool = True):
        if not force and self._stats["total_assessments"] % self.PERSIST_EVERY != 0:
            return
        CALIBRATION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CALIBRATION_STATE_FILE.write_text(json.dumps({
            "history": list(self._calibration_history),
            "calibrated_threshold": self._stats["calibrated_threshold"],
            "adaptations": self._stats["adaptations"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    def flush_calibration(self):
        """Force-persist calibration state (call at end of a generation)."""
        self._save_calibration(force=True)

    def _emit_a2a(self, message: str, topic: str = "hallucination"):
        if not self.a2a_channel:
            return
        channels_dir = Path(self.a2a_channel)
        channels_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "sender": "calibrated-hallucination-detector",
            "message": message,
            "topic": topic,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            (channels_dir / f"{topic}.jsonl").write_text(
                json.dumps(entry, ensure_ascii=False) + "\n", encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("A2A emit failed: %s", exc)

    def _get_effective_threshold(self) -> float:
        """Return the current effective threshold (calibrated or base)."""
        return self._stats.get("calibrated_threshold", self.base_threshold)

    def _adapt_threshold(self, was_correct: bool):
        """Adapt threshold based on calibration feedback."""
        if not self.adaptive:
            return
        current = self._get_effective_threshold()
        if was_correct:
            # True positive — threshold is working, nudge slightly conservative
            new_threshold = current * 0.98
        else:
            # False positive — threshold too sensitive, raise it
            new_threshold = current * 1.05
        new_threshold = max(1.0, min(5.0, new_threshold))
        if abs(new_threshold - current) > 0.01:
            self._stats["calibrated_threshold"] = new_threshold
            self._stats["adaptations"] += 1
            self._emit_a2a(
                f"Threshold adapted: {current:.2f} -> {new_threshold:.2f} "
                f"(correct={was_correct})", topic="hallucination-calibration",
            )

    def assess(
        self,
        logits: Any = None,
        *,
        position: int = 0,
        temperature: float = 1.0,
        topk_probs: list[float] | None = None,
        hidden_state: Any = None,
    ) -> dict[str, Any]:
        """Assess hallucination risk for current token position.

        Uses the LG tracker's EPR + order parameters, applies calibrated
        threshold, returns risk level with evidence.
        """
        self._stats["total_assessments"] += 1
        t0 = time.time()

        # Run LG tracker step
        step_result = self.tracker.step(
            position=position,
            logits=logits,
            current_temperature=temperature,
            topk_probs=topk_probs,
            hidden_state=hidden_state,
        )

        # Run EPR detector
        if topk_probs:
            self.epr.step(topk_probs, temperature=temperature)
        epr_risk = self.epr.is_hallucination_risk(
            threshold=self._get_effective_threshold(), temperature=temperature,
        )

        report = self.tracker.get_report()
        # TrackerReport is a dataclass (no .get()). Pull the latest order
        # parameters and LG states for "energy"/"entropy".
        latest_op = None
        latest_lg = None
        if report.order_parameters:
            latest_op = report.order_parameters[-1]
        if report.lg_states:
            latest_lg = report.lg_states[-1]
        lg_energy = latest_lg.free_energy if latest_lg else 0.0
        entropy = latest_op.entropy if latest_op else 0.0

        # Combined risk scoring
        raw_risk_score = 0.0
        reasons = []

        if epr_risk:
            raw_risk_score += 0.5
            reasons.append("high_epr")

        if lg_energy and lg_energy > 0.8:
            raw_risk_score += 0.3
            reasons.append("high_lg_energy")

        if entropy and entropy > 0.7:
            raw_risk_score += 0.2
            reasons.append("high_entropy")

        # Bebop (P2.1) TV-distribution signal — bounded gradient, entropy-invariant.
        bebop_risk = 0.0
        bebop_class = None
        bebop_signal = None
        if self.bebop_weight > 0.0 and topk_probs:
            try:
                from nexus_os.monitoring.bebop_signal import (
                    assess_bebop,
                    risk_score_from_bebop,
                )
                bebop_signal = assess_bebop(topk_probs)
                bebop_risk = risk_score_from_bebop(bebop_signal, tau=self.bebop_tau)
                if bebop_signal.divergence_class != "well_calibrated":
                    raw_risk_score += self.bebop_weight * bebop_risk
                    reasons.append(f"bebop_{bebop_signal.divergence_class}")
                    bebop_class = bebop_signal.divergence_class
                    self._stats["bebop_contributions"] += 1
            except Exception as exc:
                logger.debug("Bebop assessment skipped: %s", exc)

        raw_risk_score = min(1.0, raw_risk_score)
        current_threshold = self._get_effective_threshold()

        # Risk classification (Plan 18 quota-style: low/medium/high)
        if raw_risk_score >= RISK_HIGH:
            risk_level = "high"
            self._stats["high_risk"] += 1
        elif raw_risk_score >= RISK_MEDIUM:
            risk_level = "medium"
            self._stats["medium_risk"] += 1
        else:
            risk_level = "low"
            self._stats["low_risk"] += 1

        elapsed = time.time() - t0
        result = {
            "risk": risk_level,
            "score": round(raw_risk_score, 3),
            "threshold": round(current_threshold, 3),
            "calibrated": self.adaptive,
            "reasons": reasons,
            "lg_energy": round(lg_energy, 3) if lg_energy else None,
            "entropy": round(entropy, 3) if entropy else None,
            "epr_risk": bool(epr_risk),
            "position": position,
            "elapsed_ms": round(elapsed * 1000, 1),
            "bebop": {
                "enabled": self.bebop_weight > 0.0,
                "risk": round(bebop_risk, 3),
                "class": bebop_class,
                "tv": round(bebop_signal.tv, 3) if bebop_signal else None,
                "weight": self.bebop_weight,
            },
            "tracker_report": {
                "mode": (latest_lg.effective_temperature if latest_lg else None),
                "specific_heat": (latest_lg.specific_heat if latest_lg else None),
                "is_critical": (latest_lg.is_critical if latest_lg else None),
                "is_hallucinating": (latest_lg.is_hallucinating if latest_lg else None),
                "attention_mass": (latest_op.attention_mass if latest_op else None),
                "reward_density": (latest_op.reward_density if latest_op else None),
            } if latest_lg or latest_op else None,
        }

        # Record in calibration history
        self._calibration_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "risk": risk_level,
            "score": raw_risk_score,
            "position": position,
        })

        self._save_calibration(force=False)

        # Emit high-risk events to A2A
        if risk_level == "high":
            self._emit_a2a(
                f"High hallucination risk at pos {position} "
                f"(score={raw_risk_score:.2f}, threshold={current_threshold:.2f})",
                topic="hallucination-alert",
            )

        return result

    def record_feedback(self, was_correct: bool):
        """Record calibration feedback and adapt threshold."""
        self._adapt_threshold(was_correct)

    def get_stats(self) -> dict[str, Any]:
        return dict(self._stats)

    def get_calibration_history(self) -> list[dict[str, Any]]:
        return list(self._calibration_history)


def cli_main():
    import argparse
    ap = argparse.ArgumentParser(description="Calibrated Hallucination Detector (P1 + Bebop P2.1)")
    ap.add_argument("--assess", type=float, nargs="*", default=None,
                    help="Assess token logits/probs (pass space-separated floats)")
    ap.add_argument("--feedback", type=bool, default=None,
                    help="Record calibration feedback (True=correct, False=FP)")
    ap.add_argument("--status", action="store_true", help="Show stats + calibration state")
    ap.add_argument("--a2a-channel", default=None, help="A2A channels directory (Plan 20)")
    ap.add_argument("--bebop-weight", type=float, default=0.15,
                    help="Weight for Bebop TV-distribution signal (0.0 disables)")
    ap.add_argument("--bebop-tau", type=float, default=0.40,
                    help="TV-distance threshold (tau) mapping to ~0.5 risk")
    args = ap.parse_args()

    chd = CalibratedHallucinationDetector(
        a2a_channel=args.a2a_channel,
        bebop_weight=args.bebop_weight,
        bebop_tau=args.bebop_tau,
    )

    if args.status:
        print(json.dumps({"stats": chd.get_stats(), "history": chd.get_calibration_history()[-10:]}, indent=2))
        return

    if args.feedback is not None:
        chd.record_feedback(args.feedback)
        print(json.dumps({"feedback_recorded": args.feedback, "new_threshold": chd._get_effective_threshold()}, indent=2))
        return

    if args.assess is not None:
        result = chd.assess(topk_probs=args.assess if args.assess else None)
        print(json.dumps(result, indent=2))
        return

    ap.print_help()


if __name__ == "__main__":
    cli_main()
