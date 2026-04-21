"""tests/engine/test_skill_smith.py — SkillSmith v2.1 Full Test Suite"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from nexus_os.engine.skill_smith import (
    SkillRecord,
    SkillSmith,
    SkillStatus,
    TaskOutcome,
    _hash_pattern,
    _jaccard,
)

PATTERN_A = "write unit test for function"
PATTERN_B = "write integration test for api"
PATTERN_C = "deploy kubernetes cluster"


def _outcome(
    pattern=PATTERN_A,
    task_type="code",
    success=True,
    quality=0.9,
    tokens=500,
    latency=1000,
    model="osman-coder",
    ts=0.0,
):
    return TaskOutcome(
        task_id=f"t-{pattern[:4]}-{ts}",
        task_type=task_type,
        domain=task_type,
        pattern_hash=_hash_pattern(pattern),
        pattern=pattern,
        model_used=model,
        success=success,
        quality_score=quality,
        tokens_used=tokens,
        execution_time_ms=latency,
        timestamp=ts or time.time(),
    )


def _smith(t=0.0):
    clock = [t]
    return SkillSmith(clock=lambda: clock[0]), clock


def _fill(smith, n, pattern=PATTERN_A, success=True):
    for _ in range(n):
        smith.record_outcome(_outcome(pattern=pattern, success=success))


class TestPureFunctions:
    def test_jaccard_identical(self):
        assert _jaccard("a b c", "a b c") == 1.0

    def test_jaccard_disjoint(self):
        assert _jaccard("a b", "c d") == 0.0

    def test_jaccard_partial(self):
        score = _jaccard("write unit test function", "write integration test api")
        assert 0.2 < score < 0.8


class TestOutcomeRecording:
    def test_single_no_skill(self):
        smith, _ = _smith()
        smith.record_outcome(_outcome())
        assert len(smith._skills) == 0

    def test_below_threshold_no_skill(self):
        smith, _ = _smith()
        _fill(smith, SkillSmith.MIN_OUTCOMES - 1)
        assert len(smith._skills) == 0

    def test_at_threshold_is_candidate(self):
        smith, _ = _smith()
        _fill(smith, SkillSmith.MIN_OUTCOMES)
        skill = next(iter(smith._skills.values()))
        assert skill.status == SkillStatus.CANDIDATE

    def test_above_threshold_is_testing(self):
        smith, _ = _smith()
        _fill(smith, SkillSmith.MIN_OUTCOMES + 1)
        skill = next(iter(smith._skills.values()))
        assert skill.status == SkillStatus.TESTING


class TestExecutionCount:
    def test_no_double_count(self):
        smith, _ = _smith()
        _fill(smith, SkillSmith.MIN_OUTCOMES)
        skill = next(iter(smith._skills.values()))
        assert skill.execution_count == SkillSmith.MIN_OUTCOMES

    def test_success_plus_failure_equals_total(self):
        smith, _ = _smith()
        _fill(smith, 4, success=True)
        _fill(smith, 2, success=False)
        skill = next(iter(smith._skills.values()))
        assert skill.success_count + skill.failure_count == skill.execution_count


class TestLifecycle:
    def test_registered_after_window_good_rate(self):
        smith, clock = _smith(0.0)
        _fill(smith, 5, success=True)
        clock[0] = SkillSmith.TESTING_WINDOW + 1
        smith.record_outcome(_outcome(success=True))
        assert next(iter(smith._skills.values())).status == SkillStatus.REGISTERED

    def test_deprecated_after_window_bad_rate(self):
        smith, clock = _smith(0.0)
        _fill(smith, 4, success=True)
        _fill(smith, 4, success=False)
        clock[0] = SkillSmith.TESTING_WINDOW + 1
        smith.record_outcome(_outcome(success=False))
        assert next(iter(smith._skills.values())).status == SkillStatus.DEPRECATED

    def test_manual_registration_bypasses_window(self):
        smith, _ = _smith()
        skill = SkillRecord(
            skill_id="m1",
            name="M",
            task_type="code",
            pattern="p",
            pattern_hash=_hash_pattern("p"),
            recommended_model="m",
            domain="code",
        )
        smith.register_skill_manual(skill)
        assert smith._skills["m1"].status == SkillStatus.REGISTERED
        assert smith._skills["m1"].confidence == 1.0


class TestFastPath:
    def _register(self, smith, pattern):
        record = SkillRecord(
            skill_id=_hash_pattern(pattern)[:12],
            name="T",
            task_type="code",
            pattern=pattern,
            pattern_hash=_hash_pattern(pattern),
            recommended_model="m",
            domain="code",
            confidence=0.92,
        )
        smith.register_skill_manual(record)
        return record

    def test_exact_match(self):
        smith, _ = _smith()
        self._register(smith, PATTERN_A)
        assert smith.get_skill_for_task("code", PATTERN_A) is not None

    def test_no_match_returns_none(self):
        smith, _ = _smith()
        assert smith.get_skill_for_task("code", "unknown xyz") is None

    def test_low_jaccard_blocked(self):
        smith, _ = _smith()
        self._register(smith, PATTERN_A)
        assert smith.get_skill_for_task("code", PATTERN_C) is None

    def test_fast_path_hit_count(self):
        smith, _ = _smith()
        self._register(smith, PATTERN_A)
        for _ in range(3):
            smith.get_skill_for_task("code", PATTERN_A)
        assert smith._stats["fast_path_hits"] == 3


class TestConfidence:
    def test_none_last_success_zero_recency(self):
        smith, _ = _smith(100.0)
        skill = SkillRecord(
            skill_id="c1",
            name="C",
            task_type="code",
            pattern="p",
            pattern_hash="ph",
            recommended_model="m",
            domain="code",
            execution_count=20,
            success_rate=0.8,
            last_success=None,
        )
        confidence = smith._calc_confidence(skill)
        assert confidence < 0.40 * 0.8 + 0.40

    def test_zero_float_last_success_not_falsy(self):
        smith, _ = _smith(3600.0)
        skill = SkillRecord(
            skill_id="c2",
            name="C",
            task_type="code",
            pattern="p",
            pattern_hash="ph",
            recommended_model="m",
            domain="code",
            execution_count=10,
            success_rate=0.9,
            last_success=0.0,
        )
        assert smith._calc_confidence(skill) > 0


class TestPersistence:
    def test_save_load_roundtrip(self):
        smith, _ = _smith()
        _fill(smith, 5)
        path = os.path.join(os.getcwd(), f"skill_smith_roundtrip_{time.time_ns()}.json")
        try:
            assert smith.save_skills(path)
            loaded = SkillSmith()
            assert loaded.load_skills(path)
            assert len(loaded._skills) == len(smith._skills)
            for skill_id, skill in smith._skills.items():
                assert loaded._skills[skill_id].status == skill.status
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_load_nonexistent(self):
        smith, _ = _smith()
        assert smith.load_skills("/no/such/file.json") is False


class TestCallbacks:
    def test_created_fires(self):
        smith, _ = _smith()
        events = []
        smith.on_change(lambda event, _: events.append(event))
        _fill(smith, SkillSmith.MIN_OUTCOMES)
        assert "skill_created" in events

    def test_testing_fires(self):
        smith, _ = _smith()
        events = []
        smith.on_change(lambda event, _: events.append(event))
        _fill(smith, SkillSmith.MIN_OUTCOMES + 1)
        assert "skill_testing" in events

    def test_callback_exception_safe(self):
        smith, _ = _smith()
        smith.on_change(lambda event, skill: (_ for _ in ()).throw(RuntimeError("boom")))
        _fill(smith, 5)


class TestTTL:
    def test_old_outcomes_evicted(self):
        smith = SkillSmith(clock=lambda: 200.0, outcome_ttl=100.0)
        smith.record_outcome(_outcome(ts=50.0))
        pattern_hash = _hash_pattern(PATTERN_A)
        assert len(smith._outcomes.get(pattern_hash, [])) == 0


class TestStatistics:
    def test_stats_keys(self):
        smith, _ = _smith()
        stats = smith.get_stats()
        for key in (
            "total_outcomes",
            "total_skills",
            "registered",
            "testing",
            "candidate",
            "fast_path_hits",
            "fast_path_rate%",
        ):
            assert key in stats
