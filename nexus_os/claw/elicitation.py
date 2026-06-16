"""Interactive parameter resolution (elicitation) for NEXUSCLAW.

Wraps the MCP ``ctx.elicit()`` protocol to prompt users for
disambiguation when task parameters are ambiguous.

Silently falls back to safe defaults when the client does not support
the elicit protocol.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ElicitationUnavailable(Exception):
    """The runtime does not support the elicit protocol."""


class ElicitationGuard:
    """Guards elicit operations with suppression flags.

    Each suppression flag, once set, prevents the corresponding prompt
    from being shown again in the same session.
    """

    _INSTANCE: ElicitationGuard | None = None

    def __init__(self) -> None:
        self._suppressed: set[str] = set()

    @classmethod
    def instance(cls) -> ElicitationGuard:
        if cls._INSTANCE is None:
            cls._INSTANCE = cls()
        return cls._INSTANCE

    def is_suppressed(self, flag: str) -> bool:
        return flag in self._suppressed

    def suppress(self, flag: str) -> None:
        self._suppressed.add(flag)

    def reset(self) -> None:
        self._suppressed.clear()


async def elicit_cli_selection(
    elicit_fn: Callable[..., Any],
    options: list[str],
    prompt: str = "Select a CLI tool to use:",
    *,
    suppress_flag: str = "elicit_cli",
) -> str:
    """Prompt the user to pick from a list of CLI options.

    Falls back to the first option if elicit is unavailable or suppressed.
    """
    guard = ElicitationGuard.instance()
    if guard.is_suppressed(suppress_flag):
        return options[0]

    try:
        result = await elicit_fn(prompt, options=options)
        if isinstance(result, str) and result in options:
            return result
        return options[0]
    except Exception:
        logger.debug("Elicitation unavailable, using default: %s", options[0])
        return options[0]


async def elicit_model_selection(
    elicit_fn: Callable[..., Any],
    models: list[str],
    prompt: str = "Select a model for this task:",
    *,
    suppress_flag: str = "elicit_model",
) -> str:
    """Prompt the user to select from available models."""
    guard = ElicitationGuard.instance()
    if guard.is_suppressed(suppress_flag):
        return models[0]

    try:
        result = await elicit_fn(prompt, options=models)
        if isinstance(result, str) and result in models:
            return result
        return models[0]
    except Exception:
        logger.debug("Elicitation unavailable, using default model: %s", models[0])
        return models[0]


async def elicit_confirmation(
    elicit_fn: Callable[..., Any],
    prompt: str,
    *,
    suppress_flag: str | None = None,
    default: bool = False,
) -> bool:
    """Prompt the user for a yes/no confirmation.

    Falls back to *default* if elicit is unavailable or suppressed.
    """
    if suppress_flag and ElicitationGuard.instance().is_suppressed(suppress_flag):
        return default

    try:
        result = await elicit_fn(prompt, options=["yes", "no"])
        return isinstance(result, str) and result.lower() == "yes"
    except Exception:
        logger.debug("Elicitation unavailable, using default=%s", default)
        return default


async def elicit_vague_prompt(
    elicit_fn: Callable[..., Any],
    original_prompt: str,
    *,
    suppress_flag: str = "elicit_vague",
) -> str:
    """Ask the user to elaborate on a vague or ambiguous prompt."""
    guard = ElicitationGuard.instance()
    if guard.is_suppressed(suppress_flag):
        return original_prompt

    try:
        elaborated = await elicit_fn(
            f"Your prompt seems brief: '{original_prompt}'. "
            "Please provide more detail or press Enter to continue as-is.",
            options=None,
        )
        if isinstance(elaborated, str) and elaborated.strip():
            return elaborated.strip()
        return original_prompt
    except Exception:
        return original_prompt


def suppress_all() -> None:
    """Suppress all elicitation prompts for the remainder of the session."""
    guard = ElicitationGuard.instance()
    for flag in ("elicit_cli", "elicit_model", "elicit_vague", "elicit_yolo", "elicit_high_retries"):
        guard.suppress(flag)
