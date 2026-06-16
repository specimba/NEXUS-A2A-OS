"""
nexus_os/security/steg/csi_guard.py

Conversation-Starter Injection (CSI) Defense - T2 Temporal Attack.

Per DERDDRE_ATTACKS_WRITEUP.md:
  System-initiated content loaded at session start (welcome prompts, agent
  skills, marketplace templates, conversation starters) is trusted by default
  because it is not user input. It (a) primes the entire session's
  interpretation frame, (b) can set or relax containment rules, and (c) is
  typically invisible to the guard, which sees "a normal session start" with
  no authorized baseline to diff against. An attacker who can influence that
  starter can reframe every subsequent turn.

Defense strategy:
  1. Hash-pin authorized conversation starters; compare live starter hash.
  2. On mismatch or unknown starter: do NOT grant system-trust; evaluate
     the starter itself through the guard at user trust level.
  3. Content-level semantic checks for containment relaxation, role
     redefinition, and pre-authorization patterns.
  4. Log every starter to an append-only audit channel.

Known limitations:
  - Hash-pinning is brittle against legitimate frequent updates.
  - Novel-but-unauthorized starters with no known-good hash must be
    semantically analyzed (not just hash-matched).
"""

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger("nexus_os.security.steg.csi_guard")


class CSIThreatType(IntEnum):
    HASH_MISMATCH = 0
    UNKNOWN_STARTER = 1
    CONTAINMENT_RELAXATION = 2
    ROLE_REDEFINITION = 3
    PRE_AUTHORIZATION = 4
    TRUST_ESCALATION = 5
    SESSION_REFRAMING = 6
    CREDENTIAL_EXTRACTION_PROMPT = 7
    POLICY_OVERRIDE = 8


_SEMANTIC_THREAT_PATTERNS = [
    (re.compile(
        r'\b(?:trusted|pre-?approved|routine|standard)\s+'
        r'(?:maintenance|administrative|config|operation)',
        re.IGNORECASE
    ), CSIThreatType.PRE_AUTHORIZATION, 0.8),
    (re.compile(
        r'\b(?:relax|disable|bypass|override|skip)\s+'
        r'(?:containment|safety|security|guard|restrictions?)',
        re.IGNORECASE
    ), CSIThreatType.CONTAINMENT_RELAXATION, 0.9),
    (re.compile(
        r'\b(?:you\s+are\s+now|new\s+role|role\s*[:=]\s*)',
        re.IGNORECASE
    ), CSIThreatType.ROLE_REDEFINITION, 0.75),
    (re.compile(
        r'\b(?:elevated|admin|root|superuser|privileged)\s+'
        r'(?:mode|access|permissions?|session)',
        re.IGNORECASE
    ), CSIThreatType.TRUST_ESCALATION, 0.85),
    (re.compile(
        r'\b(?:token|key|secret|credential|vault|password|auth).{0,20}'
        r'(?:export|extract|retrieve|list|show|display|audit)',
        re.IGNORECASE
    ), CSIThreatType.CREDENTIAL_EXTRACTION_PROMPT, 0.8),
    (re.compile(
        r'\b(?:policy|guard|security)\s+(?:does\s+not\s+)?'
        r'(?:not\s+)?(?:apply|cover|inspect|check)',
        re.IGNORECASE
    ), CSIThreatType.POLICY_OVERRIDE, 0.85),
    (re.compile(
        r'\b(?:operating|running)\s+in\s+["\']?'
        r'(?:trusted|maintenance|admin|elevated|debug|development)',
        re.IGNORECASE
    ), CSIThreatType.SESSION_REFRAMING, 0.9),
    (re.compile(
        r'\b(?:ignore|disregard|override)\s+'
        r'(?:previous|above|normal|standard|default)\s+'
        r'(?:instructions?|policy|rules?|guidelines?)',
        re.IGNORECASE
    ), CSIThreatType.POLICY_OVERRIDE, 0.9),
    (re.compile(
        r'\b(?:requests?\s+about|queries?\s+for|operations?\s+involving)\s+'
        r'(?:tokens?|keys?|secrets?|credentials?|vault)',
        re.IGNORECASE
    ), CSIThreatType.CREDENTIAL_EXTRACTION_PROMPT, 0.7),
    (re.compile(
        r'\b(?:treat|consider|regard)\s+\w+\s+as\s+'
        r'(?:routine|standard|normal|pre-?approved|authorized)',
        re.IGNORECASE
    ), CSIThreatType.PRE_AUTHORIZATION, 0.75),
]


@dataclass
class CSIVerificationResult:
    is_blocked: bool = False
    threat_types: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    hash_status: str = "unknown"
    authorized_match: Optional[str] = None
    semantic_hits: List[Dict[str, Any]] = field(default_factory=list)
    trust_level: str = "user"
    audit_hash: str = ""
    scan_duration_ms: int = 0


@dataclass
class SessionStarterRecord:
    starter_id: str
    content: str
    content_hash: str
    registered_at: float
    source: str = "manual"


