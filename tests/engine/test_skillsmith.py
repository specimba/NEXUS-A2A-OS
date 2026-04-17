"""tests/engine/test_skillsmith.py — SkillSmith Auto-Discovery Diagnostics"""
import pytest
from nexus_os.engine.skillsmith import SkillSmith
from nexus_os.engine.hermes import SkillRecord

def test_skillsmith_auto_discovery():
    smith = SkillSmith(success_threshold=0.7, min_executions=3)
    
    # 1. Fail initially
    res = smith.evaluate_task_outcome("code", "Refactor the auth module", False, "osman-coder")
    assert res is None
    
    # 2. Succeed 3 times in a row
    smith.evaluate_task_outcome("code", "Refactor the auth module", True, "osman-coder")
    smith.evaluate_task_outcome("code", "Refactor the database module", True, "osman-coder")
    skill = smith.evaluate_task_outcome("code", "Refactor the api module", True, "osman-coder")
    
    # 3. Verify skill was forged
    assert skill is not None
    assert isinstance(skill, SkillRecord)
    assert skill.recommended_model == "osman-coder"
    assert skill.task_type == "code"
    assert skill.success_rate == 0.75  # 3 successes out of 4 tries
    assert "auto_skill_code" in skill.skill_id
    
    # 4. Verify fast-path routing works with the extracted pattern
    fast_path = smith.get_fast_path("refactor the network module")
    assert fast_path is not None
    assert fast_path.skill_id == skill.skill_id
