#!/usr/bin/env python3
import os
import re

ENGINE_DIR = os.path.join("src", "nexus_os", "engine")
TEST_DIR = os.path.join("tests", "engine")
os.makedirs(ENGINE_DIR, exist_ok=True)
os.makedirs(TEST_DIR, exist_ok=True)

SKILLSMITH_CODE = '''"""engine/skillsmith.py — AutoSkill Forge implementation"""
import logging
import re
from typing import Dict, List, Optional
from nexus_os.engine.hermes import SkillRecord

logger = logging.getLogger(__name__)

class SkillSmith:
    """Monitors execution outcomes and auto-discovers reusable skills."""
    def __init__(self, success_threshold: float = 0.85, min_executions: int = 3):
        self.success_threshold = success_threshold
        self.min_executions = min_executions
        self.skill_registry: Dict[str, SkillRecord] = {}
        self._task_history: Dict[str, List[bool]] = {}

    def _extract_pattern(self, prompt: str) -> str:
        words = prompt.strip().split()[:3]
        if not words: return "^.*$"
        prefix = " ".join(words).lower()
        return f"^{re.escape(prefix)}.*"

    def evaluate_task_outcome(self, task_type: str, prompt: str, success: bool, model_used: str) -> Optional[SkillRecord]:
        history_key = f"{task_type}::{model_used}"
        if history_key not in self._task_history:
            self._task_history[history_key] = []
            
        self._task_history[history_key].append(success)
        history = self._task_history[history_key]
        
        if len(history) >= self.min_executions:
            success_rate = sum(history) / len(history)
            if success_rate >= self.success_threshold:
                pattern = self._extract_pattern(prompt)
                skill_id = f"auto_skill_{task_type}_{len(self.skill_registry)}"
                
                new_skill = SkillRecord(
                    skill_id=skill_id,
                    name=f"Auto-discovered {task_type} skill",
                    task_type=task_type,
                    pattern=pattern,
                    recommended_model=model_used,
                    success_rate=success_rate,
                    execution_count=len(history)
                )
                self.skill_registry[skill_id] = new_skill
                self._task_history[history_key] = []
                return new_skill
        return None

    def get_fast_path(self, prompt: str) -> Optional[SkillRecord]:
        prompt_lower = prompt.lower()
        for skill in self.skill_registry.values():
            try:
                if re.match(skill.pattern, prompt_lower): return skill
            except re.error: continue
        return None
'''

TEST_CODE = '''"""tests/engine/test_skillsmith.py — SkillSmith Diagnostics"""
from nexus_os.engine.skillsmith import SkillSmith
from nexus_os.engine.hermes import SkillRecord

def test_skillsmith_auto_discovery():
    smith = SkillSmith(success_threshold=0.70, min_executions=3)
    
    # 1. Fail initially
    res = smith.evaluate_task_outcome("code", "Refactor the auth module", False, "osman-coder")
    assert res is None
    
    # 2. Succeed 3 times
    smith.evaluate_task_outcome("code", "Refactor the auth module", True, "osman-coder")
    smith.evaluate_task_outcome("code", "Refactor the database module", True, "osman-coder")
    skill = smith.evaluate_task_outcome("code", "Refactor the api module", True, "osman-coder")
    
    # 3. Verify skill forged
    assert skill is not None
    assert skill.recommended_model == "osman-coder"
    assert skill.success_rate == 0.75
    
    # 4. Verify fast-path routing
    fast_path = smith.get_fast_path("refactor the network module")
    assert fast_path is not None
    assert fast_path.skill_id == skill.skill_id
'''

with open(os.path.join(ENGINE_DIR, "skillsmith.py"), "w", encoding="utf-8") as f:
    f.write(SKILLSMITH_CODE)
with open(os.path.join(TEST_DIR, "test_skillsmith.py"), "w", encoding="utf-8") as f:
    f.write(TEST_CODE)
print("[✅] P1-1: SkillSmith Builder Ready.")