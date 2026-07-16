"""Claim gates for the non-operational local-router evaluation manifest."""

from __future__ import annotations

import json
from pathlib import Path


MANIFEST = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "plans"
    / "LOCAL_ROUTER_EVALUATION_MANIFEST_2026-07-15.json"
)


def _load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_is_shadow_only_and_has_no_automatic_side_effects():
    manifest = _load()

    assert manifest["kind"] == "nexus.local_router_evaluation_manifest"
    assert manifest["status"] == "evaluation_only"
    assert manifest["scope"] == {
        "purpose": "Shadow-evaluate a small local intent or tool-shape router without altering the active relay, registry, or client defaults.",
        "no_model_downloads_by_this_manifest": True,
        "registry_auto_registration": False,
        "relay_auto_routing": False,
        "promotion_requires_operator_approval": True,
    }
    assert manifest["router_contract"]["mode"] == "shadow_only"
    assert manifest["router_contract"]["side_effects"] == "prohibited"


def test_only_evidence_clearing_the_strict_artifact_cap_can_enter_verification():
    manifest = _load()
    limit = manifest["hard_limits"]["artifact_size_limit_mb"]
    candidates = {candidate["id"]: candidate for candidate in manifest["candidates"]}

    smollm = candidates["HuggingFaceTB/SmolLM2-360M-Instruct"]
    assert smollm["artifact_size_mb"] <= limit
    assert smollm["admission_status"] == "eligible_for_artifact_verification_only"
    assert smollm["source_evidence_strength"] == "medium_pinned_revision_required"

    functiongemma = candidates["google/functiongemma-270m-it"]
    assert functiongemma["artifact_size_mb"] is None
    assert functiongemma["admission_status"] == "requires_license_format_and_memory_measurement"
    assert functiongemma["source_evidence_strength"] == "high_official_documentation"

    qwen = candidates["Qwen/Qwen2.5-0.5B-Instruct"]
    assert qwen["artifact_size_mb"] > limit
    assert qwen["admission_status"].startswith("excluded_from_strict_500mb")
    assert qwen["source_evidence_strength"] == "high_official_model_card"

    assert all(candidate["operational_status"] == "not_verified_for_this_evaluation_not_routable" for candidate in candidates.values())


def test_manifest_requires_measurement_and_governed_promotion_gates():
    manifest = _load()
    required = set(manifest["router_contract"]["required_measurements"])
    assert {
        "artifact_filename_size_and_sha256",
        "cold_and_warm_peak_rss_mb",
        "valid_json_rate",
        "intent_macro_f1_and_per_class_recall",
        "false_allow_rate_for_malformed_unknown_and_low_confidence_outputs",
    } <= required
    assert manifest["router_contract"]["unknown_or_malformed_output"] == "BLOCKED"
    assert manifest["router_contract"]["minimum_confidence"] == 0.85
    assert any("operator approval" in gate for gate in manifest["promotion_gates"])
