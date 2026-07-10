"""Tests for generated artifact #8 (nexus_os/relay/scores_generated.py) and
the arena-blend wiring in scripts/gen_model_registry.py (Track A2).

The blend reads config/arena_scores.snapshot.json — a committed
lockfile-style arena snapshot — so everything here is offline and
deterministic. Models absent from the snapshot must stay tier-only
(no-data doctrine): a capability score is never synthesized.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REGISTRY = json.loads((REPO / "config" / "models.registry.json").read_text(encoding="utf-8"))
SNAPSHOT_PATH = REPO / "config" / "arena_scores.snapshot.json"
ARENA = {}
if SNAPSHOT_PATH.exists():
    ARENA = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8")).get("models", {})


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "gen_model_registry_under_test", REPO / "scripts" / "gen_model_registry.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GEN = _load_generator()
SCALE = GEN._arena_scale(REGISTRY, ARENA)


def _chimera_profiles():
    data = json.loads(
        (REPO / "nexus_os" / "twave" / "cloud_profiles_generated.json").read_text(encoding="utf-8")
    )
    return data["cloud_profiles"]


def test_scores_artifact_in_sync():
    """Byte-equality drift gate for the blend-consuming artifacts."""
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "gen_model_registry.py"),
         "--check", "--only", "scores,chimera,domains"],
        capture_output=True, text=True, cwd=REPO, timeout=60,
    )
    assert result.returncode == 0, "artifacts stale: " + result.stdout + result.stderr


def test_no_data_models_not_faked():
    """KNOWN_GAPS models carry no arena component — tier-only, never synthesized."""
    from nexus_os.relay.arena_ingest import KNOWN_GAPS
    from nexus_os.relay.scores_generated import SCORES_PROVENANCE

    registry_ids = {m["id"] for m in REGISTRY["models"]}
    gap_ids = sorted(rid for rid in KNOWN_GAPS if rid in registry_ids)
    assert gap_ids, "KNOWN_GAPS lost all overlap with the registry"
    for rid in gap_ids:
        assert rid not in ARENA, rid + " must not appear in the arena snapshot"
        prov = SCORES_PROVENANCE[rid]
        assert prov["provenance"] == "tier-only", rid
        assert "arena_score" not in prov["components"], rid
        assert prov["sources"] == [], rid
        assert prov["weights"] == {"tier": 1.0}, rid


def test_alias_resolution_matches_registry():
    """Every registry id AND alias resolves; collisions take highest blended."""
    from nexus_os.relay.scores_generated import SCORES_GENERATED

    for m in REGISTRY["models"]:
        assert m["id"] in SCORES_GENERATED, m["id"]

    alias_candidates = {}
    for m in REGISTRY["models"]:
        for alias in m.get("aliases", []):
            alias_candidates.setdefault(alias, []).append(m["id"])
    assert alias_candidates, "registry lost all aliases"

    registry_ids = {m["id"] for m in REGISTRY["models"]}
    for alias, ids in alias_candidates.items():
        assert alias in SCORES_GENERATED, alias
        pool = list(ids)
        if alias in registry_ids:
            pool.append(alias)  # alias shadows a real id: it competes too
        expected = max(SCORES_GENERATED[i]["quality"] for i in pool)
        assert SCORES_GENERATED[alias]["quality"] == expected, alias


def test_chimera_quality_prefers_blend():
    """Arena-covered profiles carry the blend (provenance arena+tier);
    uncovered ones stay at tier/100 (tier-only)."""
    rows = {(m["id"], m["provider"]): m for m in REGISTRY["models"]}
    moved = []
    for profile in _chimera_profiles():
        m = rows[(profile["name"], profile["provider"])]
        blended, provenance, _entry = GEN._blend(m, ARENA, SCALE)
        assert profile["quality_score"] == round(blended, 2), profile["name"]
        assert profile["quality_provenance"] == provenance, profile["name"]
        tier_quality = round((m.get("tier") or 50) / 100.0, 2)
        if provenance == "tier-only":
            assert profile["quality_score"] == tier_quality, profile["name"]
        elif profile["quality_score"] != tier_quality:
            moved.append(profile["name"])
    if ARENA:
        covered = [p for p in _chimera_profiles() if p["quality_provenance"] == "arena+tier"]
        assert covered, "snapshot has data but no chimera profile consumed it"
        assert moved, "blend never moved any quality off tier/100 — wiring inert"


def test_domains_order_uses_blend():
    """Domain primaries rank by (-blend_x100, -tier), not raw tier."""
    from nexus_os.gmr.domain_mapping_generated import GENERATED_DOMAIN_MAPPING

    rows = {(m["id"], m["provider"]): m for m in REGISTRY["models"]}
    for domain, cfg in GENERATED_DOMAIN_MAPPING.items():
        keys = []
        for entry in cfg["primary"]:
            m = rows[(entry["model"], entry["provider"])]
            blended, _prov, _entry = GEN._blend(m, ARENA, SCALE)
            keys.append((round(blended * 100, 4), entry["tier"]))
        assert keys == sorted(keys, reverse=True), domain + " not blend-ordered"
    if ARENA:
        # The blend must actually influence the emitted mapping (order or
        # top-6 membership) relative to a blend-free (tier-only) emission.
        with_arena = GEN.emit_domains(REGISTRY, ARENA)
        without_arena = GEN.emit_domains(REGISTRY, {})
        assert with_arena != without_arena, "arena snapshot had no effect on domain mapping"


def _gmr_level_targets():
    """GMR_LEVEL_TARGETS literal parsed from model_relay.py source (no
    import: model_relay pulls heavy runtime deps and is concurrently
    edited; the literal is the contract under test)."""
    src = (REPO / "nexus_os" / "relay" / "model_relay.py").read_text(encoding="utf-8")
    marker = "GMR_LEVEL_TARGETS = {"
    start = src.index(marker) + len(marker) - 1
    depth = 0
    end = None
    for i in range(start, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    assert end is not None, "unbalanced GMR_LEVEL_TARGETS literal"
    stripped = []
    for line in src[start:end].split(chr(10)):
        stripped.append(line.split("#")[0])
    return ast.literal_eval(chr(10).join(stripped))


def test_chimera_gmr_targets_still_reachable():
    """Scale-calibration guard: blending must not deflate the cloud tier
    below the GMR quality targets — every level keeps >= 2 profiles."""
    targets = _gmr_level_targets()
    assert set(targets) == {"L1", "L2", "L3", "L4"}
    profiles = _chimera_profiles()
    for level in sorted(targets):
        quality_target = targets[level][0]
        reachable = sorted(
            p["name"] for p in profiles if p["quality_score"] >= quality_target
        )
        assert len(reachable) >= 2, (
            level + " target " + str(quality_target)
            + " reachable by only: " + ", ".join(reachable)
        )
