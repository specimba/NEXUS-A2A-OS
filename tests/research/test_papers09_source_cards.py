from __future__ import annotations

from pathlib import Path

import pytest

from nexus_os.research.papers09_source_cards import (
    PAPERS10_PRIORITY_TITLES,
    PAPERS12_13_PRIORITY_TITLES,
    create_backlog_cards,
    create_draft_card,
    create_promoted_card_from_body,
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


def test_papers10_titles_are_in_priority_backlog(tmp_path: Path):
    assert "Fugu" in " ".join(PAPERS10_PRIORITY_TITLES)

    (tmp_path / "Fugu technical report for agentic systems.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "Unrelated paper.pdf").write_text("x", encoding="utf-8")

    cards = create_backlog_cards(tmp_path)

    assert [Path(card.source_path).name for card in cards] == ["Fugu technical report for agentic systems.pdf"]
    assert cards[0].target_lane == "free_cloud_model_relay"
    assert cards[0].evidence_grade == "E0"
    assert cards[0].promotable is False


def test_body_read_promotion_records_e1_claim_and_hash(tmp_path: Path):
    paper = tmp_path / "GLM-5 from Vibe Coding to Agentic Engineering.pdf"
    paper.write_text("fixture", encoding="utf-8")
    body = (
        "This paper reports long-horizon agentic coding behavior, repository-scale "
        "planning, and verification-oriented development loops for GLM-5 style models."
    )

    card = create_promoted_card_from_body(paper, body_text=body)

    assert card.evidence_grade == "E1"
    assert card.promotable is True
    assert "long-horizon agentic coding" in card.body_claim
    assert card.sha256
    assert card.target_lane == "modal_teacher_probe"


def test_body_read_promotion_requires_actual_body_text(tmp_path: Path):
    paper = tmp_path / "SafeDecoding.pdf"
    paper.write_text("fixture", encoding="utf-8")

    with pytest.raises(ValueError):
        create_promoted_card_from_body(paper, body_text="too short")


def test_papers12_13_titles_are_in_priority_backlog(tmp_path: Path):
    assert "Antislop" in " ".join(PAPERS12_13_PRIORITY_TITLES)

    (tmp_path / "Antislop A Comprehensive Framework for Identifying and.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "Can Editing 1 Neuron Fix Repetition Loops in.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "Unrelated paper.pdf").write_text("x", encoding="utf-8")

    cards = create_backlog_cards(tmp_path)

    assert [Path(card.source_path).name for card in cards] == [
        "Antislop A Comprehensive Framework for Identifying and.pdf",
        "Can Editing 1 Neuron Fix Repetition Loops in.pdf",
    ]
    assert cards[0].target_lane == "model_quality_anti_slop"
    assert cards[1].target_lane == "decoding_repetition_control"
    assert all(card.evidence_grade == "E0" and not card.promotable for card in cards)

