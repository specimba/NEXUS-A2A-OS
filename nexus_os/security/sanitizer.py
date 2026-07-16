"""
NEXUS OS terminal security layer.

Provides:
- TerminalSanitizer: strips ANSI/VT escape sequences from inter-agent output.
- AgentPTY: dedicated pseudo-terminal per agent on POSIX systems.
- VerifiableOutput: SHA-256/HMAC integrity for cross-agent messages.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
import threading
from typing import Any

if sys.platform != "win32":
    import pty


class TerminalSanitizer:
    """Strip ANSI/VT escape sequences and unsafe control bytes from text."""

    _C0_STRIP = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    _CSI_STRIP = re.compile(r"\x1b\[[\x30-\x3f]*[\x20-\x2f]*[\x40-\x7e]")
    _OSC_STRIP = re.compile(r"\x1b\][^\x07\x1b]*(\x07|\x1b\\)")
    _ESC_STRIP = re.compile(r"\x1b[A-Za-z]")
    _APP_KEY_STRIP = re.compile(r"\x1b\[[\d;]*~")
    _DCS_STRIP = re.compile(r"\x1bP[\s\S]*?\x1b\\")
    _SOS_STRIP = re.compile(r"\x1b[X^_][\s\S]*?\x1b\\")
    _ISO_SHIFT = re.compile(r"\x1b[()][\w]")

    @classmethod
    def sanitize(cls, text: str) -> str:
        if not text:
            return text

        text = cls._DCS_STRIP.sub("", text)
        text = cls._SOS_STRIP.sub("", text)
        text = cls._OSC_STRIP.sub("", text)
        text = cls._CSI_STRIP.sub("", text)
        text = cls._ISO_SHIFT.sub("", text)
        text = cls._ESC_STRIP.sub("", text)
        text = cls._APP_KEY_STRIP.sub("", text)
        text = cls._C0_STRIP.sub("", text)
        return text.strip()

    @classmethod
    def sanitize_stream(cls, stream: Any, chunk_size: int = 4096) -> str:
        parts: list[str] = []
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            if isinstance(chunk, bytes):
                chunk = chunk.decode("utf-8", errors="replace")
            parts.append(cls.sanitize(chunk))
        return "".join(parts)

    @classmethod
    def is_clean(cls, text: str) -> bool:
        return text == cls.sanitize(text)

    @classmethod
    def contains_escape(cls, text: str) -> bool:
        return not cls.is_clean(text)


if sys.platform != "win32":

    class AgentPTY:
        """Dedicated pseudo-terminal boundary for one agent process."""

        def __init__(self, agent_id: str, sanitize: bool = True):
            self.agent_id = agent_id
            self.sanitize = sanitize
            self.sanitizer = TerminalSanitizer()
            self._master_fd, self._slave_fd = pty.openpty()
            self._lock = threading.Lock()
            self._closed = False

        @property
        def slave_name(self) -> str:
            with self._lock:
                if self._closed:
                    raise RuntimeError(f"PTY for {self.agent_id} is closed")
                return os.ttyname(self._slave_fd)

        def read_output(self, timeout: float = 1.0) -> str:
            if self._closed:
                raise RuntimeError(f"PTY for {self.agent_id} is closed")

            raw = b""
            import select

            while True:
                ready, _, _ = select.select([self._master_fd], [], [], timeout)
                if not ready:
                    break
                try:
                    chunk = os.read(self._master_fd, 4096)
                    if not chunk:
                        break
                    raw += chunk
                except OSError:
                    break

            text = raw.decode("utf-8", errors="replace")
            if self.sanitize:
                text = self.sanitizer.sanitize(text)
            return text

        def write_input(self, data: str) -> None:
            if self._closed:
                raise RuntimeError(f"PTY for {self.agent_id} is closed")

            if self.sanitize:
                data = self.sanitizer.sanitize(data)

            with self._lock:
                os.write(self._master_fd, data.encode())

        def close(self) -> None:
            with self._lock:
                if not self._closed:
                    os.close(self._master_fd)
                    os.close(self._slave_fd)
                    self._closed = True

        def __enter__(self) -> "AgentPTY":
            return self

        def __exit__(self, *args: object) -> None:
            self.close()


if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes as wintypes
    from ctypes import (
        POINTER,
        Structure,
        byref,
        c_size_t,
        c_void_p,
        sizeof,
        windll,
    )

    # ── Win32 constants ──────────────────────────────────────────────
    _GENERIC_READ = 0x80000000
    _GENERIC_WRITE = 0x40000000
    _OPEN_EXISTING = 3
    _PIPE_ACCESS_INBOUND = 0x00000001
    _PIPE_ACCESS_OUTBOUND = 0x00000002
    _EXTENDED_STARTUPINFO_PRESENT = 0x00080000
    _PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
    _PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
    _S_OK = 0
    _STILL_ACTIVE = 259
    _WAIT_TIMEOUT = 0x00000102
    _INFINITE = 0xFFFFFFFF
    _CREATE_UNICODE_ENVIRONMENT = 0x00000400
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    # Integrity SID strings
    _LOW_INTEGRITY_SID = "S-1-16-4096"
    _SECURITY_CAPABILITY_INTERNET_CLIENT = 1

    # ── Win32 structures ─────────────────────────────────────────────
    class _COORD(Structure):
        _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

    class _SECURITY_ATTRIBUTES(Structure):
        _fields_ = [
            ("nLength", wintypes.DWORD),
            ("lpSecurityDescriptor", c_void_p),
            ("bInheritHandle", wintypes.BOOL),
        ]

    class _STARTUPINFOW(Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD),
            ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD),
            ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD),
            ("cbReserved2", wintypes.WORD),
            ("lpReserved2", c_void_p),
            ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE),
            ("hStdError", wintypes.HANDLE),
        ]

    class _STARTUPINFOEXW(Structure):
        _fields_ = [
            ("StartupInfo", _STARTUPINFOW),
            ("lpAttributeList", c_void_p),
        ]

    class _PROCESS_INFORMATION(Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
        ]

    class _SID_AND_ATTRIBUTES(Structure):
        _fields_ = [
            ("Sid", c_void_p),
            ("Attributes", wintypes.DWORD),
        ]

    class _SECURITY_CAPABILITIES(Structure):
        _fields_ = [
            ("AppContainerSid", c_void_p),
            ("Capabilities", POINTER(_SID_AND_ATTRIBUTES)),
            ("CapabilityCount", wintypes.DWORD),
            ("Reserved", wintypes.DWORD),
        ]

    # ── Kernel32 / Advapi32 function signatures ──────────────────────
    _k32 = windll.kernel32
    _advapi32 = windll.advapi32

    _k32.CreatePipe.argtypes = [
        POINTER(wintypes.HANDLE),
        POINTER(wintypes.HANDLE),
        POINTER(_SECURITY_ATTRIBUTES),
        wintypes.DWORD,
    ]
    _k32.CreatePipe.restype = wintypes.BOOL

    _k32.CreatePseudoConsole.argtypes = [
        _COORD,
        wintypes.HANDLE,
        wintypes.HANDLE,
        wintypes.DWORD,
        POINTER(c_void_p),
    ]
    _k32.CreatePseudoConsole.restype = ctypes.HRESULT

    _k32.ClosePseudoConsole.argtypes = [c_void_p]
    _k32.ClosePseudoConsole.restype = None

    _k32.ReadFile.argtypes = [
        wintypes.HANDLE,
        c_void_p,
        wintypes.DWORD,
        POINTER(wintypes.DWORD),
        c_void_p,
    ]
    _k32.ReadFile.restype = wintypes.BOOL

    _k32.WriteFile.argtypes = [
        wintypes.HANDLE,
        c_void_p,
        wintypes.DWORD,
        POINTER(wintypes.DWORD),
        c_void_p,
    ]
    _k32.WriteFile.restype = wintypes.BOOL

    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.CloseHandle.restype = wintypes.BOOL

    _k32.PeekNamedPipe.argtypes = [
        wintypes.HANDLE,
        c_void_p,
        wintypes.DWORD,
        POINTER(wintypes.DWORD),
        POINTER(wintypes.DWORD),
        POINTER(wintypes.DWORD),
    ]
    _k32.PeekNamedPipe.restype = wintypes.BOOL

    _k32.InitializeProcThreadAttributeList.argtypes = [
        c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        POINTER(c_size_t),
    ]
    _k32.InitializeProcThreadAttributeList.restype = wintypes.BOOL

    _k32.UpdateProcThreadAttribute.argtypes = [
        c_void_p,
        wintypes.DWORD,
        ctypes.c_uint64,
        c_void_p,
        c_size_t,
        c_void_p,
        c_void_p,
    ]
    _k32.UpdateProcThreadAttribute.restype = wintypes.BOOL

    _k32.DeleteProcThreadAttributeList.argtypes = [c_void_p]
    _k32.DeleteProcThreadAttributeList.restype = None

    _k32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        c_void_p,
        c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        c_void_p,
        wintypes.LPCWSTR,
        POINTER(_STARTUPINFOEXW),
        POINTER(_PROCESS_INFORMATION),
    ]
    _k32.CreateProcessW.restype = wintypes.BOOL

    _k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.TerminateProcess.restype = wintypes.BOOL

    _k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    _k32.WaitForSingleObject.restype = wintypes.DWORD

    _k32.GetExitCodeProcess.argtypes = [
        wintypes.HANDLE,
        POINTER(wintypes.DWORD),
    ]
    _k32.GetExitCodeProcess.restype = wintypes.BOOL

    _advapi32.ConvertStringSidToSidW.argtypes = [
        wintypes.LPCWSTR,
        POINTER(c_void_p),
    ]
    _advapi32.ConvertStringSidToSidW.restype = wintypes.BOOL

    _advapi32.CreateWellKnownSid.argtypes = [
        wintypes.DWORD,
        c_void_p,
        c_void_p,
        POINTER(wintypes.DWORD),
    ]
    _advapi32.CreateWellKnownSid.restype = wintypes.BOOL

    _k32.LocalFree.argtypes = [c_void_p]
    _k32.LocalFree.restype = c_void_p

    # ── Helper: create an inheritable pipe pair ──────────────────────
    def _create_pipe() -> tuple[wintypes.HANDLE, wintypes.HANDLE]:
        """Create an anonymous pipe and return (read_handle, write_handle)."""
        sa = _SECURITY_ATTRIBUTES()
        sa.nLength = sizeof(sa)
        sa.lpSecurityDescriptor = None
        sa.bInheritHandle = True
        read_h = wintypes.HANDLE()
        write_h = wintypes.HANDLE()
        if not _k32.CreatePipe(byref(read_h), byref(write_h), byref(sa), 0):
            raise OSError(f"CreatePipe failed: {ctypes.GetLastError()}")
        return read_h, write_h

    # ── WindowsAgentPTY ──────────────────────────────────────────────
    class WindowsAgentPTY:
        """Windows ConPTY-backed pseudo-console boundary for one agent.

        Mirrors the POSIX ``AgentPTY`` interface:
        ``read_output``, ``write_input``, context-manager, and
        ``TerminalSanitizer`` integration.
        """

        def __init__(self, agent_id: str, sanitize: bool = True,
                     cols: int = 120, rows: int = 30):
            self.agent_id = agent_id
            self.sanitize = sanitize
            self.sanitizer = TerminalSanitizer()
            self._lock = threading.Lock()
            self._closed = False

            # Pipes: host reads from pty_out_read, writes to pty_in_write.
            # ConPTY reads from pty_in_read, writes to pty_out_write.
            self._pty_in_read, self._pty_in_write = _create_pipe()
            self._pty_out_read, self._pty_out_write = _create_pipe()

            # Create the pseudo-console
            size = _COORD(X=cols, Y=rows)
            self._hpc = c_void_p()
            hr = _k32.CreatePseudoConsole(
                size,
                self._pty_in_read,
                self._pty_out_write,
                wintypes.DWORD(0),
                byref(self._hpc),
            )
            if hr != _S_OK:
                self._cleanup_pipes()
                raise OSError(
                    f"CreatePseudoConsole failed for {agent_id}: "
                    f"HRESULT 0x{hr & 0xFFFFFFFF:08X}"
                )

        # ── Pipe I/O ─────────────────────────────────────────────────

        def read_output(self, timeout: float = 1.0) -> str:
            """Read available output from the ConPTY, sanitising if enabled."""
            if self._closed:
                raise RuntimeError(f"PTY for {self.agent_id} is closed")

            buf_size = 4096
            buf = ctypes.create_string_buffer(buf_size)
            collected = b""

            # Wait-loop using PeekNamedPipe + deadline
            import time
            deadline = time.monotonic() + timeout

            while time.monotonic() < deadline:
                avail = wintypes.DWORD(0)
                ok = _k32.PeekNamedPipe(
                    self._pty_out_read, None, 0, None, byref(avail), None,
                )
                if not ok or avail.value == 0:
                    # Nothing available yet — brief sleep and retry
                    time.sleep(0.01)
                    continue

                read_bytes = wintypes.DWORD(0)
                to_read = min(avail.value, buf_size)
                ok = _k32.ReadFile(
                    self._pty_out_read, buf, to_read,
                    byref(read_bytes), None,
                )
                if not ok or read_bytes.value == 0:
                    break
                collected += buf.raw[: read_bytes.value]

            text = collected.decode("utf-8", errors="replace")
            if self.sanitize:
                text = self.sanitizer.sanitize(text)
            return text

        def write_input(self, data: str) -> None:
            """Write data into the ConPTY input pipe."""
            if self._closed:
                raise RuntimeError(f"PTY for {self.agent_id} is closed")

            if self.sanitize:
                data = self.sanitizer.sanitize(data)

            encoded = data.encode("utf-8")
            written = wintypes.DWORD(0)
            with self._lock:
                ok = _k32.WriteFile(
                    self._pty_in_write, encoded, len(encoded),
                    byref(written), None,
                )
                if not ok:
                    raise OSError(
                        f"WriteFile failed for {self.agent_id}: "
                        f"{ctypes.GetLastError()}"
                    )

        # ── Lifecycle ────────────────────────────────────────────────

        def close(self) -> None:
            """Tear down the ConPTY and all pipe handles."""
            with self._lock:
                if self._closed:
                    return
                self._closed = True
                if self._hpc:
                    _k32.ClosePseudoConsole(self._hpc)
                    self._hpc = c_void_p()
                self._cleanup_pipes()

        def _cleanup_pipes(self) -> None:
            for h in (
                self._pty_in_read,
                self._pty_in_write,
                self._pty_out_read,
                self._pty_out_write,
            ):
                if h and getattr(h, "value", None):
                    try:
                        _k32.CloseHandle(h)
                    except OSError:
                        pass

        @property
        def is_closed(self) -> bool:
            return self._closed

        @property
        def console_handle(self) -> c_void_p:
            """Return the raw HPCON for attaching to ``CreateProcessW``."""
            if self._closed:
                raise RuntimeError(f"PTY for {self.agent_id} is closed")
            return self._hpc

        def __enter__(self) -> "WindowsAgentPTY":
            return self

        def __exit__(self, *args: object) -> None:
            self.close()

    # ── spawn_sandboxed_windows_process ──────────────────────────────

    class SandboxedProcess:
        """Handle wrapper returned by ``spawn_sandboxed_windows_process``."""

        def __init__(
            self,
            h_process: wintypes.HANDLE,
            h_thread: wintypes.HANDLE,
            pid: int,
            pty: WindowsAgentPTY,
            _attr_buf: ctypes.Array | None = None,
            _sid_buf: ctypes.Array | None = None,
            _sec_cap: "_SECURITY_CAPABILITIES | None" = None,
        ):
            self.h_process = h_process
            self.h_thread = h_thread
            self.pid = pid
            self.pty = pty
            # prevent GC of buffers used by the running process
            self._attr_buf = _attr_buf
            self._sid_buf = _sid_buf
            self._sec_cap = _sec_cap

        def is_running(self) -> bool:
            code = wintypes.DWORD()
            _k32.GetExitCodeProcess(self.h_process, byref(code))
            return code.value == _STILL_ACTIVE

        def wait(self, timeout_ms: int = _INFINITE) -> int:
            """Block until exit; return the exit code."""
            _k32.WaitForSingleObject(self.h_process, timeout_ms)
            code = wintypes.DWORD()
            _k32.GetExitCodeProcess(self.h_process, byref(code))
            return code.value

        def terminate(self, exit_code: int = 1) -> None:
            _k32.TerminateProcess(self.h_process, exit_code)

        def close(self) -> None:
            """Close process/thread handles and PTY."""
            _k32.CloseHandle(self.h_thread)
            _k32.CloseHandle(self.h_process)
            self.pty.close()

        def __enter__(self) -> "SandboxedProcess":
            return self

        def __exit__(self, *args: object) -> None:
            if self.is_running():
                self.terminate()
            self.close()

    def _create_appcontainer_sid() -> tuple[ctypes.Array, c_void_p]:
        """Allocate a low-integrity AppContainer SID via ConvertStringSidToSidW.

        Returns ``(sid_buffer, sid_pointer)`` — caller must keep
        ``sid_buffer`` alive for the lifetime of the process.
        """
        sid_ptr = c_void_p()
        ok = _advapi32.ConvertStringSidToSidW(
            _LOW_INTEGRITY_SID, byref(sid_ptr),
        )
        if not ok:
            raise OSError(
                f"ConvertStringSidToSidW failed: {ctypes.GetLastError()}"
            )
        # Copy the SID into a Python-owned buffer so we can LocalFree
        # the original and still keep a valid pointer.
        sid_len = 28  # max sub-authority-count SID (safe upper bound)
        buf = (ctypes.c_byte * sid_len)()
        ctypes.memmove(buf, sid_ptr, sid_len)
        _k32.LocalFree(sid_ptr)
        return buf, ctypes.cast(buf, c_void_p)

    def spawn_sandboxed_windows_process(
        command_line: str,
        agent_id: str = "sandboxed",
        *,
        sanitize: bool = True,
        cols: int = 120,
        rows: int = 30,
        block_loopback: bool = True,
    ) -> SandboxedProcess:
        """Launch *command_line* in a ConPTY with an AppContainer token.

        Parameters
        ----------
        command_line:
            Full command string, e.g. ``"cmd.exe /c echo hello"``.
        agent_id:
            Identifier forwarded to ``WindowsAgentPTY``.
        sanitize:
            Whether the PTY should strip ANSI escapes.
        cols, rows:
            Console dimensions.
        block_loopback:
            If ``True``, the AppContainer has **no** network capabilities,
            which also blocks loopback (localhost) access.

        Returns
        -------
        SandboxedProcess
            Context-manager wrapping the process handle, PID, and PTY.
        """
        # 1. PTY
        agent_pty = WindowsAgentPTY(agent_id, sanitize=sanitize,
                                     cols=cols, rows=rows)

        # 2. AppContainer SID (low-integrity)
        sid_buf, sid_ptr = _create_appcontainer_sid()

        # 3. Security capabilities — empty caps = no network at all
        sec_cap = _SECURITY_CAPABILITIES()
        sec_cap.AppContainerSid = sid_ptr
        sec_cap.Capabilities = None
        sec_cap.CapabilityCount = 0
        sec_cap.Reserved = 0

        # 4. Build a PROC_THREAD_ATTRIBUTE_LIST with 2 attributes:
        #    - PSEUDOCONSOLE (to attach our ConPTY)
        #    - SECURITY_CAPABILITIES (for the AppContainer)
        attr_count = 2
        attr_size = c_size_t(0)
        _k32.InitializeProcThreadAttributeList(
            None, attr_count, 0, byref(attr_size),
        )
        attr_buf = (ctypes.c_byte * attr_size.value)()
        attr_list_ptr = ctypes.cast(attr_buf, c_void_p)

        if not _k32.InitializeProcThreadAttributeList(
            attr_list_ptr, attr_count, 0, byref(attr_size),
        ):
            agent_pty.close()
            raise OSError(
                "InitializeProcThreadAttributeList failed: "
                f"{ctypes.GetLastError()}"
            )

        # 4a. Attach ConPTY
        if not _k32.UpdateProcThreadAttribute(
            attr_list_ptr,
            0,
            _PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
            agent_pty.console_handle,
            sizeof(c_void_p),
            None,
            None,
        ):
            _k32.DeleteProcThreadAttributeList(attr_list_ptr)
            agent_pty.close()
            raise OSError(
                "UpdateProcThreadAttribute (PSEUDOCONSOLE) failed: "
                f"{ctypes.GetLastError()}"
            )

        # 4b. Attach AppContainer security capabilities
        if not _k32.UpdateProcThreadAttribute(
            attr_list_ptr,
            0,
            _PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
            byref(sec_cap),
            sizeof(sec_cap),
            None,
            None,
        ):
            _k32.DeleteProcThreadAttributeList(attr_list_ptr)
            agent_pty.close()
            raise OSError(
                "UpdateProcThreadAttribute (SECURITY_CAPABILITIES) "
                f"failed: {ctypes.GetLastError()}"
            )

        # 5. STARTUPINFOEXW
        si_ex = _STARTUPINFOEXW()
        si_ex.StartupInfo.cb = sizeof(si_ex)
        si_ex.lpAttributeList = attr_list_ptr

        # 6. Create the process
        pi = _PROCESS_INFORMATION()
        creation_flags = _EXTENDED_STARTUPINFO_PRESENT

        cmd_buf = ctypes.create_unicode_buffer(command_line)

        ok = _k32.CreateProcessW(
            None,                       # lpApplicationName
            cmd_buf,                    # lpCommandLine
            None,                       # lpProcessAttributes
            None,                       # lpThreadAttributes
            False,                      # bInheritHandles
            creation_flags,             # dwCreationFlags
            None,                       # lpEnvironment
            None,                       # lpCurrentDirectory
            byref(si_ex),               # lpStartupInfo
            byref(pi),                  # lpProcessInformation
        )

        _k32.DeleteProcThreadAttributeList(attr_list_ptr)

        if not ok:
            agent_pty.close()
            raise OSError(
                f"CreateProcessW failed: {ctypes.GetLastError()}"
            )

        return SandboxedProcess(
            h_process=pi.hProcess,
            h_thread=pi.hThread,
            pid=pi.dwProcessId,
            pty=agent_pty,
            _attr_buf=attr_buf,
            _sid_buf=sid_buf,
            _sec_cap=sec_cap,
        )


class VerifiableOutput:
    """SHA-256/HMAC content integrity envelope for inter-agent messages."""

    def __init__(self, content: str, source: str = "", target: str = ""):
        self.content = content
        self.source = source
        self.target = target
        self.content_hash = self._compute_hash(content)
        self.signature: str | None = None

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def sign(self, signing_key: str = "") -> None:
        import hmac

        self._signing_key = signing_key
        self.signature = hmac.new(
            signing_key.encode("utf-8"),
            self.content_hash.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def verify(self, signing_key: str | None = None) -> bool:
        import hmac

        computed = self._compute_hash(self.content)
        if computed != self.content_hash:
            return False
        if self.signature is None:
            return False
        key = signing_key if signing_key is not None else getattr(self, "_signing_key", None)
        if key is None:
            return False
        expected = hmac.new(key.encode("utf-8"), self.content_hash.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, self.signature)

    def verify_chain(self, other: "VerifiableOutput", signing_key: str | None = None) -> bool:
        return self.verify(signing_key) and other.verify(signing_key)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "content": self.content,
            "source": self.source,
            "target": self.target,
            "content_hash": self.content_hash,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "VerifiableOutput":
        obj = cls(data["content"], data.get("source", ""), data.get("target", ""))
        obj.content_hash = data["content_hash"]
        obj.signature = data.get("signature")
        return obj
