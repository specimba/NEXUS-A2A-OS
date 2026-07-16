"""Track A1 arena-score ingestion tests — all offline, zero network.

An autouse fixture replaces requests.get/post with a tripwire, so any
accidental network attempt fails the test. Adapter I/O is exercised via
canned snapshots under tests/relay/fixtures/arena injected as cache_dir.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from nexus_os.relay import arena_ingest as ai

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "arena"
NOW = datetime(2026, 7, 10, tzinfo=timezone.utc)
FRESH = "2026-07-09T00:00:00+00:00"    # 1 day old at NOW
STALE_AA = "2026-06-25T00:00:00+00:00" # 15 days: > AA/LMArena 7d horizon
ANCIENT = "2026-05-01T00:00:00+00:00"  # 70 days: > 30d drop threshold

MINI_REGISTRY = {
    "models": [
        {"id": "zai-org/GLM-5.2", "provider": "siliconflow", "status": "active", "aliases": ["glm-5.2"]},
        {"id": "moonshotai/Kimi-K2.6", "provider": "siliconflow", "status": "active", "aliases": []},
        {"id": "MiniMaxAI/MiniMax-M3", "provider": "siliconflow", "status": "active", "aliases": ["minimax-m3"]},
        {"id": "deepseek-ai/DeepSeek-V4-Pro", "provider": "nvidia", "status": "active", "aliases": ["deepseek-v4-pro"]},
        {"id": "deepseek-ai/DeepSeek-V4-Flash", "provider": "nvidia", "status": "active", "aliases": ["deepseek-v4-flash"]},
        {"id": "LongCat-2.0", "provider": "longcat", "status": "active", "aliases": []},
        {"id": "intern-s2-preview", "provider": "internai", "status": "active", "aliases": []},
    ]
}


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("network call attempted in offline test")
    monkeypatch.setattr(ai.requests, "get", _boom)
    monkeypatch.setattr(ai.requests, "post", _boom, raising=False)


def _sig(source, normalized, fetched=FRESH, tier="tier1", raw=None):
    return ai.ArenaSignal(
        source=source, raw=raw or {}, normalized=normalized,
        trust_tier=tier, fetched_at=fetched,
    )


def test_normalization_bounds():
    # elo: linear over [1000, 1500], clamped
    assert ai.normalize_elo(1000.0) == 0.0
    assert ai.normalize_elo(1500.0) == 1.0
    assert ai.normalize_elo(900.0) == 0.0     # clamp low
    assert ai.normalize_elo(1700.0) == 1.0    # clamp high
    assert ai.normalize_elo(1250.0) == pytest.approx(0.5)
    # AA index: /100, clamped
    assert ai.normalize_index(68.0) == pytest.approx(0.68)
    assert ai.normalize_index(150.0) == 1.0
    assert ai.normalize_index(-5.0) == 0.0
    # speed: log band [20, 300], clamped, monotone
    assert ai.normalize_speed(20.0) == pytest.approx(0.0)
    assert ai.normalize_speed(300.0) == pytest.approx(1.0)
    assert ai.normalize_speed(5.0) == pytest.approx(0.0)      # clamp low
    assert ai.normalize_speed(1000.0) == pytest.approx(1.0)   # clamp high
    mid = ai.normalize_speed(77.0)
    assert 0.0 < mid < 1.0
    assert ai.normalize_speed(150.0) > ai.normalize_speed(75.0)
    assert ai.normalize_speed(None) is None
    assert ai.normalize_speed(0.0) is None


def test_trust_weights_per_doctrine():
    # docs/handoff/BENCHMARK_TRUST_REGISTRY.md taxonomy: tier1 dynamic/live
    # boards 1.0, tier2 rotated indices 0.85, usage confidence-only 0.10.
    assert ai.TRUST_WEIGHTS["lmarena_elo"] == 1.0
    assert ai.TRUST_WEIGHTS["lmarena_code_elo"] == 1.0
    assert ai.TRUST_WEIGHTS["aa_coding"] == 1.0
    assert ai.TRUST_WEIGHTS["aa_intelligence_index"] == 0.85
    assert ai.TRUST_WEIGHTS["openrouter_usage"] == ai.USAGE_SIGNAL_WEIGHT == 0.10
    assert "openrouter_usage" in ai.USAGE_SOURCES
    # Tier-3 static benches are never ingested: no weight keys, no adapters.
    for banned in ("gsm8k", "humaneval", "mmlu", "advbench"):
        assert not any(banned in key.lower() for key in ai.TRUST_WEIGHTS)
    assert set(ai.ADAPTERS) == {"artificialanalysis", "lmarena", "openrouter"}
    # staleness horizons per source
    assert ai.MAX_AGE_DAYS == {"artificialanalysis": 7, "lmarena": 7, "openrouter": 3}
    assert ai.DROP_AFTER_DAYS == 30


def test_no_data_flagged_never_faked():
    overrides = ai.load_overrides()  # real config/arena_name_overrides.json
    per_source = {
        "openrouter": {
            "meituan/longcat-2.0": [_sig("openrouter_usage", 0.9, tier="usage")],
        },
        "lmarena": {
            "glm-5.2": [_sig("lmarena_elo", 0.84)],
        },
    }
    overlay = ai.build_scores_overlay(
        MINI_REGISTRY, per_source, overrides, include_no_data=True, now=NOW,
    )
    models = overlay["models"]
    # usage-only model: present, but never given a synthesized score
    longcat = models["LongCat-2.0"]
    assert longcat["no_data"] is True
    assert longcat["arena_score"] is None
    assert longcat["confidence"] == "no_data"
    assert longcat["reason"] == ai.KNOWN_GAPS["LongCat-2.0"]
    assert "openrouter_usage" in longcat["sources"]
    # absent-everywhere model: explicit no_data entry only when requested
    intern = models["intern-s2-preview"]
    assert intern["no_data"] is True and intern["arena_score"] is None
    assert intern["reason"] == ai.KNOWN_GAPS["intern-s2-preview"]
    # capability-scored model is untouched by the doctrine
    assert models["zai-org/GLM-5.2"]["arena_score"] == pytest.approx(0.84)
    # without include_no_data, uncovered models get NO entry at all
    lean = ai.build_scores_overlay(MINI_REGISTRY, per_source, overrides, now=NOW)
    assert "intern-s2-preview" not in lean["models"]
    # and nothing scored ever lacks a capability signal
    for entry in lean["models"].values():
        if not entry["no_data"]:
            assert any(
                key not in ai.USAGE_SOURCES and entry["sources"][key]["trust_tier"] in ("tier1", "tier2")
                for key in entry["sources"]
            )


def test_usage_never_raises_score():
    capability = [_sig("lmarena_elo", 0.5)]
    base_score, base_conf = ai.fuse_signals(capability)
    assert base_score == pytest.approx(0.5)
    # a maxed-out usage signal must not raise score or confidence
    with_usage = capability + [_sig("openrouter_usage", 1.0, tier="usage")]
    score, conf = ai.fuse_signals(with_usage)
    assert score <= base_score
    assert score == pytest.approx(base_score)
    assert conf == base_conf == "medium"
    # usage alone can never manufacture a score
    assert ai.fuse_signals([_sig("openrouter_usage", 1.0, tier="usage")]) == (None, "no_data")
    # Source names are not enough: a malformed or downgraded observation
    # carrying a capability-looking key still cannot enter the score unless
    # its trust tier itself is Tier 1 or Tier 2.
    assert ai.fuse_signals([_sig("lmarena_elo", 0.99, tier="usage")]) == (None, "no_data")


def test_cli_preserves_existing_sidecar_when_no_fresh_capability_evidence(tmp_path, monkeypatch, capsys):
    """A failed board refresh must not erase the last usable sidecar."""
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(MINI_REGISTRY), encoding="utf-8")
    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text("{}", encoding="utf-8")
    out_path = tmp_path / "scores.json"
    previous = '{"version": 1, "models": {"previous": {}}}'
    out_path.write_text(previous, encoding="utf-8")

    # Empty adapter set simulates a fetch failure after the CLI's safe
    # per-source exception handling.  No network is possible in this test.
    monkeypatch.setattr(ai, "build_adapters", lambda _spec: [])

    result = ai.main([
        "--source", "lmarena",
        "--registry", str(registry_path),
        "--overrides", str(overrides_path),
        "--out", str(out_path),
        "--include-no-data",
        "--require-capability-evidence",
    ])

    assert result == 2
    assert out_path.read_text(encoding="utf-8") == previous
    assert "no fresh Tier-1/Tier-2 capability evidence" in capsys.readouterr().out


def test_name_match_uses_registry_aliases():
    models = MINI_REGISTRY["models"]
    # exact id
    assert ai.match_registry_model("zai-org/GLM-5.2", models) == "zai-org/GLM-5.2"
    # registered alias
    assert ai.match_registry_model("glm-5.2", models) == "zai-org/GLM-5.2"
    # bare name with org prefix stripped, case-insensitive
    assert ai.match_registry_model("kimi-k2.6", models) == "moonshotai/Kimi-K2.6"
    assert ai.match_registry_model("MoonshotAI/KIMI-K2.6", models) == "moonshotai/Kimi-K2.6"
    # family-stem + version sequence: board slug "glm-5-2" is GLM-5.2
    assert ai.match_registry_model("glm-5-2", models) == "zai-org/GLM-5.2"
    # reasoning-effort suffix is stripped before matching
    assert ai.match_registry_model("glm-5-2::high", models) == "zai-org/GLM-5.2"
    # overrides pin names the heuristics cannot reach, and win first
    pins = {"weird-board-name": "MiniMaxAI/MiniMax-M3"}
    assert ai.match_registry_model("weird-board-name", models, pins) == "MiniMaxAI/MiniMax-M3"
    # honest failure: unknown stays unmatched, never guessed
    assert ai.match_registry_model("gpt-99-unknown", models) is None
    assert ai.match_registry_model("", models) is None


def test_name_match_is_separator_tolerant_but_variant_safe():
    """Board display spelling may vary; a distinct release may not collapse."""
    models = MINI_REGISTRY["models"]
    assert ai.match_registry_model("GLM 5.2 (Max)", models) == "zai-org/GLM-5.2"
    assert ai.match_registry_model("DeepSeek V4 Pro", models) == "deepseek-ai/DeepSeek-V4-Pro"
    assert ai.match_registry_model("DeepSeek V4 Flash", models) == "deepseek-ai/DeepSeek-V4-Flash"
    # Do not infer that a distinct thinking release is equivalent to either
    # plain V4 route.  An operator can add an explicit reviewed override.
    assert ai.match_registry_model("deepseek-v4-pro-thinking", models) is None


def test_lmarena_official_dataset_payload_preserves_board_provenance():
    payload = {
        "version": 2,
        "source": "huggingface_dataset_server",
        "categories": {
            "overall": [{
                "model_name": "glm-5.2-max",
                "rating": 1460.0,
                "rating_lower": 1448.0,
                "rating_upper": 1472.0,
                "vote_count": 13442,
                "rank": 22,
                "category": "overall",
                "leaderboard_publish_date": "2026-07-10",
            }],
            "coding": [{
                "model_name": "deepseek-v4-pro",
                "rating": 1449.0,
                "rating_lower": 1430.0,
                "rating_upper": 1468.0,
                "vote_count": 41017,
                "rank": 34,
                "category": "coding",
                "leaderboard_publish_date": "2026-07-10",
            }],
        },
    }

    signals = ai.LMArenaAdapter().parse(payload, FRESH)
    glm = signals["glm-5.2-max"][0]
    deepseek = signals["deepseek-v4-pro"][0]
    assert glm.source == "lmarena_elo"
    assert glm.normalized == pytest.approx((1460.0 - 1000.0) / 500.0)
    assert glm.raw["vote_count"] == 13442
    assert glm.raw["leaderboard_publish_date"] == "2026-07-10"
    assert deepseek.source == "lmarena_code_elo"
    assert deepseek.raw["rating_lower"] == 1430.0


def test_lmarena_official_fetch_paginates_with_a_hard_per_category_bound(monkeypatch):
    calls = []

    class _Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def fake_get(url, *, params, timeout, headers):
        calls.append((url, params, timeout, headers))
        category = "overall" if "overall" in params["where"] else "coding"
        offset = params["offset"]
        if category == "overall" and offset == 0:
            rows = [{"row": {"model_name": f"overall-{index}", "rating": 1200 + index}} for index in range(100)]
            return _Response({"num_rows_total": 101, "rows": rows})
        if category == "overall" and offset == 100:
            return _Response({"num_rows_total": 101, "rows": [{"row": {"model_name": "overall-last", "rating": 1400}}]})
        if category == "coding" and offset == 0:
            return _Response({"num_rows_total": 1, "rows": [{"row": {"model_name": "coding-only", "rating": 1300}}]})
        raise AssertionError(f"unexpected page: {category} offset={offset}")

    monkeypatch.setattr(ai.requests, "get", fake_get)
    payload = ai.LMArenaAdapter()._fetch_remote()

    assert [call[1]["offset"] for call in calls] == [0, 100, 0]
    assert all(call[0] == ai.LMARENA_DATASET_SERVER_FILTER_URL for call in calls)
    assert all(call[1]["length"] <= ai.LMARENA_PAGE_SIZE for call in calls)
    assert payload["categories"]["overall"][-1]["model_name"] == "overall-last"
    assert payload["categories"]["coding"][0]["model_name"] == "coding-only"


def test_stale_signals_dropped():
    fresh = _sig("lmarena_elo", 0.8, fetched=FRESH)
    stale = _sig("aa_intelligence_index", 0.2, fetched=STALE_AA, tier="tier2")
    ancient = _sig("lmarena_code_elo", 0.1, fetched=ANCIENT)
    live = ai.filter_stale([fresh, stale, ancient], now=NOW)
    # >30d dropped entirely; >horizon flagged stale; fresh untouched
    assert [s.source for s in live] == ["lmarena_elo", "aa_intelligence_index"]
    assert fresh.stale is False
    assert stale.stale is True
    # fusion uses only the fresh capability signal
    score, confidence = ai.fuse_signals(live)
    assert score == pytest.approx(0.8)
    assert confidence == "medium"
    # openrouter has a tighter 3-day horizon
    usage = _sig("openrouter_usage", 0.5, fetched="2026-07-05T00:00:00+00:00", tier="usage")
    assert ai.filter_stale([usage], now=NOW)[0].stale is True   # 5d > 3d
    usage2 = _sig("openrouter_usage", 0.5, fetched="2026-07-08T00:00:00+00:00", tier="usage")
    assert ai.filter_stale([usage2], now=NOW)[0].stale is False  # 2d < 3d


def test_fuse_confidence_levels():
    # 2+ distinct capability sources -> high, weighted by trust
    signals = [_sig("lmarena_elo", 0.8), _sig("aa_intelligence_index", 0.6, tier="tier2")]
    score, confidence = ai.fuse_signals(signals)
    expected = (1.0 * 0.8 + 0.85 * 0.6) / (1.0 + 0.85)
    assert score == pytest.approx(expected)
    assert confidence == "high"
    # exactly 1 capability source -> medium
    assert ai.fuse_signals([_sig("aa_coding", 0.7)]) == (pytest.approx(0.7), "medium")
    # zero capability sources -> no_data with None score
    assert ai.fuse_signals([]) == (None, "no_data")
    assert ai.fuse_signals([_sig("openrouter_usage", 0.9, tier="usage")]) == (None, "no_data")
    # stale capability signals do not count toward confidence
    stale = _sig("lmarena_elo", 0.9)
    stale.stale = True
    assert ai.fuse_signals([stale, _sig("aa_coding", 0.7)])[1] == "medium"
    # unweighted signal keys (meta: speed/price) never enter the mean
    assert ai.fuse_signals([_sig("aa_speed", 1.0, tier="meta")]) == (None, "no_data")


def test_offline_reads_cache():
    # ArtificialAnalysis: latest snapshot (2026-07-08) wins over 2026-07-01
    aa_signals = ai.ArtificialAnalysisAdapter().fetch(offline=True, cache_dir=FIXTURES)
    assert "glm-5-2" in aa_signals and "glm-5-2::high" in aa_signals
    by_key = {s.source: s for s in aa_signals["glm-5-2"]}
    assert by_key["aa_intelligence_index"].normalized == pytest.approx(0.68)
    assert by_key["aa_coding"].normalized == pytest.approx(0.61)
    assert 0.0 < by_key["aa_speed"].normalized < 1.0
    assert by_key["aa_price"].normalized is None
    assert by_key["aa_coding"].fetched_at == "2026-07-08T00:00:00+00:00"
    # LMArena: text + code boards, elo normalized over 1000-1500
    lm_signals = ai.LMArenaAdapter().fetch(offline=True, cache_dir=FIXTURES)
    glm = {s.source: s for s in lm_signals["glm-5.2"]}
    assert glm["lmarena_elo"].normalized == pytest.approx((1420 - 1000) / 500)
    assert glm["lmarena_code_elo"].normalized == pytest.approx((1401 - 1000) / 500)
    assert glm["lmarena_elo"].trust_tier == "tier1"
    # OpenRouter: usage share of peak, tier "usage"
    or_signals = ai.OpenRouterAdapter().fetch(offline=True, cache_dir=FIXTURES)
    top = or_signals["z-ai/glm-5.2"][0]
    assert top.normalized == pytest.approx(1.0)
    assert top.trust_tier == "usage"
    assert or_signals["meituan/longcat-2.0"][0].normalized < 0.1
    # missing cache is an empty result, not an error (and still no network)
    assert ai.LMArenaAdapter().fetch(offline=True, cache_dir=FIXTURES / "nope") == {}

    # end-to-end overlay from the fixture snapshots
    per_source = {
        "artificialanalysis": aa_signals,
        "lmarena": lm_signals,
        "openrouter": or_signals,
    }
    overlay = ai.build_scores_overlay(
        MINI_REGISTRY, per_source, ai.load_overrides(), now=NOW,
    )
    glm_entry = overlay["models"]["zai-org/GLM-5.2"]
    assert glm_entry["no_data"] is False
    assert 0.0 < glm_entry["arena_score"] <= 1.0
    assert glm_entry["confidence"] == "high"
    assert "lmarena_elo" in glm_entry["sources"] and "aa_coding" in glm_entry["sources"]
    # boards' unknown entries surface as unmatched, never guessed into scores
    assert "mystery-lab-x1" in overlay["unmatched"]["artificialanalysis"]
    assert "unlisted-frontier-x" in overlay["unmatched"]["lmarena"]
    assert overlay["version"] == 1 and overlay["generated_at"]
