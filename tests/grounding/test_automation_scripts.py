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

