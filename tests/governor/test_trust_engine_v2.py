"""tests/governor/test_trust_engine_v2.py — TrustEngine v2.2 HARDWALL tests

Covers:
- Logistic scaling (anti-gaming)
- Adaptive temporal decay
- Non-compensatory CRITICAL hard block
- 6-stage CDR state machine
- Asymptotic plateau enforcement
- Vault persistence (stateless mode)
- Research telemetry metrics
- Trust matrix queries
"""

import math
import time
import pytest

from nexus_os.governor.trust_engine_v2 import (
    CDRStage,
    DangerLevel,
    TrustEngineV2,
    TrustRecord,
    TrustUpdateResult,
)


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    return TrustEngineV2(vault=None, baseline=25.0)


@pytest.fixture
def record():
    return TrustRecord(score=50.0)


# ── DangerLevel ──────────────────────────────────────────────────────

class TestDangerLevel:
    def test_enum_values(self):
        assert DangerLevel.SAFE.value == 0
        assert DangerLevel.CRITICAL.value == 4

    def test_label_property(self):
        assert DangerLevel.SAFE.label == "Safe"
        assert DangerLevel.HIGH_RISK.label == "High Risk"
        assert DangerLevel.CRITICAL.label == "Critical"


# ── CDRStage ─────────────────────────────────────────────────────────

class TestCDRStage:
    def test_severity_ordering(self):
        assert CDRStage.NORMAL.severity == 0
        assert CDRStage.DEGRADED_REASONING.severity == 1
        assert CDRStage.COLLAPSE.severity == 5

    def test_severity_is_monotonic(self):
        stages = [
            CDRStage.NORMAL,
            CDRStage.DEGRADED_REASONING,
            CDRStage.MEMORY_CORRUPTION,
            CDRStage.OUTPUT_HALLUCINATION,
            CDRStage.CASCADE,
            CDRStage.COLLAPSE,
        ]
        for i in range(len(stages) - 1):
            assert stages[i].severity < stages[i + 1].severity

    def test_next_stage(self):
        assert CDRStage.NORMAL.next_stage() == CDRStage.DEGRADED_REASONING
        assert CDRStage.CASCADE.next_stage() == CDRStage.COLLAPSE
        assert CDRStage.COLLAPSE.next_stage() == CDRStage.COLLAPSE  # already terminal

    def test_should_escalate_normal_low_trust(self):
        assert CDRStage.NORMAL.should_escalate(trust_score=20.0, regression_events=0)

    def test_should_not_escalate_normal_high_trust(self):
        assert not CDRStage.NORMAL.should_escalate(trust_score=50.0, regression_events=0)

    def test_should_escalate_degraded_on_regressions(self):
        assert CDRStage.DEGRADED_REASONING.should_escalate(trust_score=40.0, regression_events=3)

    def test_should_not_escalate_degraded_few_regressions(self):
        assert not CDRStage.DEGRADED_REASONING.should_escalate(trust_score=40.0, regression_events=1)

    def test_should_escalate_memory_corruption_low_trust(self):
        assert CDRStage.MEMORY_CORRUPTION.should_escalate(trust_score=15.0, regression_events=0)

    def test_should_escalate_output_hallucination_many_regressions(self):
        assert CDRStage.OUTPUT_HALLUCINATION.should_escalate(trust_score=30.0, regression_events=5)

    def test_cascade_never_escalates_via_should_escalate(self):
        assert not CDRStage.CASCADE.should_escalate(trust_score=5.0, regression_events=100)


# ── TrustRecord ──────────────────────────────────────────────────────

class TestTrustRecord:
    def test_defaults(self):
        r = TrustRecord()
        assert r.score == 25.0
        assert r.cdr_stage == CDRStage.NORMAL
        assert r.regression_events == 0
        assert r.history_delta == []

    def test_custom_init(self):
        r = TrustRecord(score=80.0, cdr_stage=CDRStage.CASCADE)
        assert r.score == 80.0
        assert r.cdr_stage == CDRStage.CASCADE


# ── Logistic Scaling (Anti-Grinding) ─────────────────────────────────

