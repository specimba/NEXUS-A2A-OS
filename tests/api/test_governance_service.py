"""Tests for the pure governance API service."""

import pytest

from nexus_os.api.service import GovernanceAPIState


@pytest.fixture
def state(tmp_path):
    service = GovernanceAPIState(db_path=str(tmp_path / "api.db"))
    yield service
    service.close()


def test_dashboard_stats_empty(state):
    stats = state.dashboard_stats()

    assert stats["status"] == "operational"
    assert stats["proposal_count"] == 0
    assert stats["approved"] == 0


def test_skill_proposal_uses_governor_allow_path(state):
    record = state.propose_skill(
        proposal_id="proposal-allow-1",
        model_id="qwen2.5-coder:7b",
        skill={
            "name": "summarize-session",
            "action": "read",
            "scope": "project",
            "impact": "low",
            "clearance": "contributor",
        },
        rationale="read project context for grounded analysis",
    )

    assert record["proposal_id"] == "proposal-allow-1"
    assert record["status"] == "approved"
    assert record["decision"] == "allow"
    assert state.get_proposal("proposal-allow-1")["status"] == "approved"

    stats = state.dashboard_stats()
    assert stats["proposal_count"] == 1
    assert stats["approved"] == 1
    assert stats["audit_entries"] >= 1


def test_skill_proposal_rejects_over_clearance_request(state):
    record = state.propose_skill(
        proposal_id="proposal-deny-1",
        model_id="worker-low-clearance",
        skill={
            "name": "system-maintenance",
            "action": "execute",
            "scope": "system",
            "impact": "critical",
            "clearance": "contributor",
        },
        rationale="execute system maintenance",
    )

    assert record["status"] == "rejected"
    assert record["decision"] == "deny"


def test_duplicate_proposals_are_rejected(state):
    kwargs = {
        "proposal_id": "proposal-dupe-1",
        "model_id": "worker",
        "skill": {"action": "read"},
        "rationale": "read project context",
    }
    state.propose_skill(**kwargs)

    with pytest.raises(ValueError, match="already exists"):
        state.propose_skill(**kwargs)


def test_manual_approval_updates_held_proposal(state):
    record = state.propose_skill(
        proposal_id="proposal-hold-1",
        model_id="worker-needs-review",
        skill={
            "name": "write-record",
            "action": "write",
            "scope": "project",
            "impact": "medium",
            "clearance": "contributor",
        },
        rationale="x",
    )
    assert record["status"] == "held"

    approved = state.review_proposal(
        proposal_id="proposal-hold-1",
        decision="approve",
        reviewer="speci",
        reason="Intent reviewed manually.",
    )

    assert approved["status"] == "approved"
    assert approved["decision"] == "allow"
    assert approved["review"]["reviewer"] == "speci"
