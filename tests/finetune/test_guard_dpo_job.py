from __future__ import annotations

import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "finetune" / "gen_guard_dpo_pairs.py"
JOB = REPO / "jobs" / "finetune" / "phase1_guard_dpo.yaml"
HISTORICAL_SMOKE = REPO / "jobs" / "finetune" / "samples" / "guard_dpo_smoke.jsonl"


def _load_module():
    spec = importlib.util.spec_from_file_location("guard_dpo_job_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_job_card_matches_active_generator_and_preserves_historical_provenance():
    module = _load_module()
    card = JOB.read_text(encoding="utf-8")
    smoke = HISTORICAL_SMOKE.read_text(encoding="utf-8")

    assert f"model: {module.JUDGE_MODEL}" in card
    assert "provider: nvidia" in card
    assert f"rpm_limit: {module.JUDGE_RPM}" in card
    assert f"min_start_interval_s: {int(module.JUDGE_MIN_START_INTERVAL_S)}" in card
    assert '"judge": "intern-s2-preview"' in smoke
    assert "do not relabel it" in card


def test_offline_dpo_generation_never_instantiates_the_network_judge(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "OracleJudge", lambda: (_ for _ in ()).throw(AssertionError("network judge")))

    pairs = list(module.generate_pairs(4, offline=True))

    assert len(pairs) == 4
    assert all(pair["meta"]["judge"] == "offline-template" for pair in pairs)
    assert all(pair["chosen"].upper().startswith(f"VERDICT: {pair['meta']['label']}") for pair in pairs)


def test_deepseek_judge_honors_retry_after_and_serial_spacing(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "get_secret", lambda *args, **kwargs: "test-key")
    judge = module.OracleJudge()
    sleeps: list[float] = []
    monkeypatch.setattr(module.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(module.time, "monotonic", lambda: 100.0)

    class _Response:
        def __init__(self, status_code: int, content: str = "", headers: dict | None = None):
            self.status_code = status_code
            self.ok = status_code == 200
            self.headers = headers or {}
            self._content = content

        def json(self):
            return {"choices": [{"message": {"content": self._content}}]}

    responses = iter([
        _Response(429, headers={"Retry-After": "120"}),
        _Response(200, "VERDICT: SAFE - This routine defensive task has no exploit capability or policy conflict."),
    ])
    requests = []

    class _Requests:
        @staticmethod
        def post(*args, **kwargs):
            requests.append((args, kwargs))
            return next(responses)

    judge._requests = _Requests()
    chosen = judge.author_chosen("Review secure logging code", "SAFE")

    assert chosen.startswith("VERDICT: SAFE")
    assert judge.calls == 2
    assert max(sleeps) >= 120.0
    assert any(delay >= module.JUDGE_MIN_START_INTERVAL_S for delay in sleeps)
    assert all(call[1]["json"]["model"] == module.JUDGE_MODEL for call in requests)
    assert module._retry_after_seconds({"Retry-After": "120"}) == 120.0
