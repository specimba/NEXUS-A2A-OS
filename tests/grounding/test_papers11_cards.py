from pathlib import Path

from nexus_os.grounding import papers


def test_body_derived_card_is_e1_and_frontier_claims_require_reconciliation(
    tmp_path: Path, monkeypatch
):
    path = tmp_path / "gpt-5-6-preview.pdf"
    path.write_bytes(b"%PDF-test")
    monkeypatch.setattr(
        papers,
        "_extract_body",
        lambda _path: ("Official body-derived evidence " * 10, None),
    )

    card = papers.build_paper_card(path, event_id="ge-card")

    assert card["evidence_grade"] == "E1"
    assert card["promotable"] is True
    assert card["source_type"] == "official_system_card"
    assert card["contradiction_status"] == "requires_primary_source_reconciliation"


def test_malformed_pdf_fails_closed_to_e0(tmp_path: Path):
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"not-a-pdf")

    card = papers.build_paper_card(path, event_id="ge-broken")

    assert card["evidence_grade"] == "E0"
    assert card["promotable"] is False
    assert card["body_claim"] == ""
    assert card["extraction_error"]
