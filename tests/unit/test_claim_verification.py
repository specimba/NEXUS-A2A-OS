"""Tests for the Claim Verification Pipeline."""

import pytest
import tempfile
import os
import time


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
        import tempfile
        self.pipeline.submit_claim("c4", "agent-d", "file created")
        ev = Evidence(
            evidence_type=EvidenceType.FILE_EXISTS,
            content=tempfile.gettempdir(),
            source="agent",
        )
        assert self.pipeline.add_evidence("c4", ev) is True
        result = self.pipeline.verify_claim("c4")
        assert result.status == ClaimStatus.VERIFIED

    def test_command_output_negation_errors(self):
        verifier = ClaimVerifier()
        
        # Legitimate success outputs containing 'error' in negative/clean contexts
        ev1 = Evidence(EvidenceType.COMMAND_OUTPUT, "0 errors, 0 warnings", "pytest")
        assert verifier.verify(ev1, "run") is True
        
        ev2 = Evidence(EvidenceType.COMMAND_OUTPUT, "no error found during parse", "compiler")
        assert verifier.verify(ev2, "run") is True

        ev3 = Evidence(EvidenceType.COMMAND_OUTPUT, "completed without error", "runner")
        assert verifier.verify(ev3, "run") is True

        ev4 = Evidence(EvidenceType.COMMAND_OUTPUT, "clean error state verified", "lint")
        assert verifier.verify(ev4, "run") is True

        # Real errors should still fail
        ev_fail1 = Evidence(EvidenceType.COMMAND_OUTPUT, "error: compilation failed", "compiler")
        assert verifier.verify(ev_fail1, "run") is False

        ev_fail2 = Evidence(EvidenceType.COMMAND_OUTPUT, "fatal error: null pointer", "jvm")
        assert verifier.verify(ev_fail2, "run") is False

    def test_file_exists_out_of_sandbox_blocked(self):
        verifier = ClaimVerifier()
        # Escaping path must be blocked
        bad_path = "C:\\Windows\\System32\\cmd.exe" if os.name == "nt" else "/etc/passwd"
        ev = Evidence(EvidenceType.FILE_EXISTS, bad_path, "agent")
        assert verifier.verify(ev, "read file") is False
        assert "restricted" in ev.verification_detail

    def test_cycle_token_opt_in_enforced(self):
        pipeline = ClaimVerificationPipeline(require_cycle_token=True)
        # Without token -> status should be INSUFFICIENT
        claim = pipeline.submit_claim(
            claim_id="token-claim-fail",
            agent_id="agent-x",
            description="some claim",
            evidence_items=[{"type": "command_output", "content": "success", "source": "test"}]
        )
        assert claim.status == ClaimStatus.INSUFFICIENT
        assert "Missing or expired transient cycle opt-in token" in claim.verdict_reason

        # With expired token -> status should be INSUFFICIENT
        pipeline.active_cycle_tokens["expired-token"] = time.time() - 10
        claim2 = pipeline.submit_claim(
            claim_id="token-claim-expired",
            agent_id="agent-x",
            description="some claim",
            evidence_items=[{"type": "command_output", "content": "success", "source": "test"}],
            cycle_token="expired-token"
        )
        assert claim2.status == ClaimStatus.INSUFFICIENT

        # With valid token -> status should be PENDING or successful
        pipeline.active_cycle_tokens["valid-token"] = time.time() + 60
        claim3 = pipeline.submit_claim(
            claim_id="token-claim-success",
            agent_id="agent-x",
            description="some claim",
            evidence_items=[{"type": "command_output", "content": "success", "source": "test"}],
            cycle_token="valid-token"
        )
        assert claim3.status == ClaimStatus.PENDING

    def test_disk_state_verification(self):
        verifier = ClaimVerifier()
        # Non-empty file should pass and have sha256 hash in details
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"integrity test content")
            path = f.name
        try:
            ev = Evidence(EvidenceType.FILE_EXISTS, path, "agent")
            assert verifier.verify(ev, "file check") is True
            assert ev.verified is True
            assert "SHA256:" in ev.verification_detail
        finally:
            os.unlink(path)

        # Empty file should fail disk-state verification
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path_empty = f.name
        try:
            ev_empty = Evidence(EvidenceType.FILE_EXISTS, path_empty, "agent")
            assert verifier.verify(ev_empty, "file check") is False
            assert ev_empty.verified is False
            assert "empty (0 bytes)" in ev_empty.verification_detail
        finally:
            os.unlink(path_empty)

    def test_exact_failed_output(self):
        verifier = ClaimVerifier()
        # Test output with failing lines
        content = "5 passed, 2 failed in 1.2s\n> test_fail.py:10: assert False\nE assert False is True"
        ev = Evidence(EvidenceType.TEST_OUTPUT, content, "pytest")
        assert verifier.verify(ev, "tests") is False
        assert "Failure context:" in ev.verification_detail
        assert "2 failed" in ev.verification_detail

        # Command output with traceback error
        content_err = "Traceback (most recent call last):\n  File \"app.py\", line 5, in <module>\n    raise ValueError('database offline')"
        ev_err = Evidence(EvidenceType.COMMAND_OUTPUT, content_err, "python")
        assert verifier.verify(ev_err, "run") is False
        assert "ValueError" in ev_err.verification_detail or "traceback" in ev_err.verification_detail.lower()

    def test_hard_stop_quarantines_agent(self):
        pipeline = ClaimVerificationPipeline(min_evidence=1)
        triggered_agent = None
        triggered_reason = None
        
        def mock_callback(agent_id: str, reason: str) -> None:
            nonlocal triggered_agent, triggered_reason
            triggered_agent = agent_id
            triggered_reason = reason
            
        pipeline.hard_stop_callback = mock_callback
        
        # Submit a claim that will fail verification
        pipeline.submit_claim(
            claim_id="fail-claim",
            agent_id="agent-adversarial",
            description="failed task",
            evidence_items=[{"type": "command_output", "content": "fatal error: exception occurred", "source": "runner"}]
        )
        pipeline.verify_claim("fail-claim")
        
        assert triggered_agent == "agent-adversarial"
        assert "No evidence items could be verified" in triggered_reason
