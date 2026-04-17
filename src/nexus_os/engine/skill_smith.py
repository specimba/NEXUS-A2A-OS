"""engine/skill_smith.py — SkillSmith Auto-Discovery System v2.1"""
from __future__ import annotations
import hashlib, json, logging, threading, time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

class SkillStatus(Enum):
    CANDIDATE = "candidate"
    TESTING   = "testing"
    REGISTERED = "registered"
    DEPRECATED = "deprecated"
    MERGED    = "merged"

@dataclass
class TaskOutcome:
    task_id: str; task_type: str; domain: str; pattern_hash: str; pattern: str
    model_used: str; success: bool; quality_score: float; tokens_used: int
    execution_time_ms: int; timestamp: float
    error_message: Optional[str] = None

@dataclass
class SkillRecord:
    skill_id: str; name: str; task_type: str; pattern: str; pattern_hash: str
    recommended_model: str; domain: str
    success_rate: float = 0.0; avg_quality: float = 0.0
    execution_count: int = 0; success_count: int = 0; failure_count: int = 0
    avg_tokens: int = 0; avg_latency_ms: int = 0
    status: SkillStatus = SkillStatus.CANDIDATE
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    last_success: Optional[float] = None; confidence: float = 0.0
    merged_into: Optional[str] = None

def _hash_pattern(pattern: str) -> str:
    return hashlib.sha256(pattern.lower().strip().encode()).hexdigest()

def _jaccard(a: str, b: str) -> float:
    sa = set(a.lower().split()); sb = set(b.lower().split())
    if not sa and not sb: return 1.0
    return len(sa & sb) / max(len(sa | sb), 1)

def _running_avg(old_avg: float, old_n: int, new_val: float) -> float:
    return (old_avg * old_n + new_val) / (old_n + 1)

