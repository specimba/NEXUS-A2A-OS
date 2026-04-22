"""tests/engine/test_skillsmith.py — Legacy SkillSmith compatibility tests."""

from nexus_os.engine.skillsmith import SkillRecord, SkillSmith


def test_skillsmith_auto_discovery():
    smith = SkillSmith(success_threshold=0.7, min_executions=3)

    result = smith.evaluate_task_outcome("code", "Refactor the auth module", False, "osman-coder")
    assert result is None

    smith.evaluate_task_outcome("code", "Refactor the auth module", True, "osman-coder")
    smith.evaluate_task_outcome("code", "Refactor the database module", True, "osman-coder")
    skill = smith.evaluate_task_outcome("code", "Refactor the api module", True, "osman-coder")

    assert skill is not None
    assert isinstance(skill, SkillRecord)
    assert skill.recommended_model == "osman-coder"
    assert skill.task_type == "code"
    assert skill.success_rate == 0.75
    assert skill.skill_id.startswith("auto_skill_code_")

    fast_path = smith.get_fast_path("refactor the network module")
    assert fast_path is not None
    assert fast_path.skill_id == skill.skill_id
