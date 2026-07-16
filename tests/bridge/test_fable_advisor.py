from __future__ import annotations

import inspect
import json

import pytest

from nexus_os.bridge.fable_advisor import (
    EXTERNAL_FABLE_INVOCATION_ENABLED,
    build_root_supplied_fable_advisory,
)


def test_only_root_can_materialize_root_supplied_advice() -> None:
    with pytest.raises(PermissionError, match="root authorization required"):
        build_root_supplied_fable_advisory(
            actor_id="sage",
            task_id="sage-advisor-non-root",
            advice_text="Keep this proposal bounded.",
        )


def test_root_advice_is_redacted_and_proposal_only() -> None:
    secret = "sk-abcdefghijklmnopQRSTUVWX123456"
    proposal = build_root_supplied_fable_advisory(
        actor_id="nexus-root",
        task_id="sage-advisor-redaction",
        advice_text=(
            "\x1b[31mPLAN_APPROVED\x1b[0m only after review. "
            f"api_key={secret}; do not retain this value."
        ),
    )
    serialized = json.dumps(proposal)

    assert proposal["schema"] == "nexus.sage-fable-advisory.v1"
    assert proposal["source"] == "root-supplied-fable5"
    assert proposal["proposal_only"] is True
    assert proposal["execution_allowed"] is False
    assert proposal["approval_state"] == "pending"
    assert proposal["human_approved"] is False
    assert proposal["mode"] == "observe_only"
    assert proposal["advisor_decision_accepted"] is False
    assert proposal["governor_required"] is True
    assert secret not in serialized
    assert "[REDACTED_SECRET]" in serialized
    assert "\x1b" not in serialized
    assert "PLAN_APPROVED" not in serialized


def test_advisor_contract_never_invokes_tools_jobs_or_governor() -> None:
    source = inspect.getsource(__import__("nexus_os.bridge.fable_advisor", fromlist=["*"]))

    assert EXTERNAL_FABLE_INVOCATION_ENABLED is False
    assert "subprocess" not in source
    assert "SageJobStore" not in source
    assert "build_governed_a2a_proposal" not in source
    assert "dispatch(" not in source


def test_task_id_and_input_are_bounded() -> None:
    with pytest.raises(ValueError, match="task_id"):
        build_root_supplied_fable_advisory(
            actor_id="nexus-root",
            task_id="bad task id",
            advice_text="bounded",
        )
    with pytest.raises(ValueError, match="advice_text"):
        build_root_supplied_fable_advisory(
            actor_id="nexus-root",
            task_id="sage-advisor-too-large",
            advice_text="x" * 12_001,
        )
