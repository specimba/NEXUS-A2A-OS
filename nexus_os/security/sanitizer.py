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
