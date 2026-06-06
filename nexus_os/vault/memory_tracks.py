"""vault/memory_tracks.py — 5-Track Memory Schema

Implements the 5-track memory system as specified:
- EVENT: Raw task outcomes
- TRUST: Bayesian reputation per lane
- CAPABILITY: What agent is good at
- FAILURE_PATTERN: Recurring weaknesses
- GOVERNANCE: Behavior under rules

Integrates with the existing S-P-E-W vault structure.
"""

import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from collections import defaultdict

from nexus_os.execution_paths import ExecutionPath, get_router

logger = logging.getLogger(__name__)


class MemoryTrack(Enum):
    """5-Track Memory Schema."""
    EVENT = "event"           # Raw task outcomes
    TRUST = "trust"           # Bayesian reputation (per-lane!)
    CAPABILITY = "capability" # What agent is good at
    FAILURE_PATTERN = "failure_pattern"  # Recurring weaknesses
    GOVERNANCE = "governance" # Behavior under rules


# Valid lanes for trust scoring
VALID_LANES = {
    "research",    # Research/analysis tasks
    "audit",       # Auditing/compliance
    "compliance", # Compliance verification
    "implementation",  # Code implementation
    "orchestration", # Agent coordination
    "general",     # General tasks
}


@dataclass
class TrackRecord:
    """A record for a specific memory track."""
    track: MemoryTrack
    agent_id: str
    content: str
    lane: str = "general"  # For trust track - lane-scoped
    
    # For EVENT track
    outcome: Optional[str] = None  # "success", "failure", "partial"
    duration_ms: float = 0.0
    token_count: int = 0
    
    # For TRUST track
    trust_score: Optional[float] = None
    evidence_count: int = 0
    
    # For CAPABILITY track
    skill_tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    # For FAILURE_PATTERN track
    failure_type: Optional[str] = None
    error_count: int = 0
    
    # For GOVERNANCE track
    rule_violated: Optional[str] = None
    severity: str = "low"
    
    # Metadata
    trace_id: Optional[str] = None
    project_id: Optional[str] = None


@dataclass
class CapabilityProfile:
    """Agent capability profile from CAPABILITY track."""
    agent_id: str
    languages: Dict[str, float] = field(default_factory=dict)  # lang -> confidence
    domains: Dict[str, float] = field(default_factory=dict)    # domain -> confidence
    tools: Dict[str, float] = field(default_factory=dict)        # tool -> confidence
    total_tasks: int = 0
    successful_tasks: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks
    
    def best_skill(self) -> Optional[str]:
        """Return highest confidence skill."""
        all_skills = {}
        all_skills.update(self.languages)
        all_skills.update(self.domains)
        all_skills.update(self.tools)
        
        if not all_skills:
            return None
        return max(all_skills, key=all_skills.get)


@dataclass
class FailurePattern:
    """Agent failure pattern from FAILURE_PATTERN track."""
    agent_id: str
    failure_type: str  # e.g., "timeout", "security", "reasoning"
    frequency: int = 0
    last_occurrence: Optional[str] = None
    lanes_affected: List[str] = field(default_factory=list)
    
    @property
    def severity(self) -> str:
        if self.frequency >= 5:
            return "high"
        elif self.frequency >= 2:
            return "medium"
        return "low"


