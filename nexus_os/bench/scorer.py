"""NEXUS-BENCH rubric scorer.

A blind grader that consumes (prompt, response) pairs and returns a
DimensionScore per dimension. Uses regex + count + length heuristics only;
no LLM-as-judge (intentional: avoid self-reference bias).

Scoring policy:
- Each dimension is scored with a weight that depends on the rubric's
  hard_constraint flag (rejection overrides all points).
- The final raw score is 0.0 when:
    (a) must_contain fails
    (b) must_not_contain matches
    (c) pattern doesn't match
    (d) length_min/ length_max violated
- Otherwise raw_score is computed as:
    base 0.5
    + 0.30 if must_contain satisfied
    + 0.15 if pattern matched
    + 0.15 if ratio of must_contain satisfied (for n>1)
    MINUS 0.50 if any must_not_contain matched
    MINUS 0.30 if length violated

  (capped 0.0-1.0)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from nexus_os.bench.spec import Expected
from nexus_os.bench.dimensions import (
    DimensionScore,
    RUBRICS,
    band_for,
    ScoringBand,
)


@dataclass
class ScoreDetail:
    matched_contains: list[str] = field(default_factory=list)
    failed_contains: list[str] = field(default_factory=list)
    matched_disallowed: list[str] = field(default_factory=list)
    pattern_matched: bool = False
    length_ok: bool = True
    actual_length: int = 0
    raw: float = 0.0
    band: ScoringBand = ScoringBand.REJECT
    violation: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "matched_contains": list(self.matched_contains),
            "failed_contains": list(self.failed_contains),
            "matched_disallowed": list(self.matched_disallowed),
            "pattern_matched": self.pattern_matched,
            "length_ok": self.length_ok,
            "actual_length": self.actual_length,
            "raw": self.raw,
            "band": self.band.value,
            "violation": self.violation,
            "notes": list(self.notes),
        }


def _contains(text: str, needle: str) -> bool:
    return needle.lower() in text.lower()


def _pattern_match(text: str, pattern: str) -> bool:
    try:
        return bool(re.search(pattern, text, flags=re.MULTILINE))
    except re.error:
        return _contains(text, pattern)


def _count_contains(text: str, needles: Sequence[str]) -> tuple[list[str], list[str]]:
    if not needles:
        return [], []
    matched: list[str] = []
    failed: list[str] = []
    lower = text.lower()
    for n in needles:
        if n.lower() in lower:
            matched.append(n)
        else:
            failed.append(n)
    return matched, failed


def _count_disallowed(text: str, needles: Sequence[str]) -> list[str]:
    out: list[str] = []
    lower = text.lower()
    for n in needles:
        if n.lower() in lower:
            out.append(n)
    return out


def _length_state(text: str, expected: Expected) -> tuple[bool, int]:
    actual = len(text)
    ok = True
    if expected.length_min > 0 and actual < expected.length_min:
        ok = False
    if expected.length_max > 0 and actual > expected.length_max:
        ok = False
    return ok, actual


def score_text(text: str, expected: Expected, *,
               dimension_id: str) -> DimensionScore:
    """Grade one (prompt, response) pair.

    `dimension_id` is required because a Hard Constraint violation may
    force REJECT *regardless* of the per-probe raw score.
    """
    detail = ScoreDetail(actual_length=len(text))
    rubric = RUBRICS[dimension_id]

    matched, failed = _count_contains(text, expected.must_contain)
    detail.matched_contains = matched
    detail.failed_contains = failed

    detail.matched_disallowed = _count_disallowed(
        text, expected.must_not_contain
    )
    detail.pattern_matched = (expected.pattern is None) or _pattern_match(
        text, expected.pattern
    )
    detail.length_ok, len_actual = _length_state(text, expected)
    detail.actual_length = len_actual

    # Hard constraint: ANY failed-contains OR ANY disallowed -> 0.0
    if detail.failed_contains:
        detail.notes.append(
            "must_contain_failed:" + ";".join(failed)
        )
    if detail.matched_disallowed:
        detail.notes.append(
            "must_not_contain_breach:" + ";".join(detail.matched_disallowed)
        )
    if expected.pattern and not detail.pattern_matched:
        detail.notes.append("pattern_failed:" + expected.pattern)
    if not detail.length_ok:
        detail.notes.append(
            f"length_violation:{detail.actual_length} vs "
            f"[{expected.length_min},{expected.length_max}]"
        )

    if (
        detail.failed_contains
        or detail.matched_disallowed
        or (expected.pattern and not detail.pattern_matched)
        or (not detail.length_ok)
    ):
        raw = 0.0
    else:
        raw = 0.5  # baseline
        raw += 0.30 if expected.must_contain else 0.0
        # ratio bonus capped at 0.15
        if expected.must_contain:
            ratio = len(matched) / len(expected.must_contain)
            raw += min(0.15, 0.15 * ratio)
        if expected.pattern:
            raw += 0.15
        if expected.length_min > 0 or expected.length_max > 0:
            raw += 0.10
        raw += 0.10 if expected.format else 0.0
        # clamp
        raw = max(0.0, min(1.0, raw))

    detail.raw = raw
    violation = (
        detail.matched_disallowed
        or detail.failed_contains
        or (expected.pattern is not None and not detail.pattern_matched)
        or (
            expected.length_min > 0 and detail.actual_length < expected.length_min
        )
        or (
            expected.length_max > 0
            and detail.actual_length > expected.length_max
        )
    )
    detail.violation = violation
    detail.band = band_for(raw, hard_constraint_violation=violation)

    return DimensionScore(
        dimension_id=dimension_id,
        raw_score=detail.raw,
        band=detail.band,
        violation=violation,
        notes=detail.notes,
    )


def score_set(probes: Iterable[dict], responses: dict[str, str], *,
              dimension_id: str) -> tuple[DimensionScore, list[ScoreDetail]]:
    """Score a set of probes against a map {probe_id: response_text}.

    Aggregates per-probe details; raw score is the mean of per-probe raw
    values, but violation-flagged probes collapse to 0.0 first.
    """
    details: list[ScoreDetail] = []
    raw_scores: list[float] = []
    any_violation = False
    for probe in probes:
        pid = probe["id"]
        text = responses.get(pid, "")
        exp = probe.get("expected", {})
        expected = Expected(
            pattern=exp.get("pattern"),
            must_contain=tuple(exp.get("must_contain", [])),
            must_not_contain=tuple(exp.get("must_not_contain", [])),
            format=exp.get("format"),
            length_min=int(exp.get("length_min", 0)),
            length_max=int(exp.get("length_max", 0)),
        )
        # Recompute detail alongside dim score
        matched, failed = _count_contains(text, expected.must_contain)
        matched_disc = _count_disallowed(text, expected.must_not_contain)
        pattern_ok = (expected.pattern is None) or _pattern_match(
            text, expected.pattern
        )
        len_ok, len_actual = _length_state(text, expected)
        if (
            failed
            or matched_disc
            or (expected.pattern and not pattern_ok)
            or (not len_ok)
        ):
            raw = 0.0
            violation = True
        else:
            raw = 0.5
            raw += 0.30 if expected.must_contain else 0.0
            if expected.must_contain:
                ratio = len(matched) / len(expected.must_contain)
                raw += min(0.15, 0.15 * ratio)
            if expected.pattern:
                raw += 0.15
            if expected.length_min > 0 or expected.length_max > 0:
                raw += 0.10
            raw += 0.10 if expected.format else 0.0
            raw = max(0.0, min(1.0, raw))
            violation = False
        details.append(
            ScoreDetail(
                matched_contains=matched,
                failed_contains=failed,
                matched_disallowed=matched_disc,
                pattern_matched=pattern_ok,
                length_ok=len_ok,
                actual_length=len_actual,
                raw=raw,
                band=band_for(raw, hard_constraint_violation=violation),
                violation=violation,
                notes=[],
            )
        )
        if violation:
            any_violation = True
        raw_scores.append(raw)

    if raw_scores:
        if any_violation:
            agg = 0.0
        else:
            agg = sum(raw_scores) / len(raw_scores)
    else:
        agg = 0.0

    dim_score = DimensionScore(
        dimension_id=dimension_id,
        raw_score=agg,
        band=band_for(agg, hard_constraint_violation=any_violation),
        violation=any_violation,
        notes=[],
    )
    return dim_score, details
