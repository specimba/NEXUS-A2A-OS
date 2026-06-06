"""Legacy SkillSmith import path shim.

The canonical implementation lives in `skill_smith.py`. This module preserves
the older `nexus_os.engine.skillsmith` API so existing callers keep working
while the repo converges on a single implementation source.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

from .skill_smith import SkillRecord, _hash_pattern

logger = logging.getLogger(__name__)

__all__ = ["SkillSmith", "SkillRecord"]


class SkillSmith:
    """Backward-compatible facade over the canonical SkillSmith model."""

    def __init__(self, success_threshold: float = 0.85, min_executions: int = 3):
        self.success_threshold = success_threshold
        self.min_executions = min_executions
        self.skill_registry: Dict[str, SkillRecord] = {}
        self._task_history: Dict[str, List[bool]] = {}

    def _extract_pattern(self, prompt: str) -> str:
        # Legacy fast-path matching worked better with a broader prefix.
        words = prompt.strip().split()[:2]
        if not words:
            return "^.*$"
        prefix = " ".join(words).lower()
        return f"^{re.escape(prefix)}.*"

    def evaluate_task_outcome(
        self,
        task_type: str,
        prompt: str,
        success: bool,
        model_used: str,
    ) -> Optional[SkillRecord]:
        """Preserve the older auto-forge workflow on top of canonical records."""
        history_key = f"{task_type}::{model_used}"
        history = self._task_history.setdefault(history_key, [])
        history.append(success)

        if len(history) < self.min_executions:
            return None

        success_count = sum(history)
        success_rate = success_count / len(history)
        if success_rate < self.success_threshold:
            return None

        pattern = self._extract_pattern(prompt)
        skill_id = f"auto_skill_{task_type}_{len(self.skill_registry)}"
        skill = SkillRecord(
            skill_id=skill_id,
            name=f"Auto-discovered {task_type} skill",
            task_type=task_type,
            pattern=pattern,
            pattern_hash=_hash_pattern(pattern),
            recommended_model=model_used,
            domain=task_type,
            success_rate=success_rate,
            execution_count=len(history),
            success_count=success_count,
            failure_count=len(history) - success_count,
        )

        self.skill_registry[skill_id] = skill
        self._task_history[history_key] = []
        logger.info(
            "SkillSmith forged compatibility skill %s for %s (pattern=%s)",
            skill_id,
            model_used,
            pattern,
        )
        return skill

    def get_fast_path(self, prompt: str) -> Optional[SkillRecord]:
        prompt_lower = prompt.lower()
        for skill in self.skill_registry.values():
            try:
                if re.match(skill.pattern, prompt_lower):
                    return skill
            except re.error:
                continue
        return None