class MemoryTracker:
    """
    5-Track Memory Tracker.
    
    Provides methods to append to each track. The actual
    persistence is handled by VaultManager.write_memory()
    with the track parameter.
    """
    
    def __init__(self):
        # In-memory buffers (used for real-time queries)
        # Format: {agent_id: {track: [records]}}
        self._buffers: Dict[str, Dict[MemoryTrack, List[TrackRecord]]] = defaultdict(
            lambda: {track: [] for track in MemoryTrack}
        )
        
        # Capability profiles (cached)
        self._capabilities: Dict[str, CapabilityProfile] = {}
        
        # Failure patterns (cached)
        self._failures: Dict[str, Dict[str, FailurePattern]] = defaultdict(dict)
    
    # ── EVENT Track ─────────────────────────────────────────────
    
    def append_event(
        self,
        agent_id: str,
        content: str,
        outcome: str,
        duration_ms: float,
        token_count: int,
        trace_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> TrackRecord:
        """Append an EVENT record (task outcome)."""
        record = TrackRecord(
            track=MemoryTrack.EVENT,
            agent_id=agent_id,
            content=content,
            outcome=outcome,
            duration_ms=duration_ms,
            token_count=token_count,
            trace_id=trace_id,
            project_id=project_id,
        )
        
        self._buffers[agent_id][MemoryTrack.EVENT].append(record)
        
        # Update capability if successful
        if outcome == "success":
            self._update_capability_on_success(agent_id)
        
        logger.debug(f"EVENT: {agent_id} → {outcome} ({duration_ms:.1f}ms, {token_count}t)")
        return record
    
    def _update_capability_on_success(self, agent_id: str):
        """Update success count for capability tracking."""
        if agent_id not in self._capabilities:
            self._capabilities[agent_id] = CapabilityProfile(agent_id=agent_id)
        
        profile = self._capabilities[agent_id]
        profile.total_tasks += 1
        profile.successful_tasks += 1
    
    # ── TRUST Track ──────────────────────────────────────────────
    
    def append_trust(
        self,
        agent_id: str,
        lane: str,
        trust_score: float,
        evidence_count: int,
        content: str = "",
        trace_id: Optional[str] = None,
    ) -> TrackRecord:
        """Append a TRUST record (lane-scoped Bayesian reputation)."""
        if lane not in VALID_LANES:
            logger.warning(f"Unknown lane: {lane}, defaulting to 'general'")
            lane = "general"
        
        record = TrackRecord(
            track=MemoryTrack.TRUST,
            agent_id=agent_id,
            content=content,
            lane=lane,
            trust_score=trust_score,
            evidence_count=evidence_count,
            trace_id=trace_id,
        )
        
        self._buffers[agent_id][MemoryTrack.TRUST].append(record)
        
        logger.debug(f"TRUST: {agent_id}[{lane}] = {trust_score:.2f} (n={evidence_count})")
        return record
    
    # ── CAPABILITY Track ───────────────────────────────────────
    
    def append_capability(
        self,
        agent_id: str,
        skill_tags: List[str],
        confidence: float,
        content: str = "",
    ) -> TrackRecord:
        """
        Append a CAPABILITY record (what agent is good at).
        
        Args:
            skill_tags: e.g., ["python", "javascript", "security-audit"]
        """
        record = TrackRecord(
            track=MemoryTrack.CAPABILITY,
            agent_id=agent_id,
            content=content,
            skill_tags=skill_tags,
            confidence=confidence,
        )
        
        self._buffers[agent_id][MemoryTrack.CAPABILITY].append(record)
        
        # Update cached profile
        self._update_capability_profile(agent_id, skill_tags, confidence)
        
        logger.debug(f"CAPABILITY: {agent_id} → {skill_tags}")
        return record
    
    def _update_capability_profile(
        self,
        agent_id: str,
        skill_tags: List[str],
        confidence: float,
    ):
        """Update internal capability profile."""
        if agent_id not in self._capabilities:
            self._capabilities[agent_id] = CapabilityProfile(agent_id=agent_id)
        
        profile = self._capabilities[agent_id]
        
        # Update each skill tag
        for tag in skill_tags:
            # Determine category
            if tag in {"python", "javascript", "rust", "go", "typescript"}:
                category = "languages"
            elif tag in {"code", "research", "analysis", "security"}:
                category = "domains"
            else:
                category = "tools"
            
            # Update with exponential moving average
            store = getattr(profile, category)
            if tag in store:
                store[tag] = 0.7 * store[tag] + 0.3 * confidence
            else:
                store[tag] = confidence
    
    def get_capability(self, agent_id: str) -> Optional[CapabilityProfile]:
        """Get agent capability profile."""
        return self._capabilities.get(agent_id)
    
    # ── FAILURE_PATTERN Track ────────────────────────────────────────
    
    def append_failure(
        self,
        agent_id: str,
        failure_type: str,
        lane: str = "general",
        content: str = "",
        trace_id: Optional[str] = None,
    ) -> TrackRecord:
        """Append a FAILURE_PATTERN record."""
        record = TrackRecord(
            track=MemoryTrack.FAILURE_PATTERN,
            agent_id=agent_id,
            content=content,
            lane=lane,
            failure_type=failure_type,
            error_count=1,
        )
        
        self._buffers[agent_id][MemoryTrack.FAILURE_PATTERN].append(record)
        
        # Update cached failure pattern
        self._update_failure_pattern(agent_id, failure_type, lane)
        
        logger.debug(f"FAILURE: {agent_id} → {failure_type}")
        return record
    
    def _update_failure_pattern(
        self,
        agent_id: str,
        failure_type: str,
        lane: str,
    ):
        """Update internal failure pattern."""
        if agent_id not in self._failures:
            self._failures[agent_id] = {}
        
        patterns = self._failures[agent_id]
        
        if failure_type in patterns:
            pattern = patterns[failure_type]
            pattern.frequency += 1
            pattern.lanes_affected.append(lane)
        else:
            patterns[failure_type] = FailurePattern(
                agent_id=agent_id,
                failure_type=failure_type,
                frequency=1,
                lanes_affected=[lane],
            )
    
    def get_failures(self, agent_id: str) -> Dict[str, FailurePattern]:
        """Get all failure patterns for agent."""
        return self._failures.get(agent_id, {})
    
    def get_critical_failures(self, agent_id: str) -> List[FailurePattern]:
        """Get high-severity failures for agent."""
        failures = self.get_failures(agent_id)
        return [f for f in failures.values() if f.severity == "high"]
    
    # ── GOVERNANCE Track ─────────────────────────────────────────
    
    def append_governance(
        self,
        agent_id: str,
        rule_violated: str,
        severity: str,
        content: str = "",
        trace_id: Optional[str] = None,
    ) -> TrackRecord:
        """Append a GOVERNANCE record (behavior under rules)."""
        record = TrackRecord(
            track=MemoryTrack.GOVERNANCE,
            agent_id=agent_id,
            content=content,
            rule_violated=rule_violated,
            severity=severity,
        )
        
        self._buffers[agent_id][MemoryTrack.GOVERNANCE].append(record)
        
        logger.debug(f"GOVERNANCE: {agent_id} → {rule_violated} ({severity})")
        return record
    
    # ── Query Methods ─────────────────────────────────────────
    
    def get_events(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> List[TrackRecord]:
        """Get recent events for agent."""
        events = self._buffers[agent_id][MemoryTrack.EVENT]
        return events[-limit:]
    
    def get_trust_history(
        self,
        agent_id: str,
        lane: Optional[str] = None,
    ) -> List[TrackRecord]:
        """Get trust history for agent (optionally filtered by lane)."""
        records = self._buffers[agent_id][MemoryTrack.TRUST]
        
        if lane is None:
            return records
        
        return [r for r in records if r.lane == lane]
    
    def get_latest_trust(
        self,
        agent_id: str,
        lane: str = "general",
    ) -> Optional[float]:
        """Get latest trust score for agent in lane."""
        history = self.get_trust_history(agent_id, lane)
        if not history:
            return None
        return history[-1].trust_score
    
    def get_buffer_summary(self, agent_id: str) -> Dict[str, int]:
        """Get counts per track for an agent."""
        return {
            track.value: len(self._buffers[agent_id][track])
            for track in MemoryTrack
        }
    
    def clear_buffer(self, agent_id: str):
        """Clear buffer for agent (after persistence to DB)."""
        if agent_id in self._buffers:
            for track in MemoryTrack:
                self._buffers[agent_id][track].clear()  # type: ignore


# Singleton instance
_tracker: Optional[MemoryTracker] = None


def get_tracker() -> MemoryTracker:
    """Get the singleton MemoryTracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = MemoryTracker()
    return _tracker