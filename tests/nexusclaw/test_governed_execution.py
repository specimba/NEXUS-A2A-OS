"""Seam 3: governed live execution path for approved NexusClaw envelopes.

Dry-run stays the default everywhere; live execution is opt-in per
invocation (CLI --live / programmatic live=True) and is gated by the
envelope approval state, the explicit human approval marker for
HIGH/CRITICAL risk (HELD semantics), and a fail-closed Progent privilege
check. Every live execution appends an origin="core" evidence row to the
continuity ledger.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from nexus_os.continuity.records import read_records
from nexus_os.governor.privilege_control import PrivilegePolicy, ProgentPrivilegeControl
from nexus_os.nexusclaw.coordinator import NexusClawCoordinator
from nexus_os.nexusclaw.envelope import (
    ApprovalState,
    NexusClawTaskEnvelope,
    ResultStatus,
)


def make_envelope(**overrides) -> NexusClawTaskEnvelope:
    payload = {
        "task_id": "NC-LIVE-001",
        "source": "pytest",
        "lane": "orchestrator",
        "intent": "echo_status",
        "risk_level": "low",
        "approval_state": "approved",
        "evidence_refs": ["docs/handoff/nexusclaw/NEXUSCLAW_CORE_V0_EVIDENCE_MATRIX_2026-06-03.md"],
    }
    payload.update(overrides)
    return NexusClawTaskEnvelope.from_dict(payload)


def allow_echo_control() -> ProgentPrivilegeControl:
    return ProgentPrivilegeControl(PrivilegePolicy(allowed_tools={"echo_status": {}}))


@pytest.fixture
def tmp_ledger(tmp_path, monkeypatch):
    ledger = tmp_path / "runs.jsonl"
    monkeypatch.setenv("NEXUS_CONTINUITY_LEDGER", str(ledger))
    return ledger


# -- envelope approval schema ------------------------------------------------


def test_envelope_approval_defaults_to_pending_unapproved():
    task = NexusClawTaskEnvelope.from_dict(
        {
            "task_id": "NC-DEFAULT-1",
            "source": "pytest",
            "lane": "orchestrator",
            "intent": "noop",
            "risk_level": "low",
        }
    )
    assert task.approval_state is ApprovalState.PENDING
    assert task.human_approved is False
    round_trip = task.to_dict()
    assert round_trip["approval_state"] == "pending"
    assert round_trip["human_approved"] is False


def test_envelope_rejects_unknown_approval_state():
    with pytest.raises(ValueError, match="approval_state must be one of"):
        make_envelope(approval_state="self-approved")


# -- (a) approved benign envelope + live executes ------------------------------


def test_approved_benign_envelope_live_executes_with_continuity_row(tmp_ledger):
    calls: list[str] = []

    def executor(task: NexusClawTaskEnvelope) -> dict:
        calls.append(task.task_id)
        return {"echo": task.task_id}

    coordinator = NexusClawCoordinator(privilege_control=allow_echo_control())
    result = coordinator.dispatch(make_envelope(), live=True, executor=executor)

    assert result.status is ResultStatus.COMPLETED
    assert calls == ["NC-LIVE-001"]
    assert result.metrics["live"] is True
    assert result.metrics["privilege_check"]["allowed"] is True
    assert result.metrics["execution"] == {"echo": "NC-LIVE-001"}
    assert result.vap_record_id == "vap-live-NC-LIVE-001"

    records, meta = read_records(tmp_ledger)
    assert meta["exists"] is True
    assert len(records) == 1
    row = records[0]
    assert row.origin == "core"
    assert row.verification == "VERIFIED"
    assert row.proof["envelope_id"] == "NC-LIVE-001"
    assert row.proof["privilege_check"]["allowed"] is True
    assert row.proof["executed"] is True


# -- (b) unapproved / held / rejected refuse ----------------------------------


@pytest.mark.parametrize("approval_state", ["pending", "held", "rejected"])
def test_unapproved_envelope_live_is_refused(tmp_ledger, approval_state):
    executed: list[str] = []
    coordinator = NexusClawCoordinator(privilege_control=allow_echo_control())
    result = coordinator.dispatch_live(
        make_envelope(approval_state=approval_state),
        executor=lambda task: executed.append(task.task_id),
    )
    assert result.status is ResultStatus.REJECTED
    assert result.metrics["refused"] is True
    assert approval_state in result.metrics["refusal_reason"]
    assert executed == []
    assert not tmp_ledger.exists()


# -- (c) privilege check failure refuses, no execution -------------------------


def test_privilege_check_exception_fails_closed_without_execution(tmp_ledger):
    class ExplodingControl:
        def check_call(self, tool_name, arguments):
            raise RuntimeError("privilege backend down")

    executed: list[str] = []
    coordinator = NexusClawCoordinator(privilege_control=ExplodingControl())
    result = coordinator.dispatch_live(
        make_envelope(),
        executor=lambda task: executed.append(task.task_id),
    )
    assert result.status is ResultStatus.REJECTED
    assert result.metrics["privilege_check"]["allowed"] is False
    assert "privilege backend down" in result.metrics["privilege_check"]["error"]
    assert executed == []
    assert not tmp_ledger.exists()


def test_default_empty_privilege_policy_fails_closed(tmp_ledger):
    executed: list[str] = []
    coordinator = NexusClawCoordinator()  # no policy provisioned
    result = coordinator.dispatch_live(
        make_envelope(),
        executor=lambda task: executed.append(task.task_id),
    )
    assert result.status is ResultStatus.REJECTED
    assert result.metrics["privilege_check"]["allowed"] is False
    assert executed == []
    assert not tmp_ledger.exists()


def test_forbidden_tool_refuses_execution(tmp_ledger):
    control = ProgentPrivilegeControl(
        PrivilegePolicy(
            allowed_tools={"echo_status": {}},
            forbidden_tools={"echo_status": {}},
        )
    )
    executed: list[str] = []
    coordinator = NexusClawCoordinator(privilege_control=control)
    result = coordinator.dispatch_live(
        make_envelope(),
        executor=lambda task: executed.append(task.task_id),
    )
    assert result.status is ResultStatus.REJECTED
    assert executed == []
    assert not tmp_ledger.exists()


# -- (d) default stays dry-run --------------------------------------------------


def test_default_dispatch_is_dry_run_and_never_executes(tmp_ledger):
    executed: list[str] = []
    coordinator = NexusClawCoordinator(privilege_control=allow_echo_control())
    result = coordinator.dispatch(
        make_envelope(),
        executor=lambda task: executed.append(task.task_id),
    )
    assert result.status is ResultStatus.DRY_RUN
    assert result.vap_record_id == "vap-dryrun-NC-LIVE-001"
    assert executed == []
    assert not tmp_ledger.exists()


# -- (e) HIGH/CRITICAL require the human approval marker ------------------------


@pytest.mark.parametrize("risk", ["high", "critical"])
def test_high_critical_without_human_marker_is_held(tmp_ledger, risk):
    executed: list[str] = []
    coordinator = NexusClawCoordinator(privilege_control=allow_echo_control())
    result = coordinator.dispatch_live(
        make_envelope(risk_level=risk),  # approved but no human marker
        executor=lambda task: executed.append(task.task_id),
    )
    assert result.status is ResultStatus.REJECTED
    assert result.metrics["held_for_human"] is True
    assert executed == []
    assert not tmp_ledger.exists()


@pytest.mark.parametrize("risk", ["high", "critical"])
def test_high_critical_with_human_marker_executes(tmp_ledger, risk):
    coordinator = NexusClawCoordinator(privilege_control=allow_echo_control())
    result = coordinator.dispatch_live(
        make_envelope(risk_level=risk, human_approved=True),
        executor=lambda task: {"ok": True},
    )
    assert result.status is ResultStatus.COMPLETED
    records, _ = read_records(tmp_ledger)
    assert len(records) == 1
    assert records[0].proof["human_approved"] is True
    assert records[0].proof["risk_level"] == risk


# -- failed execution still leaves an honest evidence row -----------------------


def test_failed_execution_writes_unverified_continuity_row(tmp_ledger):
    def boom(task: NexusClawTaskEnvelope) -> dict:
        raise RuntimeError("executor exploded")

    coordinator = NexusClawCoordinator(privilege_control=allow_echo_control())
    result = coordinator.dispatch_live(make_envelope(), executor=boom)

    assert result.status is ResultStatus.HALTED
    assert "executor exploded" in (result.halt_reason or "")

    records, _ = read_records(tmp_ledger)
    assert len(records) == 1
    row = records[0]
    assert row.verification == "UNVERIFIED"
    assert row.proof["executed"] is False
    assert "executor exploded" in row.proof["execution_error"]


def test_halted_coordinator_refuses_live(tmp_ledger):
    coordinator = NexusClawCoordinator(privilege_control=allow_echo_control())
    coordinator.halt("operator stop")
    result = coordinator.dispatch_live(make_envelope())
    assert result.status is ResultStatus.HALTED
    assert not tmp_ledger.exists()


# -- CLI surface ----------------------------------------------------------------


def run_nexusctl(*args, env=None):
    import os

    merged = dict(os.environ)
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, "-m", "nexusctl", *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env=merged,
    )


def test_cli_dispatch_defaults_to_dry_run(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    proc = run_nexusctl(
        "nexusclaw", "dispatch",
        "--task-id", "CLI-LIVE-1",
        "--source", "pytest",
        "--intent", "echo_status",
        "--risk-level", "low",
        env={"NEXUS_CONTINUITY_LEDGER": str(ledger)},
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["command"] == "nexusclaw.dispatch"
    assert payload["live"] is False
    assert payload["result"]["status"] == "dry_run"
    assert not ledger.exists()


def test_cli_dispatch_live_executes_approved_envelope(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    policy_file = tmp_path / "policy.json"
    policy_file.write_text(
        json.dumps({"allowed_tools": {"echo_status": {}}}), encoding="utf-8"
    )
    proc = run_nexusctl(
        "nexusclaw", "dispatch",
        "--task-id", "CLI-LIVE-2",
        "--source", "pytest",
        "--intent", "echo_status",
        "--risk-level", "low",
        "--evidence-ref", "docs/handoff/nexusclaw/NEXUSCLAW_CORE_V0_EVIDENCE_MATRIX_2026-06-03.md",
        "--live", "--approved",
        "--privilege-policy", str(policy_file),
        env={"NEXUS_CONTINUITY_LEDGER": str(ledger)},
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["live"] is True
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["vap_record_id"] == "vap-live-CLI-LIVE-2"
    records, _ = read_records(ledger)
    assert len(records) == 1
    assert records[0].origin == "core"
    assert records[0].proof["envelope_id"] == "CLI-LIVE-2"


def test_cli_dispatch_live_without_approval_refuses(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    proc = run_nexusctl(
        "nexusclaw", "dispatch",
        "--task-id", "CLI-LIVE-3",
        "--source", "pytest",
        "--intent", "echo_status",
        "--risk-level", "low",
        "--live",
        env={"NEXUS_CONTINUITY_LEDGER": str(ledger)},
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["result"]["status"] == "rejected"
    assert not ledger.exists()
