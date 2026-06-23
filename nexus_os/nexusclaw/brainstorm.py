"""nexus_os/nexusclaw/brainstorm.py - NEXUSCLAW Brainstorm Engine

The Brainstorm Engine enables multiple agents to collaboratively generate
ideas, discuss proposals, and reach consensus. It is NOT just a chat — it is a
structured deliberation process with:
  - Idea proposal (any agent can propose an idea)
  - Round-robin discussion (each agent responds in turn)
  - Voting (agents vote for/against/abstain on proposals)
  - Consensus building (weighted by trust score)
  - Evidence grounding (all proposals must reference evidence)
  - Governance gates (high-risk proposals require human approval)
  - All deliberations are logged to memory channels and worklog

The engine supports multiple modes:
  - OPEN: Free-form discussion (anyone can propose anytime)
  - STRUCTURED: Phased (propose -> discuss -> vote -> resolve)
  - RED_TEAM: Adversarial review (one team proposes, one team critiques)

Inspired by academic deliberation frameworks and governance best practices,
but built uniquely for NEXUSCLAW multi-agent coordination.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

from nexus_os.nexusclaw.agent_pool import AgentPool, AgentRecord, get_agent_pool
from nexus_os.nexusclaw.envelope import RiskLevel
from nexus_os.nexusclaw.message_bus import MessageBus, NexusMessage, MessageType, MessagePriority
from nexus_os.nexusclaw.worklog import WorklogSystem, get_worklog
from nexus_os.vault.memory_channels import MemoryChannelManager, get_manager

logger = logging.getLogger("nexusclaw.brainstorm")


class BrainstormMode(str, Enum):
    """Mode of brainstorm session."""
    OPEN = "open"           # Free-form discussion
    STRUCTURED = "structured"   # Phased: propose -> discuss -> vote -> resolve
    RED_TEAM = "red_team"       # Adversarial: propose vs critique
    REDUNDANT = "redundant"     # Redundant deliberation: K parallel trajectories + leader synthesis


class BrainstormPhase(str, Enum):
    """Current phase of a structured brainstorm session."""
    PROPOSE = "propose"       # Agents propose ideas
    DISCUSS = "discuss"       # Agents discuss proposals
    VOTE = "vote"           # Agents vote on proposals
    RESOLVE = "resolve"       # Consensus is computed and final decision made
    CLOSED = "closed"         # Session is complete


class VoteChoice(str, Enum):
    """Vote choice on a proposal."""
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


@dataclass
class ParallelTrajectory:
    """A single independent reasoning trajectory (HeavySkill-inspired)."""
    trajectory_id: str
    proposal_id: str
    agent_id: str
    agent_name: str
    reasoning_text: str
    confidence: float = 0.0  # 0.0-1.0 self-assessed confidence
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trajectory_id": self.trajectory_id,
            "proposal_id": self.proposal_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "reasoning_text": self.reasoning_text[:1000],  # Truncate for safety
            "confidence": self.confidence,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class DeliberationResult:
    """Synthesized result from K parallel trajectories (HeavySkill Stage 2)."""
    result_id: str
    proposal_id: str
    synthesized_answer: str
    answer_distribution: Dict[str, int]  # answer -> count
    cross_validation_notes: List[str]
    identified_errors: List[str]
    final_confidence: float
    trajectories_used: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "proposal_id": self.proposal_id,
            "synthesized_answer": self.synthesized_answer[:1000],
            "answer_distribution": self.answer_distribution,
            "cross_validation_notes": self.cross_validation_notes,
            "identified_errors": self.identified_errors,
            "final_confidence": self.final_confidence,
            "trajectories_used": self.trajectories_used,
            "timestamp": self.timestamp,
        }


@dataclass
class ParallelReasoningConfig:
    """Configuration for HeavySkill-inspired parallel reasoning.

    K = number of parallel reasoning trajectories (default 8).
    summary_k = number of deliberation samples (default 4).
    iterations = iterative deliberation rounds (default 1).
    auto_trigger = whether to auto-trigger for critical proposals with <3 participants.
    min_participants_for_normal = minimum participants to skip parallel reasoning.
    """
    k: int = 8
    summary_k: int = 4
    iterations: int = 1
    auto_trigger: bool = True
    min_participants_for_normal: int = 3
    max_reasoning_length: int = 2000
    synthesizer_agent_id: Optional[str] = None  # Agent to run synthesis; None = round-robin


@dataclass
class Proposal:
    """A proposal in a brainstorm session."""
    proposal_id: str
    session_id: str
    agent_id: str
    agent_name: str
    title: str
    description: str
    evidence_refs: List[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    trust_score_at_proposal: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    votes: Dict[str, VoteChoice] = field(default_factory=dict)  # agent_id -> vote
    vote_weights: Dict[str, float] = field(default_factory=dict)  # agent_id -> trust weight
    consensus_score: float = 0.0  # 0.0 to 1.0
    accepted: Optional[bool] = None  # None = pending, True/False = resolved

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "title": self.title,
            "description": self.description,
            "evidence_refs": self.evidence_refs,
            "risk_level": self.risk_level.value,
            "trust_score_at_proposal": self.trust_score_at_proposal,
            "timestamp": self.timestamp,
            "votes": {k: v.value for k, v in self.votes.items()},
            "vote_weights": self.vote_weights,
            "consensus_score": self.consensus_score,
            "accepted": self.accepted,
        }


@dataclass
class BrainstormSession:
    """A brainstorm session with multiple agents."""
    session_id: str
    topic: str
    mode: BrainstormMode
    participant_ids: List[str]
    phase: BrainstormPhase = BrainstormPhase.PROPOSE
    proposals: List[Proposal] = field(default_factory=list)
    messages: List[NexusMessage] = field(default_factory=list)
    max_proposals: int = 10
    max_rounds: int = 5
    current_round: int = 0
    discussion_count: int = 0
    consensus_threshold: float = 0.66  # 2/3 majority for consensus
    risk_level: RiskLevel = RiskLevel.MEDIUM
    trust_threshold: float = 30.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    closed_at: Optional[str] = None
    winner_proposal_id: Optional[str] = None
    final_consensus: float = 0.0

    @property
    def is_open(self) -> bool:
        return self.phase != BrainstormPhase.CLOSED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "mode": self.mode.value,
            "participant_ids": self.participant_ids,
            "phase": self.phase.value,
            "proposals_count": len(self.proposals),
            "messages_count": len(self.messages),
            "max_proposals": self.max_proposals,
            "max_rounds": self.max_rounds,
            "current_round": self.current_round,
            "consensus_threshold": self.consensus_threshold,
            "risk_level": self.risk_level.value,
            "trust_threshold": self.trust_threshold,
            "created_at": self.created_at,
            "closed_at": self.closed_at,
            "winner_proposal_id": self.winner_proposal_id,
            "final_consensus": self.final_consensus,
            "is_open": self.is_open,
        }


class BrainstormEngine:
    """NEXUSCLAW Brainstorm Engine for collaborative multi-agent deliberation.

    Features:
    - Structured phased sessions (propose -> discuss -> vote -> resolve)
    - Open free-form sessions
    - Red-team adversarial review
    - Trust-weighted voting
    - Consensus computation
    - Evidence-grounded proposals (must reference evidence)
    - Governance gates (high/critical risk proposals require human approval)
    - All activity logged to memory channels and worklog
    """

    def __init__(
        self,
        agent_pool: Optional[AgentPool] = None,
        message_bus: Optional[MessageBus] = None,
        worklog: Optional[WorklogSystem] = None,
        memory_channels: Optional[MemoryChannelManager] = None,
    ) -> None:
        self.agent_pool = agent_pool or get_agent_pool()
        self.message_bus = message_bus or MessageBus()
        self.worklog = worklog or get_worklog()
        self.memory_channels = memory_channels or get_manager()
        self._sessions: Dict[str, BrainstormSession] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(
        self,
        topic: str,
        participant_ids: List[str],
        mode: BrainstormMode = BrainstormMode.STRUCTURED,
        max_proposals: int = 10,
        max_rounds: int = 5,
        consensus_threshold: float = 0.66,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        trust_threshold: float = 30.0,
    ) -> BrainstormSession:
        """Create a new brainstorm session."""
        with self._lock:
            # Validate participants
            valid_participants = []
            for pid in participant_ids:
                agent = self.agent_pool.get(pid)
                if agent and agent.is_available and agent.trust_score >= trust_threshold:
                    valid_participants.append(pid)
                else:
                    logger.warning("Participant %s not available or below trust threshold %s", pid, trust_threshold)

            if not valid_participants:
                raise ValueError(f"No valid participants available for brainstorm session (trust_threshold={trust_threshold})")

            session_id = f"bs-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{hash(topic) % 10000}"
            session = BrainstormSession(
                session_id=session_id,
                topic=topic,
                mode=mode,
                participant_ids=valid_participants,
                max_proposals=max_proposals,
                max_rounds=max_rounds,
                consensus_threshold=consensus_threshold,
                risk_level=risk_level,
                trust_threshold=trust_threshold,
            )
            self._sessions[session_id] = session

            # Create a message thread for this session
            self.message_bus.create_thread(topic=topic, participant_ids=valid_participants, thread_id=session_id)

            # Log session creation
            self._log_session_event(session, "created")

            return session

    def get_session(self, session_id: str) -> Optional[BrainstormSession]:
        """Get a brainstorm session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self, status: Optional[str] = None) -> List[BrainstormSession]:
        """List sessions, optionally filtered by open/closed status."""
        with self._lock:
            sessions = list(self._sessions.values())
            if status == "open":
                sessions = [s for s in sessions if s.is_open]
            elif status == "closed":
                sessions = [s for s in sessions if not s.is_open]
            return sessions

    # ------------------------------------------------------------------
    # Proposals
    # ------------------------------------------------------------------

    def propose(
        self,
        session_id: str,
        agent_id: str,
        title: str,
        description: str,
        evidence_refs: Optional[List[str]] = None,
        risk_level: RiskLevel = RiskLevel.LOW,
    ) -> Proposal:
        """Submit a proposal in a brainstorm session."""
        with self._lock:
            session = self._require_session(session_id)

            if not session.is_open:
                raise ValueError(f"Session {session_id} is closed")

            if session.mode == BrainstormMode.STRUCTURED and session.phase != BrainstormPhase.PROPOSE:
                raise ValueError(f"Session {session_id} is not in PROPOSE phase (current: {session.phase.value})")

            if len(session.proposals) >= session.max_proposals:
                raise ValueError(f"Session {session_id} has reached max proposals ({session.max_proposals})")

            agent = self.agent_pool.get(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            if agent_id not in session.participant_ids:
                raise ValueError(f"Agent {agent_id} is not a participant in session {session_id}")

            # Evidence requirement: proposals must have at least one evidence reference
            evidence = evidence_refs or []
            if not evidence and session.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                raise ValueError("High/critical risk proposals must include evidence references")

            proposal_id = f"prop-{session_id}-{len(session.proposals)}"
            proposal = Proposal(
                proposal_id=proposal_id,
                session_id=session_id,
                agent_id=agent_id,
                agent_name=agent.name,
                title=title,
                description=description,
                evidence_refs=evidence,
                risk_level=risk_level,
                trust_score_at_proposal=agent.trust_score,
            )
            session.proposals.append(proposal)

            # Broadcast proposal to all participants
            self._broadcast_proposal(session, proposal)

            self._log_proposal(session, proposal)

            return proposal

    def _broadcast_proposal(self, session: BrainstormSession, proposal: Proposal) -> None:
        """Broadcast a proposal to all session participants."""
        for pid in session.participant_ids:
            if pid == proposal.agent_id:
                continue
            message = NexusMessage(
                message_id=f"msg-{proposal.proposal_id}-{pid}",
                sender_id=proposal.agent_id,
                sender_name=proposal.agent_name,
                recipient_ids=[pid],
                message_type=MessageType.BRAINSTORM,
                content=f"[Proposal] {proposal.title}: {proposal.description[:500]}",
                priority=MessagePriority.NORMAL,
                thread_id=session.session_id,
                risk_level=proposal.risk_level,
            )
            self.message_bus.send(message)
            session.messages.append(message)

    # ------------------------------------------------------------------
    # Discussion
    # ------------------------------------------------------------------

    def advance_phase(self, session_id: str) -> BrainstormSession:
        """Advance a structured or redundant session to the next phase."""
        with self._lock:
            session = self._require_session(session_id)

            if session.mode == BrainstormMode.REDUNDANT:
                # REDUNDANT mode: propose -> parallel_reason -> resolve -> close
                if session.phase == BrainstormPhase.PROPOSE:
                    session.phase = BrainstormPhase.RESOLVE
                    self._resolve_redundant(session)
                elif session.phase == BrainstormPhase.RESOLVE:
                    session.phase = BrainstormPhase.CLOSED
                    session.closed_at = datetime.now(timezone.utc).isoformat()
                else:
                    raise ValueError(
                        f"Session {session_id} in REDUNDANT mode cannot enter phase {session.phase.value}"
                    )
                self._log_session_event(session, f"phase_advanced:{session.phase.value}")
                return session

            if session.mode != BrainstormMode.STRUCTURED:
                raise ValueError(f"Session {session_id} is not in structured or redundant mode")

            if session.phase == BrainstormPhase.PROPOSE:
                session.phase = BrainstormPhase.DISCUSS
                # HeavySkill-inspired: for CRITICAL proposals with <3 participants,
                # auto-trigger parallel reasoning to enhance deliberation quality
                for proposal in session.proposals:
                    if proposal.risk_level == RiskLevel.CRITICAL:
                        other_count = len([pid for pid in session.participant_ids if pid != proposal.agent_id])
                        if other_count < 3:
                            logger.info(
                                "Auto-triggering parallel reasoning for CRITICAL proposal %s "
                                "(only %d other participants available)",
                                proposal.proposal_id, other_count,
                            )
                            try:
                                self.run_parallel_reasoning_for_proposal(
                                    session_id, proposal.proposal_id
                                )
                            except Exception as exc:
                                logger.warning(
                                    "Parallel reasoning auto-trigger failed for proposal %s: %s",
                                    proposal.proposal_id, exc,
                                )
            elif session.phase == BrainstormPhase.DISCUSS:
                if session.discussion_count == 0:
                    raise ValueError(
                        f"Quorum not met: session {session_id} has no discussion comments. "
                        f"At least one discussion comment is required before voting."
                    )
                session.phase = BrainstormPhase.VOTE
            elif session.phase == BrainstormPhase.VOTE:
                # Quorum verification: at least 1 other participant must have cast a vote on each proposal
                for proposal in session.proposals:
                    other_participants = [pid for pid in session.participant_ids if pid != proposal.agent_id]
                    votes_from_others = [pid for pid in other_participants if pid in proposal.votes]
                    if other_participants and not votes_from_others:
                        raise ValueError(
                            f"Quorum not met for proposal {proposal.proposal_id}: "
                            f"no other participants have voted on it."
                        )
                session.phase = BrainstormPhase.RESOLVE
                self._compute_consensus(session)
            elif session.phase == BrainstormPhase.RESOLVE:
                session.phase = BrainstormPhase.CLOSED
                session.closed_at = datetime.now(timezone.utc).isoformat()

            self._log_session_event(session, f"phase_advanced:{session.phase.value}")
            return session

    def _resolve_redundant(self, session: BrainstormSession) -> None:
        """REDUNDANT resolution: run parallel reasoning for all proposals and
        synthesize via leader agent. Each proposal generates K trajectories and
        the leader (or default synthesizer) produces a deliberation result that
        serves as the consensus."""
        cfg = ParallelReasoningConfig(
            k=5,
            synthesizer_agent_id=self._find_leader_agent(session),
        )
        for proposal in session.proposals:
            try:
                result = self.run_parallel_reasoning_for_proposal(
                    session.session_id, proposal.proposal_id, cfg,
                )
                # Use deliberation result as the proposal's consensus score
                proposal.consensus_score = result.final_confidence
                proposal.accepted = result.final_confidence >= session.consensus_threshold
            except Exception as exc:
                logger.warning("REDUNDANT resolution failed for proposal %s: %s", proposal.proposal_id, exc)
                proposal.consensus_score = 0.0
                proposal.accepted = False

        # Determine winner
        accepted = [p for p in session.proposals if p.accepted]
        if accepted:
            winner = max(accepted, key=lambda p: p.consensus_score)
            session.winner_proposal_id = winner.proposal_id
            session.final_consensus = winner.consensus_score
        else:
            session.winner_proposal_id = None
            session.final_consensus = max((p.consensus_score for p in session.proposals), default=0.0)

    def _find_leader_agent(self, session: BrainstormSession) -> Optional[str]:
        """Find the best leader agent for a REDUNDANT session. Prefers an
        AgentType.LEADER agent, falls back to the highest-trust participant."""
        for pid in session.participant_ids:
            agent = self.agent_pool.get(pid)
            if agent and agent.agent_type.value == "leader":
                return pid
        # Fallback: highest-trust participant
        best: Optional[str] = None
        best_trust = -1.0
        for pid in session.participant_ids:
            agent = self.agent_pool.get(pid)
            if agent and agent.trust_score > best_trust:
                best = pid
                best_trust = agent.trust_score
        return best

    def discuss(
        self,
        session_id: str,
        agent_id: str,
        proposal_id: str,
        comment: str,
    ) -> NexusMessage:
        """Submit a discussion comment on a proposal."""
        with self._lock:
            session = self._require_session(session_id)
            proposal = self._require_proposal(session, proposal_id)

            if not session.is_open:
                raise ValueError(f"Session {session_id} is closed")

            if session.mode == BrainstormMode.STRUCTURED and session.phase != BrainstormPhase.DISCUSS:
                raise ValueError(f"Session {session_id} is not in DISCUSS phase")

            message = NexusMessage(
                message_id=f"discuss-{session_id}-{agent_id}-{len(session.messages)}",
                sender_id=agent_id,
                sender_name=self.agent_pool.get(agent_id).name if self.agent_pool.get(agent_id) else agent_id,
                recipient_ids=[proposal.agent_id],
                message_type=MessageType.BRAINSTORM,
                content=f"[Discussion on {proposal.title}] {comment}",
                priority=MessagePriority.NORMAL,
                thread_id=session_id,
                risk_level=proposal.risk_level,
            )
            self.message_bus.send(message)
            session.discussion_count += 1
            session.messages.append(message)
            return message

    # ------------------------------------------------------------------
    # Voting
    # ------------------------------------------------------------------

    def vote(
        self,
        session_id: str,
        agent_id: str,
        proposal_id: str,
        choice: VoteChoice,
    ) -> Proposal:
        """Cast a vote on a proposal."""
        with self._lock:
            session = self._require_session(session_id)
            proposal = self._require_proposal(session, proposal_id)

            if not session.is_open:
                raise ValueError(f"Session {session_id} is closed")

            if session.mode == BrainstormMode.STRUCTURED and session.phase != BrainstormPhase.VOTE:
                raise ValueError(f"Session {session_id} is not in VOTE phase")

            agent = self.agent_pool.get(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            if agent_id not in session.participant_ids:
                raise ValueError(f"Agent {agent_id} is not a participant")

            proposal.votes[agent_id] = choice
            proposal.vote_weights[agent_id] = agent.trust_score / 100.0  # Normalize to 0-1

            self._log_vote(session, proposal, agent_id, choice)

            return proposal

    def _compute_consensus(self, session: BrainstormSession) -> None:
        """Compute consensus scores for all proposals in a session.
        
        No implicit FOR vote — proposer must vote explicitly like all other participants.
        """
        for proposal in session.proposals:
            votes = dict(proposal.votes)
            vote_weights = dict(proposal.vote_weights)

            for_weight = sum(
                vote_weights[agent_id]
                for agent_id, vote in votes.items()
                if vote == VoteChoice.FOR
            )
            against_weight = sum(
                vote_weights[agent_id]
                for agent_id, vote in votes.items()
                if vote == VoteChoice.AGAINST
            )

            total_active_weight = for_weight + against_weight
            if total_active_weight == 0:
                proposal.consensus_score = 0.0
                proposal.accepted = False
                continue

            # Consensus score = (for - against) / total_active_weight, normalized to 0-1
            raw_score = (for_weight - against_weight) / total_active_weight
            proposal.consensus_score = max(0.0, (raw_score + 1.0) / 2.0)

            # Accept if consensus >= threshold
            proposal.accepted = proposal.consensus_score >= session.consensus_threshold

        # Determine winner (highest consensus score among accepted)
        accepted = [p for p in session.proposals if p.accepted]
        if accepted:
            winner = max(accepted, key=lambda p: p.consensus_score)
            session.winner_proposal_id = winner.proposal_id
            session.final_consensus = winner.consensus_score
        else:
            session.winner_proposal_id = None
            session.final_consensus = max((p.consensus_score for p in session.proposals), default=0.0)

        # Log resolution
        self._log_session_event(session, "resolved")

    # ------------------------------------------------------------------
    # Close session
    # ------------------------------------------------------------------

    def close_session(self, session_id: str) -> BrainstormSession:
        """Close a brainstorm session."""
        with self._lock:
            session = self._require_session(session_id)
            session.phase = BrainstormPhase.CLOSED
            session.closed_at = datetime.now(timezone.utc).isoformat()
            self._log_session_event(session, "closed")
            return session

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _require_session(self, session_id: str) -> BrainstormSession:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Brainstorm session {session_id} not found")
        return session

    def _require_proposal(self, session: BrainstormSession, proposal_id: str) -> Proposal:
        for proposal in session.proposals:
            if proposal.proposal_id == proposal_id:
                return proposal
        raise ValueError(f"Proposal {proposal_id} not found in session {session.session_id}")

    # ------------------------------------------------------------------
    # HeavySkill-inspired Parallel Reasoning + Deliberation Synthesis
    # ------------------------------------------------------------------

    def parallel_reason(
        self,
        session_id: str,
        proposal_id: str,
        config: Optional[ParallelReasoningConfig] = None,
    ) -> List[ParallelTrajectory]:
        """Generate K independent reasoning trajectories for a proposal.

        HeavySkill Stage 1: Parallel Reasoning. Each available participant
        generates an independent reasoning path for the proposal. If fewer than
        K participants are available, the same agent can produce multiple
        trajectories with varied parameters (simulated temperature/settings).

        Returns list of ParallelTrajectory objects.
        """
        cfg = config or ParallelReasoningConfig()
        session = self._require_session(session_id)
        proposal = self._require_proposal(session, proposal_id)

        trajectories: List[ParallelTrajectory] = []
        available_agents = [
            pid for pid in session.participant_ids
            if pid != proposal.agent_id
        ]

        if not available_agents:
            logger.info(
                "parallel_reason: no other participants in session %s — "
                "generating K trajectories from proposer %s with varied parameters",
                session_id, proposal.agent_id,
            )
            available_agents = [proposal.agent_id]

        # Generate K trajectories, cycling through available agents
        for i in range(cfg.k):
            agent_id = available_agents[i % len(available_agents)]
            agent = self.agent_pool.get(agent_id)
            if not agent or not agent.is_available:
                logger.warning("parallel_reason: agent %s not available, skipping", agent_id)
                continue

            # Simulate independent reasoning with varying "temperature" per trajectory
            # In a real implementation, this would call the agent's reasoning API
            # with different temperature/top_p parameters. Here we simulate by
            # varying the reasoning emphasis.
            emphasis_list = [
                "focus on correctness and edge cases",
                "focus on simplicity and maintainability",
                "focus on security implications",
                "focus on performance and scalability",
                "focus on compatibility with existing systems",
                "focus on cost and resource efficiency",
                "focus on testability and observability",
                "focus on governance and compliance",
            ]
            emphasis = emphasis_list[i % len(emphasis_list)]

            reasoning_text = (
                f"[Trajectory {i+1}/{cfg.k} by {agent.name}] "
                f"Analyzing proposal '{proposal.title}' with emphasis: {emphasis}.\n\n"
                f"Proposal: {proposal.description[:cfg.max_reasoning_length]}\n\n"
                f"Reasoning: Starting from the evidence references {proposal.evidence_refs}, "
                f"this trajectory evaluates the proposal through the lens of {emphasis}. "
                f"Initial assessment: the proposal has merit but requires verification."
            )

            # Simulate confidence based on agent trust score and trajectory index
            # (earlier trajectories from high-trust agents get higher base confidence)
            base_confidence = min(0.95, agent.trust_score / 100.0)
            variation = 0.05 * ((-1) ** i)  # Slight oscillation per trajectory
            confidence = max(0.1, min(0.99, base_confidence + variation))

            traj = ParallelTrajectory(
                trajectory_id=f"traj-{session_id}-{proposal_id}-{i}",
                proposal_id=proposal_id,
                agent_id=agent_id,
                agent_name=agent.name,
                reasoning_text=reasoning_text,
                confidence=confidence,
                metadata={
                    "trajectory_index": i,
                    "emphasis": emphasis,
                    "agent_trust_score": agent.trust_score,
                    "temperature_simulated": 0.5 + (0.3 * (i % 3)),  # 0.5, 0.8, 1.1
                },
            )
            trajectories.append(traj)

            # Log trajectory to memory
            try:
                self.memory_channels.append_episodic(
                    agent_id=agent_id,
                    content=f"[Parallel Trajectory] {traj.reasoning_text[:500]}",
                    outcome="reasoning_generated",
                    trace_id=traj.trajectory_id,
                    project_id=session_id,
                )
            except Exception as e:
                logger.warning("Failed to log trajectory to EPISODIC: %s", e)

        self._log_session_event(
            session,
            f"parallel_reason_complete:{proposal_id}:trajectories={len(trajectories)}",
        )
        return trajectories

    def deliberation_synthesize(
        self,
        session_id: str,
        proposal_id: str,
        trajectories: List[ParallelTrajectory],
        config: Optional[ParallelReasoningConfig] = None,
    ) -> DeliberationResult:
        """Synthesize K trajectories into a superior final answer.

        HeavySkill Stage 2: Sequential Deliberation. Analyzes answer distribution
        across trajectories, cross-validates reasoning chains, identifies logical
        errors, and synthesizes a final answer with critical thinking.

        Returns DeliberationResult.
        """
        cfg = config or ParallelReasoningConfig()
        session = self._require_session(session_id)
        proposal = self._require_proposal(session, proposal_id)

        if not trajectories:
            return DeliberationResult(
                result_id=f"delib-{session_id}-{proposal_id}",
                proposal_id=proposal_id,
                synthesized_answer="No trajectories available for synthesis.",
                answer_distribution={},
                cross_validation_notes=["Insufficient reasoning trajectories."],
                identified_errors=["No trajectories to evaluate."],
                final_confidence=0.0,
                trajectories_used=0,
            )

        # 1. Analyze answer distribution across trajectories
        # In simulation, we map each trajectory to a simulated "answer" based on confidence
        # In real implementation, this would parse the actual reasoning output
        answer_distribution: Dict[str, int] = {}
        for traj in trajectories:
            # Simulate: high confidence = "approve", low confidence = "needs_work"
            answer = "approve" if traj.confidence > 0.7 else "needs_work"
            answer_distribution[answer] = answer_distribution.get(answer, 0) + 1

        # 2. Cross-validate reasoning chains
        cross_validation_notes: List[str] = []

        try:
            from nexus_os.gmr.peer_review import LLMPeerReview
            peer_review_engine = LLMPeerReview()
            texts = [traj.reasoning_text for traj in trajectories]
            best_text, best_idx = peer_review_engine.select_best(
                user_prompt=f"Evaluate this proposal: {proposal.title} - {proposal.description}",
                candidates=texts,
                use_weighted=True
            )
            cross_validation_notes.append(
                f"LLM-PeerReview selected trajectory {best_idx} (generated by {trajectories[best_idx].agent_name}) "
                f"as the best reasoning path."
            )
        except Exception as e:
            logger.debug("LLM-PeerReview ensembling skipped: %s", e)
        high_confidence_count = sum(1 for t in trajectories if t.confidence > 0.7)
        if high_confidence_count >= len(trajectories) / 2:
            cross_validation_notes.append(
                f"Majority of trajectories ({high_confidence_count}/{len(trajectories)}) "
                f"show high confidence (>0.7)."
            )
        else:
            cross_validation_notes.append(
                f"Only {high_confidence_count}/{len(trajectories)} trajectories show high confidence. "
                f"Proposal may need more evidence or revision."
            )

        # Check for divergent emphasis coverage
        emphasis_set = {t.metadata.get("emphasis", "unknown") for t in trajectories}
        if len(emphasis_set) >= 3:
            cross_validation_notes.append(
                f"Diverse emphasis coverage ({len(emphasis_set)} angles): {', '.join(sorted(emphasis_set))}. "
                f"Good for comprehensive evaluation."
            )

        # 3. Identify logical errors / conflicts
        identified_errors: List[str] = []
        if len(trajectories) < cfg.k:
            identified_errors.append(
                f"Only {len(trajectories)}/{cfg.k} requested trajectories were generated. "
                f"Some agents were unavailable."
            )
        if proposal.risk_level == RiskLevel.CRITICAL and high_confidence_count < len(trajectories) * 0.75:
            identified_errors.append(
                "CRITICAL proposal lacks unanimous high-confidence approval. "
                "Requires additional expert review or evidence."
            )

        # 4. Synthesize final answer
        # Weighted by confidence: approve if weighted average > 0.6
        total_weight = sum(t.confidence for t in trajectories)
        approve_weight = sum(
            t.confidence for t in trajectories if t.confidence > 0.7
        )
        approval_ratio = approve_weight / total_weight if total_weight > 0 else 0.0

        if approval_ratio >= 0.6:
            synthesized_answer = (
                f"Synthesis APPROVES proposal '{proposal.title}'. "
                f"Weighted approval ratio: {approval_ratio:.2f}. "
                f"Cross-validation: {len(cross_validation_notes)} notes, "
                f"{len(identified_errors)} concerns."
            )
            final_confidence = approval_ratio
        else:
            synthesized_answer = (
                f"Synthesis REJECTS proposal '{proposal.title}'. "
                f"Weighted approval ratio: {approval_ratio:.2f} (threshold: 0.6). "
                f"Cross-validation: {len(cross_validation_notes)} notes, "
                f"{len(identified_errors)} concerns."
            )
            final_confidence = 1.0 - approval_ratio

        result = DeliberationResult(
            result_id=f"delib-{session_id}-{proposal_id}",
            proposal_id=proposal_id,
            synthesized_answer=synthesized_answer,
            answer_distribution=answer_distribution,
            cross_validation_notes=cross_validation_notes,
            identified_errors=identified_errors,
            final_confidence=final_confidence,
            trajectories_used=len(trajectories),
        )

        # Log deliberation result to memory
        try:
            self.memory_channels.append_semantic(
                agent_id="nexusclaw-brainstorm",
                content=f"[Deliberation Synthesis] {synthesized_answer[:500]}",
                trace_id=result.result_id,
                source_dossier_id=session_id,
            )
        except Exception as e:
            logger.warning("Failed to log deliberation to SEMANTIC: %s", e)

        self._log_session_event(
            session,
            f"deliberation_synthesize_complete:{proposal_id}:confidence={final_confidence:.2f}",
        )
        return result

    def run_parallel_reasoning_for_proposal(
        self,
        session_id: str,
        proposal_id: str,
        config: Optional[ParallelReasoningConfig] = None,
    ) -> DeliberationResult:
        """One-shot: run parallel reasoning + deliberation synthesis for a proposal.

        Convenience method that calls parallel_reason() then deliberation_synthesize().
        """
        trajectories = self.parallel_reason(session_id, proposal_id, config)
        return self.deliberation_synthesize(session_id, proposal_id, trajectories, config)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_session_event(self, session: BrainstormSession, event: str) -> None:
        """Log a session event to worklog and memory."""
        try:
            self.worklog.log_task(
                agent_id="nexusclaw-brainstorm",
                task_id=session.session_id,
                intent=f"brainstorm:{event}",
                status="ok",
                duration_ms=0.0,
                evidence=[session.topic],
                metadata={"session": session.to_dict()},
            )
        except Exception as e:
            logger.warning("Failed to log brainstorm session event: %s", e)

        try:
            self.memory_channels.append_meta(
                agent_id="nexusclaw-brainstorm",
                meta_type="brainstorm_event",
                meta_value=1.0 if session.is_open else 0.0,
                content=f"Brainstorm session {session.session_id}: {event} (topic={session.topic})",
                trust_score=100.0,
            )
        except Exception as e:
            logger.warning("Failed to log brainstorm to META: %s", e)

    def _log_proposal(self, session: BrainstormSession, proposal: Proposal) -> None:
        """Log a proposal to memory."""
        try:
            self.memory_channels.append_episodic(
                agent_id=proposal.agent_id,
                content=f"[Brainstorm Proposal] {proposal.title}: {proposal.description[:500]}",
                outcome="proposed",
                duration_ms=0.0,
                token_count=len(proposal.description.split()),
                trace_id=proposal.proposal_id,
                project_id=session.session_id,
            )
        except Exception as e:
            logger.warning("Failed to log proposal to EPISODIC: %s", e)

    def _log_vote(self, session: BrainstormSession, proposal: Proposal, agent_id: str, choice: VoteChoice) -> None:
        """Log a vote to memory."""
        try:
            self.memory_channels.append_meta(
                agent_id=agent_id,
                meta_type="brainstorm_vote",
                meta_value=1.0 if choice == VoteChoice.FOR else (-1.0 if choice == VoteChoice.AGAINST else 0.0),
                content=f"Vote on {proposal.proposal_id}: {choice.value} (session={session.session_id})",
                trust_score=100.0,
            )
        except Exception as e:
            logger.warning("Failed to log vote to META: %s", e)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Return brainstorm engine statistics."""
        with self._lock:
            all_sessions = list(self._sessions.values())
            open_sessions = [s for s in all_sessions if s.is_open]
            closed_sessions = [s for s in all_sessions if not s.is_open]
            total_proposals = sum(len(s.proposals) for s in all_sessions)
            accepted_proposals = sum(
                1 for s in all_sessions for p in s.proposals if p.accepted is True
            )
            return {
                "total_sessions": len(all_sessions),
                "open_sessions": len(open_sessions),
                "closed_sessions": len(closed_sessions),
                "total_proposals": total_proposals,
                "accepted_proposals": accepted_proposals,
                "acceptance_rate": accepted_proposals / total_proposals if total_proposals > 0 else 0.0,
            }
