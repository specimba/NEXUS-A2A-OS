from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_task_uses_windowless_launcher():
    installer = (
        ROOT / "scripts" / "install_nexus_grounding_automation.ps1"
    ).read_text(encoding="utf-8")
    launcher = (
        ROOT
        / "tools"
        / "browser_ai_supervisor"
        / "run_browser_ai_supervisor_hidden.vbs"
    ).read_text(encoding="utf-8")

    assert "wscript.exe" in installer
    assert "run_browser_ai_supervisor_hidden.vbs" in installer
    assert "WindowStyle Hidden" not in installer
    assert "shell.Run(command, 0, True)" in launcher


def test_supervisor_does_not_globally_kill_chrome_or_write_runtime_to_repo():
    supervisor = (
        ROOT / "tools" / "browser_ai_supervisor" / "run_browser_ai_supervisor.ps1"
    ).read_text(encoding="utf-8")
    director = (
        ROOT / "tools" / "browser_ai_supervisor" / "run_external_director.ps1"
    ).read_text(encoding="utf-8")

    assert "Stop-Process -Name chrome" not in supervisor
    assert "NEXUS\\BrowserAI\\runtime" in supervisor
    assert "powershell -NoProfile" not in director
