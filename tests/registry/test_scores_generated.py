"""Tests for evidence-backed model benchmark artifacts.

The generator reads config/arena_scores.snapshot.json as a committed,
offline snapshot. Every benchmark dimension is independent: missing
categories remain null, while registry tier is isolated as a routing policy
prior and is never presented or blended as benchmark evidence.
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

def _chimera_profiles():
    data = json.loads(
        (REPO / "nexus_os" / "twave" / "cloud_profiles_generated.json").read_text(encoding="utf-8")
    )
    return data["cloud_profiles"]


def test_registry_artifacts_in_sync():
    """Byte-equality drift gate for every registry consumer."""
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "gen_model_registry.py"),
         "--check"],
        capture_output=True, text=True, cwd=REPO, timeout=60,
    )
    assert result.returncode == 0, "artifacts stale: " + result.stdout + result.stderr


def test_no_data_models_not_faked():
    """KNOWN_GAPS models carry no synthetic tier or neutral scores."""
    from nexus_os.relay.arena_ingest import KNOWN_GAPS
    from nexus_os.relay.scores_generated import SCORES_GENERATED, SCORES_PROVENANCE

    registry_ids = {m["id"] for m in REGISTRY["models"]}
    gap_ids = sorted(rid for rid in KNOWN_GAPS if rid in registry_ids)
    assert gap_ids, "KNOWN_GAPS lost all overlap with the registry"
    for rid in gap_ids:
        assert rid not in ARENA, rid + " must not appear in the arena snapshot"
        prov = SCORES_PROVENANCE[rid]
        assert prov["provenance"] == "unscored", rid
        assert "arena_score" not in prov["components"], rid
        assert prov["sources"] == [], rid
        assert prov["weights"] == {}, rid
        assert all(value is None for value in SCORES_GENERATED[rid].values()), rid


def test_fixture_snapshot_never_claims_high_confidence():
    """Fixture-seeded evidence is useful for wiring, never high-confidence truth."""
    from nexus_os.relay.scores_generated import SCORES_PROVENANCE

    assert "fixture-seeded" in SNAPSHOT_PATH.read_text(encoding="utf-8")
    covered = sorted(rid for rid in ARENA if rid in SCORES_PROVENANCE)
    assert covered, "fixture snapshot lost all registry overlap"
    for rid in covered:
        prov = SCORES_PROVENANCE[rid]
        assert prov["evidence_kind"] == "fixture", rid
        assert prov["confidence"].lower() != "high", rid

def test_registry_tier_is_policy_prior_not_benchmark_evidence():
    """Registry tier may guide routing, but never contributes to benchmark score."""
    from nexus_os.relay.scores_generated import SCORES_GENERATED, SCORES_PROVENANCE

    for rid, prov in SCORES_PROVENANCE.items():
        assert "tier" not in prov["weights"], rid
        assert "registry_tier" not in prov["weights"], rid
        assert set(prov["policy_prior"]) == {"registry_tier"}, rid

    covered = sorted(rid for rid in ARENA if rid in SCORES_PROVENANCE)
    assert covered
    for rid in covered:
        assert SCORES_GENERATED[rid]["quality"] == round(
            float(ARENA[rid]["arena_score"]), 4
        ), rid



def test_glm_5_2_registry_context_is_at_least_one_million():
    """Every hosted GLM-5.2 route advertises its >=1M context contract."""
    rows = [m for m in REGISTRY["models"] if m["id"].lower().endswith("glm-5.2")]
    assert rows, "GLM-5.2 missing from registry"
    for row in rows:
        assert row.get("context", 0) >= 1_000_000, (row["provider"], row.get("context"))


def test_alias_resolution_matches_registry():
    """Every registry id and alias resolves to the richest evidenced record."""
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
        candidates = [SCORES_GENERATED[i]["quality"] for i in pool]
        expected = max((score for score in candidates if score is not None), default=None)
        assert SCORES_GENERATED[alias]["quality"] == expected, alias


def test_chimera_separates_policy_prior_from_benchmarks():
    """Compatibility quality is labelled policy; benchmarks stay dimensional."""
    from nexus_os.relay.scores_generated import SCORES_GENERATED, SCORES_PROVENANCE

    rows = {(m["id"], m["provider"]): m for m in REGISTRY["models"]}
    covered = 0
    unscored = 0
    for profile in _chimera_profiles():
        m = rows[(profile["name"], profile["provider"])]
        registry_tier = m.get("tier") or 50
        assert profile["quality_score"] == round(registry_tier / 100.0, 2)
        assert profile["quality_provenance"] == "policy_prior.registry_tier"
        assert profile["policy_prior"] == {"registry_tier": registry_tier}
        assert profile["benchmark_scores"] == SCORES_GENERATED[m["id"]]
        assert profile["benchmark_provenance"] == SCORES_PROVENANCE[m["id"]]
        if profile["benchmark_provenance"]["provenance"] == "unscored":
            unscored += 1
            assert all(value is None for value in profile["benchmark_scores"].values())
        else:
            covered += 1
    assert covered > 0
    assert unscored > 0
    serialized = json.dumps(_chimera_profiles())
    assert "arena+tier" not in serialized
    assert "tier-only" not in serialized


def _parse_generated_domains(text: str) -> dict:
    marker = "GENERATED_DOMAIN_MAPPING: dict = "
    return ast.literal_eval(text.split(marker, 1)[1])


def test_domains_rank_by_policy_prior_and_expose_benchmarks():
    """Sparse fixture evidence is visible but cannot silently reorder policy."""
    from nexus_os.gmr.domain_mapping_generated import GENERATED_DOMAIN_MAPPING

    for domain, cfg in GENERATED_DOMAIN_MAPPING.items():
        tiers = [entry["tier"] for entry in cfg["primary"]]
        assert tiers == sorted(tiers, reverse=True), domain + " not tier-ordered"
        for entry in cfg["primary"]:
            assert entry["policy_prior"] == {"registry_tier": entry["tier"]}
            assert set(entry["benchmark_scores"]) == {
                "quality", "code", "reasoning", "swe", "speed", "cost_efficiency"
            }
            provenance = entry["benchmark_provenance"]
            assert "tier" not in provenance["weights"]
            assert provenance["policy_prior"] == entry["policy_prior"]

    with_arena = _parse_generated_domains(GEN.emit_domains(REGISTRY, GEN._load_arena()))
    without_arena = _parse_generated_domains(GEN.emit_domains(REGISTRY, {}))
    assert with_arena != without_arena, "benchmark snapshot was not exposed"
    for domain in with_arena:
        with_routes = [entry["model"] for entry in with_arena[domain]["primary"]]
        without_routes = [entry["model"] for entry in without_arena[domain]["primary"]]
        assert with_routes == without_routes, domain + " fixture evidence reordered policy"


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
    """The explicit routing prior still satisfies each GMR target."""
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
