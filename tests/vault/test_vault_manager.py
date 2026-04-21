"""
tests/vault/test_vault_manager.py - VaultManager V3 5-track tests.

The V2 write_memory/read_memory API was removed. These tests validate the
canonical V3 S-P-E-W memory track contract: store_track, retrieve_track, and
get_agent_profile.
"""

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from nexus_os.vault.manager import VaultManager


@pytest.fixture
def vault(tmp_path):
    manager = VaultManager(str(tmp_path / "vault.db"))
    manager.conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_memory_tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            lane TEXT NOT NULL,
            track_type TEXT,
            key TEXT NOT NULL,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(agent_id, lane, track_type, key)
        )
    """)
    manager.conn.commit()
    return manager


class TestStoreTrack:
    def test_store_event_track(self, vault):
        vault.store_track("agent-a", "code", "event", "task-1", {"status": "done"})

        record = vault.retrieve_track("agent-a", "code", "event", "task-1")
        assert record == {"status": "done"}

    def test_store_all_supported_tracks(self, vault):
        payloads = {
            "event": {"action": "dispatch"},
            "trust": {"alpha": 2.0, "beta": 1.0},
            "capability": {"skill": "python", "score": 0.91},
            "failure_pattern": {"pattern": "timeout", "count": 1},
            "governance": {"policy": "deny-by-default"},
        }

        for track_type, payload in payloads.items():
            vault.store_track("agent-a", "analysis", track_type, track_type, payload)

        for track_type, payload in payloads.items():
            assert vault.retrieve_track("agent-a", "analysis", track_type, track_type) == payload

    def test_store_rejects_invalid_track_type(self, vault):
        with pytest.raises(sqlite3.IntegrityError):
            vault.store_track("agent-a", "code", "invalid", "bad", {"value": True})

    def test_store_upserts_existing_key(self, vault):
        vault.store_track("agent-a", "code", "trust", "alpha_beta", {"alpha": 1.0, "beta": 1.0})
        vault.store_track("agent-a", "code", "trust", "alpha_beta", {"alpha": 3.0, "beta": 1.5})

        assert vault.retrieve_track("agent-a", "code", "trust", "alpha_beta") == {
            "alpha": 3.0,
            "beta": 1.5,
        }


class TestRetrieveTrack:
    def test_retrieve_missing_track_returns_none(self, vault):
        assert vault.retrieve_track("missing", "code", "event", "none") is None

    def test_retrieve_is_scoped_by_agent(self, vault):
        vault.store_track("agent-a", "code", "event", "task", {"owner": "a"})
        vault.store_track("agent-b", "code", "event", "task", {"owner": "b"})

        assert vault.retrieve_track("agent-a", "code", "event", "task") == {"owner": "a"}
        assert vault.retrieve_track("agent-b", "code", "event", "task") == {"owner": "b"}

    def test_retrieve_is_scoped_by_lane(self, vault):
        vault.store_track("agent-a", "code", "event", "task", {"lane": "code"})
        vault.store_track("agent-a", "security", "event", "task", {"lane": "security"})

        assert vault.retrieve_track("agent-a", "code", "event", "task") == {"lane": "code"}
        assert vault.retrieve_track("agent-a", "security", "event", "task") == {"lane": "security"}

    def test_json_round_trip_preserves_nested_values(self, vault):
        payload = {"nested": {"items": [1, 2, 3], "flag": True}, "note": "stable"}
        vault.store_track("agent-a", "ops", "governance", "policy", payload)

        assert vault.retrieve_track("agent-a", "ops", "governance", "policy") == payload


class TestAgentProfile:
    def test_profile_contains_all_five_tracks(self, vault):
        profile = vault.get_agent_profile("agent-a", "code")

        assert set(profile.keys()) == {
            "event",
            "trust",
            "capability",
            "failure_pattern",
            "governance",
        }

    def test_profile_groups_records_by_track(self, vault):
        vault.store_track("agent-a", "code", "event", "task-1", {"status": "done"})
        vault.store_track("agent-a", "code", "trust", "alpha_beta", {"alpha": 2.0, "beta": 1.0})
        vault.store_track("agent-a", "code", "capability", "python", {"score": 0.8})

        profile = vault.get_agent_profile("agent-a", "code")

        assert profile["event"]["task-1"] == {"status": "done"}
        assert profile["trust"]["alpha_beta"] == {"alpha": 2.0, "beta": 1.0}
        assert profile["capability"]["python"] == {"score": 0.8}
        assert profile["failure_pattern"] == {}
        assert profile["governance"] == {}

    def test_profile_is_lane_scoped(self, vault):
        vault.store_track("agent-a", "code", "trust", "alpha_beta", {"alpha": 5.0, "beta": 1.0})
        vault.store_track("agent-a", "research", "trust", "alpha_beta", {"alpha": 1.0, "beta": 4.0})

        code_profile = vault.get_agent_profile("agent-a", "code")
        research_profile = vault.get_agent_profile("agent-a", "research")

        assert code_profile["trust"]["alpha_beta"]["alpha"] == 5.0
        assert research_profile["trust"]["alpha_beta"]["beta"] == 4.0


class TestSchema:
    def test_agent_memory_tracks_table_exists(self, vault):
        rows = vault.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_memory_tracks'"
        ).fetchall()
        assert len(rows) == 1

    def test_schema_supports_v3_unique_upsert_contract(self, vault):
        vault.store_track("agent-a", "code", "event", "task-1", {"version": 1})
        vault.store_track("agent-a", "code", "event", "task-1", {"version": 2})

        rows = vault.conn.execute(
            """
            SELECT value FROM agent_memory_tracks
            WHERE agent_id='agent-a' AND lane='code' AND track_type='event' AND key='task-1'
            """
        ).fetchall()

        assert len(rows) == 1
        assert vault.retrieve_track("agent-a", "code", "event", "task-1") == {"version": 2}
