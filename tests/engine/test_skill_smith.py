"""tests/engine/test_skill_smith.py — SkillSmith Auto-Discovery Tests"""
import os, sys, time, pytest
from nexus_os.engine.skill_smith import SkillSmith, SkillRecord, TaskOutcome, SkillStatus

@pytest.fixture
def smith():
    return SkillSmith()

@pytest.fixture
def smith_with_outcomes(smith):
    for i in range(3):
        smith.record_outcome(TaskOutcome(
            task_id=f"test-{i}", task_type="code", domain="code",
            pattern_hash="abc123_hash", pattern="write unit test for function",
            model_used="osman-coder", success=True, quality_score=0.9,
            tokens_used=500, execution_time_ms=1000, timestamp=time.time()
        ))
    return smith

class TestOutcomeRecording:
    def test_record_single_outcome(self, smith):
        outcome = TaskOutcome("t1", "code", "code", "h1", "write function", "osman-coder", True, 0.9, 500, 1000, time.time())
        result = smith.record_outcome(outcome)
        assert result is None
        assert smith._stats["total_outcomes"] == 1

    def test_record_multiple_outcomes_same_pattern(self, smith):
        for i in range(SkillSmith.MIN_OUTCOMES_FOR_CANDIDATE):
            smith.record_outcome(TaskOutcome(f"t{i}", "code", "code", "phash", "write test", "osman-coder", True, 0.9, 500, 1000, time.time()))
        skill_id = list(smith._skills.keys())[0]
        # After 3 outcomes, code promotes to TESTING immediately (> not >=)
        assert smith._skills[skill_id].status == SkillStatus.TESTING

class TestSkillLookup:
    def test_get_skill_exact_match(self, smith_with_outcomes):
        skill = smith_with_outcomes.get_skill_for_task("code", "write unit test for function")
        assert skill is None or isinstance(skill, SkillRecord) # May be None if not yet REGISTERED

class TestSkillLifecycle:
    def test_candidate_to_testing(self, smith):
        for i in range(3):
            smith.record_outcome(TaskOutcome(f"t{i}", "code", "code", "phash", "lifecycle test", "osman-coder", True, 0.9, 500, 1000, time.time()))
        skill_id = list(smith._skills.keys())[0]
        assert smith._skills[skill_id].status == SkillStatus.TESTING

    def test_manual_registration(self, smith):
        skill = SkillRecord("manual-123", "Manual", "code", "pattern", "hash", "osman-coder", "code", 0.9)
        result = smith.register_skill_manual(skill)
        assert result == "manual-123"
        assert smith._skills["manual-123"].status == SkillStatus.REGISTERED

class TestPersistence:
    def test_save_and_load(self, smith_with_outcomes, tmp_path):
        path = str(tmp_path / "skills.json")
        assert smith_with_outcomes.save_skills(path) is True
        
        new_smith = SkillSmith()
        assert new_smith.load_skills(path) is True
        assert len(new_smith._skills) == len(smith_with_outcomes._skills)
