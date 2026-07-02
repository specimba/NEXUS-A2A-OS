"""vault/memory_channels.py — 8-Channel Memory Architecture

Implements the 8-channel memory system as specified in NEXUS Trust Framework v1.0:
- SENSORY (0): Pre-filtered raw input buffer (LightMem stage 1)
- WORKING (1): Active context window (ephemeral, direct LLM buffer)
- EPISODIC (2): Task outcomes, events, raw experiences (merged from EVENT + FAILURE_PATTERN)
- SEMANTIC (3): Abstracted knowledge, ARCHIVIST dossiers (sleep-time consolidated)
- PROCEDURAL (4): Verified skills, execution paths, reusable patterns (merged from CAPABILITY)
- TRUST (5): Novel tanh-based trust formula (11 elements), real-time governance (merged from TRUST + GOVERNANCE)
- TASK (6): Task-specific context, bound to lifecycle
- META (7): Memory about memory, reflection, health stats

Integration with Trust Framework:
- Trust scores gate write access to channels (min trust thresholds)
- Channel 2 (EPISODIC) and 5 (TRUST) feed the 11-element trust formula
- Channel 3 (SEMANTIC) receives ARCHIVIST dossier output

References:
- Du (2026) — Memory for Autonomous LLM Agents: 4 memory types, 5 mechanism families
- Wei (DeepMind, 2026) — Evo-Memory: Search→Synthesize→Evolve cycle
- Fang (ICLR 2026) — LightMem: 3-stage human memory (Sensory→STM→LTM)
- NEXUS Trust Framework: docs/research/NEXUS_TRUST_FRAMEWORK.md
"""

import logging
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from collections import defaultdict

from nexus_os.execution_paths import ExecutionPath, get_router

logger = logging.getLogger(__name__)


class MemoryChannel(Enum):
    """8-Channel Memory Architecture."""
    SENSORY = "sensory"           # 0: Pre-filtered raw input buffer
    WORKING = "working"           # 1: Active context window (ephemeral)
    EPISODIC = "episodic"         # 2: Task outcomes, events, raw experiences
    SEMANTIC = "semantic"         # 3: Abstracted knowledge, ARCHIVIST dossiers
    PROCEDURAL = "procedural"     # 4: Verified skills, execution paths
    TRUST = "trust"               # 5: Novel tanh-based trust formula (11 elements), real-time governance
    TASK = "task"                 # 6: Task-specific context, bound to lifecycle
    META = "meta"                 # 7: Memory about memory, reflection, health


# Trust-gated write access thresholds (0-100 display scale)
# Source: NEXUS Trust Framework §4.2
CHANNEL_WRITE_TRUST = {
    MemoryChannel.SENSORY: 0.0,
    MemoryChannel.WORKING: 0.0,
    MemoryChannel.EPISODIC: 30.0,
    MemoryChannel.SEMANTIC: 65.0,
    MemoryChannel.PROCEDURAL: 80.0,
    MemoryChannel.TRUST: 90.0,
    MemoryChannel.TASK: 40.0,
    MemoryChannel.META: 70.0,
}


# Valid lanes for trust scoring (same as before, now used in TRUST channel)
VALID_LANES = {
    "research",    # Research/analysis tasks
    "audit",       # Auditing/compliance
    "compliance",  # Compliance verification
    "implementation",  # Code implementation
    "orchestration",   # Agent coordination
    "governance",  # Governance entries (DG bridge rules/config, append_governance)
    "general",     # General tasks
}