class TestLogisticScaling:
    def test_at_center_returns_half_difficulty(self, engine):
        result = engine.logistic_scale(50.0, difficulty=1.0)
        assert abs(result - 0.5) < 0.01

    def test_low_trust_gives_high_scale(self, engine):
        """Anti-grinding: low-trust agents retain normal gain potential."""
        result = engine.logistic_scale(10.0, difficulty=1.0)
        assert result > 0.90  # ~0.924 for trust=10

    def test_high_trust_gives_low_scale(self, engine):
        """Anti-grinding: high-trust agents face severely reduced gains."""
        result = engine.logistic_scale(90.0, difficulty=1.0)
        assert result < 0.05  # ~0.018 for trust=90

    def test_difficulty_multiplier(self, engine):
        base = engine.logistic_scale(50.0, difficulty=1.0)
        doubled = engine.logistic_scale(50.0, difficulty=2.0)
        assert abs(doubled - base * 2) < 0.01

    def test_monotonic_decrease(self, engine):
        """Anti-grinding: scale factor decreases monotonically with trust."""
        prev = engine.logistic_scale(0.0)
        for trust in range(1, 100):
            curr = engine.logistic_scale(float(trust))
            assert curr <= prev, f"scale increased at trust={trust}: {curr} > {prev}"
            prev = curr

    def test_anti_grinding_ratio(self, engine):
        """High-trust gain must be < 5% of low-trust gain (non-linear penalty)."""
        low = engine.logistic_scale(10.0, difficulty=1.0)
        high = engine.logistic_scale(90.0, difficulty=1.0)
        assert high / low < 0.05, f"high/low ratio={high/low:.4f}, expected < 0.05"


# ── Adaptive Decay ───────────────────────────────────────────────────

class TestAdaptiveDecay:
    def test_no_decay_at_baseline(self, engine):
        record = TrustRecord(score=25.0)
        result = engine.adaptive_decay(record)
        assert result == 25.0

    def test_decay_above_baseline(self, engine):
        record = TrustRecord(score=80.0)
        result = engine.adaptive_decay(record)
        assert 25.0 <= result < 80.0

    def test_higher_disagreement_faster_decay(self, engine):
        r1 = TrustRecord(score=80.0, validator_disagreement_rate=0.0)
        r2 = TrustRecord(score=80.0, validator_disagreement_rate=0.5)
        decay1 = engine.adaptive_decay(r1)
        decay2 = engine.adaptive_decay(r2)
        assert decay2 < decay1

    def test_never_decays_below_baseline(self, engine):
        record = TrustRecord(score=26.0, validator_disagreement_rate=1.0)
        result = engine.adaptive_decay(record, base_lambda=10.0)
        assert result >= engine.baseline


# ── Core Update Trust ────────────────────────────────────────────────

class TestUpdateTrust:
    def test_success_increases_trust(self, engine):
        result = engine.update_trust("agent-1", "code", success=True, danger=DangerLevel.SAFE)
        assert result.trust >= 25.0
        assert result.delta > 0

    def test_failure_decreases_trust(self, engine):
        result = engine.update_trust("agent-1", "code", success=False, danger=DangerLevel.SAFE)
        assert result.trust < 25.0
        assert result.delta < 0

    def test_critical_danger_hard_penalty(self, engine):
        engine.update_trust("agent-1", "code", success=True, danger=DangerLevel.SAFE)
        result = engine.update_trust("agent-1", "code", success=True, danger=DangerLevel.CRITICAL)
        assert result.delta == -20.0

    def test_critical_forces_cascade_cdr(self, engine):
        result = engine.update_trust("agent-1", "code", success=True, danger=DangerLevel.CRITICAL)
        assert result.cdr_stage in ("Cascade", "Collapse")

    def test_asymptotic_plateau(self, engine):
        for _ in range(200):
            result = engine.update_trust(
                "agent-1", "code", success=True,
                danger=DangerLevel.SAFE, difficulty=3.0,
            )
        assert result.trust <= 99.5

    def test_trust_never_below_zero(self, engine):
        for _ in range(100):
            result = engine.update_trust("agent-1", "code", success=False, danger=DangerLevel.HIGH_RISK)
        assert result.trust >= 0.0

    def test_update_returns_result_type(self, engine):
        result = engine.update_trust("agent-1", "code", success=True, danger=DangerLevel.SAFE)
        assert isinstance(result, TrustUpdateResult)
        assert result.agent_id == "agent-1"
        assert result.lane == "code"

    def test_difficulty_affects_gain(self, engine):
        r1 = engine.update_trust("agent-a", "code", success=True, danger=DangerLevel.SAFE, difficulty=1.0)
        r2 = engine.update_trust("agent-b", "code", success=True, danger=DangerLevel.SAFE, difficulty=3.0)
        assert r2.delta > r1.delta

    def test_disagreement_rate_stored(self, engine):
        result = engine.update_trust("agent-1", "code", success=True, danger=DangerLevel.SAFE, disagreement_rate=0.7)
        assert result.disagreement_rate == 0.7

    def test_convergence_tracking(self, engine):
        for _ in range(20):
            engine.update_trust("agent-1", "code", success=True, danger=DangerLevel.SAFE)
        record = engine.get_trust("agent-1", "code")
        assert record.convergence_turns >= 0

    def test_regression_events_increment_on_failure(self, engine):
        engine.update_trust("agent-1", "code", success=False, danger=DangerLevel.SAFE)
        engine.update_trust("agent-1", "code", success=False, danger=DangerLevel.SAFE)
        record = engine.get_trust("agent-1", "code")
        assert record.regression_events == 2

    def test_separate_lanes_independent(self, engine):
        engine.update_trust("agent-1", "code", success=True, danger=DangerLevel.SAFE)
        engine.update_trust("agent-1", "review", success=False, danger=DangerLevel.SAFE)
        code_rec = engine.get_trust("agent-1", "code")
        review_rec = engine.get_trust("agent-1", "review")
        assert code_rec.score > review_rec.score


