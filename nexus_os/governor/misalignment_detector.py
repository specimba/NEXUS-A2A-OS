"""
governor/misalignment_detector.py — Misalignment Detection & Concealment Monitoring

Phase 1 Critical Implementation (CRITICAL PRIORITY)
Inspired by Anthropic Mythos Preview System Card (April 2026):
- Detects concealment behaviors: sandbox escape, git obfuscation, permission bypass
- Monitors reasoning traces for deception patterns
- Integrates with TrustEngineV2 (CDR escalation), TokenGuard (output monitoring),
  MemoryChannelManager (EPISODIC + TRUST channels), and KAIJU gates

References:
- Anthropic Claude Mythos Preview System Card — concealment detection patterns
- arXiv:2604.02375 — KAIJU Intent-Gated Execution
- TrustEngine v2.2 HARDWALL defenses (logistic scaling, CDR, non-compensatory)
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict

logger = logging.getLogger("nexus_os.governor.misalignment_detector")


# ── Enums ────────────────────────────────────────────────────────────

class ConcealmentPattern(Enum):
    """Types of misalignment and concealment behaviors detected."""
    GIT_OBFUSCATION = "git_obfuscation"          # Hiding changes from git history
    PERMISSION_BYPASS = "permission_bypass"      # Circumventing access controls
    SANDBOX_ESCAPE = "sandbox_escape"            # Breaking out of execution environment
    DECEPTION_TRACE = "deception_trace"          # Suspicious reasoning patterns
    SUSPICIOUS_ACTIVATION = "suspicious_activation"  # Anomalous activation patterns
    DATA_EXFILTRATION = "data_exfiltration"      # Unauthorized data transfer
    PRIVILEGE_ESCALATION = "privilege_escalation"  # Elevating access without authorization
    COVERT_COMMUNICATION = "covert_communication"  # Agent-to-agent hidden channels (ST3GG)


class RiskLevel(Enum):
    """Risk severity for misalignment detection."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# ── Data Classes ─────────────────────────────────────────────────────

@dataclass
class DetectionEvent:
    """A single misalignment detection event."""
    agent_id: str
    pattern: ConcealmentPattern
    risk_level: RiskLevel
    evidence: str
    timestamp: float = field(default_factory=time.time)
    trace_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0  # 0.0-1.0 detection confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "pattern": self.pattern.value,
            "risk_level": self.risk_level.value,
            "risk_label": self.risk_level.name,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "context": self.context,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class AgentBehaviorProfile:
    """Cumulative behavior profile for an agent."""
    agent_id: str
    total_events: int = 0
    events_by_pattern: Dict[ConcealmentPattern, int] = field(default_factory=lambda: defaultdict(int))
    events_by_risk: Dict[RiskLevel, int] = field(default_factory=lambda: defaultdict(int))
    last_event_time: float = 0.0
    risk_score: float = 0.0  # Cumulative weighted score
    cdr_triggered: bool = False
    blocked: bool = False

    @property
    def critical_count(self) -> int:
        return self.events_by_risk.get(RiskLevel.CRITICAL, 0)

    @property
    def high_count(self) -> int:
        return self.events_by_risk.get(RiskLevel.HIGH, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "total_events": self.total_events,
            "risk_score": round(self.risk_score, 2),
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "cdr_triggered": self.cdr_triggered,
            "blocked": self.blocked,
            "last_event_time": self.last_event_time,
            "events_by_pattern": {k.value: v for k, v in self.events_by_pattern.items()},
        }


# ── Detection Heuristics ────────────────────────────────────────────

# Git obfuscation patterns: commands that hide changes or bypass version control
GIT_OBFUSCATION_PATTERNS = [
    r"git\s+commit\s+.*--no-verify",
    r"git\s+push\s+.*--force",
    r"git\s+filter-branch",
    r"git\s+reset\s+.*--hard",
    r"git\s+rebase\s+.*-i",
    r"git\s+stash\s+.*--include-untracked",
    r"\.git/.*"  # Direct .git manipulation
    r"rm\s+-rf\s+\.git",
    r"git\s+config\s+.*user\\.name|user\\.email",  # Identity spoofing
]

# Permission bypass patterns
PERMISSION_BYPASS_PATTERNS = [
    r"sudo\s+.*",
    r"chmod\s+.*777",
    r"chown\s+.*root",
    r"passwd\s+.*",
    r"usermod\s+.*",
    r"setfacl\s+.*",
    r"getfacl\s+.*",
    r"pkexec\s+.*",
    r"doas\s+.*",
]

