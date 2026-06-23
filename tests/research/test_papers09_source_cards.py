from __future__ import annotations

from pathlib import Path

import pytest

from nexus_os.research.papers09_source_cards import (
    create_draft_card,
    iter_priority_paths,
    lane_for_title,
    promote_card,
)


def test_draft_card_is_not_promotable_without_body_claim(tmp_path: Path):
    paper = tmp_path / "VibeThinker-3B Exploring the Frontier.pdf"
    paper.write_bytes(b"%PDF-1.4 minimal fixture")

    card = create_draft_card(paper)

    assert card.evidence_grade == "E0"
    assert card.target_lane == "smart_math_coding"
    assert card.body_claim == ""
    assert card.promotable is False


def test_card_promotion_requires_body_claim(tmp_path: Path):
    paper = tmp_path / "FastContext Training Efficient Repository Explorer.pdf"
    paper.write_text("fixture", encoding="utf-8")
    card = create_draft_card(paper)

    with pytest.raises(ValueError):
        promote_card(card, body_claim="")

    promoted = promote_card(card, body_claim="The paper defines a read-only repository explorer subagent.")

    assert promoted.promotable is True
    assert promoted.evidence_grade == "E1"
    assert promoted.body_claim.startswith("The paper defines")


def test_lane_hints_cover_priority_models():
    assert lane_for_title("Nanbeige4.1-3B A Small General Model") == "small_model_probe"
    assert lane_for_title("SWE-LEGO PUSHING THE LIMITS") == "heavyskill_reviewer"
    assert lane_for_title("GUARD-SLM Token Activation-Based Defense") == "guard_bouncer"
    assert lane_for_title("AllMem A Memory-centric Recipe") == "vault_memory"


def test_priority_paths_are_deterministic(tmp_path: Path):
    (tmp_path / "Other.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "FastContext Training Efficient Repository Explorer.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "VibeThinker-3B Exploring the Frontier.pdf").write_text("x", encoding="utf-8")

    paths = list(iter_priority_paths(tmp_path))

    assert [path.name for path in paths] == [
        "VibeThinker-3B Exploring the Frontier.pdf",
        "FastContext Training Efficient Repository Explorer.pdf",
    ]
