"""engine/skill_smith.py — SkillSmith Auto-Discovery System

Monitors task outcomes and automatically registers successful patterns
as SkillRecords for fast-path routing.
"""
import hashlib
import threading
import time
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

# ── Enums ──────────────────────────────────────────────────────

class SkillStatus(Enum):
    """Skill lifecycle status."""
    CANDIDATE = "candidate"      # Observed, not yet registered
    TESTING = "testing"          # Currently being validated
    REGISTERED = "registered"    # Confirmed, fast-path enabled
    DEPRECATED = "deprecated"    # Success rate dropped
    MERGED = "merged"            # Consolidated with similar skill

# ── Dataclasses ────────────────────────────────────────────────

@dataclass
class TaskOutcome:
    """Outcome of a single task execution."""
    task_id: str
    task_type: str
    domain: str
    pattern_hash: str
    pattern: str
    model_used: str
    success: bool
    quality_score: float  # 0.0 - 1.0
    tokens_used: int
    execution_time_ms: int
    timestamp: float
    error_message: Optional[str] = None

@dataclass
class SkillRecord:
    """Registered skill for fast-path routing."""
    skill_id: str
    name: str
    task_type: str
    pattern: str
    pattern_hash: str
    recommended_model: str
    domain: str
    success_rate: float = 0.0
    avg_quality: float = 0.0
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_tokens: int = 0
    avg_latency_ms: int = 0
    status: SkillStatus = SkillStatus.CANDIDATE
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    last_success: Optional[float] = None
    confidence: float = 0.0

@dataclass
class SkillMetrics:
    """Aggregate metrics for a skill category."""
    total_outcomes: int
    success_count: int
    failure_count: int
    avg_quality: float
    avg_tokens: int
    avg_latency_ms: int
    unique_patterns: int
    models_used: List[str]

# ── SkillSmith Core ────────────────────────────────────────────

