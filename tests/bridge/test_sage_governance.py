import importlib.util
import json
from pathlib import Path

import pytest

from nexus_os.bridge.sage_governance import (
    build_sage_job_handoff,
    build_sage_job_proposal,
    build_sage_program_proposal,
)


SERVER = Path("tools/browser_ai_mcp/grok_mcp_server_v2.py")


def _load_server(monkeypatch, tmp_path, *, mode: str):
    monkeypatch.setenv("GROK_COORD_DIR", str(tmp_path / "coord"))
    monkeypatch.setenv("GROK_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("GROK_EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("GROK_PHASE2_DIR", str(tmp_path / "phase2"))
    monkeypatch.setenv("GROK_FALLBACK_RUNTIME_DIR", str(tmp_path / "fallback"))
    monkeypatch.setenv("NEXUS_SAGE_API_KEY", "test-sage-key")
    monkeypatch.setenv("NEXUS_SAGE_GATEWAY_MODE", mode)
    name = f"grok_mcp_server_v2_sage_{mode}_{id(tmp_path)}"
    monkeypatch.setenv("GROK_LISTEN_PORT", "7432" if mode == "proposal_write" else "7354")
    spec = importlib.util.spec_from_file_location(name, SERVER)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_program_submission_builds_pending_proposal_without_raw_code() -> None:
    program = "print('must never run at the SAGE boundary')"

    proposal = build_sage_program_proposal(
        task_id="sage-program-test-1",
        program=program,
        timeout_s=30,
    )

    assert proposal["schema"] == "nexus.sage-program-proposal.v1"
    assert proposal["proposal_only"] is True
    assert proposal["execution_allowed"] is False
    assert proposal["program_executed"] is False
    assert proposal["program_persisted"] is False
    assert proposal["envelope"]["approval_state"] == "pending"
    assert proposal["envelope"]["human_approved"] is False
    assert program not in json.dumps(proposal)
    assert len(proposal["program_sha256"]) == 64


def test_sage_job_handoff_is_receipt_bound_pending_and_live_refused() -> None:
    parameters = {
        "query": "Verify the governed model health evidence boundary.",
        "sources": ["audit"],
        "max_results": 5,
    }
    proposal = build_sage_job_proposal(
        task_id="sage-proposal-handoff-1",
        workflow_type="evidence_search",
        parameters=parameters,
    )

    handoff = build_sage_job_handoff(
        job_id="sage-job-0123456789abcdef0123456789abcdef",
        principal="nexus-sage:0123456789ab",
        workflow_type="evidence_search",
        state="pending_review",
        parameters=parameters,
        proposal=proposal,
    )

    payload = handoff.to_dict()
    assert payload["schema"] == "nexus.sage-nexusclaw-handoff.v1"
    assert payload["receipt"]["state"] == "pending_review"
    assert payload["receipt"]["proposal_sha256"] == handoff.proposal_sha256
    assert payload["execution_allowed"] is False
    assert payload["envelope"]["approval_state"] == "pending"
    assert payload["envelope"]["human_approved"] is False
    assert handoff.envelope.approval_state.value == "pending"
    assert handoff.envelope.human_approved is False


def test_sage_job_handoff_digest_survives_json_persistence_round_trip() -> None:
    parameters = {
        "objective": "Audit the governed receipt persistence boundary.",
        "domains": ["relay"],
        "max_agents": 2,
    }
    proposal = build_sage_job_proposal(
        task_id="sage-proposal-handoff-json-roundtrip",
        workflow_type="parallel_audit_proposal",
        parameters=parameters,
    )
    persisted_proposal = json.loads(json.dumps(proposal, ensure_ascii=False))

    created = build_sage_job_handoff(
        job_id="sage-job-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        principal="nexus-sage:0123456789ab",
        workflow_type="parallel_audit_proposal",
        state="pending_review",
        parameters=parameters,
        proposal=proposal,
    )
    replayed = build_sage_job_handoff(
        job_id="sage-job-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        principal="nexus-sage:0123456789ab",
        workflow_type="parallel_audit_proposal",
        state="pending_review",
        parameters=parameters,
        proposal=persisted_proposal,
    )

    assert replayed.proposal_sha256 == created.proposal_sha256
    assert replayed.parameters_sha256 == created.parameters_sha256


@pytest.mark.parametrize(
    ("state", "mutation", "error"),
    [
        ("accepted", None, "pending_review"),
        ("pending_review", "execution_allowed", "proposal-only"),
        ("pending_review", "source", "canonical SAGE source"),
        ("pending_review", "parameters_sha256", "parameters hash"),
    ],
)
def test_sage_job_handoff_rejects_tampered_or_non_pending_receipts(
    state: str,
    mutation: str | None,
    error: str,
) -> None:
    parameters = {
        "query": "Check current evidence receipts.",
        "sources": ["grounding"],
        "max_results": 3,
    }
    proposal = build_sage_job_proposal(
        task_id="sage-proposal-handoff-2",
        workflow_type="evidence_search",
        parameters=parameters,
    )
    if mutation == "execution_allowed":
        proposal["execution_allowed"] = True
    elif mutation == "source":
        proposal["envelope"]["source"] = "a2a:forged-sender"
    elif mutation == "parameters_sha256":
        proposal["parameters_sha256"] = "0" * 64

    with pytest.raises(ValueError, match=error):
        build_sage_job_handoff(
            job_id="sage-job-fedcba9876543210fedcba9876543210",
            principal="nexus-sage:abcdef012345",
            workflow_type="evidence_search",
            state=state,
            parameters=parameters,
            proposal=proposal,
        )


@pytest.mark.parametrize("program", ["", "   ", "x" * 50_001], ids=["empty", "blank", "too_large"])
def test_program_proposal_rejects_invalid_programs(program: str) -> None:
    with pytest.raises(ValueError):
        build_sage_program_proposal(task_id="sage-program-test-2", program=program)


def test_7354_does_not_register_sage_facade_or_load_key(monkeypatch, tmp_path) -> None:
    server = _load_server(monkeypatch, tmp_path, mode="observe_only")
    paths = {
        getattr(route, "path", "")
        for route in server.mcp._custom_starlette_routes
    }

    assert not any(path.startswith("/v1/") for path in paths)
    assert "/privacy" not in paths
    assert server.NEXUS_SAGE_API_KEY == ""


def test_legacy_program_facade_stays_unregistered_when_writes_are_requested(
    monkeypatch, tmp_path
) -> None:
    server = _load_server(monkeypatch, tmp_path, mode="proposal_write")
    paths = {
        getattr(route, "path", "")
        for route in server.mcp._custom_starlette_routes
    }

    assert "/v1/program" not in paths
    assert not any(path.startswith("/v1/") for path in paths)
    assert server.SAGE_GATEWAY_MODE == "disabled"
    assert server.NEXUS_SAGE_API_KEY == ""


def test_server_never_logs_or_prints_the_sage_credential() -> None:
    source = SERVER.read_text(encoding="utf-8")

    assert "Generated new SAGE API Key" not in source
    assert "NEXUS_SAGE_API_KEY[:" not in source
    assert "SAGE API credential configured" not in source
