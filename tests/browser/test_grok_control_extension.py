import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXT_DIR = ROOT / "tools" / "grok_control_chrome"


def test_manifest_is_grok_scoped_mv3():
    manifest = json.loads((EXT_DIR / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == 3
    assert "https://grok.com/*" in manifest["host_permissions"]
    assert "https://*.grok.com/*" in manifest["host_permissions"]
    assert "*://*/*" not in manifest["host_permissions"]
    assert "<all_urls>" not in manifest["host_permissions"]
    assert manifest["background"]["service_worker"] == "background.js"


def test_background_defaults_are_safe():
    background = (EXT_DIR / "background.js").read_text(encoding="utf-8")

    assert "bridgeEnabled: false" in background
    assert "autoContinue: false" in background
    assert "autoSend: false" in background
    assert "bridge_endpoint_must_be_localhost_http" in background
    assert "chrome.alarms.create" in background


def test_content_script_uses_dom_observer_and_bounded_continuation():
    content = (EXT_DIR / "content.js").read_text(encoding="utf-8")

    assert "new MutationObserver" in content
    assert "maxContinuesPerChat" in content
    assert "settings.autoSend === true" in content
    assert "settings.autoContinue !== true" in content
    assert "NEXUS_GROK_STATE" in content


def test_content_script_targets_grok_composer_without_broad_cancel_false_positive():
    content = (EXT_DIR / "content.js").read_text(encoding="utf-8")

    assert '[aria-label="Ask Grok anything"]' in content
    assert 'button[data-testid="chat-submit"]' in content
    assert "includes(\"cancel\")" not in content
    assert ".animate-pulse" not in content
    assert "stop generating" in content
    assert "document.execCommand(\"insertText\"" in content
