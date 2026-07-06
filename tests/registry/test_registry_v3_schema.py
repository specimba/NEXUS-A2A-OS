"""FI-Q1 registry schema v3 validation.

Every provider must carry a structured quota block (windows / tokens /
metering / confidence / degradation) and an outputLicense; providerQuirks
entries must be well-formed. The trainability rule is fail-safe: unknown
NEVER resolves to permissive.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REGISTRY = json.loads(
    (REPO / "config" / "models.registry.json").read_text(encoding="utf-8")
)

CONFIDENCE = {"HIGH", "MEDIUM", "LOW", "CONFLICTED"}
DEGRADATION = {"hard_fail", "silent", "dynamic_throttle", "opaque"}
LICENSE_CLASSES = {"permissive", "restricted", "unknown"}
METERING = {"requests", "tokens", "neurons", "gpu_time", "credits"}
WINDOW_KEYS = {"rps", "rpm", "rph", "rpd"}
TOKEN_KEYS = {"tpm", "tph", "tpd", "monthly"}
QUIRK_KINDS = {
    "tool_calling_broken", "silent_degradation", "dollar_then_dead",
    "no_free_tier", "dynamic_throttle", "intermittent_hang", "silent_rename",
}


def test_registry_is_version_3():
    assert REGISTRY["version"] == 3


def test_every_provider_has_structured_quota():
    for slug, prov in REGISTRY["providers"].items():
        quota = prov.get("quota")
        assert isinstance(quota, dict), f"{slug}: missing quota block"
        assert set(quota["windows"]) == WINDOW_KEYS, f"{slug}: windows keys"
        assert set(quota["tokens"]) == TOKEN_KEYS, f"{slug}: tokens keys"
        assert quota["metering"] in METERING, f"{slug}: metering {quota['metering']}"
        assert quota["confidence"] in CONFIDENCE, f"{slug}: confidence"
        assert quota["degradation"] in DEGRADATION, f"{slug}: degradation"
        assert isinstance(quota["credit"], dict), f"{slug}: credit block"


def test_every_provider_has_output_license():
    for slug, prov in REGISTRY["providers"].items():
        lic = prov.get("outputLicense")
        assert isinstance(lic, dict) and lic.get("class") in LICENSE_CLASSES, (
            f"{slug}: outputLicense {lic}"
        )
        assert lic.get("basis"), f"{slug}: license needs a basis string"


def test_model_license_overrides_valid():
    for m in REGISTRY["models"]:
        lic = m.get("outputLicense")
        if lic is not None:
            assert lic.get("class") in LICENSE_CLASSES, f"{m['id']}: {lic}"


def test_provider_quirks_wellformed():
    quirks = REGISTRY.get("providerQuirks")
    assert isinstance(quirks, dict) and quirks, "providerQuirks missing"
    ids = []
    for slug, entries in quirks.items():
        assert slug in REGISTRY["providers"], f"quirk provider {slug} unknown"
        for e in entries:
            assert e["kind"] in QUIRK_KINDS, f"{slug}: quirk kind {e['kind']}"
            assert e["confidence"] in CONFIDENCE
            assert e.get("appliesTo") and e.get("action") and e.get("id")
            ids.append(e["id"])
    assert len(ids) == len(set(ids)), "duplicate quirk ids"
    # the two seed quirks the FI plan demanded are actually recorded
    assert "kimi26-nim-tool-calls" in ids
    assert "dollar-then-dead" in ids


def test_known_seed_facts_from_tariff_intel():
    provs = REGISTRY["providers"]
    assert provs["cerebras"]["quota"]["confidence"] == "CONFLICTED"
    assert provs["nvidia"]["quota"]["confidence"] == "MEDIUM"
    assert provs["moonshot"]["quota"]["credit"]["min_recharge_usd"] == 1.0
    assert provs["moonshot"]["quota"]["degradation"] == "dynamic_throttle"
    assert provs["cloudflare"]["quota"]["metering"] == "neurons"


# ── generated consumers ────────────────────────────────────────────────

def test_license_class_unknown_never_permissive():
    from nexus_os.relay.tracing.license_map_generated import license_class

    assert license_class("never-heard-of-it", "mystery/model") == "unknown"
    assert license_class("siliconflow", "zai-org/GLM-5.2") == "permissive"
    assert license_class("nvidia", "deepseek-ai/deepseek-v4-pro") == "permissive"
    assert license_class("googleai", "gemini-3.5-flash") == "restricted"


def test_quota_tracker_consumes_generated_table():
    import nexus_os.model_relay.quota_tracker as qt

    assert qt.KNOWN_QUOTAS, "derived KNOWN_QUOTAS is empty"
    # derived from registry v3, not the old hand table
    assert qt.KNOWN_QUOTAS["opencode"]["daily_call_limit"] == 200
    assert qt.KNOWN_QUOTAS["kilocode"]["hourly_call_limit"] == 60
    assert "openai-compatible:github" in qt.KNOWN_QUOTAS  # legacy alias kept
    assert qt.PROVIDER_QUIRKS_GENERATED["nvidia"]
