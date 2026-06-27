from pathlib import Path

from tools.browser_ai_supervisor.external_browser_ai_director import (
    BRIDGE_TOOL_MAP,
    CycleObservation,
    DirectorRunner,
    ProviderWindow,
    SOURCE_PROFILES,
    append_memory,
    build_outro_record,
    classify_bridge_status,
    decide_cycle,
    decide_source_run,
    stable_fingerprint,
)


def test_blocked_setup_is_distinct_from_retryable_bridge_down():
    blocked = decide_cycle(
        CycleObservation(cdp_status="error", error_code="cdp_missing"),
        previous_fingerprint=None,
    )
    retry = decide_cycle(
        CycleObservation(cdp_status="ok", error_code="runtime_evaluate_timeout"),
        previous_fingerprint=None,
    )

    assert blocked.action == "BLOCKED_SETUP"
    assert blocked.codex_escalation is False
    assert retry.action == "RETRY_LATER"
    assert retry.codex_escalation is False


def test_noop_unchanged_never_allows_provider():
    observation = CycleObservation(
        cdp_status="ok",
        visible_marker="same",
        visible_tail="stable text",
    )
    previous = stable_fingerprint("same", "stable text", "")

    decision = decide_cycle(observation, previous_fingerprint=previous)

    assert decision.action == "NOOP_UNCHANGED"
    assert decision.provider_allowed is False
    assert decision.provider == "none"
    assert decision.bridge_tools == ()


def test_provider_cooldown_blocks_material_delta():
    observation = CycleObservation(
        cdp_status="ok",
        bridge_status="ok",
        visible_marker="new",
        visible_tail="new artifact arrived",
        new_artifact_name="GrokDirectorCycleContract_v1",
        requires_bridge=True,
    )
    window = ProviderWindow(
        calls_last_hour=1,
        last_provider_call_at="2026-06-21T18:00:00Z",
    )

    decision = decide_cycle(
        observation,
        previous_fingerprint=None,
        provider_window=window,
        now="2026-06-21T18:05:00Z",
    )

    assert decision.action == "RETRY_LATER"
    assert decision.reason == "provider_cooldown"
    assert decision.provider_allowed is False


def test_new_artifact_maps_exact_bridge_tools_once_cooldown_allows():
    observation = CycleObservation(
        cdp_status="ok",
        bridge_status="ok",
        visible_marker="new",
        visible_tail="contract text",
        new_artifact_name="GrokDirectorCycleContract_v1",
        requires_bridge=True,
    )

    decision = decide_cycle(
        observation,
        previous_fingerprint=None,
        provider_window=ProviderWindow(calls_last_hour=0),
        now="2026-06-21T18:30:00Z",
    )

    assert decision.action == "ARTIFACT_CAPTURED"
    assert decision.provider_allowed is True
    assert decision.provider == "internai"
    assert decision.bridge_tools == ("ping", "registry_debug", "http_diagnostic", "task_add")
    assert {tool: BRIDGE_TOOL_MAP[tool] for tool in decision.bridge_tools} == {
        "ping": "connectivity_probe",
        "registry_debug": "tool_inventory_probe",
        "http_diagnostic": "governed_public_http_probe",
        "task_add": "single_bounded_task_proposal",
    }


def test_grok_missing_connector_tools_blocks_before_provider():
    observation = CycleObservation(
        cdp_status="ok",
        bridge_status="ok",
        visible_marker="grok report",
        visible_tail="GrokMcpEgressIntegrationReport_v2\nconnector_status: BLOCKED\nhealth_result: BLOCKED_TOOL_NOT_VISIBLE\nhttp_diagnostic_result: BLOCKED_TOOL_NOT_VISIBLE",
        requires_bridge=True,
    )

    decision = decide_cycle(observation, previous_fingerprint=None)

    assert decision.action == "BLOCKED_SETUP"
    assert decision.reason == "grok_connector_tools_missing"
    assert decision.provider_allowed is False
    assert decision.bridge_tools == ("ping", "registry_debug", "http_diagnostic", "task_add")

def test_bridge_required_down_is_blocked_setup_not_provider_call():
    decision = decide_cycle(
        CycleObservation(
            cdp_status="ok",
            bridge_status="down",
            visible_marker="new",
            visible_tail="needs bridge",
            requires_bridge=True,
        ),
        previous_fingerprint=None,
    )

    assert decision.action == "BLOCKED_SETUP"
    assert decision.reason == "bridge_not_listening"
    assert decision.provider_allowed is False


