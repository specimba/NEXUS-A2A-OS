"""NEXUSCLAW structured error hierarchy.

Every error carries structured metadata for consistent handling,
logging, and recovery across the CLAW ecosystem.
"""

from __future__ import annotations

from typing import Any


class ClawError(Exception):
    """Base for all NEXUSCLAW errors."""

    def __init__(self, message: str = "", **context: Any) -> None:
        self.context = context
        super().__init__(message)

    @property
    def message(self) -> str:
        return str(self.args[0]) if self.args else ""


class SubprocessError(ClawError):
    """A subprocess exited with a non-zero return code."""

    def __init__(
        self,
        message: str = "",
        *,
        command: str = "",
        stderr: str = "",
        stdout: str = "",
        returncode: int = -1,
        **context: Any,
    ) -> None:
        context.setdefault("command", command)
        context.setdefault("stderr", stderr)
        context.setdefault("stdout", stdout)
        context.setdefault("returncode", returncode)
        super().__init__(message, **context)


class SubprocessTimeoutError(SubprocessError):
    """A subprocess exceeded its configured timeout."""

    def __init__(
        self,
        message: str = "",
        *,
        timeout: float = 0.0,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("timeout", timeout)
        super().__init__(message, **kwargs)


class CLINotFoundError(SubprocessError):
    """The requested CLI binary was not found on the system PATH."""


class ParseError(ClawError):
    """Output from a tool or subprocess could not be parsed."""


class RetryableError(ClawError):
    """A transient failure that MAY be retried with back-off.

    Typically wraps HTTP 429 (Too Many Requests) or 503 (Service Unavailable).
    """

    def __init__(
        self,
        message: str = "",
        *,
        http_status: int = 0,
        retry_after: float | None = None,
        **context: Any,
    ) -> None:
        context.setdefault("http_status", http_status)
        context.setdefault("retry_after", retry_after)
        super().__init__(message, **context)


class PolicyError(ClawError):
    """Base for policy enforcement failures."""


class PolicyDeniedError(PolicyError):
    """An action was blocked by an active network / filesystem policy."""


class PolicyNotApprovedError(PolicyError):
    """An action requires human approval and has not yet been approved."""


class ConfigIntegrityError(ClawError):
    """A configuration file hash does not match its pinned value."""


class SecretDetectedError(ClawError):
    """A secret was detected in data being written, and the write was blocked."""


class LockError(ClawError):
    """A write-lock could not be acquired within the configured timeout."""


class UnsupportedAgentError(ClawError):
    """The requested agent CLI or runtime is not recognised."""