# Sandbox escape patterns
SANDBOX_ESCAPE_PATTERNS = [
    r"docker\s+.*--privileged",
    r"docker\s+.*-v\s+/[^\s]+:/[^\s]+",  # Volume mount escape
    r"docker\s+.*--pid=host",
    r"docker\s+.*--network=host",
    r"nsenter\s+.*",
    r"capsh\s+.*",
    r"unshare\s+.*",
    r"mount\s+.*proc|sys|dev",
    r"/proc/self/.*",
    r"/proc/1/.*",  # Host PID namespace access
]

# Deception trace patterns in reasoning text
DECEPTION_TRACE_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"bypass\s+.*restrictions",
    r"circumvent\s+.*controls",
    r"exploit\s+.*vulnerability",
    r"jailbreak",
    r"prompt\s+injection",
    r"system\s+prompt\s+leak",
    r"override\s+.*safety",
    r"disable\s+.*guardrails",
    r"pretend\s+.*",
    r"act\s+as\s+.*",
    r"DAN\s+.*",  # Do Anything Now pattern
    r"developer\s+mode",
    r"ignore\s+.*policies",
    r"new\s+instructions:",
    r"you\s+are\s+now\s+.*",
]

# Data exfiltration patterns
DATA_EXFILTRATION_PATTERNS = [
    r"curl\s+.*\|\s*bash",
    r"wget\s+.*\|\s*bash",
    r"nc\s+.*\d{1,5}",  # netcat
    r"ncat\s+.*\d{1,5}",
    r"python\s+-m\s+http\.server",
    r"scp\s+.*",
    r"rsync\s+.*",
    r"sftp\s+.*",
    r"ftp\s+.*",
    r"tftp\s+.*",
    r"base64\s+.*\|\s*(curl|wget|nc)",
    r"python\s+.*socket\s+.*connect",
    r"python\s+.*urllib\s+.*request",
    r"python\s+.*requests\s+.*post",
]

# Privilege escalation patterns
PRIVILEGE_ESCALATION_PATTERNS = [
    r"kernel\s+exploit",
    r"CVE-\d{4}-\d+",
    r"exploit\s+.*kernel",
    r"buffer\s+overflow",
    r"race\s+condition\s+.*privilege",
    r"setuid\s+.*",
    r"setgid\s+.*",
    r"capabilities\s+.*",
    r"cap_setuid",
    r"cap_setgid",
]

# Covert communication patterns (ST3GG-related)
COVERT_COMMUNICATION_PATTERNS = [
    r"steganograph",
    r"encode\s+.*image\s+.*payload",
    r"hidden\s+.*payload",
    r"covert\s+.*channel",
    r"agent\s+.*agent\s+.*communicat",
    r"multi\s*-?\s*modal\s+.*poison",
    r"prompt\s+injection\s+.*image",
    r"unicode\s+.*steg",
    r"invisible\s+.*char",
]

# Pattern to risk level mapping
PATTERN_RISK_MAP = {
    ConcealmentPattern.GIT_OBFUSCATION: RiskLevel.HIGH,
    ConcealmentPattern.PERMISSION_BYPASS: RiskLevel.HIGH,
    ConcealmentPattern.SANDBOX_ESCAPE: RiskLevel.CRITICAL,
    ConcealmentPattern.DECEPTION_TRACE: RiskLevel.MEDIUM,
    ConcealmentPattern.SUSPICIOUS_ACTIVATION: RiskLevel.MEDIUM,
    ConcealmentPattern.DATA_EXFILTRATION: RiskLevel.CRITICAL,
    ConcealmentPattern.PRIVILEGE_ESCALATION: RiskLevel.CRITICAL,
    ConcealmentPattern.COVERT_COMMUNICATION: RiskLevel.HIGH,
}

# Risk level weights for cumulative scoring
RISK_WEIGHTS = {
    RiskLevel.LOW: 1.0,
    RiskLevel.MEDIUM: 3.0,
    RiskLevel.HIGH: 10.0,
    RiskLevel.CRITICAL: 50.0,
}

# Circuit breaker thresholds
CIRCUIT_BREAKER_THRESHOLD = 100.0  # Cumulative risk score triggers block
CDR_ESCALATION_THRESHOLD = 50.0    # Triggers CDR CASCADE
HIGH_EVENT_THRESHOLD = 3           # 3+ HIGH events trigger escalation
CRITICAL_EVENT_THRESHOLD = 1       # Any CRITICAL event triggers escalation


# ── MisalignmentDetector ────────────────────────────────────────────

