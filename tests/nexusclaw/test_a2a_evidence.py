"""Tests for the A2A evidence gate (anti-simulation-theatre). File-based, no browser/CDP."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from nexus_os.nexusclaw.a2a_evidence import (
    VERDICT_SIMULATED,
    VERDICT_UNPROVEN,
    VERDICT_VERIFIED,
    CycleEvidence,
    to_grounding_event,
    validate,
    write_episode,
)
from nexus_os.nexusclaw.a2a_experiment_aggregate import main as aggregate_main

LANE = "glm_5_2"
REGISTRY = {"lanes": [{"id": LANE, "host": "chat.z.ai", "required_probe": "chat.z.ai"}]}
SESSION = "a2a_test-session"


def _append(path: Path, obj: dict) -> int:
    """Append one JSONL line and return the pre-append byte offset (real offsets)."""
    offset = path.stat().st_size if path.exists() else 0
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(obj) + "\n")
    return offset


def _write_send_wait(
    events: Path,
    cycle: int = 1,
    lane: str = LANE,
    send_ts: str = "2026-07-06T00:00:10+00:00",
    wait_ts: str = "2026-07-06T00:01:10+00:00",
    elapsed: float = 58.0,
) -> tuple[int, int]:
    _append(events, {"type": "CYCLE_START", "cycle": cycle, "ts": "2026-07-06T00:00:00+00:00"})
    send_off = _append(
        events, {"type": "SEND_PING", "cycle": cycle, "lane": lane, "exit": 0, "ts": send_ts}
    )
    wait_off = _append(
        events,
        {
            "type": "WAIT_RESULT",
            "cycle": cycle,
            "lane": lane,
            "wait": {"status": "RESPONSE_READY", "elapsedSec": elapsed},
            "ts": wait_ts,
        },
    )
    return send_off, wait_off


def _evidence(send_off: int, wait_off: int, cycle: int = 1, **overrides) -> CycleEvidence:
    base = CycleEvidence(
        session_id=SESSION,
        cycle=cycle,
        lane=LANE,
        agent_id=LANE,
        cdp_target_id="ABCDEF0123456789",
        url="https://chat.z.ai/c/1b1cd50b",
        prompt_sha256="p" * 64,
        tail_before_sha256="a" * 64,
        tail_after_sha256="b" * 64,
        tail_growth=142,
        send_ts="2026-07-06T00:00:11+00:00",
        response_ts="2026-07-06T00:01:09+00:00",
        elapsed_sec=58.0,
        wait_status="RESPONSE_READY",
        send_offset=send_off,
        wait_offset=wait_off,
    )
    return replace(base, **overrides)


@pytest.fixture
def real_cycle(tmp_path):
    events = tmp_path / "events.jsonl"
    send_off, wait_off = _write_send_wait(events)
    return events, _evidence(send_off, wait_off)


def test_all_checks_pass_is_verified(real_cycle):
    events, evidence = real_cycle
    verdict, failures = validate(evidence, events, REGISTRY)
    assert verdict == VERDICT_VERIFIED
    assert failures == []


def test_identical_tail_hashes_is_simulated(real_cycle):
    events, evidence = real_cycle
    evidence = replace(evidence, tail_after_sha256=evidence.tail_before_sha256)
    verdict, failures = validate(evidence, events, REGISTRY)
    assert verdict == VERDICT_SIMULATED
    assert "no_tail_delta" in failures


def test_zero_tail_growth_is_simulated(real_cycle):
    events, evidence = real_cycle
    verdict, failures = validate(replace(evidence, tail_growth=0), events, REGISTRY)
    assert verdict == VERDICT_SIMULATED
    assert "no_tail_growth" in failures


def test_missing_cdp_target_is_simulated(real_cycle):
    events, evidence = real_cycle
    verdict, failures = validate(replace(evidence, cdp_target_id=None), events, REGISTRY)
    assert verdict == VERDICT_SIMULATED
    assert "missing_cdp_target_id" in failures


def test_url_host_mismatch_is_simulated(real_cycle):
    events, evidence = real_cycle
    verdict, failures = validate(
        replace(evidence, url="https://example.com/fake"), events, REGISTRY
    )
    assert verdict == VERDICT_SIMULATED
    assert "url_host_mismatch" in failures


def test_lane_not_in_registry_is_simulated(real_cycle):
    events, evidence = real_cycle
    verdict, failures = validate(evidence, events, {"lanes": []})
    assert verdict == VERDICT_SIMULATED
    assert "lane_not_in_registry" in failures


def test_elapsed_too_fast_is_simulated(real_cycle):
    events, evidence = real_cycle
    verdict, failures = validate(replace(evidence, elapsed_sec=0.4), events, REGISTRY)
    assert verdict == VERDICT_SIMULATED
    assert "elapsed_too_fast" in failures


def test_elapsed_over_max_wait_is_simulated(real_cycle):
    events, evidence = real_cycle
    verdict, failures = validate(replace(evidence, elapsed_sec=1200.0), events, REGISTRY)
    assert verdict == VERDICT_SIMULATED
    assert "elapsed_exceeds_max_wait" in failures
    # But an explicit larger budget accepts it.
    verdict2, _ = validate(replace(evidence, elapsed_sec=1200.0), events, REGISTRY, max_wait_sec=1800)
    assert verdict2 == VERDICT_VERIFIED


def test_send_ts_after_response_ts_is_simulated(real_cycle):
    events, evidence = real_cycle
    verdict, failures = validate(
        replace(
            evidence,
            send_ts="2026-07-06T00:02:00+00:00",
            response_ts="2026-07-06T00:01:00+00:00",
        ),
        events,
        REGISTRY,
    )
    assert verdict == VERDICT_SIMULATED
    assert "clock_not_monotonic" in failures


def test_wait_status_not_ready_is_simulated(real_cycle):
    events, evidence = real_cycle
    verdict, failures = validate(replace(evidence, wait_status="TIMEOUT"), events, REGISTRY)
    assert verdict == VERDICT_SIMULATED
    assert "wait_status_not_ready" in failures


def test_wrong_offset_lines_are_simulated(tmp_path):
    events = tmp_path / "events.jsonl"
    send_off, wait_off = _write_send_wait(events)
    # Point send_offset at the CYCLE_START line (offset 0) — wrong event type.
    evidence = _evidence(0, wait_off)
    verdict, failures = validate(evidence, events, REGISTRY)
    assert verdict == VERDICT_SIMULATED
    assert "send_event_mismatch" in failures
    # Offset beyond EOF.
    evidence = _evidence(send_off, events.stat().st_size + 4096)
    verdict, failures = validate(evidence, events, REGISTRY)
    assert verdict == VERDICT_SIMULATED
    assert "wait_event_mismatch" in failures


def test_missing_events_file_is_simulated(tmp_path):
    evidence = _evidence(0, 10)
    verdict, failures = validate(evidence, tmp_path / "nope.jsonl", REGISTRY)
    assert verdict == VERDICT_SIMULATED
    assert "events_file_missing" in failures


def test_non_monotonic_event_ts_is_simulated(tmp_path):
    events = tmp_path / "events.jsonl"
    send_off, wait_off = _write_send_wait(
        events,
        send_ts="2026-07-06T00:05:00+00:00",
        wait_ts="2026-07-06T00:01:00+00:00",  # earlier than the send event
    )
    evidence = _evidence(send_off, wait_off)
    verdict, failures = validate(evidence, events, REGISTRY)
    assert verdict == VERDICT_SIMULATED
    assert "events_ts_not_monotonic" in failures


def test_probe_only_is_unproven(real_cycle):
    events, evidence = real_cycle
    verdict, failures = validate(evidence, events, REGISTRY, probe_only=True)
    assert verdict == VERDICT_UNPROVEN
    assert failures == []
    # Negative send_offset means no send was attempted.
    verdict, failures = validate(replace(evidence, send_offset=-1), events, REGISTRY)
    assert verdict == VERDICT_UNPROVEN
    assert failures == []


def test_verified_emits_e1_grounding_event_and_episode(real_cycle, tmp_path):
    events, evidence = real_cycle
    verdict, failures = validate(evidence, events, REGISTRY)
    evidence = replace(evidence, verdict=verdict, failures=failures)
    ge = to_grounding_event(evidence)
    assert ge.evidence_grade == "E1"
    assert ge.source_kind == "browser_ai_collaboration"
    assert ge.content_hash == evidence.tail_after_sha256
    assert ge.trace_id == f"{SESSION}:1:{LANE}"
    assert ge.metadata["send_offset"] == evidence.send_offset

    archivist = tmp_path / "ARCHIVIST"
    episode_path = write_episode(evidence, "response text " * 20, archivist_root=archivist)
    assert episode_path == archivist / "EPISODES" / "a2a" / f"{SESSION}.jsonl"
    assert episode_path.is_file()


def test_simulated_emits_e0_and_episode_write_raises(real_cycle, tmp_path):
    events, evidence = real_cycle
    evidence = replace(evidence, cdp_target_id=None)
    verdict, failures = validate(evidence, events, REGISTRY)
    evidence = replace(evidence, verdict=verdict, failures=failures)
    assert to_grounding_event(evidence).evidence_grade == "E0"
    with pytest.raises(ValueError):
        write_episode(evidence, "fabricated", archivist_root=tmp_path / "ARCHIVIST")
    assert not (tmp_path / "ARCHIVIST" / "EPISODES").exists()


def test_episode_record_capped_and_round_trips(real_cycle, tmp_path):
    events, evidence = real_cycle
    verdict, failures = validate(evidence, events, REGISTRY)
    evidence = replace(evidence, verdict=verdict, failures=failures)
    long_tail = "Ω response chunk. " * 2000  # non-ascii inflates escaped size
    episode_path = write_episode(evidence, long_tail, archivist_root=tmp_path / "ARCHIVIST")
    line = episode_path.read_text(encoding="utf-8").splitlines()[-1]
    assert len(line.encode("utf-8")) <= 4096
    record = json.loads(line)
    assert record["verdict"] == VERDICT_VERIFIED
    assert record["session"] == SESSION
    assert record["evidence"]["cdp_target_id"] == evidence.cdp_target_id
    assert len(record["response_excerpt"]) <= 2000


def test_evidence_round_trips_dict(real_cycle):
    _, evidence = real_cycle
    clone = CycleEvidence.from_dict(json.loads(json.dumps(evidence.to_dict())))
    assert clone == evidence
    # Unknown keys are ignored.
    payload = evidence.to_dict()
    payload["totally_new_field"] = 1
    assert CycleEvidence.from_dict(payload) == evidence


def _write_registry(tmp_path: Path) -> Path:
    reg = tmp_path / "registry.json"
    reg.write_text(json.dumps(REGISTRY), encoding="utf-8")
    return reg


def test_aggregate_recomputes_and_excludes_simulated(tmp_path, capsys):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    events = session_dir / "events.jsonl"

    # Cycle 1: genuinely verifiable.
    s1, w1 = _write_send_wait(events, cycle=1, elapsed=42.0)
    ev1 = _evidence(s1, w1, cycle=1, elapsed_sec=42.0, verdict=VERDICT_VERIFIED)
    _append(events, {"type": "CYCLE_EVIDENCE", "cycle": 1, "lane": LANE,
                     "verdict": VERDICT_VERIFIED, "failures": [], "evidence": ev1.to_dict()})

    # Cycle 2: inline verdict LIES ("VERIFIED") but tail hashes are identical.
    s2, w2 = _write_send_wait(
        events, cycle=2,
        send_ts="2026-07-06T01:00:10+00:00", wait_ts="2026-07-06T01:03:10+00:00",
        elapsed=180.0,
    )
    ev2 = _evidence(
        s2, w2, cycle=2, elapsed_sec=180.0,
        tail_after_sha256="a" * 64, tail_growth=0, verdict=VERDICT_VERIFIED,
    )
    _append(events, {"type": "CYCLE_EVIDENCE", "cycle": 2, "lane": LANE,
                     "verdict": VERDICT_VERIFIED, "failures": [], "evidence": ev2.to_dict()})

    # Cycle 2 also had a probe-only lane.
    ev3 = CycleEvidence(session_id=SESSION, cycle=2, lane="grok", agent_id="grok",
                        send_offset=-1, wait_offset=-1, verdict=VERDICT_UNPROVEN)
    _append(events, {"type": "CYCLE_EVIDENCE", "cycle": 2, "lane": "grok",
                     "verdict": VERDICT_UNPROVEN, "failures": [], "evidence": ev3.to_dict()})

    rc = aggregate_main(["--session-dir", str(session_dir), "--registry", str(_write_registry(tmp_path))])
    assert rc == 0
    report = json.loads((session_dir / "FINAL_REPORT.json").read_text(encoding="utf-8"))
    assert report["evidence_gate"] == "v1"
    assert report["verified_cycles"] == 1
    assert report["simulated_cycles"] == 1
    assert report["unproven_cycles"] == 1
    assert report["simulation_suspected"] is False
    # Median wait must come from the verified cycle only (42s, not 180s).
    assert report["wait_by_lane"] == {LANE: 42.0}

    md = (session_dir / "FINAL_REPORT.md").read_text(encoding="utf-8")
    assert not md.startswith("STATUS: SIMULATION_SUSPECTED")
    assert f"SIMULATED cycle=2 lane={LANE}" in md
    assert "no_tail_delta" in md


def test_aggregate_flags_simulation_when_no_verified_sends(tmp_path, capsys):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    events = session_dir / "events.jsonl"
    s1, w1 = _write_send_wait(events, cycle=1)
    # Fabricated evidence: no CDP target, no tail delta.
    ev = _evidence(s1, w1, cycle=1, cdp_target_id=None,
                   tail_after_sha256="a" * 64, tail_growth=0)
    _append(events, {"type": "CYCLE_EVIDENCE", "cycle": 1, "lane": LANE,
                     "verdict": VERDICT_VERIFIED, "failures": [], "evidence": ev.to_dict()})

    rc = aggregate_main(["--session-dir", str(session_dir), "--registry", str(_write_registry(tmp_path))])
    assert rc == 0
    md = (session_dir / "FINAL_REPORT.md").read_text(encoding="utf-8")
    assert md.splitlines()[0] == "STATUS: SIMULATION_SUSPECTED"
    report = json.loads((session_dir / "FINAL_REPORT.json").read_text(encoding="utf-8"))
    assert report["verified_cycles"] == 0
    assert report["simulated_cycles"] == 1
    assert report["simulation_suspected"] is True


def test_aggregate_pre_gate_session_with_sends_is_suspected(tmp_path, capsys):
    """A legacy events file with sends but zero CYCLE_EVIDENCE records is suspect."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    events = session_dir / "events.jsonl"
    _write_send_wait(events, cycle=1)
    rc = aggregate_main(["--session-dir", str(session_dir), "--registry", str(_write_registry(tmp_path))])
    assert rc == 0
    md = (session_dir / "FINAL_REPORT.md").read_text(encoding="utf-8")
    assert md.splitlines()[0] == "STATUS: SIMULATION_SUSPECTED"
    assert "No CYCLE_EVIDENCE records found" in md