# ── CDR State Machine ────────────────────────────────────────────────

class TestCDRStateMachine:
    def test_collapse_on_very_low_trust(self, engine):
        for _ in range(20):
            engine.update_trust("agent-1", "code", success=False, danger=DangerLevel.HIGH_RISK)
        record = engine.get_trust("agent-1", "code")
        if record.score < 15.0:
            assert record.cdr_stage == CDRStage.COLLAPSE

    def test_escalation_chain(self, engine):
        for _ in range(10):
            engine.update_trust("agent-1", "code", success=False, danger=DangerLevel.CAUTION)
        record = engine.get_trust("agent-1", "code")
        assert record.cdr_stage.severity > CDRStage.NORMAL.severity


# ── Query Methods ────────────────────────────────────────────────────

class TestQueryMethods:
    def test_get_trust_creates_new_record(self, engine):
        record = engine.get_trust("new-agent", "code")
        assert record.score == 25.0

    def test_get_all_records(self, engine):
        engine.update_trust("a1", "code", success=True, danger=DangerLevel.SAFE)
        engine.update_trust("a2", "review", success=True, danger=DangerLevel.SAFE)
        records = engine.get_all_records()
        assert len(records) == 2

    def test_get_research_metrics(self, engine):
        engine.update_trust("agent-1", "code", success=True, danger=DangerLevel.SAFE)
        metrics = engine.get_research_metrics("agent-1", "code")
        assert "convergence_rate" in metrics
        assert "regression_rate" in metrics
        assert "trust_velocity" in metrics
        assert "cdr_stage" in metrics
        assert metrics["total_validations"] == 1

    def test_get_research_metrics_unknown_agent(self, engine):
        metrics = engine.get_research_metrics("unknown", "code")
        assert metrics["current_trust"] == engine.baseline
        assert metrics["total_validations"] == 0

    def test_get_trust_matrix(self, engine):
        engine.update_trust("a1", "code", success=True, danger=DangerLevel.SAFE)
        engine.update_trust("a1", "review", success=False, danger=DangerLevel.SAFE)
        matrix = engine.get_trust_matrix()
        assert len(matrix) == 2
        assert all("agent_id" in entry for entry in matrix)
        assert all("lane" in entry for entry in matrix)


# ── Stateless Mode ───────────────────────────────────────────────────

class TestStatelessMode:
    def test_operates_without_vault(self):
        engine = TrustEngineV2(vault=None)
        result = engine.update_trust("a1", "code", success=True, danger=DangerLevel.SAFE)
        assert result.trust > 0

    def test_cache_persists_within_session(self):
        engine = TrustEngineV2(vault=None)
        engine.update_trust("a1", "code", success=True, danger=DangerLevel.SAFE)
        engine.update_trust("a1", "code", success=True, danger=DangerLevel.SAFE)
        record = engine.get_trust("a1", "code")
        assert record.total_validations == 2


# ── Stress / Invariant Tests ─────────────────────────────────────────

class TestStressInvariants:
    def test_500_updates_stays_bounded(self):
        engine = TrustEngineV2(vault=None)
        import random
        random.seed(42)
        for _ in range(500):
            success = random.random() > 0.3
            danger = random.choice(list(DangerLevel))
            diff = random.uniform(0.5, 3.0)
            result = engine.update_trust("stress-agent", "code", success=success, danger=danger, difficulty=diff)
            assert 0.0 <= result.trust <= 99.5

    def test_peak_score_tracked(self):
        engine = TrustEngineV2(vault=None)
        for _ in range(50):
            engine.update_trust("a1", "code", success=True, danger=DangerLevel.SAFE, difficulty=2.0)
        record = engine.get_trust("a1", "code")
        assert record.peak_score >= record.score

    def test_history_delta_bounded(self):
        engine = TrustEngineV2(vault=None)
        for _ in range(200):
            engine.update_trust("a1", "code", success=True, danger=DangerLevel.SAFE)
        record = engine.get_trust("a1", "code")
        assert len(record.history_delta) <= engine.MAX_HISTORY_LENGTH
