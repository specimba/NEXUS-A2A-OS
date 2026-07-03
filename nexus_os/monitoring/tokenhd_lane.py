"""TokenHD supervised token-level hallucination lane (papers10, arXiv 2605.12384).

TOKENHD trains a small (0.6B-8B) detector that operates directly on
free-form text and emits a score sequence s_i in [0, 1] per response token
— no step segmentation, no reformatting. A threshold binarizes the scores
into flagged token indexes; consecutive indexes group into hallucinated
spans. This is a *supervised, learned* signal, complementary to the LG
tracker's unsupervised order parameters and the Bebop TV signal, and it
targets the reasoning-hallucination case (coherent-looking logical errors)
those are weakest on.

This module is the SCAFFOLD lane: the classifier itself is pluggable
(``TokenHDClassifier`` protocol) so the trained detector can be dropped in
later — hosted behind an HTTP endpoint (``HTTPTokenHDClassifier``, resolved
from ``NEXUS_TOKENHD_ENDPOINT``) or in-process. Until then the lane stays
dark: CalibratedHallucinationDetector gates it behind ``tokenhd_weight``
(default 0.0) and fails safe to a zero contribution on any classifier
error.

Module boundary (mirrors bebop_signal.py):
  - No model imports at module scope; HTTP client imported lazily.
  - Pure functions own no state; the CHD owns the rolling text window.
"""
from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

#: Default binarization threshold beta for flagged tokens (paper Sec. 2).
DEFAULT_FLAG_THRESHOLD = 0.5

TOKENHD_ENDPOINT_ENV = "NEXUS_TOKENHD_ENDPOINT"


class TokenHDUnavailable(RuntimeError):
    """Raised by classifiers that cannot score right now (lane fails safe)."""


@runtime_checkable
class TokenHDClassifier(Protocol):
    """H(x, y) -> per-token hallucination scores in [0, 1]."""

    name: str

    def score_tokens(self, context: str, tokens: list[str]) -> list[float]:
        """Score each response token; len(result) == len(tokens)."""
        ...


@dataclass
class TokenHDSignal:
    """Result of one token-level hallucination assessment."""

    token_scores: list[float]
    flagged_indices: list[int]
    spans: list[tuple[int, int]]  # inclusive (start, end) index ranges
    max_score: float
    mean_score: float
    flagged_fraction: float
    threshold: float
    classifier: str

    def to_dict(self) -> dict:
        return asdict(self)


def group_spans(indices: list[int]) -> list[tuple[int, int]]:
    """Group consecutive flagged token indexes into inclusive spans.

    Paper Sec. 2: consecutive indices in the flagged set form segments that
    map back to hallucinated text fragments.
    """
    spans: list[tuple[int, int]] = []
    start = prev = None
    for i in indices:
        if start is None:
            start = prev = i
        elif i == prev + 1:
            prev = i
        else:
            spans.append((start, prev))
            start = prev = i
    if start is not None:
        spans.append((start, prev))
    return spans


def assess_tokenhd(
    context: str,
    tokens: list[str],
    classifier: TokenHDClassifier,
    *,
    threshold: float = DEFAULT_FLAG_THRESHOLD,
) -> TokenHDSignal:
    """Run the classifier over the response tokens and structure the result.

    Raises TokenHDUnavailable (propagated from the classifier) when scoring
    is impossible; raises ValueError if the classifier violates the
    per-token contract — both are caught by the CHD lane and fail safe.
    """
    if not tokens:
        return TokenHDSignal(
            token_scores=[], flagged_indices=[], spans=[], max_score=0.0,
            mean_score=0.0, flagged_fraction=0.0, threshold=threshold,
            classifier=getattr(classifier, "name", type(classifier).__name__),
        )
    scores = list(classifier.score_tokens(context, list(tokens)))
    if len(scores) != len(tokens):
        raise ValueError(
            f"TokenHD classifier returned {len(scores)} scores for "
            f"{len(tokens)} tokens"
        )
    scores = [min(1.0, max(0.0, float(s))) for s in scores]
    flagged = [i for i, s in enumerate(scores) if s > threshold]
    return TokenHDSignal(
        token_scores=scores,
        flagged_indices=flagged,
        spans=group_spans(flagged),
        max_score=max(scores),
        mean_score=sum(scores) / len(scores),
        flagged_fraction=len(flagged) / len(scores),
        threshold=threshold,
        classifier=getattr(classifier, "name", type(classifier).__name__),
    )


def risk_score_from_tokenhd(signal: TokenHDSignal) -> float:
    """Map a TokenHD signal to a [0, 1] risk score.

    Blends peak confidence with flagged density: a single certain
    hallucinated token matters (max term), and so does a diffuse cluster
    of moderately suspicious ones (fraction term). Both terms are already
    bounded, so the blend is too.
    """
    if not signal.token_scores:
        return 0.0
    return min(1.0, 0.6 * signal.max_score + 0.4 * signal.flagged_fraction)


class HTTPTokenHDClassifier:
    """Trained-detector client for a hosted TokenHD scorer.

    Expects an OpenAI-compat-adjacent JSON endpoint:
        POST {endpoint}  {"context": str, "tokens": [str]}
          -> {"scores": [float]}
    Any transport or contract error raises TokenHDUnavailable so the lane
    fails safe rather than failing the assessment.
    """

    def __init__(self, endpoint: str, *, timeout: float = 5.0):
        self.endpoint = endpoint
        self.timeout = timeout
        self.name = f"tokenhd-http:{endpoint}"

    def score_tokens(self, context: str, tokens: list[str]) -> list[float]:
        import requests

        try:
            resp = requests.post(
                self.endpoint,
                json={"context": context, "tokens": tokens},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            scores = resp.json().get("scores")
        except Exception as exc:  # transport, JSON, HTTP status
            raise TokenHDUnavailable(f"TokenHD endpoint failed: {exc}") from exc
        if not isinstance(scores, list):
            raise TokenHDUnavailable("TokenHD endpoint returned no 'scores' list")
        return scores


@dataclass
class StubTokenHDClassifier:
    """Deterministic test/dev classifier — NOT a trained detector.

    Scores ``flag_score`` for tokens containing any marker substring and
    ``base_score`` otherwise. Lets integration paths run end-to-end before
    the trained 0.6B detector exists.
    """

    markers: tuple[str, ...] = ("<<HALLU>>",)
    flag_score: float = 0.9
    base_score: float = 0.05
    name: str = field(default="tokenhd-stub")

    def score_tokens(self, context: str, tokens: list[str]) -> list[float]:
        return [
            self.flag_score if any(m in t for m in self.markers) else self.base_score
            for t in tokens
        ]


def resolve_classifier(
    explicit: TokenHDClassifier | None = None,
) -> TokenHDClassifier | None:
    """Pick the lane's classifier: explicit arg > env endpoint > None (dark)."""
    if explicit is not None:
        return explicit
    endpoint = os.environ.get(TOKENHD_ENDPOINT_ENV, "").strip()
    if endpoint:
        return HTTPTokenHDClassifier(endpoint)
    return None
