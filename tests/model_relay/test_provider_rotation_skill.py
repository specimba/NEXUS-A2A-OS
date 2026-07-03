from pathlib import Path


def test_provider_rotation_skill_preserves_port_ownership():
    script = Path(".agents/skills/modelrelay-provider-rotation/scripts/sync.py").read_text(encoding="utf-8")

    assert 'owner == "modelrelay_npm"' in script
    assert 'owner == "modelrelay_python"' in script
    assert "--port 7352" not in script
    assert "localhost:7352" not in script
    assert "-LocalPort 7352" not in script
    assert "7352 must remain Brain API only" in script
    assert "CREATE_NO_WINDOW" in script
    assert "_is_modelrelay_process" in script
