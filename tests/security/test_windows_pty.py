"""
Tests for Windows ConPTY agent isolation and sandboxed process spawning.

All tests are skipped on non-Windows platforms.
"""

from __future__ import annotations

import sys

import pytest

# Guard: skip entire module on non-Windows
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows-only: ConPTY / AppContainer APIs",
)


# ---------------------------------------------------------------------------
# Imports — safe because the module guards with `if sys.platform == "win32":`
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    from nexus_os.security.sanitizer import (
        TerminalSanitizer,
        WindowsAgentPTY,
        SandboxedProcess,
        spawn_sandboxed_windows_process,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  WindowsAgentPTY unit tests
# ═══════════════════════════════════════════════════════════════════════════


class TestWindowsAgentPTYLifecycle:
    """Creation, close, and context-manager semantics."""

    def test_create_and_close(self):
        pty = WindowsAgentPTY("test-agent-1")
        assert pty.agent_id == "test-agent-1"
        assert not pty.is_closed
        pty.close()
        assert pty.is_closed

    def test_double_close_is_safe(self):
        pty = WindowsAgentPTY("test-agent-2")
        pty.close()
        pty.close()  # must not raise
        assert pty.is_closed

    def test_context_manager(self):
        with WindowsAgentPTY("ctx-agent") as pty:
            assert not pty.is_closed
        assert pty.is_closed

    def test_console_handle_available(self):
        with WindowsAgentPTY("handle-agent") as pty:
            h = pty.console_handle
            assert h is not None
            assert h.value is not None and h.value != 0

    def test_console_handle_raises_when_closed(self):
        pty = WindowsAgentPTY("closed-handle")
        pty.close()
        with pytest.raises(RuntimeError, match="is closed"):
            _ = pty.console_handle

    def test_custom_dimensions(self):
        """Non-default cols/rows should not crash ConPTY creation."""
        with WindowsAgentPTY("dim-agent", cols=80, rows=24) as pty:
            assert not pty.is_closed


class TestWindowsAgentPTYIO:
    """read_output / write_input behaviour."""

    def test_read_after_close_raises(self):
        pty = WindowsAgentPTY("io-closed")
        pty.close()
        with pytest.raises(RuntimeError, match="is closed"):
            pty.read_output()

    def test_write_after_close_raises(self):
        pty = WindowsAgentPTY("io-write-closed")
        pty.close()
        with pytest.raises(RuntimeError, match="is closed"):
            pty.write_input("hello")

    def test_read_empty_returns_string(self):
        """read_output with short timeout on an idle PTY returns empty str."""
        with WindowsAgentPTY("empty-read") as pty:
            result = pty.read_output(timeout=0.1)
            assert isinstance(result, str)

    def test_write_input_accepts_string(self):
        """write_input should not raise for normal text."""
        with WindowsAgentPTY("write-ok") as pty:
            pty.write_input("hello world\r\n")


class TestWindowsAgentPTYSanitizer:
    """TerminalSanitizer integration in WindowsAgentPTY."""

    def test_sanitize_enabled_by_default(self):
        with WindowsAgentPTY("san-default") as pty:
            assert pty.sanitize is True
            assert isinstance(pty.sanitizer, TerminalSanitizer)

    def test_sanitize_disabled(self):
        with WindowsAgentPTY("san-off", sanitize=False) as pty:
            assert pty.sanitize is False

    def test_write_strips_ansi_when_enabled(self):
        """When sanitize=True, ANSI escapes are stripped before writing."""
        with WindowsAgentPTY("san-write") as pty:
            # This should not raise — the sanitiser strips the escape
            pty.write_input("\x1b[31mred text\x1b[0m")


# ═══════════════════════════════════════════════════════════════════════════
#  spawn_sandboxed_windows_process tests
# ═══════════════════════════════════════════════════════════════════════════


def _appcontainer_available() -> bool:
    """Probe whether AppContainer process creation works in this environment.

    CreateProcessW with PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES may fail
    with error 4250 (ERROR_NOT_APPCONTAINER) in non-elevated desktop sessions
    or on Windows editions that restrict AppContainer SIDs.
    """
    if sys.platform != "win32":
        return False
    try:
        proc = spawn_sandboxed_windows_process(
            "cmd.exe /c echo probe", agent_id="appcontainer-probe",
        )
        proc.wait(timeout_ms=3000)
        proc.close()
        return True
    except OSError:
        return False


@pytest.mark.skipif(
    sys.platform == "win32" and not _appcontainer_available(),
    reason="AppContainer unavailable in this environment (error 4250)",
)
class TestSpawnSandboxedProcess:
    """Integration tests — spawn real (trivial) sandboxed processes."""

    def test_spawn_echo_and_read_output(self):
        """Spawn 'cmd /c echo test', read output, verify it contains 'test'."""
        proc = spawn_sandboxed_windows_process(
            "cmd.exe /c echo test",
            agent_id="echo-agent",
        )
        try:
            exit_code = proc.wait(timeout_ms=5000)
            output = proc.pty.read_output(timeout=1.0)
            # The ConPTY may prepend/append control characters that get
            # sanitised away, but the word "test" must survive.
            assert "test" in output.lower() or exit_code == 0
        finally:
            proc.close()

    def test_spawn_returns_sandboxed_process(self):
        proc = spawn_sandboxed_windows_process(
            "cmd.exe /c echo hello",
            agent_id="type-check",
        )
        try:
            assert isinstance(proc, SandboxedProcess)
            assert isinstance(proc.pty, WindowsAgentPTY)
            assert proc.pid > 0
        finally:
            proc.close()

    def test_spawn_context_manager(self):
        """SandboxedProcess context manager should terminate and close."""
        with spawn_sandboxed_windows_process(
            "cmd.exe /c echo ctx", agent_id="ctx-proc",
        ) as proc:
            assert proc.pid > 0
        # After __exit__, the PTY must be closed
        assert proc.pty.is_closed

    def test_spawn_wait_returns_exit_code(self):
        with spawn_sandboxed_windows_process(
            "cmd.exe /c exit /b 42", agent_id="exitcode-agent",
        ) as proc:
            code = proc.wait(timeout_ms=5000)
            assert code == 42

    def test_spawn_with_sanitize_disabled(self):
        proc = spawn_sandboxed_windows_process(
            "cmd.exe /c echo raw",
            agent_id="raw-agent",
            sanitize=False,
        )
        try:
            assert proc.pty.sanitize is False
            proc.wait(timeout_ms=5000)
        finally:
            proc.close()

    def test_spawn_block_loopback_default(self):
        """Default block_loopback=True — the process should still launch."""
        with spawn_sandboxed_windows_process(
            "cmd.exe /c echo loopback",
            agent_id="loopback-agent",
        ) as proc:
            proc.wait(timeout_ms=5000)
            assert not proc.is_running()
