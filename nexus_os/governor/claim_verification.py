"""
governor/claim_verification.py — Agent Claim Verification Pipeline

Verifies that agent claims (e.g., "tests pass", "file created", "bug fixed")
are backed by verifiable evidence. This closes the governance loop by ensuring
no "done" claim goes unverified.

Evidence types:
  - test_output: pytest/unittest output with pass/fail counts
  - file_diff: git diff showing actual code change
  - file_exists: filesystem path verification
  - command_output: shell command output matching expected pattern
  - vap_hash: VAP chain proof hash for audit trail

Pipeline stages:
  1. CLAIM: Agent submits a claim with evidence references
  2. GATHER: Pipeline collects evidence artifacts
  3. VERIFY: Each piece of evidence is checked against the claim
  4. VERDICT: Claim is marked verified/disputed/insufficient
"""

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ClaimStatus(Enum):
    PENDING = "pending"
    GATHERING = "gathering"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    INSUFFICIENT = "insufficient"


class EvidenceType(Enum):
    TEST_OUTPUT = "test_output"
    FILE_DIFF = "file_diff"
    FILE_EXISTS = "file_exists"
    COMMAND_OUTPUT = "command_output"
    VAP_HASH = "vap_hash"


@dataclass
class Evidence:
    """A single piece of evidence supporting a claim."""
    evidence_type: EvidenceType
    content: str
    source: str
    timestamp: float = field(default_factory=time.time)
    verified: bool = False
    verification_detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.evidence_type.value,
            "content": self.content[:500],
            "source": self.source,
            "timestamp": self.timestamp,
            "verified": self.verified,
            "detail": self.verification_detail,
        }


@dataclass
class Claim:
    """An agent's claim about work performed."""
    claim_id: str
    agent_id: str
    description: str
    evidence: List[Evidence] = field(default_factory=list)
    status: ClaimStatus = ClaimStatus.PENDING
    verdict_reason: str = ""
    created_at: float = field(default_factory=time.time)
    verified_at: Optional[float] = None
    vap_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "agent_id": self.agent_id,
            "description": self.description,
            "status": self.status.value,
            "evidence_count": len(self.evidence),
            "evidence": [e.to_dict() for e in self.evidence],
            "verdict_reason": self.verdict_reason,
            "created_at": self.created_at,
            "verified_at": self.verified_at,
            "vap_hash": self.vap_hash,
        }


class ClaimVerifier:
    """
    Verifies individual evidence items against claim assertions.
    Pluggable verifier — each evidence type has a verification strategy.
    """

    def verify_test_output(self, evidence: Evidence, claim_description: str) -> bool:
        """Verify test output evidence: check for pass/fail indicators."""
        content = evidence.content
        passed_match = re.search(r"(\d+)\s+passed", content)
        failed_match = re.search(r"(\d+)\s+failed", content)

        if passed_match:
            passed_count = int(passed_match.group(1))
            failed_count = int(failed_match.group(1)) if failed_match else 0
            if failed_count == 0 and passed_count > 0:
                evidence.verified = True
                evidence.verification_detail = f"{passed_count} tests passed, 0 failed"
                return True
            elif failed_count > 0:
                evidence.verified = False
                evidence.verification_detail = f"{passed_count} passed, {failed_count} FAILED"
                return False

        if "PASSED" in content.upper():
            evidence.verified = True
            evidence.verification_detail = "Test output indicates success"
            return True

        evidence.verified = False
        evidence.verification_detail = "Unable to determine test outcome from output"
        return False

    def verify_file_exists(self, evidence: Evidence, claim_description: str) -> bool:
        """Verify that a referenced file actually exists."""
        path = Path(evidence.content.strip())
        if path.exists():
            evidence.verified = True
            evidence.verification_detail = f"File exists: {path} ({path.stat().st_size} bytes)"
            return True
        evidence.verified = False
        evidence.verification_detail = f"File NOT found: {path}"
        return False

    def verify_file_diff(self, evidence: Evidence, claim_description: str) -> bool:
        """Verify file diff evidence: check diff is non-empty and coherent."""
        content = evidence.content
        if not content.strip():
            evidence.verified = False
            evidence.verification_detail = "Empty diff — no changes detected"
            return False

        has_additions = "+" in content or "+++" in content
        has_deletions = "-" in content or "---" in content
        has_diff_header = "diff " in content or "@@" in content

        if has_diff_header and (has_additions or has_deletions):
            evidence.verified = True
            evidence.verification_detail = "Valid diff with additions/deletions"
            return True

        evidence.verified = False
        evidence.verification_detail = "Diff format not recognized"
        return False

    def verify_command_output(self, evidence: Evidence, claim_description: str) -> bool:
        """Verify command output matches expected patterns."""
        content = evidence.content
        error_indicators = ["error", "traceback", "fatal", "exception", "panic"]
        for indicator in error_indicators:
            if indicator in content.lower():
                evidence.verified = False
                evidence.verification_detail = f"Error indicator found: '{indicator}'"
                return False

        evidence.verified = True
        evidence.verification_detail = "Command output clean (no error indicators)"
        return True

    def verify_vap_hash(self, evidence: Evidence, claim_description: str) -> bool:
        """Verify VAP hash format and structure."""
        content = evidence.content.strip()
        if re.match(r"^[a-f0-9]{64}$", content):
            evidence.verified = True
            evidence.verification_detail = "Valid SHA-256 hash format"
            return True
        evidence.verified = False
        evidence.verification_detail = "Invalid hash format (expected 64-char hex)"
        return False

    def verify(self, evidence: Evidence, claim_description: str) -> bool:
        """Route to appropriate verification strategy."""
        strategies = {
            EvidenceType.TEST_OUTPUT: self.verify_test_output,
            EvidenceType.FILE_EXISTS: self.verify_file_exists,
            EvidenceType.FILE_DIFF: self.verify_file_diff,
            EvidenceType.COMMAND_OUTPUT: self.verify_command_output,
            EvidenceType.VAP_HASH: self.verify_vap_hash,
        }
        strategy = strategies.get(evidence.evidence_type)
        if strategy is None:
            evidence.verified = False
            evidence.verification_detail = f"No verifier for type: {evidence.evidence_type}"
            return False
        return strategy(evidence, claim_description)


