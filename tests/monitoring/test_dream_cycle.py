"""Tests for dream_cycle.py — periodic memory consolidation & cross-session learning (P0#3)."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from nexus_os.vault.dream_cycle import DreamCycle, DREAM_STATE_FILE


def _make_entry(content: str = "test message", topic: str = "general",
                sender: str = "agent", timestamp: float | None = None) -> dict:
    return {
        "content": content,
        "topic": topic,
        "sender": sender,
        "timestamp": timestamp or time.time(),
    }


def _make_static_entry(content: str, topic: str = "general",
                       sender: str = "agent") -> dict:
    """Entry with fixed timestamp for deterministic equality comparisons."""
    return _make_entry(content, topic, sender, timestamp=1000000.0)


class TestLoadMemoryEntries:
    def test_no_vault_path_and_no_state_file_returns_empty(self, tmp_path):
        fake_state = tmp_path / "non_existent_dream.json"
        with patch("nexus_os.vault.dream_cycle.DREAM_STATE_FILE", new=fake_state):
            dc = DreamCycle()
            entries = dc._load_memory_entries()
        assert entries == []

    def test_loads_from_vault_path(self, tmp_path):
        f = tmp_path / "vault.json"
        data = [_make_entry("hello"), _make_entry("world")]
        f.write_text(json.dumps(data))
        dc = DreamCycle(vault_path=str(f))
        entries = dc._load_memory_entries()
        assert len(entries) == 2

    def test_vault_path_dict_with_entries_key(self, tmp_path):
        f = tmp_path / "vault.json"
        f.write_text(json.dumps({"entries": [_make_entry("a"), _make_entry("b")]}))
        dc = DreamCycle(vault_path=str(f))
        entries = dc._load_memory_entries()
        assert len(entries) == 2

    def test_vault_path_dict_with_memories_key(self, tmp_path):
        f = tmp_path / "vault.json"
        f.write_text(json.dumps({"memories": [_make_entry("x")]}))
        dc = DreamCycle(vault_path=str(f))
        entries = dc._load_memory_entries()
        assert len(entries) == 1

    def test_vault_path_single_dict_wrapped_in_list(self, tmp_path):
        f = tmp_path / "vault.json"
        f.write_text(json.dumps(_make_entry("single")))
        dc = DreamCycle(vault_path=str(f))
        entries = dc._load_memory_entries()
        assert len(entries) == 1

    def test_loads_from_default_state_file(self, tmp_path):
        state_file = tmp_path / ".nexus" / "dream_state.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text(json.dumps({"entries": [_make_entry("persisted")]}))
        with patch("nexus_os.vault.dream_cycle.DREAM_STATE_FILE", new=state_file):
            dc = DreamCycle()
            entries = dc._load_memory_entries()
        assert len(entries) == 1

    def test_corrupted_vault_returns_empty(self, tmp_path):
        f = tmp_path / "vault.json"
        f.write_text("not json")
        dc = DreamCycle(vault_path=str(f))
        entries = dc._load_memory_entries()
        assert entries == []


class TestDeduplicate:
    def test_identical_content_deduplicated(self):
        dc = DreamCycle()
        e1 = _make_static_entry("hello")
        e2 = _make_static_entry("hello")
        result = dc._deduplicate([e1, e2])
        assert len(result) == 1
        assert dc._stats["entries_deduplicated"] == 1

    def test_different_content_preserved(self):
        dc = DreamCycle()
        e1 = _make_static_entry("hello")
        e2 = _make_static_entry("world")
        result = dc._deduplicate([e1, e2])
        assert len(result) == 2

    def test_empty_input(self):
        dc = DreamCycle()
        assert dc._deduplicate([]) == []

    def test_single_entry(self):
        dc = DreamCycle()
        entry = _make_static_entry("only")
        result = dc._deduplicate([entry])
        assert len(result) == 1
        assert result[0]["content"] == "only"


class TestPruneStale:
    def test_old_entry_pruned(self):
        dc = DreamCycle(ttl_hours=0.001)  # ~3.6 seconds
        old = _make_entry(timestamp=time.time() - 3600)  # 1 hour old
        fresh = _make_entry(timestamp=time.time() + 1)  # future
        time.sleep(0.01)  # ensure TTL has elapsed since init
        result = dc._prune_stale([old, fresh])
        assert len(result) == 1
        assert dc._stats["entries_pruned"] == 1
        assert result[0]["content"] == "test message"

    def test_within_ttl_preserved(self):
        dc = DreamCycle(ttl_hours=72)
        entry = _make_entry(timestamp=time.time() - 3600)  # 1 hour old
        result = dc._prune_stale([entry])
        assert len(result) == 1

    def test_all_expired(self):
        dc = DreamCycle(ttl_hours=0.001)
        time.sleep(0.01)
        result = dc._prune_stale([_make_entry(timestamp=1)])
        assert result == []

    def test_empty_input(self):
        dc = DreamCycle()
        assert dc._prune_stale([]) == []

    def test_iso_timestamp_string(self):
        dc = DreamCycle(ttl_hours=0.001)
        time.sleep(0.01)
        entry = _make_entry(timestamp=datetime.fromisoformat("2000-01-01T00:00:00+00:00").timestamp())
        result = dc._prune_stale([entry])
        assert result == []

    def test_iso_string_parse(self):
        dc = DreamCycle(ttl_hours=72)
        entry = _make_entry(timestamp=datetime.fromisoformat("2026-06-26T00:00:00+00:00").timestamp())
        result = dc._prune_stale([entry])
        assert len(result) == 1


class TestExtractPatterns:
    def test_frequent_topics_detected(self):
        dc = DreamCycle()
        entries = [_make_entry(topic="chat") for _ in range(3)] + [
            _make_entry(topic="code") for _ in range(1)]
        patterns = dc._extract_patterns(entries)
        assert len(patterns) >= 1
        chat_pattern = next(p for p in patterns if p["value"] == "chat")
        assert chat_pattern["frequency"] == 3

    def test_no_patterns_for_unique_topics(self):
        dc = DreamCycle()
        entries = [_make_entry(topic=t) for t in ("a", "b", "c")]
        patterns = dc._extract_patterns(entries)
        assert patterns == []

    def test_pattern_ratio(self):
        dc = DreamCycle()
        entries = [_make_entry(topic="chat") for _ in range(4)]
        patterns = dc._extract_patterns(entries)
        assert patterns
        assert abs(patterns[0]["ratio"] - 1.0) < 0.001

    def test_empty_input(self):
        dc = DreamCycle()
        assert dc._extract_patterns([]) == []


class TestConsolidate:
    def test_consolidation_stats(self, tmp_path):
        f = tmp_path / "vault.json"
        now = time.time()
        f.write_text(json.dumps([
            {"content": "a", "topic": "t1", "sender": "ag", "timestamp": now - 100},
            {"content": "b", "topic": "t2", "sender": "ag", "timestamp": now - 200},
            {"content": "c", "topic": "t3", "sender": "ag", "timestamp": now - 300},
        ]))
        dc = DreamCycle(vault_path=str(f), ttl_hours=72)
        result = dc.consolidate()
        assert result["ok"] is True
        assert result["entries_before"] == 3
        assert result["entries_after"] == 3
        assert result["elapsed_seconds"] > 0
        assert "stats" in result

    def test_consolidation_prunes_and_updates_stats(self, tmp_path):
        f = tmp_path / "vault.json"
        f.write_text(json.dumps([
            _make_entry(content="fresh", timestamp=time.time()),
            _make_entry(content="stale", timestamp=1),
        ]))
        dc = DreamCycle(vault_path=str(f), ttl_hours=0.001)
        time.sleep(0.01)
        result = dc.consolidate()
        assert result["pruned"] >= 1
        assert result["entries_after"] <= 1

    def test_multiple_cycles_accumulate(self, tmp_path):
        f = tmp_path / "vault.json"
        f.write_text(json.dumps([_make_entry("x")]))
        dc = DreamCycle(vault_path=str(f))
        r1 = dc.consolidate()
        r2 = dc.consolidate()
        assert r2["stats"]["cycles_run"] == 2


class TestGetStats:
    def test_initial_stats(self):
        dc = DreamCycle()
        s = dc.get_stats()
        assert s["cycles_run"] == 0
        assert s["total_entries_processed"] == 0
        assert s["entries_pruned"] == 0
        assert s["patterns_extracted"] == 0
        assert "trust_memory" in s

    def test_stats_update_after_consolidate(self, tmp_path):
        f = tmp_path / "vault.json"
        f.write_text(json.dumps([_make_entry("hello")]))
        dc = DreamCycle(vault_path=str(f))
        dc.consolidate()
        s = dc.get_stats()
        assert s["cycles_run"] == 1
        assert s["total_entries_processed"] == 1


class TestEmitToA2A:
    def test_no_channel_no_op(self):
        dc = DreamCycle()
        dc._emit_to_a2a("msg", "test")
        # Should not raise

    def test_writes_to_a2a_channel(self, tmp_path):
        dc = DreamCycle(a2a_channel=str(tmp_path))
        dc._emit_to_a2a("hello world", topic="dream-patterns")
        out_file = tmp_path / "dream-patterns.jsonl"
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert data["sender"] == "dream_cycle"
        assert data["message"] == "hello world"
        assert data["topic"] == "dream-patterns"

    def test_a2a_channel_creates_dir(self, tmp_path):
        dc = DreamCycle(a2a_channel=str(tmp_path / "deep" / "dir"))
        dc._emit_to_a2a("msg")
        assert (tmp_path / "deep" / "dir" / "dream-cycle.jsonl").exists()


class TestSaveState:
    def test_saves_and_overwrites(self, tmp_path):
        state_file = tmp_path / ".nexus" / "dream_state.json"
        with patch("nexus_os.vault.dream_cycle.DREAM_STATE_FILE", new=state_file):
            dc = DreamCycle(vault_path=tmp_path / "vault.json")
            dc._save_state([_make_static_entry("x")])
            assert state_file.exists()
            data = json.loads(state_file.read_text())
            assert "entries" in data
            assert "last_consolidation" in data
            assert "stats" in data


class TestCLI:
    def test_cli_consolidate(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sys.argv", ["dream_cycle", "--consolidate"])
        with patch("nexus_os.vault.dream_cycle.DreamCycle.consolidate", return_value={"ok": True}):
            from nexus_os.vault.dream_cycle import cli_main
            cli_main()

    def test_cli_status(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["dream_cycle", "--status"])
        with patch("nexus_os.vault.dream_cycle.DreamCycle.get_stats", return_value={"cycles_run": 0}):
            from nexus_os.vault.dream_cycle import cli_main
            cli_main()

    def test_cli_daemon_immediate_shutdown(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["dream_cycle", "--daemon", "--interval", "1"])
        def short_run(*a, **kw):
            raise SystemExit(0)
        with patch("nexus_os.vault.dream_cycle.DreamCycle.run_daemon", side_effect=short_run):
            from nexus_os.vault.dream_cycle import cli_main
            with pytest.raises(SystemExit):
                cli_main()
