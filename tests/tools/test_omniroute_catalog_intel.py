"""Claim gates for the opt-in OmniRoute catalogue-intelligence adapter."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from tools.frontier_scanner.signals.omniroute_catalog import (
    OFFICIAL_OMNIROUTE_REPOSITORY,
    AdapterDisabledError,
    ProvenanceError,
    build_source_card_bundle,
)
from tools.frontier_scanner.orchestrator import main


FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "frontier_scanner"
    / "omniroute_snapshot"
)
PINNED_VERSION = "3.8.46"
PINNED_COMMIT = "9cd18bf9a11b7d2e8c037c374631b492adabf469"


def _manifest_path(root: Path = FIXTURE_ROOT) -> Path:
    return root / "nexus-omniroute-snapshot.json"


def _build(root: Path = FIXTURE_ROOT) -> dict:
    return build_source_card_bundle(
        source_root=root,
        expected_version=PINNED_VERSION,
        expected_commit=PINNED_COMMIT,
        provenance_manifest=_manifest_path(root),
        enabled=True,
    )


def test_adapter_is_disabled_before_any_source_access(tmp_path: Path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises(AdapterDisabledError, match="disabled by default"):
        build_source_card_bundle(
            source_root=missing,
            expected_version=PINNED_VERSION,
            expected_commit=PINNED_COMMIT,
        )


def test_pinned_snapshot_emits_namespaced_quarantined_source_cards_only():
    bundle = _build()

    assert bundle["kind"] == "nexus.catalogue_intelligence.source_cards"
    assert bundle["source"]["repository"] == OFFICIAL_OMNIROUTE_REPOSITORY
    assert bundle["source"]["version"] == PINNED_VERSION
    assert bundle["source"]["commit"] == PINNED_COMMIT
    assert len(bundle["source"]["snapshot_sha256"]) == 64
    assert bundle["source"]["commit_verification"] == "detached_manifest"
    assert bundle["policy"] == {
        "adapter_enabled_by_default": False,
        "candidate_only": True,
        "network_access": False,
        "provider_traffic": False,
        "registry_auto_promotion": False,
    }

    cards = bundle["source_cards"]
    assert bundle["summary"]["provider_candidate_count"] == 4
    assert [card["provider_id"] for card in cards] == [
        "github",
        "nvidia",
        "opencode",
        "prepaid",
    ]
    assert all(card["namespace"] == bundle["namespace"] for card in cards)
    assert all(card["candidate_id"].startswith(bundle["namespace"] + "::provider::") for card in cards)
    assert all(card["admission_class"] == "source_card_candidate" for card in cards)
    assert all(card["lifecycle"] == "quarantined" for card in cards)
    assert all(card["promotion_allowed"] is False for card in cards)
    assert all(card["snapshot_sha256"] == bundle["source"]["snapshot_sha256"] for card in cards)

    nvidia = next(card for card in cards if card["provider_id"] == "nvidia")
    assert nvidia["observations"]["provider_id"]["verification"] == "source_observed"
    assert nvidia["claims"]["has_free"] == {
        "value": True,
        "verification": "unverified_upstream_claim",
    }
    assert nvidia["claims"]["free_note"]["verification"] == "unverified_upstream_claim"
    assert nvidia["claims"]["name"]["verification"] == "unverified_upstream_claim"
    assert nvidia["claims"]["website"]["verification"] == "unverified_upstream_claim"


def test_adapter_does_not_touch_registry_or_open_network(monkeypatch):
    registry = Path(__file__).resolve().parents[2] / "config" / "models.registry.json"
    before = hashlib.sha256(registry.read_bytes()).hexdigest()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr("socket.create_connection", forbidden)
    bundle = _build()

    assert bundle["summary"]["provider_candidate_count"] == 4
    assert hashlib.sha256(registry.read_bytes()).hexdigest() == before


@pytest.mark.parametrize(
    ("version", "commit", "message"),
    [
        ("3.8.45", PINNED_COMMIT, "version mismatch"),
        (PINNED_VERSION, "0" * 40, "commit mismatch"),
    ],
)
def test_provenance_pin_mismatch_fails_closed(version: str, commit: str, message: str):
    with pytest.raises(ProvenanceError, match=message):
        build_source_card_bundle(
            source_root=FIXTURE_ROOT,
            expected_version=version,
            expected_commit=commit,
            provenance_manifest=_manifest_path(),
            enabled=True,
        )


def test_snapshot_hash_mismatch_fails_closed(tmp_path: Path):
    copied = tmp_path / "snapshot"
    shutil.copytree(FIXTURE_ROOT, copied)
    provider_file = copied / "src" / "shared" / "constants" / "providers" / "noauth.ts"
    provider_file.write_text(provider_file.read_text(encoding="utf-8") + "\n// tampered\n", encoding="utf-8")

    with pytest.raises(ProvenanceError, match="snapshot hash mismatch"):
        _build(copied)


def test_cli_requires_explicit_enable_and_emits_only_requested_artifact(tmp_path: Path, capsys):
    output = tmp_path / "candidates.json"
    common = [
        "--state-dir",
        str(tmp_path / "unused-state"),
        "omniroute-intel",
        "--source-root",
        str(FIXTURE_ROOT),
        "--expected-version",
        PINNED_VERSION,
        "--expected-commit",
        PINNED_COMMIT,
        "--provenance-manifest",
        str(_manifest_path()),
        "--emit-json",
        str(output),
    ]

    assert main(common) == 2
    assert not output.exists()
    assert "disabled by default" in capsys.readouterr().err

    assert main(common + ["--enable-omniroute-intel"]) == 0
    emitted = json.loads(output.read_text(encoding="utf-8"))
    assert emitted["policy"]["registry_auto_promotion"] is False
    assert emitted["summary"]["provider_candidate_count"] == 4
    assert not (tmp_path / "unused-state").exists()
