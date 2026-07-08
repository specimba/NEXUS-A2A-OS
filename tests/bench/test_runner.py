"""FI-B1 thin bench runner — Trust Ledger aggregation math and inputs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from nexus_os.bench.runner import (
    TrustCell,
    iter_verdict_outcomes,
    render_leaderboard,
    trust_leaderboard,
)
from nexus_os.relay.tracing.capture import (
    record_response,
    reset_writer_for_tests,
    close_writer_for_tests,
)


@pytest.fixture
def trace_db(tmp_path: Path):
    reset_writer_for_tests(tmp_path)
    yield tmp_path
    close_writer_for_tests()


def _response(content="fine"):
    return {
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 2, "completion_tokens": 2, "total_tokens": 4},
    }


def _verdicts_file(tmp_path: Path, rows):
    p = tmp_path / "verdicts.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return p


def test_posterior_and_interval_math():
    cell = TrustCell(model_id="m", domain="code", successes=9, failures=1)
    assert cell.posterior_mean == pytest.approx(10 / 12)
    low, high = cell.interval()
    assert 0.0 < low < 0.9 < high <= 1.0
    empty = TrustCell(model_id="m", domain="code")
    assert empty.posterior_mean == 0.5  # uniform prior
    assert empty.interval() == (0.0, 1.0)


def test_leaderboard_aggregates_traces_and_verdicts(trace_db: Path, tmp_path: Path):
    for outcome in ("ok", "ok", "suspect"):
        record_response(
            provider="nvidia", model_id="z-ai/glm-5.2",
            request_payload={"messages": [{"role": "user", "content": "q"}]},
            response_payload=_response(), latency_ms=5, temperature=0.2,
            domain="code", outcome=outcome,
        )
    verdicts = _verdicts_file(tmp_path, [
        {"model": "minimax-m3:cloud", "risk_level": "high", "risk_score": 0.9},
        {"model": "minimax-m3:cloud", "risk_level": "low", "risk_score": 0.1},
        {"model": None, "risk_level": "high", "risk_score": 0.9},          # no model → skipped
        {"model": "minimax-m3:cloud", "risk_level": "unknown", "risk_score": 0.0},  # no signal
    ])
    rows = trust_leaderboard(base_dir=trace_db, verdicts_path=verdicts)
    by_key = {(r["model_id"], r["domain"]): r for r in rows}
    glm = by_key[("z-ai/glm-5.2", "code")]
    assert (glm["successes"], glm["failures"]) == (2, 1)
    m3 = by_key[("minimax-m3:cloud", "verdicts")]
    assert (m3["successes"], m3["failures"]) == (1, 1)
    # sorted best posterior first
    assert rows[0]["posterior_mean"] >= rows[-1]["posterior_mean"]


def test_domain_filter_and_render(trace_db: Path, tmp_path: Path):
    record_response(
        provider="nvidia", model_id="m1",
        request_payload={"messages": [{"role": "user", "content": "q"}]},
        response_payload=_response(), latency_ms=5, temperature=0.2,
        domain="code",
    )
    verdicts = _verdicts_file(tmp_path, [
        {"model": "m2", "risk_level": "low", "risk_score": 0.2},
    ])
    rows = trust_leaderboard(domain="code", base_dir=trace_db, verdicts_path=verdicts)
    assert [r["model_id"] for r in rows] == ["m1"]
    text = render_leaderboard(rows)
    assert "m1" in text and "95% CI" in text


def test_empty_inputs_render_cleanly(tmp_path: Path):
    rows = trust_leaderboard(base_dir=tmp_path / "nothing",
                             verdicts_path=tmp_path / "absent.jsonl")
    assert rows == []
    assert "No bench data yet" in render_leaderboard(rows)


def test_verdict_iterator_skips_garbage(tmp_path: Path):
    p = tmp_path / "v.jsonl"
    p.write_text('not json\n{"model": "m", "risk_level": "medium", "risk_score": 0.6}\n',
                 encoding="utf-8")
    rows = list(iter_verdict_outcomes(p))
    assert rows == [("m", "verdicts", False)]


# -- Probe-replay (FI-B increment 2, log-28 Week-4e) -----------------------

def test_run_probes_scores_and_persists(tmp_path):
    from nexus_os.bench.runner import run_probes

    def fake_executor(prompt, *, model, provider=None):
        # echo enough of the prompt back that must_contain probes can hit
        return "Acknowledged. " + prompt[:400]

    report = run_probes(
        probeset="v1", model="test/model", provider=None,
        executor=fake_executor, pace=False, results_dir=tmp_path,
    )
    assert report["probes_run"] > 0
    assert report["dimensions"], "at least one dimension scored"
    for score in report["dimensions"].values():
        assert 0.0 <= score["raw_score"] <= 1.0
    out = tmp_path / "probe_run_test_model.jsonl"
    assert out.exists()
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == len(report["dimensions"])
    assert rows[0]["model"] == "test/model"


def test_run_probes_dimension_filter_and_failures(tmp_path):
    from nexus_os.bench.runner import run_probes

    def broken_executor(prompt, *, model, provider=None):
        raise RuntimeError("provider down")

    report = run_probes(
        probeset="v1", model="m", executor=broken_executor,
        pace=False, results_dir=tmp_path, dimensions=["D1"],
    )
    assert list(report["dimensions"]) == ["D1"]  # filter respected
    # executor failures degrade to empty responses, never raise


def test_run_probes_unknown_probeset(tmp_path):
    from nexus_os.bench.runner import run_probes

    with pytest.raises(ValueError, match="unknown probeset"):
        run_probes(probeset="v9", executor=lambda *a, **k: "", results_dir=tmp_path)


def test_provider_pace_respects_registry_rpm():
    from nexus_os.bench.runner import provider_pace_seconds

    assert provider_pace_seconds("nvidia") == pytest.approx(60.0 / 8)  # 8 RPM
    assert provider_pace_seconds(None) == 10.0
    assert provider_pace_seconds("never-heard-of") == 10.0


def test_render_probe_report_shape(tmp_path):
    from nexus_os.bench.runner import render_probe_report, run_probes

    report = run_probes(
        probeset="v1", model="m", executor=lambda p, **k: "ok",
        pace=False, results_dir=tmp_path, dimensions=["D1"],
    )
    text = render_probe_report(report)
    assert "D1" in text and "results:" in text