def test_source_profiles_keep_grok_frequent_and_private_sources_slow():
    assert SOURCE_PROFILES["grok-project-nexus"].cadence_seconds == 10 * 60
    assert SOURCE_PROFILES["grok-project-nexus"].requires_bridge is True
    assert SOURCE_PROFILES["zo-computer-nexus"].cadence_seconds == 6 * 60 * 60
    assert SOURCE_PROFILES["glm52-dashboard"].cadence_seconds == 6 * 60 * 60


def test_bridge_status_classifier_separates_retry_from_setup_block():
    assert classify_bridge_status("timeout") == ("retry", "bridge_timeout")
    assert classify_bridge_status("down") == ("down", "bridge_not_listening")
    assert classify_bridge_status("missing") == ("down", "bridge_tool_missing")
    assert classify_bridge_status("ok") == ("ok", None)


def test_source_run_cadence_blocks_before_provider():
    previous = stable_fingerprint("old", "old tail", "")
    observation = CycleObservation(
        cdp_status="ok",
        bridge_status="ok",
        visible_marker="new",
        visible_tail="new artifact",
        new_artifact_name="Contract",
        requires_bridge=True,
    )

    decision = decide_source_run(
        source_id="grok-project-nexus",
        observation=observation,
        entries=[
            {
                "source_id": "grok-project-nexus",
                "started_at": "2026-06-21T18:00:00Z",
                "completed_at": "2026-06-21T18:00:10Z",
                "visible_fingerprint": previous,
                "provider_calls": 1,
            }
        ],
        now="2026-06-21T18:05:00Z",
    )

    assert decision.action == "NOOP_UNCHANGED"
    assert decision.reason == "cadence_not_elapsed"
    assert decision.provider_allowed is False


def test_source_run_allows_grok_after_cadence_elapsed():
    observation = CycleObservation(
        cdp_status="ok",
        bridge_status="ok",
        visible_marker="new",
        visible_tail="new artifact",
        new_artifact_name="Contract",
        requires_bridge=True,
    )

    decision = decide_source_run(
        source_id="grok-project-nexus",
        observation=observation,
        entries=[
            {
                "source_id": "grok-project-nexus",
                "started_at": "2026-06-21T18:00:00Z",
                "completed_at": "2026-06-21T18:00:10Z",
                "provider_calls": 0,
            }
        ],
        now="2026-06-21T18:10:11Z",
    )

    assert decision.action == "ARTIFACT_CAPTURED"
    assert decision.provider_allowed is True


def test_runner_does_not_call_provider_on_unchanged(tmp_path: Path):
    memory_path = tmp_path / "director.jsonl"
    previous = stable_fingerprint("same", "tail", "")
    append_memory(
        memory_path,
        {
            "run_id": "previous",
            "source_id": "grok-project-nexus",
            "started_at": "2026-06-21T18:00:00Z",
            "visible_fingerprint": previous,
            "action": "CONTINUE_SENT",
        },
    )
    provider_calls = []

    runner = DirectorRunner(
        memory_path,
        observe=lambda: CycleObservation(cdp_status="ok", visible_marker="same", visible_tail="tail"),
        provider_eval=lambda observation, provider: provider_calls.append(provider) or {"status": "called"},
    )

    record = runner.run_once(run_id="noop", now="2026-06-21T18:10:00Z")

    assert record["action"] == "NOOP_UNCHANGED"
    assert record["provider_calls"] == 0
    assert provider_calls == []


def test_runner_calls_provider_once_for_new_artifact(tmp_path: Path):
    memory_path = tmp_path / "director.jsonl"
    provider_calls = []

    runner = DirectorRunner(
        memory_path,
        observe=lambda: CycleObservation(
            cdp_status="ok",
            bridge_status="ok",
            visible_marker="new",
            visible_tail="artifact",
            new_artifact_name="Contract",
            requires_bridge=True,
        ),
        provider_eval=lambda observation, provider: provider_calls.append(provider) or {"status": "reviewed"},
    )

    record = runner.run_once(run_id="artifact", now="2026-06-21T18:20:00Z")

    assert record["action"] == "ARTIFACT_CAPTURED"
    assert record["provider_calls"] == 1
    assert record["provider_result_status"] == "reviewed"
    assert provider_calls == ["internai"]
    assert record["bridge_tools"] == ["ping", "registry_debug", "http_diagnostic", "task_add"]


def test_outro_record_has_blocker_only_for_retry_or_setup():
    observation = CycleObservation(cdp_status="ok", error_code="runtime_evaluate_timeout")
    decision = decide_cycle(observation, previous_fingerprint=None)

    record = build_outro_record(
        run_id="retry",
        observation=observation,
        decision=decision,
        started_at="2026-06-21T18:00:00Z",
    )

    assert record["action"] == "RETRY_LATER"
    assert record["blocker"] == "runtime_evaluate_timeout"
    assert record["provider_calls"] == 0


