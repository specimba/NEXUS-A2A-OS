"""Tests for NEXUS trace capture middleware.

Force the singleton writer to a tmp directory so the test never touches
the operator's $NEXUS_REASONS_DB.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

import nexus_os.relay.tracing.capture as capture
from nexus_os.relay.tracing.capture import (
    record_response,
    reset_writer_for_tests,
    close_writer_for_tests,
)
from nexus_os.relay.tracing.record import TraceWriter


@pytest.fixture
def tmp_writer(tmp_path: Path):
    reset_writer_for_tests(tmp_path)
    yield tmp_path
    close_writer_for_tests()



def _all_records(base: Path):
    """Read back records across both license partitions (FI-T2)."""
    out = []
    for part in ("trainable", "reference"):
        d = base / part
        if d.exists():
            w = TraceWriter(base_dir=d)
            out.extend(w.iter_all())
            w.close()
    return out

def _ok_response(provider: str = "nvidia", model_id: str = "z-ai/glm-5.2"):
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_id,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "CONFIRMED",
                },
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }


def test_record_response_persists(tmp_writer: Path):
    rid = record_response(
        provider="nvidia",
        model_id="z-ai/glm-5.2",
        request_payload={
            "model": "z-ai/glm-5.2",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 0.0,
            "max_tokens": 200,
        },
        response_payload=_ok_response(),
        latency_ms=1500,
        temperature=0.0,
        outcome="ok",
        session_id="sess-1",
        domain="general",
        difficulty="medium",
        tags=["smoke"],
    )
    assert rid is not None
    records = _all_records(tmp_writer)
    assert len(records) == 1
    assert records[0].models_tried[0].model_id == "z-ai/glm-5.2"


def test_record_response_scrubs_request_body(tmp_writer: Path):
    rid = record_response(
        provider="nvidia",
        model_id="z-ai/glm-5.2",
        request_payload={
            "model": "z-ai/glm-5.2",
            "messages": [
                {"role": "user", "content": "use sk-proj-abc1234567890notreal"},
            ],
        },
        response_payload=_ok_response(),
        latency_ms=200,
        temperature=0.0,
    )
    assert rid is not None
    found = [r for r in _all_records(tmp_writer)
             if "REDACTED" in (r.models_tried[0].message_content or "")
             or "REDACTED" in r.request_subject]
    assert found  # if scrubbing didn't happen, the raw key would remain


def test_record_response_discards_when_classified(tmp_writer: Path):
    """When the response carries a probable API key in raw message,
    the captured trace must NOT contain the unscrubbed key.

    The capture path scrubs first then persists; classified detection
    is purely defensive if a scrubber regex misses something. This
    test asserts the persisted record never holds the raw key.
    """
    bad = {
        "id": "chatcmpl-bad",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "minimax-m3",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "Your real key is ak_2NX8Y89gC6BE6j21SA2gj8II2bH8J",
                },
            }
        ],
        "usage": {"total_tokens": 5},
    }
    rid = record_response(
        provider="longcat",
        model_id="LongCat-2.0",
        request_payload={"model": "LongCat-2.0",
                          "messages": [{"role": "user", "content": "hi"}]},
        response_payload=bad,
        latency_ms=200,
        temperature=0.0,
    )
    assert rid is not None  # capture happens
    found = _all_records(tmp_writer)
    assert len(found) == 1
    raw_text = json.dumps(found[0].to_json(), ensure_ascii=False)
    # ensure unscrubbed key is NOT in the persisted record
    assert "ak_2NX8Y89gC6BE6j21SA2gj8II2bH8J" not in raw_text
    # ensure scrub marker IS in
    assert "[REDACTED_LONGCAT_KEY]" in raw_text


def test_record_response_handles_no_choices(tmp_writer: Path):
    """An empty choices list must NOT raise but should also not persist."""
    rid = record_response(
        provider="nvidia",
        model_id="z-ai/glm-5.2",
        request_payload={"messages": []},
        response_payload={"choices": []},
        latency_ms=0,
        temperature=0.0,
    )
    assert rid is None


def test_record_response_handles_none_payload(tmp_writer: Path):
    rid = record_response(
        provider="nvidia",
        model_id="z-ai/glm-5.2",
        request_payload=None,
        response_payload=None,
        latency_ms=0,
        temperature=0.0,
    )
    assert rid is None


def test_record_response_includes_reasoning_content(tmp_writer: Path):
    resp = _ok_response()
    resp["choices"][0]["message"]["reasoning_content"] = (
        "Step 1: parse. Step 2: prove. CONFIRMED."
    )
    rid = record_response(
        provider="longcat",
        model_id="LongCat-2.0",
        request_payload={"model": "LongCat-2.0",
                          "messages": [{"role": "user", "content": "prove X"}]},
        response_payload=resp,
        latency_ms=4000,
        temperature=0.5,
        outcome="ok",
    )
    assert rid is not None
    records = _all_records(tmp_writer)
    assert records[0].models_tried[0].reasoning_content and (
        "parse" in records[0].models_tried[0].reasoning_content.lower()
    )


def test_record_response_includes_tool_calls(tmp_writer: Path, monkeypatch):
    resp = _ok_response()
    resp["choices"][0]["message"]["tool_calls"] = [
        {"function": {"name": "lookup", "arguments": "{\"q\":\"foo\"}"}}
    ]
    rid = record_response(
        provider="nvidia",
        model_id="z-ai/glm-5.2",
        request_payload={"messages": [{"role": "user", "content": "call lookup"}]},
        response_payload=resp,
        latency_ms=200,
        temperature=0.0,
    )
    assert rid is not None
    records = _all_records(tmp_writer)
    assert records[0].models_tried[0].tool_calls


# ── Slice-4 retrofit: T2 verdict threading, T4 prompt_hash/flags, T5 ───

def test_record_response_threads_verdict_and_hash(tmp_writer: Path):
    verdict = {"risk_level": "medium", "risk_score": 0.61,
               "reasons": ["entropy_spike"], "tokens_assessed": 42}
    rid = record_response(
        provider="nvidia",
        model_id="z-ai/glm-5.2",
        request_payload={"messages": [
            {"role": "user", "content": "email me at x@y.com please"}]},
        response_payload=_ok_response(),
        latency_ms=100,
        temperature=0.7,
        outcome="suspect",
        hallucination_verdict=verdict,
    )
    assert rid
    # nvidia:z-ai/glm-5.2 carries a permissive outputLicense override →
    # the record must land in the TRAINABLE partition with the class set
    records = _all_records(tmp_writer)
    assert len(records) == 1
    rec = records[0]
    assert (tmp_writer / "trainable" / "hot").exists()
    assert not any((tmp_writer / "reference" / "hot").glob("*.jsonl"))
    assert rec.license_class == "permissive"
    assert rec.hallucination_verdict == verdict
    assert rec.outcome == "suspect"
    assert len(rec.prompt_hash) == 64  # sha256 of scrubbed messages
    assert "REDACTED_EMAIL" in rec.redaction_flags
    assert rec.models_tried[0].evaluator_score == 0.61
    assert rec.generation_lineage == "organic"


def test_prompt_hash_deterministic_over_scrubbed_content(tmp_writer: Path):
    from nexus_os.relay.tracing.capture import _prompt_hash

    a = _prompt_hash({"messages": [{"role": "user", "content": "same body"}]})
    b = _prompt_hash({"messages": [{"role": "user", "content": "same body"}]})
    c = _prompt_hash({"messages": [{"role": "user", "content": "other"}]})
    assert a == b != c
    assert _prompt_hash(None) == "" and _prompt_hash({}) == ""


def test_capture_disabled_warns_once(monkeypatch, caplog):
    import logging
    import nexus_os.relay.tracing.capture as cap

    monkeypatch.setattr(cap, "_DISABLED_REASON", "No module named 'zstandard'")
    monkeypatch.setattr(cap, "_DISABLED_WARNED", False)
    with caplog.at_level(logging.WARNING, logger="nexus.relay.tracing.capture"):
        assert cap.record_response(
            provider="p", model_id="m", request_payload=None,
            response_payload=_ok_response(), latency_ms=1, temperature=0.0,
        ) is None
        assert cap.record_response(
            provider="p", model_id="m", request_payload=None,
            response_payload=_ok_response(), latency_ms=1, temperature=0.0,
        ) is None
    warnings = [r for r in caplog.records if "DISABLED" in r.message]
    assert len(warnings) == 1  # once, not per call — and never silent


# ── Slice-5: license partition + provider/model resolution (FI-T2/T3) ──

def test_restricted_and_unknown_route_to_reference(tmp_writer: Path):
    # googleai is restricted at provider level; never-heard-of is unknown —
    # BOTH must land in reference/ (unknown never trains)
    for provider, model in (("googleai", "gemini-3.5-flash"),
                            ("mystery-lab", "mystery/model-x")):
        record_response(
            provider=provider, model_id=model,
            request_payload={"messages": [{"role": "user", "content": "hi"}]},
            response_payload=_ok_response(provider, model),
            latency_ms=10, temperature=0.1,
        )
    refs = _all_records(tmp_writer)
    assert len(refs) == 2
    assert not (tmp_writer / "trainable" / "hot").exists() or \
        not any((tmp_writer / "trainable" / "hot").glob("*.jsonl"))
    classes = sorted(r.license_class for r in refs)
    assert classes == ["restricted", "unknown"]


def test_split_provider_model_resolves_registry_slugs():
    from nexus_os.relay.tracing.capture import split_provider_model

    assert split_provider_model("nvidia/z-ai/glm-5.2") == ("nvidia", "z-ai/glm-5.2")
    assert split_provider_model("googleai/gemini-3.5-flash") == ("googleai", "gemini-3.5-flash")
    # a namespaced model id whose head is NOT a provider slug stays unknown
    assert split_provider_model("meituan/owl-alpha") == ("unknown", "meituan/owl-alpha")
    assert split_provider_model("bare-model") == ("unknown", "bare-model")
