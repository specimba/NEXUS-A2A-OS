from nexus_os.nexusclaw.lane_timing import (
    DEFAULT_BASELINE_SEC,
    LaneTimingEvent,
    append_event,
    median_elapsed,
    suggest_max_wait_sec,
)


def test_suggest_max_wait_uses_default_without_history(tmp_path, monkeypatch):
    path = tmp_path / "events.jsonl"
    monkeypatch.setattr("nexus_os.nexusclaw.lane_timing.DEFAULT_EVENTS_PATH", path)
    sec = suggest_max_wait_sec("grok", "smoke", path=path)
    assert sec == DEFAULT_BASELINE_SEC[("grok", "smoke")]


def test_median_after_events(tmp_path, monkeypatch):
    path = tmp_path / "events.jsonl"
    monkeypatch.setattr("nexus_os.nexusclaw.lane_timing.DEFAULT_EVENTS_PATH", path)
    for elapsed in (10.0, 20.0, 30.0):
        append_event(
            LaneTimingEvent(
                ts="2026-01-01T00:00:00+00:00",
                agent_id="grok",
                task_class="smoke",
                status="RESPONSE_READY",
                elapsed_sec=elapsed,
                poll_count=3,
            ),
            path=path,
        )
    med = median_elapsed("grok", "smoke", path=path)
    assert med == 20.0