@dataclass
class ChannelRecord:
    """A record for a specific memory channel."""
    record_id: str = field(default_factory=lambda: f"cr-{__import__('uuid').uuid4().hex[:12]}")
    channel: MemoryChannel = MemoryChannel.SENSORY
    agent_id: str = ""
    content: str = ""
    lane: str = "general"  # For TRUST channel - lane-scoped
    
    # For EPISODIC channel (merged from EVENT + FAILURE_PATTERN)
    outcome: Optional[str] = None  # "success", "failure", "partial"
    failure_type: Optional[str] = None  # e.g., "timeout", "security", "reasoning"
    duration_ms: float = 0.0
    token_count: int = 0
    
    # For TRUST channel (merged from TRUST + GOVERNANCE)
    trust_score: Optional[float] = None
    evidence_count: int = 0
    rule_violated: Optional[str] = None  # From GOVERNANCE
    severity: str = "low"  # From GOVERNANCE
    
    # For PROCEDURAL channel (merged from CAPABILITY)
    skill_tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    # For SENSORY channel (LightMem pre-compression)
    compression_ratio: float = 1.0  # 1.0 = no compression, 0.5 = 50% compressed
    topic_tags: List[str] = field(default_factory=list)
    threat_flags: List[str] = field(default_factory=list)  # Memory threat scanner output
    
    # For TASK channel (task-bound)
    task_id: Optional[str] = None
    task_status: Optional[str] = None  # "active", "completed", "cancelled"
    
    # For META channel (memory health)
    meta_type: Optional[str] = None  # "consolidation", "retrieval_stats", "health"
    meta_value: Optional[float] = None
    
    # Adaptive Memory Persistence (B'MOJO-inspired)
    access_count: int = 0       # Number of times this record has been read
    last_access: Optional[float] = None  # Timestamp of last read
    persistence_score: float = 0.5  # 0.0 (fade) to 1.0 (eidetic), auto-adjusted by access frequency
    
    # Common metadata
    trace_id: Optional[str] = None
    project_id: Optional[str] = None
    timestamp: Optional[float] = None


@dataclass
class CapabilityProfile:
    """Agent capability profile from PROCEDURAL channel."""
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
    """Agent failure pattern from EPISODIC channel."""
    agent_id: str
    failure_type: str
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


@dataclass
class ConsolidationStats:
    """META channel statistics for memory health monitoring."""
    channel: MemoryChannel
    total_records: int = 0
    consolidated_records: int = 0
    deduplicated_records: int = 0
    last_consolidation: Optional[float] = None
    avg_retrieval_time_ms: float = 0.0
    retrieval_hit_rate: float = 0.0


