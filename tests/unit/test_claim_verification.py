"""Tests for the Claim Verification Pipeline."""

import pytest
import tempfile
import os

from nexus_os.governor.claim_verification import (
    ClaimVerificationPipeline,
    ClaimVerifier,
    Evidence,
    EvidenceType,
    ClaimStatus,
)


class TestClaimVerifier:
    """Test individual evidence verification strategies."""

    def setup_method(self):
        self.verifier = ClaimVerifier()

    def test_verify_test_output_passing(self):
        ev = Evidence(
            evidence_type=EvidenceType.TEST_OUTPUT,
            content="670 passed in 58.98s",
            source="pytest",
        )
        assert self.verifier.verify(ev, "all tests pass") is True
        assert ev.verified is True
        assert "670" in ev.verification_detail

    def test_verify_test_output_failing(self):
        ev = Evidence(
            evidence_type=EvidenceType.TEST_OUTPUT,
            content="668 passed, 2 failed in 60s",
            source="pytest",
        )
        assert self.verifier.verify(ev, "tests pass") is False
        assert ev.verified is False
        assert "FAILED" in ev.verification_detail

    def test_verify_file_exists_real(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            path = f.name
        try:
            ev = Evidence(
                evidence_type=EvidenceType.FILE_EXISTS,
                content=path,
                source="agent",
            )
            assert self.verifier.verify(ev, "file created") is True
            assert ev.verified is True
        finally:
            os.unlink(path)

    def test_verify_file_exists_missing(self):
        ev = Evidence(
            evidence_type=EvidenceType.FILE_EXISTS,
            content="/nonexistent/file.py",
            source="agent",
        )
        assert self.verifier.verify(ev, "file created") is False
        assert ev.verified is False

    def test_verify_file_diff_valid(self):
        ev = Evidence(
            evidence_type=EvidenceType.FILE_DIFF,
            content="diff --git a/foo.py b/foo.py\n@@ -1,3 +1,4 @@\n+new line\n old",
            source="git diff",
        )
        assert self.verifier.verify(ev, "code changed") is True
        assert ev.verified is True

    def test_verify_file_diff_empty(self):
        ev = Evidence(
            evidence_type=EvidenceType.FILE_DIFF,
            content="",
            source="git diff",
        )
        assert self.verifier.verify(ev, "code changed") is False

    def test_verify_command_output_clean(self):
        ev = Evidence(
            evidence_type=EvidenceType.COMMAND_OUTPUT,
            content="Build succeeded\nDone in 2.3s",
            source="build script",
        )
        assert self.verifier.verify(ev, "build works") is True

    def test_verify_command_output_with_error(self):
        ev = Evidence(
            evidence_type=EvidenceType.COMMAND_OUTPUT,
            content="Traceback (most recent call last):\n  File...",
            source="python",
        )
        assert self.verifier.verify(ev, "script runs") is False

    def test_verify_vap_hash_valid(self):
        ev = Evidence(
            evidence_type=EvidenceType.VAP_HASH,
            content="a" * 64,
            source="vap chain",
        )
        assert self.verifier.verify(ev, "audited") is True

    def test_verify_vap_hash_invalid(self):
        ev = Evidence(
            evidence_type=EvidenceType.VAP_HASH,
            content="not-a-hash",
            source="vap chain",
        )
        assert self.verifier.verify(ev, "audited") is False


class TestClaimVerificationPipeline:
    """Test the end-to-end pipeline."""

    def setup_method(self):
        self.pipeline = ClaimVerificationPipeline(min_evidence=1)

    def test_submit_and_verify_passing(self):
        claim = self.pipeline.submit_claim(
            claim_id="claim-001",
            agent_id="agent-x",
            description="tests pass",
            evidence_items=[{
                "type": "test_output",
                "content": "45 passed in 3.2s",
                "source": "pytest",
            }],
        )
        result = self.pipeline.verify_claim("claim-001")
        assert result.status == ClaimStatus.VERIFIED
        assert result.vap_hash is not None
        assert len(result.vap_hash) == 64

    def test_insufficient_evidence(self):
        pipeline = ClaimVerificationPipeline(min_evidence=2)
        pipeline.submit_claim(
            claim_id="claim-002",
            agent_id="agent-y",
            description="fixed bug",
            evidence_items=[{
                "type": "command_output",
                "content": "ok",
                "source": "shell",
            }],
        )
        result = pipeline.verify_claim("claim-002")
        assert result.status == ClaimStatus.INSUFFICIENT

    def test_disputed_claim(self):
        self.pipeline.submit_claim(
            claim_id="claim-003",
            agent_id="agent-z",
            description="no errors",
            evidence_items=[{
                "type": "command_output",
                "content": "fatal error: segmentation fault",
                "source": "runtime",
            }],
        )
        result = self.pipeline.verify_claim("claim-003")
        assert result.status == ClaimStatus.DISPUTED

    def test_list_claims_by_agent(self):
        self.pipeline.submit_claim("c1", "agent-a", "desc1")
        self.pipeline.submit_claim("c2", "agent-b", "desc2")
        self.pipeline.submit_claim("c3", "agent-a", "desc3")
        claims = self.pipeline.list_claims(agent_id="agent-a")
        assert len(claims) == 2

    def test_add_evidence_after_submission(self):
        self.pipeline.submit_claim("c4", "agent-d", "file created")
        ev = Evidence(
            evidence_type=EvidenceType.FILE_EXISTS,
            content="/tmp",
            source="agent",
        )
        assert self.pipeline.add_evidence("c4", ev) is True
        result = self.pipeline.verify_claim("c4")
        assert result.status == ClaimStatus.VERIFIED