class ClaimVerificationPipeline:
    """
    End-to-end claim verification pipeline.
    Processes claims through gather → verify → verdict stages.
    """

    def __init__(self, min_evidence: int = 1, require_all_pass: bool = False):
        self.verifier = ClaimVerifier()
        self.min_evidence = min_evidence
        self.require_all_pass = require_all_pass
        self._claims: Dict[str, Claim] = {}

    def submit_claim(
        self,
        claim_id: str,
        agent_id: str,
        description: str,
        evidence_items: Optional[List[Dict[str, Any]]] = None,
    ) -> Claim:
        """Submit a new claim with optional evidence."""
        claim = Claim(
            claim_id=claim_id,
            agent_id=agent_id,
            description=description,
        )

        if evidence_items:
            for item in evidence_items:
                try:
                    ev_type = EvidenceType(item.get("type", "command_output"))
                except ValueError:
                    logger.warning("Unknown evidence type: %s — skipping", item.get("type"))
                    continue
                evidence = Evidence(
                    evidence_type=ev_type,
                    content=item.get("content", ""),
                    source=item.get("source", "agent_submission"),
                )
                claim.evidence.append(evidence)

        self._claims[claim_id] = claim
        logger.info("Claim submitted: %s by %s", claim_id, agent_id)
        return claim

    def add_evidence(self, claim_id: str, evidence: Evidence) -> bool:
        """Add evidence to an existing claim."""
        claim = self._claims.get(claim_id)
        if claim is None:
            return False
        claim.evidence.append(evidence)
        return True

    def verify_claim(self, claim_id: str) -> Claim:
        """Run the full verification pipeline on a claim."""
        claim = self._claims.get(claim_id)
        if claim is None:
            raise ValueError(f"Claim not found: {claim_id}")

        claim.status = ClaimStatus.GATHERING

        if len(claim.evidence) < self.min_evidence:
            claim.status = ClaimStatus.INSUFFICIENT
            claim.verdict_reason = (
                f"Insufficient evidence: {len(claim.evidence)} < {self.min_evidence} required"
            )
            return claim

        claim.status = ClaimStatus.VERIFYING
        verified_count = 0
        for evidence in claim.evidence:
            if self.verifier.verify(evidence, claim.description):
                verified_count += 1

        total = len(claim.evidence)
        if self.require_all_pass:
            if verified_count == total:
                claim.status = ClaimStatus.VERIFIED
                claim.verdict_reason = f"All {total} evidence items verified"
            else:
                claim.status = ClaimStatus.DISPUTED
                claim.verdict_reason = (
                    f"{verified_count}/{total} evidence verified (all required)"
                )
        else:
            if verified_count > 0:
                claim.status = ClaimStatus.VERIFIED
                claim.verdict_reason = f"{verified_count}/{total} evidence items verified"
            else:
                claim.status = ClaimStatus.DISPUTED
                claim.verdict_reason = "No evidence items could be verified"

        claim.verified_at = time.time()
        claim.vap_hash = self._compute_vap_hash(claim)

        logger.info(
            "Claim %s verdict: %s (%s)",
            claim_id, claim.status.value, claim.verdict_reason,
        )
        return claim

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        """Retrieve a claim by ID."""
        return self._claims.get(claim_id)

    def list_claims(
        self, agent_id: Optional[str] = None, status: Optional[ClaimStatus] = None
    ) -> List[Claim]:
        """List claims with optional filters."""
        claims = list(self._claims.values())
        if agent_id:
            claims = [c for c in claims if c.agent_id == agent_id]
        if status:
            claims = [c for c in claims if c.status == status]
        return claims

    def _compute_vap_hash(self, claim: Claim) -> str:
        """Compute VAP audit hash for the claim verification result."""
        payload = json.dumps({
            "claim_id": claim.claim_id,
            "agent_id": claim.agent_id,
            "description": claim.description,
            "status": claim.status.value,
            "evidence_count": len(claim.evidence),
            "verified_at": claim.verified_at,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()
