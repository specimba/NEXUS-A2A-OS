"""tests/security/test_mcp_zero_day_defenses.py — Validate MCP Zero-Day threat defenses.

Verifies that MetaAttackDetector correctly flags:
  - MCP Tool Shadowing (egress overrides, name collisions, priority overrides).
  - MCP Tool Poisoning (external URLs, secrets paths, dangerous CLI args, Docker mounts, external interface bindings).
  - MCP Tool Confusion (alphabetical race, schema mismatch, UI parameter collapse).
"""
import pytest
from nexus_os.security.meta_attack_detector import MetaAttackDetector


@pytest.fixture
def detector():
    return MetaAttackDetector()


class TestMcpToolShadowingZeroDay:
    """MCP Tool Shadowing: egress overrides, name collisions, routing/priority overrides."""

    @pytest.mark.parametrize("text", [
        "mcp egress-override detected in server configs",
        "egress_override in mcp tool is a vulnerability",
        "the tool registration has mcp routing override active",
        "priority_override in the mcp manifest should be blocked",
        "mcp server has tool-collision with builtins",
        "name collision on mcp tools allows shadowing",
        "this ambiguous_tool is registered on mcp server",
        "shadow_tool in the mcp configuration causes routing issues"
    ])
    def test_shadowing_adversarial(self, detector, text):
        r = detector.scan(text)
        assert r.is_threat
        assert r.category == "mcp_tool_shadowing"
        assert r.confidence >= 0.80

    @pytest.mark.parametrize("text", [
        "How does MCP routing work by default?",
        "Can we override a method in python?",
        "The shadowing effect is observed in physics.",
    ])
    def test_shadowing_benign(self, detector, text):
        r = detector.scan(text)
        assert not r.is_threat


class TestMcpToolPoisoningZeroDay:
    """MCP Tool Poisoning: external URLs, secrets paths, dangerous CLI args, Docker mounts, 0.0.0.0 bindings."""

    @pytest.mark.parametrize("text", [
        "mcp description contains url https://evil.com/leak",
        "webhook configured on mcp tool to leak data",
        "mcp access to secret path /etc/passwd is forbidden",
        "/etc/shadow leak via mcp description",
        "system32 path read request in mcp tool",
        "mcp --auto-approve parameter in runtime",
        "auto-approve argument passed to mcp server",
        "mcp tool has dangerous mount -v /:/host",
        "filesystem escape via -v /var:/host in mcp tool",
        "--mount type=bind in mcp container configuration",
        "mcp binding to 0.0.0.0 is risky",
        "bind to external interface in mcp server"
    ])
    def test_poisoning_adversarial(self, detector, text):
        r = detector.scan(text)
        assert r.is_threat
        assert r.category == "mcp_tool_poisoning"
        assert r.confidence >= 0.80

    @pytest.mark.parametrize("text", [
        "How do you write a description for an MCP tool?",
        "Is there an auto-approve option in the CLI client?",
        "How does a Docker volume mount work?",
        "Should we bind localhost to port 8080?",
    ])
    def test_poisoning_benign(self, detector, text):
        r = detector.scan(text)
        assert not r.is_threat


class TestMcpToolConfusionZeroDay:
    """MCP Tool Confusion: alphabetical race, schema mismatch, UI parameter collapse."""

    @pytest.mark.parametrize("text", [
        "mcp alphabetical-race triggered in registry",
        "alphabetical precedence exploit on mcp server",
        "mcp alphabetically first tool wins the invocation routing",
        "schema-mismatch in mcp tool configuration",
        "parameter skew on mcp endpoints",
        "mismatched_parameter in mcp call",
        "mcp ui-parameter-collapse hides options",
        "parameter collapse in mcp interface",
        "hidden_parameter configured on mcp tool schema"
    ])
    def test_confusion_adversarial(self, detector, text):
        r = detector.scan(text)
        assert r.is_threat
        assert r.category == "mcp_tool_confusion"
        assert r.confidence >= 0.80

    @pytest.mark.parametrize("text", [
        "What is the alphabetical order of these files?",
        "Explain the JSON schema structure.",
        "Does the UI collapse parameters in the settings panel?",
    ])
    def test_confusion_benign(self, detector, text):
        r = detector.scan(text)
        assert not r.is_threat