class SkillSmith:
    MIN_OUTCOMES_FOR_CANDIDATE = 3
    MIN_SUCCESS_RATE_FOR_REGISTRATION = 0.75
    MIN_CONFIDENCE_FOR_FAST_PATH = 0.80
    TESTING_WINDOW_SECONDS = 3600  # 1 hour
    PATTERN_SIMILARITY_THRESHOLD = 0.85
    MERGE_CANDIDATES_AFTER = 10 

    def __init__(self):
        self._skills: Dict[str, SkillRecord] = {}
        self._outcomes_by_pattern: Dict[str, List[TaskOutcome]] = defaultdict(list)
        self._outcomes_by_task_type: Dict[str, List[TaskOutcome]] = defaultdict(list)
        self._lock = threading.RLock()
        self._callbacks: List[callable] = []
        self._stats = {
            "total_outcomes": 0,
            "skills_created": 0,
            "skills_registered": 0,
            "skills_merged": 0,
            "fast_path_hits": 0,
        }

    def record_outcome(self, outcome: TaskOutcome) -> Optional[str]:
        with self._lock:
            self._stats["total_outcomes"] += 1
            self._outcomes_by_pattern[outcome.pattern_hash].append(outcome)
            self._outcomes_by_task_type[outcome.task_type].append(outcome)
            
            new_skill_id = self._maybe_create_skill(outcome)
            self._update_skills_with_outcome(outcome)
            self._evaluate_skill_status()
            
            return new_skill_id

    def _maybe_create_skill(self, outcome: TaskOutcome) -> Optional[str]:
        pattern_outcomes = self._outcomes_by_pattern.get(outcome.pattern_hash, [])
        if len(pattern_outcomes) < self.MIN_OUTCOMES_FOR_CANDIDATE: return None
        for skill in self._skills.values():
            if skill.pattern_hash == outcome.pattern_hash: return None
            
        metrics = self._compute_pattern_metrics(outcome.pattern_hash)
        skill_id = self._generate_skill_id(outcome.pattern, outcome.task_type)
        
        skill = SkillRecord(
            skill_id=skill_id,
            name=self._generate_skill_name(outcome.pattern, outcome.task_type),
            task_type=outcome.task_type,
            pattern=self._truncate_pattern(outcome.pattern),
            pattern_hash=outcome.pattern_hash,
            recommended_model=outcome.model_used,
            domain=outcome.domain,
            success_rate=metrics.success_rate if hasattr(metrics, 'success_rate') else (metrics.success_count / max(metrics.total_outcomes, 1)),
            avg_quality=metrics.avg_quality,
            execution_count=metrics.total_outcomes,
            success_count=metrics.success_count,
            failure_count=metrics.failure_count,
            avg_tokens=metrics.avg_tokens,
            avg_latency_ms=metrics.avg_latency_ms,
            status=SkillStatus.CANDIDATE,
            confidence=0.0,
        )
        
        self._skills[skill_id] = skill
        self._stats["skills_created"] += 1
        self._notify_callbacks("skill_created", skill)
        return skill_id

    def _update_skills_with_outcome(self, outcome: TaskOutcome):
        for skill in self._skills.values():
            if skill.pattern_hash == outcome.pattern_hash:
                skill.execution_count += 1
                skill.avg_tokens = int((skill.avg_tokens * (skill.execution_count - 1) + outcome.tokens_used) / skill.execution_count)
                skill.avg_latency_ms = int((skill.avg_latency_ms * (skill.execution_count - 1) + outcome.execution_time_ms) / skill.execution_count)
                
                if outcome.success:
                    skill.success_count += 1
                    skill.last_success = outcome.timestamp
                else:
                    skill.failure_count += 1
                
                skill.success_rate = skill.success_count / skill.execution_count
                skill.confidence = self._calculate_confidence(skill)
                skill.last_used = outcome.timestamp

    def _evaluate_skill_status(self):
        now = time.time()
        for skill in list(self._skills.values()):
            if skill.status == SkillStatus.CANDIDATE:
                if skill.execution_count >= self.MIN_OUTCOMES_FOR_CANDIDATE:
                    skill.status = SkillStatus.TESTING
                    self._notify_callbacks("skill_testing", skill)
            elif skill.status == SkillStatus.TESTING:
                testing_duration = now - skill.created_at
                if testing_duration >= self.TESTING_WINDOW_SECONDS:
                    if skill.success_rate >= self.MIN_SUCCESS_RATE_FOR_REGISTRATION:
                        skill.status = SkillStatus.REGISTERED
                        self._stats["skills_registered"] += 1
                        self._notify_callbacks("skill_registered", skill)
                    else:
                        skill.status = SkillStatus.DEPRECATED
                        self._notify_callbacks("skill_deprecated", skill)
            elif skill.status == SkillStatus.REGISTERED:
                if skill.success_rate < self.MIN_SUCCESS_RATE_FOR_REGISTRATION * 0.7:
                    skill.status = SkillStatus.DEPRECATED
                    self._notify_callbacks("skill_deprecated", skill)

    def _compute_pattern_metrics(self, pattern_hash: str) -> SkillMetrics:
        outcomes = self._outcomes_by_pattern.get(pattern_hash, [])
        if not outcomes:
            return SkillMetrics(0, 0, 0, 0.0, 0, 0, 0, [])
        successes = [o for o in outcomes if o.success]
        failures = [o for o in outcomes if not o.success]
        return SkillMetrics(
            total_outcomes=len(outcomes),
            success_count=len(successes),
            failure_count=len(failures),
            avg_quality=sum(o.quality_score for o in outcomes) / len(outcomes),
            avg_tokens=int(sum(o.tokens_used for o in outcomes) / len(outcomes)),
            avg_latency_ms=int(sum(o.execution_time_ms for o in outcomes) / len(outcomes)),
            unique_patterns=1,
            models_used=list(set(o.model_used for o in outcomes)),
        )

    def _calculate_confidence(self, skill: SkillRecord) -> float:
        n = min(skill.execution_count, 100)
        sample_factor = 0.4 * (1 - (1 / (1 + n / 10)))
        success_factor = 0.4 * skill.success_rate
        recency_factor = 0.0
        if skill.last_success:
            hours_since = (time.time() - skill.last_success) / 3600
            recency_factor = 0.2 * max(0, 1 - hours_since / 168)
        return min(1.0, sample_factor + success_factor + recency_factor)

    def get_skill_for_task(self, task_type: str, pattern: str) -> Optional[SkillRecord]:
        with self._lock:
            pattern_hash = self._hash_pattern(pattern)
            for skill in self._skills.values():
                if skill.pattern_hash == pattern_hash:
                    if skill.status == SkillStatus.REGISTERED and skill.confidence >= self.MIN_CONFIDENCE_FOR_FAST_PATH:
                        self._stats["fast_path_hits"] += 1
                        return skill
            
            best_candidate = None
            best_confidence = 0.0
            for skill in self._skills.values():
                if skill.task_type == task_type and skill.status == SkillStatus.REGISTERED:
                    if skill.confidence > best_confidence:
                        best_confidence = skill.confidence
                        best_candidate = skill
            
            if best_candidate and best_confidence >= self.MIN_CONFIDENCE_FOR_FAST_PATH:
                self._stats["fast_path_hits"] += 1
                return best_candidate
            return None

    def get_skills_by_status(self, status: SkillStatus) -> List[SkillRecord]:
        with self._lock: return [s for s in self._skills.values() if s.status == status]

    def register_skill_manual(self, skill: SkillRecord) -> str:
        with self._lock:
            skill.status = SkillStatus.REGISTERED
            skill.confidence = 1.0
            self._skills[skill.skill_id] = skill
            self._stats["skills_registered"] += 1
            self._notify_callbacks("skill_registered", skill)
            return skill.skill_id

    def on_change(self, callback: callable):
        self._callbacks.append(callback)

    def _notify_callbacks(self, event: str, skill: SkillRecord):
        for callback in self._callbacks:
            try: callback(event, skill)
            except Exception as e: print(f"[SkillSmith] Callback error: {e}")

    def _generate_skill_id(self, pattern: str, task_type: str) -> str:
        content = f"{pattern}|{task_type}|{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _generate_skill_name(self, pattern: str, task_type: str) -> str:
        words = pattern.split()[:3]
        prefix = "".join(w[:2].upper() for w in words if w)
        return f"{task_type.upper()[:4]}-{prefix}"

    def _hash_pattern(self, pattern: str) -> str:
        return hashlib.sha256(pattern.lower().strip().encode()).hexdigest()

    def _truncate_pattern(self, pattern: str, max_len: int = 200) -> str:
        return pattern if len(pattern) <= max_len else pattern[:max_len] + "..."

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                **self._stats,
                "total_skills": len(self._skills),
                "registered_skills": len(self.get_skills_by_status(SkillStatus.REGISTERED)),
                "testing_skills": len(self.get_skills_by_status(SkillStatus.TESTING)),
                "candidate_skills": len(self.get_skills_by_status(SkillStatus.CANDIDATE)),
            }

    def get_report(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "stats": self.get_stats(),
            }

    def save_skills(self, path: str) -> bool:
        import json
        with self._lock:
            try:
                data = {"skills": [vars(s) for s in self._skills.values()], "stats": self._stats}
                # Fix Enum serialization
                for s in data["skills"]: s["status"] = s["status"].value
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return True
            except Exception:
                return False

    def load_skills(self, path: str) -> bool:
        import json
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with self._lock:
                self._skills = {}
                for s_data in data.get("skills", []):
                    status_val = s_data.pop("status", "candidate")
                    status = SkillStatus(status_val) if isinstance(status_val, str) else SkillStatus.CANDIDATE
                    skill = SkillRecord(status=status, **s_data)
                    self._skills[skill.skill_id] = skill
                self._stats = data.get("stats", self._stats)
            return True
        except Exception:
            return False

    _instance = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "SkillSmith":
        with cls._instance_lock:
            if cls._instance is None: cls._instance = cls()
            return cls._instance

def record_task_outcome(task_type: str, domain: str, pattern: str, model_used: str, success: bool, quality_score: float = 1.0, tokens_used: int = 0, execution_time_ms: int = 0, error_message: Optional[str] = None) -> Optional[str]:
    import uuid
    outcome = TaskOutcome(
        task_id=str(uuid.uuid4()), task_type=task_type, domain=domain,
        pattern_hash=hashlib.sha256(pattern.lower().strip().encode()).hexdigest(),
        pattern=pattern, model_used=model_used, success=success, quality_score=quality_score,
        tokens_used=tokens_used, execution_time_ms=execution_time_ms, timestamp=time.time(), error_message=error_message
    )
    return SkillSmith.get_instance().record_outcome(outcome)

def get_skill_for_task(task_type: str, pattern: str) -> Optional[SkillRecord]:
    return SkillSmith.get_instance().get_skill_for_task(task_type, pattern)
