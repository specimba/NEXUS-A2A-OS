"""FI-T1 universal-capture hooks: god-mode proxy + adapter primary tier.

No network — hooks are exercised with canned payloads and a tmp trace DB.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

import nexus_os.relay.tracing.capture as capture
from nexus_os.relay.tracing.capture import reset_writer_for_tests, close_writer_for_tests
from nexus_os.relay.tracing.record import TraceWriter


@pytest.fixture
def tmp_db(tmp_path: Path):
    reset_writer_for_tests(tmp_path)
    yield tmp_path
    close_writer_for_tests()


def _all_records(base: Path):
    out = []
    for part in ("trainable", "reference"):
        d = base / part
        if d.exists():
            w = TraceWriter(base_dir=d)
            out.extend(w.iter_all())
            w.close()
    return out


# ── god_mode_proxy ─────────────────────────────────────────────────────

def test_sse_reassembly_produces_capturable_payload():
    from nexus_os.relay.god_mode_proxy import _assemble_sse_for_trace

    raw = (
        b'data: {"model":"nvidia/z-ai/glm-5.2","choices":[{"delta":{"reasoning_content":"think "}}]}\n'
        b'data: {"choices":[{"delta":{"reasoning_content":"hard"}}]}\n'
        b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n'
        b'data: {"choices":[{"delta":{"content":" world"},"finish_reason":"stop"}],'
        b'"usage":{"prompt_tokens":3,"completion_tokens":2,"total_tokens":5}}\n'
        b"data: [DONE]\n"
    )
    payload = _assemble_sse_for_trace(raw)
    msg = payload["choices"][0]["message"]
    assert msg["content"] == "Hello world"
    assert msg["reasoning_content"] == "think hard"
    assert payload["model"] == "nvidia/z-ai/glm-5.2"
    assert payload["usage"]["total_tokens"] == 5
    assert _assemble_sse_for_trace(b"garbage\n") is None


def test_god_mode_capture_routes_by_resolved_provider(tmp_db: Path):
    from nexus_os.relay.god_mode_proxy import _capture_trace

    body = {"model": "auto", "messages": [{"role": "user", "content": "q"}],
            "temperature": 0.5}
    response = {
        "model": "nvidia/z-ai/glm-5.2",  # namespaced Node-relay modelId
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": "a"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }
    _capture_trace(body, {"provider": "god-mode"}, response, latency_ms=42)
    recs = _all_records(tmp_db)
    assert len(recs) == 1
    at = recs[0].models_tried[0]
    assert (at.provider, at.model_id) == ("nvidia", "z-ai/glm-5.2")
    assert recs[0].license_class == "permissive"  # → trainable partition
    assert (tmp_db / "trainable" / "hot").exists()
    assert "god-mode" in recs[0].tags


def test_god_mode_capture_never_raises(tmp_db: Path, monkeypatch):
    from nexus_os.relay import god_mode_proxy as gmp

    monkeypatch.setattr(
        capture, "record_response",
        lambda **kw: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(gmp, "_TRACE_FAIL_WARNED", False)
    gmp._capture_trace({"model": "m"}, {}, {"model": "m", "choices": []}, 1)


# ── model_relay_adapter primary-tier gating ────────────────────────────

class _Args:
    pass


def test_adapter_captures_only_primary_tier(tmp_db: Path, monkeypatch):
    from nexus_os.relay.model_relay_adapter import ModelRelayAdapter

    calls: list[dict] = []
    monkeypatch.setattr(
        capture, "record_response",
        lambda **kw: calls.append(kw) or "tid",
    )

    adapter = ModelRelayAdapter.__new__(ModelRelayAdapter)  # skip __init__ plumbing
    data = {
        "model": "nvidia/minimaxai/minimax-m3",
        "choices": [{"message": {"role": "assistant", "content": "ok"}}],
    }
    adapter._capture_trace({"messages": [], "temperature": 0.2}, data, latency_ms=7)
    assert len(calls) == 1
    assert calls[0]["provider"] == "nvidia"
    assert calls[0]["model_id"] == "minimaxai/minimax-m3"
    assert calls[0]["tags"] == ["adapter-primary"]


def test_adapter_call_chat_gates_on_tier(monkeypatch, tmp_db: Path):
    import io
    import urllib.request as ur
    from nexus_os.relay import model_relay_adapter as mra
    from nexus_os.relay.model_relay_adapter import ModelRelayAdapter, RelayRequest

    body = (b'{"model":"nvidia/z-ai/glm-5.2","choices":'
            b'[{"message":{"role":"assistant","content":"hi"}}]}')

    class _Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(ur, "urlopen", lambda *a, **kw: _Resp(body))

    captured: list[str] = []
    monkeypatch.setattr(
        ModelRelayAdapter, "_capture_trace",
        lambda self, *a, **kw: captured.append("hit"),
    )
    adapter = ModelRelayAdapter.__new__(ModelRelayAdapter)
    adapter.timeout_seconds = 5
    req = RelayRequest(model="auto", prompt="q")

    status, _, _ = adapter._call_chat(req, "http://x", "godmode")
    assert status == "ok" and captured == []  # godmode tier: server-side capture
    status, _, _ = adapter._call_chat(req, "http://x", "primary")
    assert status == "ok" and captured == ["hit"]
