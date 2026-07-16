"""Regression gates for the persisted NEXUS SAGE Custom GPT instructions."""

from __future__ import annotations

from pathlib import Path
import re


INSTRUCTIONS_PATH = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "sage"
    / "nexus_sage_v3_instructions.md"
)

BUILDER_HARD_LIMIT = 8_000
BUILDER_SAFETY_MARGIN = 100


def _instructions() -> str:
    return INSTRUCTIONS_PATH.read_text(encoding="utf-8")


def _section(document: str, title: str, *, level: int = 3) -> str:
    heading = "#" * level
    match = re.search(
        rf"(?ms)^{heading} {re.escape(title)}\s*\n"
        rf"(?P<body>.*?)(?=^#{{1,{level}}}\s|\Z)",
        document,
    )
    assert match is not None, f"missing SAGE instruction section: {title}"
    return " ".join(match.group("body").lower().split())


def _builder_character_count(document: str) -> int:
    """Match JavaScript textarea length by counting UTF-16 code units."""

    return len(document.encode("utf-16-le")) // 2


def test_instructions_fit_the_builder_limit_with_safety_margin() -> None:
    character_count = _builder_character_count(_instructions())

    assert character_count <= BUILDER_HARD_LIMIT
    assert character_count <= BUILDER_HARD_LIMIT - BUILDER_SAFETY_MARGIN


def test_current_nexus_requests_require_the_corresponding_sage_action() -> None:
    selection = _section(_instructions(), "Action selection rule")

    assert "when the operator asks for current nexus health" in selection
    assert "capabilities" in selection
    assert "grounding metadata" in selection
    assert "model-card evidence" in selection
    assert "sage receipt" in selection
    assert "use the corresponding allowlisted sage action" in selection


def test_current_runtime_evidence_cannot_be_substituted() -> None:
    selection = _section(_instructions(), "Action selection rule")

    assert re.search(
        r"do not substitute web search, browsing, uploaded knowledge,.*"
        r"for current nexus runtime evidence",
        selection,
    )


def test_action_failure_preserves_not_observed_typed_failure() -> None:
    selection = _section(_instructions(), "Action selection rule")

    assert "label the fields `not observed`" in selection
    assert "report the typed failure" in selection
    assert "never fabricate or silently switch evidence sources" in selection



def test_advisor_receipts_remain_root_supplied_and_non_authoritative() -> None:
    protocol_boundary = _section(_instructions(), "A2A, ACP, and memory", level=2)

    assert "root-supplied advice" in protocol_boundary
    assert "cannot invoke it" in protocol_boundary
    assert "authorize with it" in protocol_boundary


def test_action_boundary_forbids_disabled_capability_fallbacks() -> None:
    boundary = _section(_instructions(), "Action boundary", level=2)

    assert "no sage action permits shell/python execution" in boundary
    assert "generic http or urls" in boundary


def test_observe_only_forbids_proposal_job_submission() -> None:
    observe_only = _section(_instructions(), "Observe-only rule")

    assert "mode is `observe_only`" in observe_only
    assert "`proposal_writes_enabled=false`" in observe_only
    assert "do not call `post /jobs`" in observe_only
