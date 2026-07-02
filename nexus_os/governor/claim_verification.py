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
from typing import Callable, Dict, Any, List, Optional

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
        """Verify test output evidence: check for pass/fail indicators with exact failed output context."""
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
                # Capture exact failed summary context
                failing_lines = [line.strip() for line in content.splitlines() if "failed" in line.lower() or "error" in line.lower()][:3]
                evidence.verification_detail = f"Test failure detected: {passed_count} passed, {failed_count} FAILED. Failure context: {'; '.join(failing_lines)}"
                return False

        evidence.verified = False
        evidence.verification_detail = f"Unable to determine test outcome from output. First line: '{content.splitlines()[0] if content.splitlines() else 'empty'}'"
        return False

    def verify_file_exists(self, evidence: Evidence, claim_description: str) -> bool:
        """Verify that a referenced file actually exists on disk, validating non-emptiness and SHA-256 integrity."""
        try:
            import tempfile
            import hashlib
            cwd = Path.cwd().resolve()
            temp_dir = Path(tempfile.gettempdir()).resolve()
            input_path = Path(evidence.content.strip()).resolve()

            under_cwd = (input_path == cwd or cwd in input_path.parents)
            under_temp = (input_path == temp_dir or temp_dir in input_path.parents)

            if not (under_cwd or under_temp):
                evidence.verified = False
                evidence.verification_detail = "File checking restricted to workspace or temporary directory."
                return False

            if input_path.exists():
                if input_path.is_file():
                    content = input_path.read_bytes()
                    if len(content) == 0:
                        evidence.verified = False
                        evidence.verification_detail = "Disk-state failure: File exists but is empty (0 bytes)"
                        return False
                    file_hash = hashlib.sha256(content).hexdigest()
                    evidence.verified = True
                    evidence.verification_detail = f"File existence verified: {input_path.name} (SHA256: {file_hash[:16]}...)"
                    return True
                else:
                    # Directory existence is allowed
                    evidence.verified = True
                    evidence.verification_detail = f"Directory existence verified: {input_path.name}"
                    return True

            evidence.verified = False
            evidence.verification_detail = f"Disk-state failure: File NOT found: {input_path.name}"
            return False
        except Exception as e:
            evidence.verified = False
            evidence.verification_detail = f"Disk-state verification error: {e}"
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
        """Verify command output matches expected patterns, with context-aware error checking and exact failure logging."""
        content = evidence.content
        content_lower = content.lower()

        # Context-aware check for 'error'
        if "error" in content_lower:
            # Find all occurrences of the word "error"
            for match in re.finditer(r"\berror\b", content_lower):
                start = match.start()
                # Scan up to 10 characters before "error" for negation prefixes (e.g. "0 errors", "no error")
                preceding_text = content_lower[max(0, start - 10):start]
                if any(neg in preceding_text for neg in ["no ", "0 ", "zero ", "without ", "clean "]):
                     continue
                evidence.verified = False
                # Capture exact line containing the error
                start_line = content.splitlines()[content_lower[:start].count('\n')]
                evidence.verification_detail = f"Exact error output detected: '{start_line.strip()}'"
                return False

        # Check for other positive-indicator error keywords
        error_indicators = ["traceback", "fatal", "exception", "panic", "segmentation fault"]
        for indicator in error_indicators:
            if indicator in content_lower:
                evidence.verified = False
                # Find matching failure line
                matching_line = ""
                for line in content.splitlines():
                    if indicator in line.lower():
                        matching_line = line.strip()
                        break
                evidence.verification_detail = f"Error indicator '{indicator}' found in command output line: '{matching_line}'"
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

    def __init__(self, min_evidence: int = 1, require_all_pass: bool = False, require_cycle_token: bool = False):
        self.verifier = ClaimVerifier()
        self.min_evidence = min_evidence
        self.require_all_pass = require_all_pass
        self._claims: Dict[str, Claim] = {}
        self.active_cycle_tokens: Dict[str, float] = {}
        self.hard_stop_callback: Optional[Callable[[str, str], None]] = None
        self.require_cycle_token = require_cycle_token

    def validate_cycle_token(self, token: Optional[str]) -> bool:
        """Validate transient cycle opt-in token against active tokens and expiry."""
        if not self.require_cycle_token:
            return True
        if not token:
            return False
        expiry = self.active_cycle_tokens.get(token)
        if not expiry or time.time() > expiry:
            return False
        return True

    def submit_claim(
        self,
        claim_id: str,
        agent_id: str,
        description: str,
        evidence_items: Optional[List[Dict[str, Any]]] = None,
        cycle_token: Optional[str] = None,
    ) -> Claim:
        """Submit a new claim with optional evidence and cycle opt-in validation."""
        claim = Claim(
            claim_id=claim_id,
            agent_id=agent_id,
            description=description,
        )

        # Validate transient cycle opt-in token
        if not self.validate_cycle_token(cycle_token):
            claim.status = ClaimStatus.INSUFFICIENT
            claim.verdict_reason = "Missing or expired transient cycle opt-in token. Use governance.request_cycle_token to acquire one."

        if evidence_items and claim.status != ClaimStatus.INSUFFICIENT:
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
        """Run the full verification pipeline on a claim, checking transient tokens and hooks."""
        claim = self._claims.get(claim_id)
        if claim is None:
            raise ValueError(f"Claim not found: {claim_id}")

        # If already marked INSUFFICIENT due to cycle token failure, exit early and run hard stop
        if claim.status == ClaimStatus.INSUFFICIENT:
            if self.hard_stop_callback:
                try:
                    self.hard_stop_callback(claim.agent_id, claim.verdict_reason)
                except Exception as e:
                    logger.error("Error executing hard-stop callback: %s", e)
            return claim

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

        # Trigger Hard Stop circuit breaker if claim is disputed or insufficient
        if claim.status in {ClaimStatus.DISPUTED, ClaimStatus.INSUFFICIENT}:
            if self.hard_stop_callback:
                try:
                    self.hard_stop_callback(claim.agent_id, claim.verdict_reason)
                except Exception as e:
                    logger.error("Error executing hard-stop callback: %s", e)
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
        """Compute VAP audit hash for the claim verification result, binding all evidence data."""
        # Deterministically sort evidence items to ensure a stable, repeatable hash
        sorted_evidence = sorted(
            claim.evidence,
            key=lambda e: (e.timestamp, e.source, e.evidence_type.value)
        )
        evidence_payloads = []
        for e in sorted_evidence:
            content_hash = hashlib.sha256(e.content.encode("utf-8")).hexdigest()
            evidence_payloads.append({
                "type": e.evidence_type.value,
                "source": e.source,
                "content_sha256": content_hash,
                "verified": e.verified,
                "detail": e.verification_detail
            })
        payload = json.dumps({
            "claim_id": claim.claim_id,
            "agent_id": claim.agent_id,
            "description": claim.description,
            "status": claim.status.value,
            "evidence_count": len(claim.evidence),
            "evidence": evidence_payloads,
            "verified_at": claim.verified_at,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()
