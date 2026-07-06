"""W1 wiring: reasoning engine ← live REASONS-DB trainable partition."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("nexus_os.reasoning.trace_source")

from nexus_os.reasoning.trace_source import (
    _is_tainted,
    extract_patterns_from_traces,
    iter_trainable_records,
)
from nexus_os.relay.tracing.record import TraceWriter
from nexus_os.relay.tracing.schema import ModelAttempt, TraceRecord


def _record(license_class="permissive", flags=(), outcome="ok",
            reasoning="Let me diagnose the server state by inspecting logs.",
            content="The server is healthy."):
    return TraceRecord(
        session_id="s1",
        domain="code",
        request_subject="Check the server",
        outcome=outcome,
        license_class=license_class,
        redaction_flags=list(flags),
        models_tried=[ModelAttempt(
            provider="nvidia", model_id="z-ai/glm-5.2",
            reasoning_content=reasoning, message_content=content,
            outcome=outcome,
        )],
    )


@pytest.fixture
def db(tmp_path: Path):
    w = TraceWriter(base_dir=tmp_path / "trainable")
    yield tmp_path, w
    w.close()


def test_trainable_records_flow_in_cot_shape(db):
    base, w = db
    w.append(_record())
    entries = list(iter_trainable_records(base))
    assert len(entries) == 1
    e = entries[0]
    assert e["model"] == "nvidia/z-ai/glm-5.2"
    assert e["context"].startswith("USER: Check the server")
    assert "ASSISTANT:" in e["context"]
    assert e["source_file"] == "reasons_db/trainable"


def test_non_permissive_record_refused_even_inside_trainable(db):
    base, w = db
    w.append(_record(license_class="restricted"))
    w.append(_record(license_class="unknown"))
    assert list(iter_trainable_records(base)) == []


def test_reference_path_raises(tmp_path: Path):
    with pytest.raises(ValueError, match="reference"):
        list(iter_trainable_records(tmp_path / "reasons_db" / "reference"))


def test_tainted_redaction_flags_skip_record(db):
    base, w = db
    w.append(_record(flags=["REDACTED_NVIDIA_KEY"]))
    w.append(_record(flags=["REDACTED_GITHUB_PAT"]))
    w.append(_record(flags=["REDACTED_EMAIL", "REDACTED_IP"]))  # anonymous → ok
    entries = list(iter_trainable_records(base))
    assert len(entries) == 1
    assert _is_tainted(["REDACTED_JWT"]) and not _is_tainted(["REDACTED_EMAIL"])
    assert _is_tainted(["SOMETHING_NEW"])  # unrecognized flag fails safe


def test_failed_outcomes_do_not_train(db):
    base, w = db
    w.append(_record(outcome="suspect"))
    assert list(iter_trainable_records(base)) == []


def test_round_trip_through_pattern_extractor(db):
    base, w = db
    w.append(_record())
    patterns = extract_patterns_from_traces(base)
    assert patterns, "extractor should find at least one reasoning pattern"
    assert all(p.source_uid for p in patterns)


def test_engine_trace_dir_loads_live_patterns(db):
    from nexus_os.reasoning.fable_engine import FableReasoningEngine

    base, w = db
    w.append(_record())
    engine = FableReasoningEngine(
        cot_path="C:/nonexistent/ignored.jsonl", trace_dir=str(base)
    )
    engine.initialize()
    assert engine.patterns, "trace_dir must feed patterns, cot_path ignored"
