"""Terminal sanitizer tests for the canonical nexus_os package."""

from nexus_os.security import TerminalSanitizer, VerifiableOutput


def test_terminal_sanitizer_strips_control_sequences():
    poisoned = "\x1b]0;fake-title\x07hello\x1b[2J\nworld\x1b[31m"

    clean = TerminalSanitizer.sanitize(poisoned)

    assert clean == "hello\nworld"
    assert TerminalSanitizer.is_clean(clean) is True
    assert TerminalSanitizer.contains_escape(poisoned) is True


def test_verifiable_output_detects_content_tampering():
    message = VerifiableOutput("approved output", source="agent-a", target="agent-b")
    message.sign("local-test-key")

    assert message.verify() is True

    payload = message.to_dict()
    payload["content"] = "tampered output"

    assert VerifiableOutput.from_dict(payload).verify() is False