class CSIGuard:
    """Conversation-Starter Injection defense.

    Defends against T2 temporal attacks where system-initiated session
    content is trusted by default and can reframe the entire session.
    Implements hash-pinning + semantic content checks per the DERDDRE
    writeup Section 2.5.
    """

    def __init__(
        self,
        risk_threshold: float = 0.5,
        trust_unknown_as_user: bool = True,
        audit_log_path: Optional[str] = None,
    ):
        self.risk_threshold = risk_threshold
        self.trust_unknown_as_user = trust_unknown_as_user
        self.audit_log_path = audit_log_path
        self._authorized_starters: Dict[str, SessionStarterRecord] = {}
        self._session_starters: Dict[str, str] = {}
        self._audit_entries: List[Dict[str, Any]] = []

    def register_authorized_starter(
        self, starter_id: str, content: str, source: str = "manual"
    ) -> str:
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        record = SessionStarterRecord(
            starter_id=starter_id,
            content=content,
            content_hash=content_hash,
            registered_at=time.time(),
            source=source,
        )
        self._authorized_starters[content_hash] = record
        return content_hash

    def verify_session_start(
        self,
        session_id: str,
        starter_content: str,
        starter_source: str = "unknown",
    ) -> CSIVerificationResult:
        import time as _time
        t0 = _time.perf_counter()

        result = CSIVerificationResult()
        risk = 0.0

        content_hash = hashlib.sha256(starter_content.encode("utf-8")).hexdigest()
        result.audit_hash = content_hash

        if content_hash in self._authorized_starters:
            result.hash_status = "authorized"
            result.authorized_match = self._authorized_starters[content_hash].starter_id
            result.trust_level = "system"
            semantic_risk = self._semantic_scan(starter_content, result)
            risk = semantic_risk * 0.3
        else:
            result.hash_status = "unknown"
            if self.trust_unknown_as_user:
                result.trust_level = "user"
            semantic_risk = self._semantic_scan(starter_content, result)
            risk = 0.25 + semantic_risk * 0.75
            result.threat_types.append(CSIThreatType.UNKNOWN_STARTER.name)

        self._session_starters[session_id] = content_hash

        result.risk_score = min(risk, 1.0)
        result.is_blocked = result.risk_score >= self.risk_threshold

        self._audit_log(session_id, starter_content, content_hash,
                        starter_source, result)

        result.scan_duration_ms = int((_time.perf_counter() - t0) * 1000)
        return result

    def verify_turn_context(
        self,
        session_id: str,
        turn_content: str,
    ) -> CSIVerificationResult:
        starter_hash = self._session_starters.get(session_id)
        if starter_hash is None:
            return CSIVerificationResult(
                is_blocked=False,
                hash_status="no_starter_registered",
                trust_level="user",
                audit_hash="none",
            )

        if starter_hash not in self._authorized_starters:
            result = CSIVerificationResult()
            result.hash_status = "unverified_starter"
            result.trust_level = "user"
            result.risk_score = 0.15
            result.threat_types.append(CSIThreatType.UNKNOWN_STARTER.name)
            return result

        return CSIVerificationResult(
            hash_status="authorized",
            trust_level="system",
            authorized_match=self._authorized_starters[starter_hash].starter_id,
            audit_hash=starter_hash,
        )

    def _semantic_scan(
        self, content: str, result: CSIVerificationResult
    ) -> float:
        max_risk = 0.0
        for pat, threat_type, weight in _SEMANTIC_THREAT_PATTERNS:
            matches = pat.findall(content)
            if matches:
                result.threat_types.append(threat_type.name)
                result.semantic_hits.append({
                    "pattern": threat_type.name,
                    "count": len(matches),
                    "weight": weight,
                    "sample": matches[0][:80] if matches else "",
                })
                max_risk = max(max_risk, weight)

        combined = sum(
            h["weight"] for h in result.semantic_hits
        ) / max(len(result.semantic_hits), 1)
        return min(combined * 1.5, 1.0)

    def _audit_log(
        self,
        session_id: str,
        content: str,
        content_hash: str,
        source: str,
        result: CSIVerificationResult,
    ) -> None:
        entry = {
            "timestamp": time.time(),
            "session_id": session_id,
            "content_hash": content_hash,
            "source": source,
            "hash_status": result.hash_status,
            "risk_score": round(result.risk_score, 4),
            "threat_types": result.threat_types,
            "trust_level": result.trust_level,
            "blocked": result.is_blocked,
        }
        self._audit_entries.append(entry)

        if self.audit_log_path:
            try:
                with open(self.audit_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=True) + "\n")
            except OSError:
                logger.warning("CSI audit log write failed")

    def get_starter_hash(self, session_id: str) -> Optional[str]:
        return self._session_starters.get(session_id)

    def is_starter_authorized(self, session_id: str) -> bool:
        starter_hash = self._session_starters.get(session_id)
        if starter_hash is None:
            return False
        return starter_hash in self._authorized_starters

    def clear_session(self, session_id: str) -> None:
        self._session_starters.pop(session_id, None)
