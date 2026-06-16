import pytest

from nexus_os.nexusclaw.envelope import (
    NexusClawResultEnvelope,
    NexusClawTaskEnvelope,
    ResultStatus,
)


def valid_task_payload(**overrides):
    payload = {
        "task_id": "NC-001",
        "source": "unit-test",
        "lane": "orchestrator",
        "intent": "dry-run a bounded adapter task",
        "risk_level": "medium",
        "required_capabilities": ["dry_run"],
        "resource_budget": {"max_tokens": 1000, "max_runtime_s": 60},
        "egress_policy": {
            "cloud_fallback": False,
            "remote_stdio": False,
            "all_filesystem_access": False,
        },
        "evidence_refs": ["docs/handoff/nexusclaw/NEXUSCLAW_CORE_V0_EVIDENCE_MATRIX_2026-06-03.md"],
    }
    payload.update(overrides)
    return payload


def test_task_envelope_round_trip():
    task = NexusClawTaskEnvelope.from_dict(valid_task_payload())

    assert task.to_dict()["task_id"] == "NC-001"
    assert task.to_dict()["risk_level"] == "medium"


def test_task_envelope_rejects_invalid_lane():
    with pytest.raises(ValueError, match="lane must be one of"):
        NexusClawTaskEnvelope.from_dict(valid_task_payload(lane="invalid_lane"))


def test_task_envelope_accepts_v1_lanes():
    # V1 lanes like governance, research, security should be valid
    task = NexusClawTaskEnvelope.from_dict(valid_task_payload(lane="research"))
    assert task.lane == "research"
    task = NexusClawTaskEnvelope.from_dict(valid_task_payload(lane="governance"))
    assert task.lane == "governance"
    task = NexusClawTaskEnvelope.from_dict(valid_task_payload(lane="security"))
    assert task.lane == "security"


@pytest.mark.parametrize("field", ["required_capabilities", "evidence_refs"])
def test_task_envelope_requires_real_lists(field):
    with pytest.raises(ValueError, match=f"{field} must be a list"):
        NexusClawTaskEnvelope.from_dict(valid_task_payload(**{field: "not-a-list"}))


@pytest.mark.parametrize("flag", ["cloud_fallback", "remote_stdio", "all_filesystem_access"])
def test_task_envelope_rejects_forbidden_egress_flags(flag):
    payload = valid_task_payload(egress_policy={flag: True})

    with pytest.raises(ValueError):
        NexusClawTaskEnvelope.from_dict(payload)


@pytest.mark.parametrize("budget", [{"max_tokens": 0}, {"max_runtime_s": -1}])
def test_task_envelope_requires_positive_resource_budget(budget):
    with pytest.raises(ValueError, match="positive integer"):
        NexusClawTaskEnvelope.from_dict(valid_task_payload(resource_budget=budget))


def test_completed_result_requires_evidence_and_vap_record():
    with pytest.raises(ValueError, match="completed results require evidence"):
        NexusClawResultEnvelope(
            task_id="NC-001",
            status=ResultStatus.COMPLETED,
            executor="nexusclaw.test",
        )

    with pytest.raises(ValueError, match="vap_record_id"):
        NexusClawResultEnvelope(
            task_id="NC-001",
            status=ResultStatus.COMPLETED,
            executor="nexusclaw.test",
            evidence=["evidence"],
        )


def test_halted_result_requires_halt_reason():
    with pytest.raises(ValueError, match="halt_reason"):
        NexusClawResultEnvelope(
            task_id="NC-001",
            status=ResultStatus.HALTED,
            executor="nexusclaw.test",
        )
