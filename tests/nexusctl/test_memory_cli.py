"""Unit tests for `nexusctl memory` CLI subcommands.

The CLI exposes 8 vault channels, the canonical TrustKernel snapshot, and
in-memory record buffering. Tests are dispatch-driven (calling `cli.main()`)
and verify read-only behaviors plus the append write-gate.
"""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from nexusctl.cli import main
from nexusctl.memory_cli import (
    CHANNEL_MIN_TRUST,
    run_memory,
)


def _args(command: str, **kwargs) -> SimpleNamespace:
    """Mimic the argparse namespace used by `nexusctl memory <command>`."""
    base = {
        "command": "memory",
        "memory_command": command,
        "agent": None,
        "channel": None,
        "limit": 50,
        "lane": None,
        "content": None,
        "allow_write": False,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_run_memory_channels_lists_eight():
    code, payload = run_memory(_args("channels"))
    assert code == 0
    names = [c["name"] for c in payload["channels"]]
    assert names == ["sensory", "working", "episodic", "semantic", "procedural", "trust", "task", "meta"]
    by_name = {c["name"]: c["min_trust"] for c in payload["channels"]}
    assert by_name["semantic"] == 65
    assert by_name["procedural"] == 80
    assert by_name["trust"] == 90


def test_run_memory_show_invalid_channel_returns_error_code_2():
    code, payload = run_memory(_args("show", channel="bogus"))
    assert code == 2
    assert "error" in payload
    assert "bogus" in payload["error"]


def test_run_memory_show_empty_channel_returns_empty_records():
    code, payload = run_memory(_args("show", channel="semantic", agent="test-agent-no-records"))
    assert code == 0
    assert payload["channel"] == "semantic"
    assert payload["count"] == 0
    assert payload["records"] == []


def test_run_memory_append_refuses_without_allow_write():
    code, payload = run_memory(_args("append", channel="episodic", content="probe"))
    assert code == 2
    assert "--allow-write" in payload["error"] or payload["error"].startswith("append requires")


def test_run_memory_append_with_allow_write_calls_manager(monkeypatch):
    """Append with --allow-write invokes the manager's per-channel `append_*`.

    We do not assert the channel-side write actually happens (the manager may
    reject low-trust writes for SENSORY-elevation channels); we only assert
    that the gate was honored and the manager was reached.
    """
    captured: dict = {}

    def fake_append_episodic(*, agent_id, content):
        captured["agent_id"] = agent_id
        captured["content"] = content
        raise RuntimeError("captured-only-fake")

    from nexusctl import memory_cli

    monkeypatch.setattr(memory_cli, "get_manager", lambda: SimpleNamespace(append_episodic=fake_append_episodic))

    code, payload = run_memory(
        _args(
            "append",
            channel="episodic",
            content="hello world",
            agent="test-agent",
            allow_write=True,
        )
    )
    assert code == 2  # because fake threw RuntimeError, mapping to error path
    assert "appended" not in payload
    assert captured["agent_id"] == "test-agent"
    assert captured["content"] == "hello world"


def test_cli_memory_channels_via_main_dispatch(monkeypatch, capsys):
    """End-to-end through `main()`: argparse → dispatcher → stdout JSON."""
    monkeypatch.setattr(sys, "argv", ["nexusctl", "memory", "channels"])
    assert main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert "channels" in payload
    assert len(payload["channels"]) == 8


def test_cli_memory_show_unknown_channel_exits_2(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["nexusctl", "memory", "show", "bogus"])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2
    payload = json.loads(capsys.readouterr().out)
    assert "error" in payload


def test_cli_memory_append_refusal_exits_2(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["nexusctl", "memory", "append", "semantic", "--content", "probe"])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2
    payload = json.loads(capsys.readouterr().out)
    assert "error" in payload
    # sanity: the gate message mentions --allow-write
    assert "--allow-write" in payload["error"]


def test_channel_min_trust_table_is_complete():
    """The CLI's gate table covers every channel defined in MemoryChannel."""
    from nexus_os.vault.memory_channels import MemoryChannel
    assert set(CHANNEL_MIN_TRUST.keys()) == {ch.value for ch in MemoryChannel}
    # sentinel: episodic must be > 0 because failure events are sensitive
    assert CHANNEL_MIN_TRUST["episodic"] >= 50
