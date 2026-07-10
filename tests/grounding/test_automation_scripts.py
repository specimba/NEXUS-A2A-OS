from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_browser_supervisor_is_idempotent_and_uses_canonical_ports():
    text = (
        ROOT / "tools" / "browser_ai_supervisor" / "run_browser_ai_supervisor.ps1"
    ).read_text(encoding="utf-8")

    assert "9224" in text
    assert "7352" not in text
    assert "Test-Cdp" in text
    assert "start_browser_ai_profile.ps1" in text
    assert "-RequiresBridge" in text


def test_task_installer_uses_single_instance_and_bounded_restart():
    text = (
        ROOT / "scripts" / "install_nexus_grounding_automation.ps1"
    ).read_text(encoding="utf-8")

    assert "NexusGroundingSupervisor" in text
    assert "NexusBrowserAISupervisor" in text
    assert "-MultipleInstances IgnoreNew" in text
    assert "-RestartCount 3" in text
    assert "New-TimeSpan -Minutes 10" in text

def test_browser_cycle_is_mirrored_to_grounding_ledger():
    wrapper = (
        ROOT / "tools" / "browser_ai_supervisor" / "run_external_director.ps1"
    ).read_text(encoding="utf-8")
    adapter = (
        ROOT / "tools" / "browser_ai_supervisor" / "record_grounding_event.py"
    ).read_text(encoding="utf-8")

    assert "NEXUS_GROUNDING_ROOT" in wrapper
    assert "record_grounding_event.py" in wrapper
    assert 'source_id="browser_ai.grok"' in adapter



def test_browser_supervisor_sets_continuity_ledger():
    text = (
        ROOT / "tools" / "browser_ai_supervisor" / "run_browser_ai_supervisor.ps1"
    ).read_text(encoding="utf-8")

    assert "NEXUS_CONTINUITY_LEDGER" in text
    assert "NEXUScontinuity_runs.jsonl" in text


def test_foreground_repair_is_manual_only_for_automation_paths():
    repair = (ROOT / "scripts" / "fix_lane_chrome_interactive_window.ps1").read_text(encoding="utf-8")
    supervisor = (
        ROOT / "tools" / "browser_ai_supervisor" / "run_browser_ai_supervisor.ps1"
    ).read_text(encoding="utf-8")

    assert "ManualObservation" in repair
    assert "NEXUS_ALLOW_FOREGROUND_LANE_REPAIR" in repair
    assert "fix_lane_chrome_interactive_window.ps1" not in supervisor


def test_cdp_probe_rejects_duplicate_targets_instead_of_guessing():
    probe = (
        ROOT / "tools" / "browser_ai_supervisor" / "grok_cdp_context_probe.mjs"
    ).read_text(encoding="utf-8")

    assert "duplicate_target_match" in probe
    assert "matchingTargets.length > 1" in probe
