"""tests/claw/test_policies.py — Policy validation and preset loading."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from nexus_os.claw.policies import PolicyValidationError, validate_policy
from nexus_os.claw.policies.presets import (
    list_presets,
    load_preset,
    sandbox_preset,
    github_preset,
    discord_preset,
    huggingface_preset,
)


def test_sandbox_preset_validates() -> None:
    doc = sandbox_preset()
    result = validate_policy(doc)
    assert result["version"] == 1


def test_github_preset_validates() -> None:
    doc = github_preset()
    result = validate_policy(doc)
    assert result["version"] == 1


def test_discord_preset_validates() -> None:
    doc = discord_preset()
    result = validate_policy(doc)
    assert result["version"] == 1


def test_all_presets_validate() -> None:
    for name in list_presets():
        doc = load_preset(name)
        result = validate_policy(doc)
        assert result["version"] >= 1, f"Preset {name} failed validation"


def test_preset_trust_levels() -> None:
    sandbox = sandbox_preset()
    assert sandbox["trust_level"] == "HARDWALL"
    github = github_preset()
    assert github["trust_level"] == "CAUTION"
    hf = huggingface_preset()
    assert hf["trust_level"] == "RESTRICTED"


def test_invalid_policy_schema_rejected() -> None:
    bad = {"version": "abc"}
    with pytest.raises(PolicyValidationError):
        validate_policy(bad)


def test_invalid_trust_level_rejected() -> None:
    bad = {"version": 1, "trust_level": "UNKNOWN"}
    with pytest.raises(PolicyValidationError):
        validate_policy(bad)


def test_missing_network_policy_fields() -> None:
    bad = {"version": 1, "network_policies": [{"name": "bad"}]}
    with pytest.raises(PolicyValidationError):
        validate_policy(bad)


def test_unknown_preset_raises() -> None:
    with pytest.raises(KeyError):
        load_preset("nonexistent")


def test_preset_registry_has_expected() -> None:
    presets = list_presets()
    assert "sandbox" in presets
    assert "github" in presets
    assert "discord" in presets
    assert "telegram" in presets
    assert "slack" in presets
    assert "huggingface" in presets
    assert "npm" in presets
    assert "pypi" in presets


if __name__ == "__main__":
    pytest.main([__file__])