class MemoryChannelManager:
    """
    8-Channel Memory Manager.
    
    Provides methods to append to each channel. Write access is gated
    by agent trust score (CHANNEL_WRITE_TRUST thresholds).
    
    Channel → Execution Path mapping:
    - HOT (0.02s): SENSORY, WORKING, TRUST
    - WARM (50s): EPISODIC, TASK
    - COLD (1000s): SEMANTIC, PROCEDURAL, META
    """
    
    MAX_RECORDS_PER_CHANNEL = 500
    
    def __init__(self):
        # In-memory buffers (used for real-time queries)
        # Format: {agent_id: {channel: [records]}}
        self._buffers: Dict[str, Dict[MemoryChannel, List[ChannelRecord]]] = defaultdict(
            lambda: {channel: [] for channel in MemoryChannel}
        )
        
        # Capability profiles (cached, from PROCEDURAL channel)
        self._capabilities: Dict[str, CapabilityProfile] = {}
        
        # Failure patterns (cached, from EPISODIC channel)
        self._failures: Dict[str, Dict[str, FailurePattern]] = defaultdict(dict)
        
        # Consolidation statistics (from META channel)
        self._consolidation_stats: Dict[MemoryChannel, ConsolidationStats] = {
            channel: ConsolidationStats(channel=channel) for channel in MemoryChannel
        }
        
        # Router for execution path selection
        self._router = get_router()
    
    # ── Trust-Gated Write Helper ──────────────────────────────────
    
    def _check_write_access(self, agent_id: str, channel: MemoryChannel, trust_score: float) -> bool:
        """Check if agent has sufficient trust to write to channel."""
        threshold = CHANNEL_WRITE_TRUST[channel]
        if trust_score < threshold:
            logger.warning(
                "WRITE DENIED: %s → %s (trust=%.1f < threshold=%.1f)",
                agent_id, channel.value, trust_score, threshold
            )
            return False
        return True
    
    def _maybe_prune(self, agent_id: str, channel: MemoryChannel):
        """Auto-prune channel buffer if it exceeds limit."""
        buf = self._buffers[agent_id][channel]
        if channel == MemoryChannel.WORKING:
            return
        if len(buf) > self.MAX_RECORDS_PER_CHANNEL:
            self._buffers[agent_id][channel] = buf[-self.MAX_RECORDS_PER_CHANNEL:]
    
    # ── SENSORY Channel (0) ─────────────────────────────────────
    
    def append_sensory(
        self,
        agent_id: str,
        content: str,
        compression_ratio: float = 1.0,
        topic_tags: Optional[List[str]] = None,
        threat_flags: Optional[List[str]] = None,
        trace_id: Optional[str] = None,
    ) -> Optional[ChannelRecord]:
        """Append a SENSORY record (pre-filtered raw input).
        
        Trust gate: 0 (open to all agents).
        Execution path: HOT (0.02s SLA).
        """
        record = ChannelRecord(
            channel=MemoryChannel.SENSORY,
            agent_id=agent_id,
            content=content,
            compression_ratio=compression_ratio,
            topic_tags=topic_tags or [],
            threat_flags=threat_flags or [],
            trace_id=trace_id,
        )
        self._buffers[agent_id][MemoryChannel.SENSORY].append(record)
        self._maybe_prune(agent_id, MemoryChannel.SENSORY)
        logger.debug(f"SENSORY: {agent_id} → compressed={compression_ratio:.2f}")
        return record
    
    # ── WORKING Channel (1) ─────────────────────────────────────
    
    def append_working(
        self,
        agent_id: str,
        content: str,
        trace_id: Optional[str] = None,
    ) -> Optional[ChannelRecord]:
        """Append a WORKING record (active context window).
        
        Trust gate: 0 (open to all agents).
        Execution path: HOT (0.02s SLA).
        Note: WORKING is ephemeral; records are not persisted to cold storage.
        """
        record = ChannelRecord(
            channel=MemoryChannel.WORKING,
            agent_id=agent_id,
            content=content,
            trace_id=trace_id,
        )
        self._buffers[agent_id][MemoryChannel.WORKING].append(record)
        # WORKING channel auto-prunes: keep only last 50 entries
        if len(self._buffers[agent_id][MemoryChannel.WORKING]) > 50:
            self._buffers[agent_id][MemoryChannel.WORKING] = \
                self._buffers[agent_id][MemoryChannel.WORKING][-50:]
        logger.debug(f"WORKING: {agent_id} → len={len(content)}")
        return record
    
    # ── EPISODIC Channel (2) ──────────────────────────────────────
    
    def append_episodic(
        self,
        agent_id: str,
        content: str,
        outcome: str = "success",
        duration_ms: float = 0.0,
        token_count: int = 0,
        failure_type: Optional[str] = None,
        trace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        trust_score: float = 0.0,
    ) -> Optional[ChannelRecord]:
        """Append an EPISODIC record (task outcome).

        Merged from original EVENT + FAILURE_PATTERN tracks.
        Trust gate: 30 (basic agent history). Legacy callers that do not
        pass ``trust_score`` are treated as internal-trusted (same
        convention as append_task/append_meta); explicit callers are gated.
        Execution path: WARM (50s SLA).
        """
        effective_trust = 100.0 if trust_score == 0.0 else trust_score
        if not self._check_write_access(agent_id, MemoryChannel.EPISODIC, effective_trust):
            return None
        record = ChannelRecord(
            channel=MemoryChannel.EPISODIC,
            agent_id=agent_id,
            content=content,
            outcome=outcome,
            failure_type=failure_type,
            duration_ms=duration_ms,
            token_count=token_count,
            trace_id=trace_id,
            project_id=project_id,
        )
        self._buffers[agent_id][MemoryChannel.EPISODIC].append(record)
        self._maybe_prune(agent_id, MemoryChannel.EPISODIC)
        
        # Update capability if successful
        if outcome == "success":
            self._update_capability_on_success(agent_id)
        
        # Update failure pattern if failure
        if failure_type:
            self._update_failure_pattern(agent_id, failure_type, "general")
        
        logger.debug(f"EPISODIC: {agent_id} → {outcome} ({duration_ms:.1f}ms, {token_count}t)")
        return record
    
    def _update_capability_on_success(self, agent_id: str):
        """Update success count for capability tracking."""
        if agent_id not in self._capabilities:
            self._capabilities[agent_id] = CapabilityProfile(agent_id=agent_id)
        profile = self._capabilities[agent_id]
        profile.total_tasks += 1
        profile.successful_tasks += 1
    
    def _update_failure_pattern(self, agent_id: str, failure_type: str, lane: str):
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
    
    # ── SEMANTIC Channel (3) ──────────────────────────────────────
    
    def append_semantic(
        self,
        agent_id: str,
        content: str,
        topic_tags: Optional[List[str]] = None,
        source_dossier_id: Optional[str] = None,
        trust_score: float = 0.0,
        trace_id: Optional[str] = None,
    ) -> Optional[ChannelRecord]:
        """Append a SEMANTIC record (abstracted knowledge, ARCHIVIST dossiers).
        
        Trust gate: 65 (abstracted knowledge requires moderate trust).
        Execution path: COLD (1000s SLA).
        Source: ARCHIVIST pipeline dossier synthesis.
        """
        if not self._check_write_access(agent_id, MemoryChannel.SEMANTIC, trust_score):
            return None
        
        record = ChannelRecord(
            channel=MemoryChannel.SEMANTIC,
            agent_id=agent_id,
            content=content,
            topic_tags=topic_tags or [],
            trace_id=trace_id,
        )
        self._buffers[agent_id][MemoryChannel.SEMANTIC].append(record)

        # Also write to semantic backend (ChromaDB/hybrid) if configured
        try:
            from nexus_os.vault.semantic_backend import get_semantic_backend
            backend = get_semantic_backend()
            if backend:
                backend.store(
                    key=record.record_id,
                    content=content,
                    metadata={
                        "agent_id": agent_id,
                        "dossier_id": source_dossier_id or "",
                        "tags": ",".join(topic_tags or []),
                        "channel": "semantic",
                    },
                )
        except (ImportError, Exception):
            pass

        logger.debug(f"SEMANTIC: {agent_id} → dossier={source_dossier_id}")
        return record
    
    # ── PROCEDURAL Channel (4) ─────────────────────────────────────
    
    def append_procedural(
        self,
        agent_id: str,
        content: str,
        skill_tags: List[str],
        confidence: float,
        trust_score: float = 0.0,
        trace_id: Optional[str] = None,
    ) -> Optional[ChannelRecord]:
        """Append a PROCEDURAL record (verified skill, execution path).
        
        Merged from original CAPABILITY track.
        Trust gate: 80 (verified skills require high trust).
        Execution path: COLD (1000s SLA).
        """
        if not self._check_write_access(agent_id, MemoryChannel.PROCEDURAL, trust_score):
            return None
        
        record = ChannelRecord(
            channel=MemoryChannel.PROCEDURAL,
            agent_id=agent_id,
            content=content,
            skill_tags=skill_tags,
            confidence=confidence,
            trace_id=trace_id,
        )
        self._buffers[agent_id][MemoryChannel.PROCEDURAL].append(record)
        self._update_capability_profile(agent_id, skill_tags, confidence)
        logger.debug(f"PROCEDURAL: {agent_id} → {skill_tags}")
        return record
    
    def _update_capability_profile(self, agent_id: str, skill_tags: List[str], confidence: float):
        """Update internal capability profile."""
        if agent_id not in self._capabilities:
            self._capabilities[agent_id] = CapabilityProfile(agent_id=agent_id)
        profile = self._capabilities[agent_id]
        for tag in skill_tags:
            if tag in {"python", "javascript", "rust", "go", "typescript"}:
                category = "languages"
            elif tag in {"code", "research", "analysis", "security"}:
                category = "domains"
            else:
                category = "tools"
            store = getattr(profile, category)
            if tag in store:
                store[tag] = 0.7 * store[tag] + 0.3 * confidence
            else:
                store[tag] = confidence
    
    def get_capability(self, agent_id: str) -> Optional[CapabilityProfile]:
        """Get agent capability profile."""
        return self._capabilities.get(agent_id)
    
    # ── TRUST Channel (5) ──────────────────────────────────────────
    
    def append_trust(
        self,
        agent_id: str,
        lane: str = "general",
        trust_score: float = 100.0,
        evidence_count: int = 1,
        content: str = "",
        trace_id: Optional[str] = None,
        writer_trust: float = 0.0,
    ) -> Optional[ChannelRecord]:
        """Append a TRUST record (lane-scoped novel tanh-based trust formula scoring).

        Merged from original TRUST + GOVERNANCE tracks.
        Trust gate: 90, enforced against ``writer_trust`` — the writing
        entity's authority — NOT against ``trust_score``, which is the
        recorded value and may legitimately be low (e.g. the TrustKernel
        recording a failing agent's score). Hard-fail default: writes are
        denied unless the caller states sufficient authority.
        Execution path: HOT (0.02s SLA).
        """
        if not self._check_write_access(agent_id, MemoryChannel.TRUST, writer_trust):
            return None
        if lane not in VALID_LANES and content == "":
            content = lane
            lane = "general"
        if lane not in VALID_LANES:
            logger.warning(f"Unknown lane: {lane}, defaulting to 'general'")
            lane = "general"
        
        record = ChannelRecord(
            channel=MemoryChannel.TRUST,
            agent_id=agent_id,
            content=content,
            lane=lane,
            trust_score=trust_score,
            evidence_count=evidence_count,
            trace_id=trace_id,
        )
        self._buffers[agent_id][MemoryChannel.TRUST].append(record)
        logger.debug(f"TRUST: {agent_id}[{lane}] = {trust_score:.2f} (n={evidence_count})")
        return record
    
    def append_governance(
        self,
        agent_id: str,
        rule_violated: str,
        severity: str = "low",
        content: str = "",
        trace_id: Optional[str] = None,
        writer_trust: float = 0.0,
    ) -> Optional[ChannelRecord]:
        """Append a governance record (behavior under rules).

        Stored in TRUST channel with governance metadata.
        Trust gate: 90, enforced against ``writer_trust`` (hard-fail default —
        denied unless the caller states sufficient authority).
        """
        if not self._check_write_access(agent_id, MemoryChannel.TRUST, writer_trust):
            return None
        record = ChannelRecord(
            channel=MemoryChannel.TRUST,
            agent_id=agent_id,
            content=content,
            lane="governance",
            rule_violated=rule_violated,
            severity=severity,
            trace_id=trace_id,
        )
        self._buffers[agent_id][MemoryChannel.TRUST].append(record)
        logger.debug(f"GOVERNANCE: {agent_id} → {rule_violated} ({severity})")
        return record
    
    # ── TASK Channel (6) ───────────────────────────────────────────
    
    def append_task(
        self,
        agent_id: str,
        content: str,
        task_id: Optional[str] = None,
        task_status: str = "active",
        trust_score: float = 0.0,
        trace_id: Optional[str] = None,
    ) -> Optional[ChannelRecord]:
        """Append a TASK record (task-specific context).
        
        Trust gate: 40 (task context requires basic trust).
        Execution path: WARM (50s SLA).
        Auto-cleanup: completed/cancelled tasks are archived after 24h.
        """
        legacy_simple_call = task_id is None and trust_score == 0.0
        effective_trust = 100.0 if legacy_simple_call else trust_score
        if not self._check_write_access(agent_id, MemoryChannel.TASK, effective_trust):
            return None
        task_id = task_id or f"task-{len(self._buffers[agent_id][MemoryChannel.TASK]) + 1}"
        
        record = ChannelRecord(
            channel=MemoryChannel.TASK,
            agent_id=agent_id,
            content=content,
            task_id=task_id,
            task_status=task_status,
            trace_id=trace_id,
        )
        self._buffers[agent_id][MemoryChannel.TASK].append(record)
        logger.debug(f"TASK: {agent_id} → {task_id} ({task_status})")
        return record
    
    # ── META Channel (7) ───────────────────────────────────────────
    
    def append_meta(
        self,
        agent_id: str,
        meta_type: str,
        meta_value: Optional[float] = None,
        content: str = "",
        trust_score: float = 0.0,
        trace_id: Optional[str] = None,
    ) -> Optional[ChannelRecord]:
        """Append a META record (memory health, consolidation stats).
        
        Trust gate: 70 (system health metrics require good trust).
        Execution path: COLD (1000s SLA).
        Types: "consolidation", "retrieval_stats", "health", "sleep_time"
        """
        legacy_simple_call = meta_value is None and trust_score == 0.0
        if legacy_simple_call:
            content = content or meta_type
            meta_type = "note"
            meta_value = 1.0
        effective_trust = 100.0 if legacy_simple_call else trust_score
        if not self._check_write_access(agent_id, MemoryChannel.META, effective_trust):
            return None
        
        record = ChannelRecord(
            channel=MemoryChannel.META,
            agent_id=agent_id,
            content=content,
            meta_type=meta_type,
            meta_value=meta_value,
            trace_id=trace_id,
        )
        self._buffers[agent_id][MemoryChannel.META].append(record)
        logger.debug(f"META: {agent_id} → {meta_type}={meta_value:.2f}")
        return record
    
    def update_consolidation_stats(
        self,
        channel: MemoryChannel,
        total: int = 0,
        consolidated: int = 0,
        deduplicated: int = 0,
        avg_retrieval_ms: float = 0.0,
        hit_rate: float = 0.0,
    ):
        """Update consolidation statistics for a channel."""
        stats = self._consolidation_stats[channel]
        stats.total_records = total
        stats.consolidated_records = consolidated
        stats.deduplicated_records = deduplicated
        stats.avg_retrieval_time_ms = avg_retrieval_ms
        stats.retrieval_hit_rate = hit_rate
        stats.last_consolidation = __import__('time').time()
    
    # ── Query Methods ────────────────────────────────────────────
    
    def get_records(
        self,
        agent_id: str,
        channel: MemoryChannel,
        limit: int = 100,
    ) -> List[ChannelRecord]:
        """Get recent records for agent on a specific channel.
        Each read increments the record's access_count and updates last_access
        for adaptive memory persistence tracking."""
        if isinstance(channel, str):
            channel = MemoryChannel(channel)
        records = self._buffers[agent_id][channel]
        now = time.time()
        for r in records[-limit:]:
            r.access_count += 1
            r.last_access = now
        return records[-limit:]

    def update_persistence_scores(self, agent_id: str, channel: MemoryChannel) -> None:
        """Recalculate persistence scores for all records in a channel.
        B'MOJO-inspired: frequently-accessed records approach eidetic (1.0),
        while rarely-accessed records fade toward 0.0."""
        if isinstance(channel, str):
            channel = MemoryChannel(channel)
        now = time.time()
        for record in self._buffers[agent_id][channel]:
            last = record.last_access or record.timestamp or now
            hours_since_access = (now - last) / 3600.0
            decay = 1.0 / (1.0 + hours_since_access * 0.1)
            freq_boost = 1.0 - (1.0 / (1.0 + record.access_count * 0.5))
            record.persistence_score = min(1.0, max(0.0, freq_boost * 0.7 + decay * 0.3))

    def run_adaptive_persistence(self, agent_id: str) -> Dict[str, int]:
        """Scan all channels for an agent and auto-migrate entries whose
        persistence score suggests a different channel. Returns migration
        counts per target channel.

        Channel migration rules:
          - persistence >= 0.8 → candidate for next higher channel (eidetic)
          - persistence < 0.1 → candidate for next lower channel (fading)
          - SENSORY/WORKING are baseline; PROCEDURAL/TRUST are stable.
        """
        migrations: Dict[str, int] = {}
        channel_rank = {
            MemoryChannel.SENSORY: 0,
            MemoryChannel.WORKING: 1,
            MemoryChannel.EPISODIC: 2,
            MemoryChannel.SEMANTIC: 3,
            MemoryChannel.PROCEDURAL: 4,
            MemoryChannel.TRUST: 5,
            MemoryChannel.TASK: 6,
            MemoryChannel.META: 7,
        }

        # Track IDs of migrated records to prevent cascading re-migration
        migrated_ids: set[str] = set()

        for channel in MemoryChannel:
            self.update_persistence_scores(agent_id, channel)
            rank = channel_rank[channel]
            survivors: List[ChannelRecord] = []
            for record in self._buffers[agent_id][channel]:
                # Generate stable identifier for this record
                record_id = f"{channel.value}:{id(record)}"
                if record_id in migrated_ids:
                    survivors.append(record)
                    continue
                if record.persistence_score >= 0.8 and rank < 7 and channel not in (MemoryChannel.PROCEDURAL, MemoryChannel.TRUST, MemoryChannel.META):
                    target = next(c for c, r in channel_rank.items() if r == rank + 1)
                    self._buffers[agent_id][target].append(record)
                    migrated_ids.add(f"{target.value}:{id(record)}")
                    migrations[target.value] = migrations.get(target.value, 0) + 1
                elif record.persistence_score < 0.1 and rank > 0 and channel not in (MemoryChannel.SENSORY, MemoryChannel.WORKING, MemoryChannel.META):
                    target = next(c for c, r in channel_rank.items() if r == rank - 1)
                    self._buffers[agent_id][target].append(record)
                    migrated_ids.add(f"{target.value}:{id(record)}")
                    migrations[target.value] = migrations.get(target.value, 0) + 1
                else:
                    survivors.append(record)
            self._buffers[agent_id][channel] = survivors

        return migrations
    
    def get_trust_history(
        self,
        agent_id: str,
        lane: Optional[str] = None,
    ) -> List[ChannelRecord]:
        """Get trust history for agent (optionally filtered by lane)."""
        records = self._buffers[agent_id][MemoryChannel.TRUST]
        if lane is None:
            return records
        return [r for r in records if r.lane == lane]
    
    def get_latest_trust(self, agent_id: str, lane: str = "general") -> Optional[float]:
        """Get latest trust score for agent in lane."""
        history = self.get_trust_history(agent_id, lane)
        if not history:
            return None
        return history[-1].trust_score
    
    def get_failures(self, agent_id: str) -> Dict[str, FailurePattern]:
        """Get all failure patterns for agent."""
        return self._failures.get(agent_id, {})
    
    def get_critical_failures(self, agent_id: str) -> List[FailurePattern]:
        """Get high-severity failures for agent."""
        failures = self.get_failures(agent_id)
        return [f for f in failures.values() if f.severity == "high"]
    
    def get_buffer_summary(self, agent_id: str) -> Dict[str, int]:
        """Get counts per channel for an agent."""
        return {
            channel.value: len(self._buffers[agent_id][channel])
            for channel in MemoryChannel
        }
    
    def get_consolidation_stats(self, channel: MemoryChannel) -> ConsolidationStats:
        """Get consolidation statistics for a channel."""
        return self._consolidation_stats[channel]
    
    def clear_buffer(self, agent_id: str) -> Dict[str, list]:
        """Clear buffer for agent (after persistence to DB).
        
        Returns:
            Dict mapping channel name to list of cleared records.
        """
        cleared: Dict[str, list] = {}
        if agent_id in self._buffers:
            for channel in MemoryChannel:
                buf = self._buffers[agent_id][channel]
                if buf:
                    cleared[channel.value] = list(buf)
                buf.clear()  # type: ignore
        return cleared
    
    def get_execution_path(self, channel: MemoryChannel) -> ExecutionPath:
        """Map channel to execution path (HOT/WARM/COLD)."""
        if channel in {MemoryChannel.SENSORY, MemoryChannel.WORKING, MemoryChannel.TRUST}:
            return ExecutionPath.HOT
        elif channel in {MemoryChannel.EPISODIC, MemoryChannel.TASK}:
            return ExecutionPath.WARM
        else:
            return ExecutionPath.COLD


# Singleton instance
_manager: Optional[MemoryChannelManager] = None


def get_manager() -> MemoryChannelManager:
    """Get the singleton MemoryChannelManager instance."""
    global _manager
    if _manager is None:
        _manager = MemoryChannelManager()
    return _manager