class SkillSmith:
    MIN_OUTCOMES: int = 3
    REGISTRATION_RATE: float = 0.75
    CONFIDENCE_THRESHOLD: float = 0.80
    TESTING_WINDOW: float = 3600.0
    FALLBACK_MIN_JACCARD: float = 0.30
    MERGE_AFTER: int = 10
    MERGE_JACCARD: float = 0.85

    def __init__(self, clock: Callable[[], float] = time.time,
                 outcome_ttl: float = 7*86400):
        self._clock = clock; self._ttl = outcome_ttl
        self._skills: Dict[str, SkillRecord] = {}
        self._outcomes: Dict[str, List[TaskOutcome]] = defaultdict(list)
        self._rlock = threading.RLock()
        self._callbacks: List[Callable] = []
        self._stats: Dict[str, int] = {
            "total_outcomes": 0, "skills_created": 0, "skills_registered": 0,
            "skills_merged": 0, "fast_path_hits": 0, "outcomes_evicted": 0,
        }

    def record_outcome(self, o: TaskOutcome) -> Optional[str]:
        with self._rlock:
            self._stats["total_outcomes"] += 1
            self._outcomes[o.pattern_hash].append(o)
            self._evict(o.pattern_hash)
            new_id = self._maybe_create(o)
            self._update_stats(o)
            self._eval_statuses()
            self._maybe_merge()
        return new_id

    def _maybe_create(self, o: TaskOutcome) -> Optional[str]:
        outcomes = self._outcomes.get(o.pattern_hash, [])
        if len(outcomes) < self.MIN_OUTCOMES: return None
        if any(s.pattern_hash == o.pattern_hash for s in self._skills.values()): return None
        sid = hashlib.sha256(f"{o.pattern.lower().strip()}|{o.task_type}".encode()).hexdigest()[:16]
        words = o.pattern.split()[:3]
        name = f"{o.task_type.upper()[:4]}-{''.join(w[:2].upper() for w in words if w)}"
        prior = outcomes[:-1]
        if prior:
            init_success = sum(1 for x in prior if x.success)
            init_count   = len(prior)
            skill = SkillRecord(
                skill_id=sid, name=name, task_type=o.task_type,
                pattern=o.pattern[:200], pattern_hash=o.pattern_hash,
                recommended_model=o.model_used, domain=o.domain,
                success_rate=init_success/max(init_count,1),
                avg_quality=sum(x.quality_score for x in prior)/init_count,
                execution_count=init_count, success_count=init_success,
                failure_count=init_count-init_success,
                avg_tokens=int(sum(x.tokens_used for x in prior)/init_count),
                avg_latency_ms=int(sum(x.execution_time_ms for x in prior)/init_count),
                created_at=self._clock(), last_used=self._clock(),
                last_success=next((x.timestamp for x in reversed(prior) if x.success), None),
            )
        else:
            skill = SkillRecord(skill_id=sid, name=name, task_type=o.task_type,
                pattern=o.pattern[:200], pattern_hash=o.pattern_hash,
                recommended_model=o.model_used, domain=o.domain)
        self._skills[sid] = skill
        self._stats["skills_created"] += 1
        self._emit("skill_created", skill)
        return sid

    def _update_stats(self, o: TaskOutcome):
        for s in self._skills.values():
            if s.pattern_hash != o.pattern_hash: continue
            n = s.execution_count
            s.execution_count += 1
            s.avg_tokens      = int(_running_avg(s.avg_tokens, n, o.tokens_used))
            s.avg_latency_ms  = int(_running_avg(s.avg_latency_ms, n, o.execution_time_ms))
            s.avg_quality     = _running_avg(s.avg_quality, n, o.quality_score)
            if o.success:
                s.success_count += 1; s.last_success = o.timestamp
            else:
                s.failure_count += 1
            s.success_rate = s.success_count / s.execution_count
            s.confidence   = self._calc_confidence(s)
            s.last_used     = o.timestamp

    def _calc_confidence(self, s: SkillRecord) -> float:
        n = min(s.execution_count, 100)
        sample = 0.40 * (1.0 - 1.0/(1.0 + n/10.0))
        success = 0.40 * s.success_rate
        recency = 0.0
        if s.last_success is not None:           # Bug 3 fix: is not None, not truthiness
            hours = (self._clock() - s.last_success) / 3600.0
            recency = 0.20 * max(0.0, 1.0 - hours/168.0)
        return min(1.0, sample + success + recency)

    def _eval_statuses(self):
        now = self._clock()
        for s in list(self._skills.values()):
            if s.status == SkillStatus.CANDIDATE:
                if s.execution_count > self.MIN_OUTCOMES:   # Bug 2 fix: > not >=
                    s.status = SkillStatus.TESTING
                    self._emit("skill_testing", s)
            elif s.status == SkillStatus.TESTING:
                if now - s.created_at >= self.TESTING_WINDOW:
                    if s.success_rate >= self.REGISTRATION_RATE:
                        s.status = SkillStatus.REGISTERED
                        self._stats["skills_registered"] += 1
                        self._emit("skill_registered", s)
                    else:
                        s.status = SkillStatus.DEPRECATED
                        self._emit("skill_deprecated", s)
            elif s.status == SkillStatus.REGISTERED:
                if s.success_rate < self.REGISTRATION_RATE * 0.70:
                    s.status = SkillStatus.DEPRECATED
                    self._emit("skill_deprecated", s)

    def _maybe_merge(self):
        candidates = [s for s in self._skills.values() if s.status == SkillStatus.CANDIDATE]
        if len(candidates) < self.MERGE_AFTER: return
        visited: Set[str] = set()
        for i, a in enumerate(candidates):
            if a.skill_id in visited: continue
            cluster = [a]
            for b in candidates[i+1:]:
                if b.skill_id in visited: continue
                if _jaccard(a.pattern, b.pattern) >= self.MERGE_JACCARD:
                    cluster.append(b); visited.add(b.skill_id)
            if len(cluster) > 1:
                best = max(cluster, key=lambda s: s.success_rate)
                for dup in cluster:
                    if dup.skill_id == best.skill_id: continue
                    dup.status = SkillStatus.MERGED; dup.merged_into = best.skill_id
                    self._stats["skills_merged"] += 1
                    self._emit("skill_merged", dup)

    def _evict(self, ph: str):
        cutoff = self._clock() - self._ttl
        before = len(self._outcomes[ph])
        self._outcomes[ph] = [o for o in self._outcomes[ph] if o.timestamp >= cutoff]
        self._stats["outcomes_evicted"] += before - len(self._outcomes[ph])

    def get_skill_for_task(self, task_type: str, pattern: str) -> Optional[SkillRecord]:
        with self._rlock:
            ph = _hash_pattern(pattern)
            for s in self._skills.values():
                if s.pattern_hash == ph and s.status == SkillStatus.REGISTERED                    and s.confidence >= self.CONFIDENCE_THRESHOLD:
                    self._stats["fast_path_hits"] += 1
                    return s
            best = None; best_score = 0.0
            for s in self._skills.values():
                if s.task_type != task_type or s.status != SkillStatus.REGISTERED: continue
                if s.confidence < self.CONFIDENCE_THRESHOLD: continue
                sim = _jaccard(pattern, s.pattern)
                if sim >= self.FALLBACK_MIN_JACCARD and sim > best_score:
                    best_score = sim; best = s
            if best:
                self._stats["fast_path_hits"] += 1
                return best
        return None

    def register_skill_manual(self, s: SkillRecord) -> str:
        with self._rlock:
            s.status = SkillStatus.REGISTERED; s.confidence = 1.0
            self._skills[s.skill_id] = s
            self._stats["skills_registered"] += 1
            self._emit("skill_registered", s)
        return s.skill_id

    def deprecate_skill(self, sid: str) -> bool:
        with self._rlock:
            s = self._skills.get(sid)
            if not s: return False
            s.status = SkillStatus.DEPRECATED
            self._emit("skill_deprecated", s)
        return True

    def get_skills_by_status(self, status: SkillStatus) -> List[SkillRecord]:
        with self._rlock:
            return [s for s in self._skills.values() if s.status == status]

    def on_change(self, cb: Callable): self._callbacks.append(cb)
    def _emit(self, ev: str, s: SkillRecord):
        for cb in self._callbacks:
            try: cb(ev, s)
            except Exception as exc: logger.warning("callback error: %s", exc)

    def get_stats(self) -> Dict[str, Any]:
        with self._rlock:
            total = max(self._stats["total_outcomes"], 1)
            return {**self._stats, "total_skills": len(self._skills),
                "registered": len(self.get_skills_by_status(SkillStatus.REGISTERED)),
                "testing":    len(self.get_skills_by_status(SkillStatus.TESTING)),
                "candidate":  len(self.get_skills_by_status(SkillStatus.CANDIDATE)),
                "fast_path_rate%": round(self._stats["fast_path_hits"]/total*100, 1)}

    def save_skills(self, path: str) -> bool:
        with self._rlock:
            try:
                data = {"version": "2.1",
                    "skills": [{**vars(s), "status": s.status.value} for s in self._skills.values()],
                    "stats": dict(self._stats)}
                with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
                return True
            except Exception as exc: logger.error("save failed: %s", exc); return False

    def load_skills(self, path: str) -> bool:
        try:
            with open(path, "r", encoding="utf-8") as f: data = json.load(f)
            with self._rlock:
                self._skills = {}
                for raw in data.get("skills", []):
                    sv = raw.pop("status", "candidate")
                    self._skills[raw["skill_id"]] = SkillRecord(
                        status=SkillStatus(sv) if isinstance(sv, str) else SkillStatus.CANDIDATE, **raw)
                self._stats = data.get("stats", self._stats)
            return True
        except Exception as exc: logger.error("load failed: %s", exc); return False

    _instance = None; _singleton_lock = threading.Lock()
    @classmethod
    def get_instance(cls) -> "SkillSmith":
        with cls._singleton_lock:
            if cls._instance is None: cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls):
        with cls._singleton_lock: cls._instance = None
