"""engine/skillsmith.py — AutoSkill Forge implementation for NEXUS OS"""
import logging
import re
from typing import Dict, List, Optional
from dataclasses import asdict
from nexus_os.engine.hermes import SkillRecord

logger = logging.getLogger(__name__)

class SkillSmith:
    """
    Monitors execution outcomes and auto-discovers reusable skills.
    Implementation of AutoSkill Forge (Rank #4 requested feature).
    """
    def __init__(self, success_threshold: float = 0.85, min_executions: int = 3):
        self.success_threshold = success_threshold
        self.min_executions = min_executions
        self.skill_registry: Dict[str, SkillRecord] = {}
        self._task_history: Dict[str, List[bool]] = {}

    def _extract_pattern(self, prompt: str) -> str:
        """Heuristically extract a matching pattern from a successful prompt."""
        words = prompt.strip().split()[:3]
        if not words:
            return "^.*$"
        prefix = " ".join(words).lower()
        return f"^{re.escape(prefix)}.*"

    def evaluate_task_outcome(self, task_type: str, prompt: str, success: bool, model_used: str) -> Optional[SkillRecord]:
        """
        Called after a task executes. If a task type repeatedly succeeds 
        with a specific model, promote it to a fast-path Skill.
        """
        history_key = f"{task_type}::{model_used}"
        
        if history_key not in self._task_history:
            self._task_history[history_key] = []
            
        self._task_history[history_key].append(success)
        history = self._task_history[history_key]
        
        if len(history) >= self.min_executions:
            success_rate = sum(history) / len(history)
            
            if success_rate >= self.success_threshold:
                # Auto-discover and register the skill
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
                logger.info(f"SkillSmith forged new skill: {skill_id} for {model_used} (Pattern: {pattern})")
                
                # Reset history to prevent duplicate triggering
                self._task_history[history_key] = []
                return new_skill
                
        return None

    def get_fast_path(self, prompt: str) -> Optional[SkillRecord]:
        """Check if a prompt matches any forged skills for fast-path routing."""
        prompt_lower = prompt.lower()
        for skill in self.skill_registry.values():
            try:
                if re.match(skill.pattern, prompt_lower):
                    return skill
            except re.error:
                continue
        return None
