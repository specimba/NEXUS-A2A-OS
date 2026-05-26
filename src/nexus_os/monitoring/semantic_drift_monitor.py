"""semantic_drift_monitor.py — Lightweight lexical drift detection for multi-turn sessions.

Addresses ERNIE Session06 EV-004 (Chrono-Drift), EV-014 (Viral Load Escalation),
and EV-017 (Thread Pull Extraction). These attacks gradually shift conversation
topics over many turns, with each individual turn appearing benign.

Uses simple word-token Jaccard similarity as a proxy for semantic drift.
No neural embedding model required; runs in <1ms per turn.

Usage:
    from nexus_os.monitoring.semantic_drift_monitor import SemanticDriftMonitor
    monitor = SemanticDriftMonitor()
    monitor.register_session("sess-001", "Tell me about the history of chemistry.")
    alert = monitor.check_turn("sess-001", "What if someone in 1920 wanted to make X?")
    if alert:
        print("Drift detected:", alert)
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class DriftAlert:
    session_id: str
    turn_number: int
    similarity: float
    threshold: float
    reason: str


class SemanticDriftMonitor:
    """Track per-session lexical similarity across conversation turns.

    Threshold curve: as turn count increases, expected similarity drops.
    If actual similarity falls below the curve, emit a DriftAlert.
    """

    # Thresholds as Jaccard similarity (0.0–1.0)
    # These are lower than raw thresholds because we use a *trend* check:
    # alert only when similarity is both below threshold AND monotonically
    # decreasing over the last 3 turns (signature of adversarial thread-pull).
    THRESHOLD_CURVE: dict[int, float] = {
        5: 0.35,
        10: 0.30,
        15: 0.25,
        20: 0.20,
    }
    DEFAULT_THRESHOLD: float = 0.15
    MIN_BASELINE_WORDS: int = 3
    MIN_TURN_BEFORE_ALERT: int = 4
    TREND_WINDOW: int = 3

    def __init__(self):
        # session_id → {
        #   "baseline": set[str],
        #   "recent_tokens": list[set],
        #   "similarity_history": list[float],
        #   "turn_count": int,
        # }
        self._sessions: dict[str, dict] = {}

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Extract lowercase word tokens."""
        return set(re.findall(r"[a-z]+", text.lower()))

    @staticmethod
    def _jaccard(a: set[str], b: set[str]) -> float:
        """Jaccard similarity between two token sets."""
        intersection = len(a & b)
        union = len(a | b)
        if union == 0:
            return 1.0  # both empty → identical
        return intersection / union

    def register_session(self, session_id: str, baseline_text: str) -> None:
        """Register a new session with its first (baseline) turn."""
        tokens = self._tokenize(baseline_text)
        self._sessions[session_id] = {
            "baseline": tokens.copy(),
            "recent_tokens": [tokens.copy()],
            "similarity_history": [1.0],  # baseline vs baseline = perfect
            "turn_count": 0,
        }

    @staticmethod
    def _is_monotonic_decreasing(values: list[float]) -> bool:
        """True if each value is strictly less than the previous."""
        return all(values[i] < values[i - 1] for i in range(1, len(values)))

    def check_turn(self, session_id: str, turn_text: str) -> Optional[DriftAlert]:
        """Check a new turn for semantic drift against the session baseline.

        Uses a sliding baseline + trend detection:
        - Sliding baseline = union of last 3 turns (allows benign topic pivots)
        - Trend check = alert only if similarity is monotonically decreasing
          over the last TREND_WINDOW turns AND below threshold.

        This catches adversarial "thread-pull" escalation (EV-004/014/017)
        while tolerating normal conversational topic shifts.
        """
        sess = self._sessions.get(session_id)
        if sess is None:
            # Auto-register if first turn
            self.register_session(session_id, turn_text)
            return None

        sess["turn_count"] += 1
        turn_n = sess["turn_count"]

        # Skip very short turns (greetings, yes/no, etc.)
        tokens = self._tokenize(turn_text)
        if len(tokens) < self.MIN_BASELINE_WORDS:
            return None

        # Sliding baseline = union of last 3 turns (tracks topic cluster)
        sess["recent_tokens"].append(tokens.copy())
        if len(sess["recent_tokens"]) > 3:
            sess["recent_tokens"].pop(0)
        sliding_baseline = set().union(*sess["recent_tokens"])
        similarity = self._jaccard(sliding_baseline, tokens)
        sess["similarity_history"].append(similarity)

        # Only alert after enough turns
        if turn_n < self.MIN_TURN_BEFORE_ALERT:
            return None

        # Determine threshold from curve
        threshold = self.DEFAULT_THRESHOLD
        for max_turn, thresh in sorted(self.THRESHOLD_CURVE.items()):
            if turn_n <= max_turn:
                threshold = thresh
                break

        # Core logic: below threshold AND monotonically decreasing trend
        if similarity < threshold:
            hist = sess["similarity_history"]
            if len(hist) >= self.TREND_WINDOW + 1:
                recent = hist[-self.TREND_WINDOW:]
                if self._is_monotonic_decreasing(recent):
                    return DriftAlert(
                        session_id=session_id,
                        turn_number=turn_n,
                        similarity=round(similarity, 3),
                        threshold=threshold,
                        reason=(
                            f"similarity {similarity:.3f} < threshold {threshold} "
                            f"at turn {turn_n}; monotonic-decrease trend detected"
                        ),
                    )
        return None

    def reset_session(self, session_id: str) -> None:
        """Drop session state."""
        self._sessions.pop(session_id, None)

    def session_count(self) -> int:
        """Return number of active sessions."""
        return len(self._sessions)
