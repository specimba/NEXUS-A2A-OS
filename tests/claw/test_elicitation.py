"""tests/claw/test_elicitation.py — Elicitation guard tests."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from nexus_os.claw.elicitation import (
    ElicitationGuard,
    elicit_cli_selection,
    elicit_confirmation,
    elicit_model_selection,
    suppress_all,
)


async def _fake_elicit_ok(prompt: str, options: list[str] | None = None) -> str:
    if options:
        return options[0]
    return "elaborated details"


async def _fake_elicit_second(prompt: str, options: list[str] | None = None) -> str:
    if options and len(options) > 1:
        return options[1]
    return "user said no"


async def _fake_elicit_fail(*args: object, **kwargs: object) -> str:
    msg = "Elicitation not supported"
    raise Exception(msg)


class TestElicitation:
    @pytest.mark.asyncio
    async def test_elicit_cli_selected(self) -> None:
        guard = ElicitationGuard()
        guard.reset()
        result = await elicit_cli_selection(
            _fake_elicit_ok, ["docker", "kubectl"], suppress_flag="test_cli"
        )
        assert result == "docker"

    @pytest.mark.asyncio
    async def test_elicit_cli_fallback(self) -> None:
        guard = ElicitationGuard()
        guard.reset()
        result = await elicit_cli_selection(
            _fake_elicit_fail, ["docker", "kubectl"], suppress_flag="test_cli_fail"
        )
        assert result == "docker"

    @pytest.mark.asyncio
    async def test_elicit_model_selection(self) -> None:
        guard = ElicitationGuard()
        guard.reset()
        result = await elicit_model_selection(
            _fake_elicit_second, ["gpt-4o", "claude-opus"], suppress_flag="test_model"
        )
        assert result == "claude-opus"

    @pytest.mark.asyncio
    async def test_elicit_confirmation_accepted(self) -> None:
        guard = ElicitationGuard()
        guard.reset()
        result = await elicit_confirmation(
            _fake_elicit_ok, "Proceed?", suppress_flag="test_confirm_yes"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_elicit_confirmation_declined(self) -> None:
        guard = ElicitationGuard()
        guard.reset()
        result = await elicit_confirmation(
            _fake_elicit_second, "Proceed?", suppress_flag="test_confirm_no"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_elicit_suppression_flag(self) -> None:
        guard = ElicitationGuard.instance()
        guard.reset()
        guard.suppress("elicit_cli")
        result = await elicit_cli_selection(
            _fake_elicit_second, ["docker", "kubectl"], suppress_flag="elicit_cli"
        )
        guard.reset()
        assert result == "docker"

    @pytest.mark.asyncio
    async def test_elicit_disabled(self) -> None:
        guard = ElicitationGuard()
        guard.reset()
        suppress_all()
        result = await elicit_model_selection(
            _fake_elicit_second, ["gpt-4o", "claude-opus"], suppress_flag="elicit_model"
        )
        assert result == "gpt-4o"

    @pytest.mark.asyncio
    async def test_elicit_vague_prompt_elaborated(self) -> None:
        from nexus_os.claw.elicitation import elicit_vague_prompt

        guard = ElicitationGuard()
        guard.reset()
        result = await elicit_vague_prompt(_fake_elicit_ok, "run it", suppress_flag="test_vague")
        assert result == "elaborated details"

    @pytest.mark.asyncio
    async def test_elicit_vague_fallback(self) -> None:
        from nexus_os.claw.elicitation import elicit_vague_prompt

        guard = ElicitationGuard()
        guard.reset()
        result = await elicit_vague_prompt(_fake_elicit_fail, "run it", suppress_flag="test_vague_fail")
        assert result == "run it"


if __name__ == "__main__":
    pytest.main([__file__])
