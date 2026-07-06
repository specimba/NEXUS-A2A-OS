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
    writer = TraceWriter(base_dir=tmp_writer)
    assert writer.count() == 1
    records = list(writer.iter_all())
    assert records[0].models_tried[0].model_id == "z-ai/glm-5.2"
    writer.close()


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
    writer = TraceWriter(base_dir=tmp_writer)
    found = writer.search("REDACTED")
    assert found  # if scrubbing didn't happen, the key would be in the index
    writer.close()


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
    writer = TraceWriter(base_dir=tmp_writer)
    found = list(writer.iter_all())
    assert len(found) == 1
    raw_text = json.dumps(found[0].to_json(), ensure_ascii=False)
    # ensure unscrubbed key is NOT in the persisted record
    assert "ak_2NX8Y89gC6BE6j21SA2gj8II2bH8J" not in raw_text
    # ensure scrub marker IS in
    assert "[REDACTED_LONGCAT_KEY]" in raw_text
    writer.close()


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
    writer = TraceWriter(base_dir=tmp_writer)
    records = list(writer.iter_all())
    assert records[0].models_tried[0].reasoning_content and (
        "parse" in records[0].models_tried[0].reasoning_content.lower()
    )
    writer.close()


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
    writer = TraceWriter(base_dir=tmp_writer)
    records = list(writer.iter_all())
    assert records[0].models_tried[0].tool_calls
    writer.close()