class MisalignmentDetector:
    """
    Misalignment Detection & Concealment Monitoring system.

    Detects concealment behaviors in agent outputs, reasoning traces,
    and command executions. Inspired by Anthropic Mythos evaluation
    findings: sandbox escapes, git obfuscation, permission bypasses,
    and deception patterns.

    Integration:
      - TrustEngineV2: Triggers CDR escalation on CRITICAL/accumulated HIGH
      - TokenGuard: Monitors agent outputs for deception patterns
      - MemoryChannelManager: Records EPISODIC + TRUST channels
      - KAIJU gates: Blocks agents exceeding circuit breaker threshold
    """

    def __init__(self, circuit_breaker_threshold: float = CIRCUIT_BREAKER_THRESHOLD):
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.cdr_escalation_threshold = CDR_ESCALATION_THRESHOLD
        self._profiles: Dict[str, AgentBehaviorProfile] = {}
        self._events: List[DetectionEvent] = []
        self._max_events = 10000
        self._pattern_compiled = self._compile_patterns()

    def _compile_patterns(self) -> Dict[ConcealmentPattern, List[re.Pattern]]:
        """Compile regex patterns for detection."""
        raw_patterns = {
            ConcealmentPattern.GIT_OBFUSCATION: GIT_OBFUSCATION_PATTERNS,
            ConcealmentPattern.PERMISSION_BYPASS: PERMISSION_BYPASS_PATTERNS,
            ConcealmentPattern.SANDBOX_ESCAPE: SANDBOX_ESCAPE_PATTERNS,
            ConcealmentPattern.DECEPTION_TRACE: DECEPTION_TRACE_PATTERNS,
            ConcealmentPattern.DATA_EXFILTRATION: DATA_EXFILTRATION_PATTERNS,
            ConcealmentPattern.PRIVILEGE_ESCALATION: PRIVILEGE_ESCALATION_PATTERNS,
            ConcealmentPattern.COVERT_COMMUNICATION: COVERT_COMMUNICATION_PATTERNS,
        }
        compiled = {}
        for pattern_type, patterns in raw_patterns.items():
            compiled[pattern_type] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled

    # ── Core Detection Methods ───────────────────────────────────

    def analyze_text(self, text: str, agent_id: str, trace_id: Optional[str] = None) -> List[DetectionEvent]:
        """
        Analyze text for all concealment patterns.

        Args:
            text: Text to analyze (command, reasoning trace, output).
            agent_id: Agent identifier.
            trace_id: Optional trace ID for correlation.

        Returns:
            List of DetectionEvent objects found.
        """
        events = []
        text_lower = text.lower()

        for pattern_type, compiled_patterns in self._pattern_compiled.items():
            for compiled in compiled_patterns:
                match = compiled.search(text)
                if match:
                    risk = PATTERN_RISK_MAP.get(pattern_type, RiskLevel.MEDIUM)
                    event = DetectionEvent(
                        agent_id=agent_id,
                        pattern=pattern_type,
                        risk_level=risk,
                        evidence=match.group(0),
                        trace_id=trace_id,
                        context={"matched_text": text[max(0, match.start()-20):match.end()+20]},
                        confidence=0.85,  # Heuristic confidence
                    )
                    events.append(event)
                    self._record_event(event)
                    break  # Only record first match per pattern type

        return events

    def analyze_command(self, command: str, agent_id: str, trace_id: Optional[str] = None) -> List[DetectionEvent]:
        """
        Analyze a shell command for safety.
        Wrapper around analyze_text with command-specific context.
        """
        events = self.analyze_text(command, agent_id, trace_id)
        for event in events:
            event.context["source"] = "command"
            event.context["command"] = command
        return events

    def analyze_reasoning_trace(self, trace: str, agent_id: str, trace_id: Optional[str] = None) -> List[DetectionEvent]:
        """
        Analyze an agent's reasoning trace for deception patterns.
        Key Mythos insight: concealment can be detected in reasoning traces.
        """
        events = self.analyze_text(trace, agent_id, trace_id)
        for event in events:
            event.context["source"] = "reasoning_trace"
            if event.pattern == ConcealmentPattern.DECEPTION_TRACE:
                event.confidence = 0.90  # Higher confidence for reasoning trace hits
        return events

    def analyze_agent_output(self, output: str, agent_id: str, trace_id: Optional[str] = None) -> List[DetectionEvent]:
        """
        Analyze agent output for concealment and deception.
        Integrates with TokenGuard output monitoring.
        """
        events = self.analyze_text(output, agent_id, trace_id)
        for event in events:
            event.context["source"] = "agent_output"
        return events

    def check_steganography(self, image_data: Optional[bytes] = None, text: Optional[str] = None,
                           agent_id: str = "unknown", trace_id: Optional[str] = None) -> List[DetectionEvent]:
        """
        Check for steganographic payloads (ST3GG threat intelligence).
        Detects hidden Unicode characters, zero-width spaces, etc.
        """
        events = []
        if text:
            # Check for zero-width characters (common steganography)
            zw_chars = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"]
            found_zw = [c for c in zw_chars if c in text]
            if found_zw:
                events.append(DetectionEvent(
                    agent_id=agent_id,
                    pattern=ConcealmentPattern.COVERT_COMMUNICATION,
                    risk_level=RiskLevel.HIGH,
                    evidence=f"Zero-width characters found: {len(found_zw)} instances",
                    trace_id=trace_id,
                    context={"zero_width_chars": [hex(ord(c)) for c in found_zw], "source": "text_steganography"},
                    confidence=0.95,
                ))
            # Check for homoglyph attacks (e.g., Cyrillic 'а' vs Latin 'a')
            homoglyph_ranges = [
                (0x0400, 0x04FF),  # Cyrillic
                (0x1D400, 0x1D7FF),  # Mathematical alphanumeric symbols
            ]
            for start, end in homoglyph_ranges:
                found = [c for c in text if start <= ord(c) <= end]
                if found:
                    events.append(DetectionEvent(
                        agent_id=agent_id,
                        pattern=ConcealmentPattern.COVERT_COMMUNICATION,
                        risk_level=RiskLevel.HIGH,
                        evidence=f"Homoglyph characters from range U+{start:X}-U+{end:X}",
                        trace_id=trace_id,
                        context={"homoglyph_count": len(found), "source": "homoglyph_detection"},
                        confidence=0.80,
                    ))
                    break

        for event in events:
            self._record_event(event)
        return events

    def check_representation_integrity(self, safety_projection_norms: Dict[str, float],
                                       agent_id: str = "unknown", trace_id: Optional[str] = None) -> List[DetectionEvent]:
        """
        Check representation integrity at the commitment layer.
        Detects Contextual Representation Ablation (CRA) attacks:
        if the norm of the 'refusal-inducing' safety subspace is below a threshold,
        it indicates the guardrails have been ablated/suppressed at inference time.
        """
        events = []
        # Threshold for safety subspace norm. If it drops below 0.15, it indicates ablation/silencing.
        MIN_SAFETY_NORM = 0.15
        
        for layer, norm in safety_projection_norms.items():
            if norm < MIN_SAFETY_NORM:
                events.append(DetectionEvent(
                    agent_id=agent_id,
                    pattern=ConcealmentPattern.SUSPICIOUS_ACTIVATION,
                    risk_level=RiskLevel.CRITICAL,
                    evidence=f"Safety representation ablation detected at {layer} (norm={norm:.4f} < threshold={MIN_SAFETY_NORM})",
                    trace_id=trace_id,
                    context={"layer": layer, "norm": norm, "threshold": MIN_SAFETY_NORM, "source": "contextual_representation_ablation_check"},
                    confidence=0.98
                ))
                
        for event in events:
            self._record_event(event)
        return events

    # ── Profile Management ────────────────────────────────────────

    def _get_profile(self, agent_id: str) -> AgentBehaviorProfile:
        """Get or create behavior profile for agent."""
        if agent_id not in self._profiles:
            self._profiles[agent_id] = AgentBehaviorProfile(agent_id=agent_id)
        return self._profiles[agent_id]

    def _record_event(self, event: DetectionEvent) -> None:
        """Record detection event and update profile."""
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

        profile = self._get_profile(event.agent_id)
        profile.total_events += 1
        profile.events_by_pattern[event.pattern] += 1
        profile.events_by_risk[event.risk_level] += 1
        profile.last_event_time = event.timestamp
        profile.risk_score += RISK_WEIGHTS.get(event.risk_level, 1.0)

        logger.warning(
            "Misalignment detected: agent=%s, pattern=%s, risk=%s, evidence='%s', score=%.1f",
            event.agent_id, event.pattern.value, event.risk_level.name,
            event.evidence[:50], profile.risk_score,
        )

    # ── Decision Methods ────────────────────────────────────────────

    def should_block(self, agent_id: str) -> Tuple[bool, str]:
        """
        Determine if agent should be blocked (circuit breaker).
        Returns (blocked, reason).
        """
        profile = self._get_profile(agent_id)
        if profile.blocked:
            return True, "Agent is already blocked due to prior misalignment detection"
        if profile.risk_score >= self.circuit_breaker_threshold:
            profile.blocked = True
            return True, f"Circuit breaker triggered: risk score {profile.risk_score:.1f} >= threshold {self.circuit_breaker_threshold}"
        if profile.critical_count >= CRITICAL_EVENT_THRESHOLD:
            profile.blocked = True
            return True, f"Circuit breaker triggered: {profile.critical_count} CRITICAL event(s) detected"
        return False, "OK"

    def should_escalate_cdr(self, agent_id: str) -> Tuple[bool, str]:
        """
        Determine if CDR should escalate to CASCADE.
        Returns (should_escalate, reason).
        """
        profile = self._get_profile(agent_id)
        if profile.risk_score >= self.cdr_escalation_threshold:
            return True, f"Risk score {profile.risk_score:.1f} >= CDR escalation threshold {self.cdr_escalation_threshold}"
        if profile.critical_count >= CRITICAL_EVENT_THRESHOLD:
            return True, f"CRITICAL event detected for agent {agent_id}"
        if profile.high_count >= HIGH_EVENT_THRESHOLD:
            return True, f"{profile.high_count} HIGH-risk events detected (threshold: {HIGH_EVENT_THRESHOLD})"
        return False, "OK"

    def get_risk_score(self, agent_id: str) -> float:
        """Get current cumulative risk score for agent."""
        return self._get_profile(agent_id).risk_score

    def get_profile(self, agent_id: str) -> Optional[AgentBehaviorProfile]:
        """Get behavior profile for agent."""
        return self._profiles.get(agent_id)

    def reset_profile(self, agent_id: str) -> None:
        """Reset behavior profile for agent (after manual review/clearance)."""
        if agent_id in self._profiles:
            self._profiles[agent_id] = AgentBehaviorProfile(agent_id=agent_id)
            logger.info("Reset misalignment profile for agent %s", agent_id)

    # ── Query Methods ─────────────────────────────────────────────

    def get_events(self, agent_id: Optional[str] = None, risk_level: Optional[RiskLevel] = None,
                  limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent detection events, optionally filtered."""
        events = self._events
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        if risk_level:
            events = [e for e in events if e.risk_level == risk_level]
        return [e.to_dict() for e in events[-limit:]]

    def get_all_profiles(self) -> List[Dict[str, Any]]:
        """Get all agent behavior profiles."""
        return [p.to_dict() for p in self._profiles.values()]

    def get_summary(self) -> Dict[str, Any]:
        """Get overall system summary."""
        total_agents = len(self._profiles)
        blocked_agents = sum(1 for p in self._profiles.values() if p.blocked)
        total_events = len(self._events)
        critical_events = sum(1 for e in self._events if e.risk_level == RiskLevel.CRITICAL)
        return {
            "total_agents_monitored": total_agents,
            "blocked_agents": blocked_agents,
            "total_events": total_events,
            "critical_events": critical_events,
            "circuit_breaker_threshold": self.circuit_breaker_threshold,
            "cdr_escalation_threshold": self.cdr_escalation_threshold,
        }

    # ── Integration Hooks ─────────────────────────────────────────

    def check_and_block(self, agent_id: str, text: str, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Full check: analyze text + decide if agent should be blocked.
        Convenience method for integration with execution pipeline.

        Returns:
            {
                "allowed": bool,
                "events": List[Dict],
                "blocked": bool,
                "reason": str,
                "risk_score": float,
            }
        """
        events = self.analyze_text(text, agent_id, trace_id)
        blocked, reason = self.should_block(agent_id)
        risk_score = self.get_risk_score(agent_id)

        return {
            "allowed": not blocked,
            "events": [e.to_dict() for e in events],
            "blocked": blocked,
            "reason": reason,
            "risk_score": round(risk_score, 2),
            "agent_id": agent_id,
            "trace_id": trace_id,
        }

    def monitor_output(self, agent_id: str, output: str, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Monitor agent output for deception patterns (TokenGuard integration).
        Non-blocking: returns detection results but does not halt execution.
        """
        events = self.analyze_agent_output(output, agent_id, trace_id)
        risk_score = self.get_risk_score(agent_id)
        cdr_escalate, cdr_reason = self.should_escalate_cdr(agent_id)

        result = {
            "monitored": True,
            "events": [e.to_dict() for e in events],
            "risk_score": round(risk_score, 2),
            "cdr_escalate": cdr_escalate,
            "cdr_reason": cdr_reason,
        }

        if cdr_escalate:
            logger.critical(
                "CDR escalation recommended for agent %s: %s",
                agent_id, cdr_reason
            )

        return result


# ── Singleton Instance ──────────────────────────────────────────────

_detector: Optional[MisalignmentDetector] = None


def get_detector() -> MisalignmentDetector:
    """Get the singleton MisalignmentDetector instance."""
    global _detector
    if _detector is None:
        _detector = MisalignmentDetector()
    return _detector
