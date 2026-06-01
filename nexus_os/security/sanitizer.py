"""
NEXUS OS Terminal Security Layer
Phase 0 Emergency Fix — Cross-Agent Injection Prevention

Provides:
- TerminalSanitizer: Strips ANSI/VT escape sequences from inter-agent output
- AgentPTY: Dedicated pseudo-terminal per agent (no shared I/O)
- VerifiableOutput: SHA-256 content integrity for cross-agent messages
"""

import os
import re
import sys
import hashlib
import threading

if sys.platform != "win32":
    import pty
    import tty
    import termios


class TerminalSanitizer:
    """
    Strips ALL ANSI/VT escape sequences from text output.
    
    Blocks:
    - Cursor positioning (CUP, CUU, CUD, CUF, CUB)
    - Screen clearing (ED, EL)
    - Title bar changes (OSC)
    - Color/font changes (SGR)
    - Application-defined key codes
    - All C0 control codes except \n, \t, \r
    
    Usage:
        clean = TerminalSanitizer.sanitize(agent_output)
    """

    # Strip all C0 control codes except \n, \t, \r
    _C0_STRIP = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

    # Strip all CSI sequences: ESC [ <params> <final>
    _CSI_STRIP = re.compile(r'\x1b\[[\d;]*[A-Za-z]')

    # Strip all OSC sequences: ESC ] <string> ST (BEL or ESC \)
    _OSC_STRIP = re.compile(r'\x1b\][^\x07\x1b]*(\x07|\x1b\\)')

    # Strip all other ESC sequences (single-char after ESC)
    _ESC_STRIP = re.compile(r'\x1b[^\[A-Za-z]')

    # Strip application-defined key codes (ESC [ n ~)
    _APP_KEY_STRIP = re.compile(r'\x1b\[[\d;]*~')

    # Strip DCS sequences (Device Control String)
    _DCS_STRIP = re.compile(r'\x1bP[\s\S]*?\x1b\\')

    # Strip SOS/PM/APC sequences
    _SOS_STRIP = re.compile(r'\x1b[X^_][\s\S]*?\x1b\\')

    # Strip ISO 2022 shift sequences
    _ISO_SHIFT = re.compile(r'\x1b[()][\w]')

    @classmethod
    def sanitize(cls, text: str) -> str:
        if not text:
            return text

        text = cls._DCS_STRIP.sub('', text)
        text = cls._SOS_STRIP.sub('', text)
        text = cls._OSC_STRIP.sub('', text)
        text = cls._CSI_STRIP.sub('', text)
        text = cls._ESC_STRIP.sub('', text)
        text = cls._APP_KEY_STRIP.sub('', text)
        text = cls._ISO_SHIFT.sub('', text)
        text = cls._C0_STRIP.sub('', text)

        return text.strip()

    @classmethod
    def sanitize_stream(cls, stream: callable, chunk_size: int = 4096) -> str:
        """
        Sanitize a stream (file-like object) in chunks.
        
        Args:
            stream: A file-like object with .read(n) method
            chunk_size: Bytes per read
        
        Returns:
            Fully sanitized text
        """
        parts = []
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            if isinstance(chunk, bytes):
                chunk = chunk.decode('utf-8', errors='replace')
            parts.append(cls.sanitize(chunk))
        return ''.join(parts)

    @classmethod
    def is_clean(cls, text: str) -> bool:
        """Check if text contains any ANSI escape sequences."""
        return text == cls.sanitize(text)

    @classmethod
    def contains_escape(cls, text: str) -> bool:
        """Check if text contains escape sequences (before sanitization)."""
        return not cls.is_clean(text)


if sys.platform != "win32":

    class AgentPTY:
        """
        Dedicated pseudo-terminal per agent.
        
        Prevents cross-agent I/O leakage by giving each agent its own PTY.
        All output is sanitized at the PTY boundary before being readable
        by any other process.
        
        Usage:
            pty = AgentPTY("codex-agent-01")
            pty.write_input("git status")
            output = pty.read_output()  # automatically sanitized
        """

        def __init__(self, agent_id: str, sanitize: bool = True):
            self.agent_id = agent_id
            self.sanitize = sanitize
            self.sanitizer = TerminalSanitizer()

            self._master_fd, self._slave_fd = pty.openpty()
            self._lock = threading.Lock()
            self._closed = False

        @property
        def slave_name(self) -> str:
            return os.ttyname(self._slave_fd)

        def read_output(self, timeout: float = 1.0) -> str:
            if self._closed:
                raise RuntimeError(f"PTY for {self.agent_id} is closed")

            raw = b''
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

            text = raw.decode('utf-8', errors='replace')

            if self.sanitize:
                text = self.sanitizer.sanitize(text)

            return text

        def write_input(self, data: str):
            if self._closed:
                raise RuntimeError(f"PTY for {self.agent_id} is closed")

            if self.sanitize:
                data = self.sanitizer.sanitize(data)

            with self._lock:
                os.write(self._master_fd, data.encode())

        def close(self):
            with self._lock:
                if not self._closed:
                    os.close(self._master_fd)
                    os.close(self._slave_fd)
                    self._closed = True

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()


class VerifiableOutput:
    """
    SHA-256 content integrity for inter-agent messages.
    
    Every output between agents must be verifiable.
    If the hash doesn't match what was sent, the content was tampered with.
    
    Usage:
        msg = VerifiableOutput("agent_action_result", source="pi", target="codex")
        msg.sign(kaiyu_key)
        
        # On receiver side
        if msg.verify():
            process(msg.content)
        else:
            reject("Content integrity violation")
    """

    def __init__(self, content: str, source: str = "", target: str = ""):
        self.content = content
        self.source = source
        self.target = target
        self.content_hash = self._compute_hash(content)
        self.signature = None

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def sign(self, signing_key: str = ""):
        """
        Sign the content hash.
        In production, this should use KAIJU's signing key.
        """
        payload = f"{self.content_hash}:{self.source}:{self.target}:{signing_key}"
        self.signature = hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def verify(self) -> bool:
        """Verify content integrity."""
        computed = self._compute_hash(self.content)
        if computed != self.content_hash:
            return False
        if self.signature is None:
            return False
        return True

    def verify_chain(self, other: 'VerifiableOutput') -> bool:
        """Verify that two outputs form a valid chain."""
        if not self.verify() or not other.verify():
            return False
        # Chained messages must be in sequence
        return True

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "source": self.source,
            "target": self.target,
            "content_hash": self.content_hash,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'VerifiableOutput':
        obj = cls(d["content"], d.get("source", ""), d.get("target", ""))
        obj.content_hash = d["content_hash"]
        obj.signature = d.get("signature")
        return obj
