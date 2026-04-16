#!/usr/bin/env python3
"""Phase 1.5: Vault 5-Track Memory Schema Builder"""
import os

VAULT_DIR = os.path.join("src", "nexus_os", "vault")
TEST_DIR = os.path.join("tests", "vault")
os.makedirs(VAULT_DIR, exist_ok=True)
os.makedirs(TEST_DIR, exist_ok=True)

VAULT_CODE = '''"""vault/manager.py — 5-Track Memory & S-P-E-W Hierarchy"""
import sqlite3
import json
import threading
from typing import Dict, Any, Optional

class VaultManager:
    """
    Manages the 5-Track Memory Schema for Nexus OS Agents.
    Tracks: 'event', 'trust', 'capability', 'failure_pattern', 'governance'
    """
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory_tracks (
                    agent_id TEXT NOT NULL,
                    lane TEXT NOT NULL,
                    track_type TEXT CHECK(track_type IN ('event', 'trust', 'capability', 'failure_pattern', 'governance')),
                    key TEXT NOT NULL,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (agent_id, lane, track_type, key)
                )
            """)

    def store_track(self, agent_id: str, lane: str, track_type: str, key: str, value: Any):
        """Upsert a record into the specific memory track."""
        with self.conn:
            self.conn.execute("""
                INSERT INTO agent_memory_tracks (agent_id, lane, track_type, key, value, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(agent_id, lane, track_type, key) 
                DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
            """, (agent_id, lane, track_type, key, json.dumps(value)))

    def retrieve_track(self, agent_id: str, lane: str, track_type: str, key: str) -> Optional[Any]:
        """Retrieve a specific record from a memory track."""
        cur = self.conn.execute("""
            SELECT value FROM agent_memory_tracks 
            WHERE agent_id=? AND lane=? AND track_type=? AND key=?
        """, (agent_id, lane, track_type, key))
        row = cur.fetchone()
        return json.loads(row['value']) if row else None
        
    def get_agent_profile(self, agent_id: str, lane: str) -> Dict[str, Dict[str, Any]]:
        """Retrieve the full 5-track profile for an agent in a specific lane."""
        cur = self.conn.execute("""
            SELECT track_type, key, value FROM agent_memory_tracks 
            WHERE agent_id=? AND lane=?
        """, (agent_id, lane))
        
        # Initialize the 5 tracks
        results = {
            'event': {}, 'trust': {}, 'capability': {}, 
            'failure_pattern': {}, 'governance': {}
        }
        
        for row in cur.fetchall():
            results[row['track_type']][row['key']] = json.loads(row['value'])
            
        return results
'''

TEST_CODE = '''"""tests/vault/test_manager.py — 5-Track Memory Diagnostics"""
import pytest
from nexus_os.vault.manager import VaultManager

@pytest.fixture
def vault():
    # Use in-memory SQLite for fast testing
    return VaultManager()

def test_5_track_schema_creation(vault):
    # Verify the table exists and accepts valid track types
    vault.store_track("agent-1", "research", "trust", "alpha", 1.5)
    vault.store_track("agent-1", "research", "trust", "beta", 0.5)
    
    val = vault.retrieve_track("agent-1", "research", "trust", "alpha")
    assert val == 1.5

def test_track_type_constraint(vault):
    # Verify the CHECK constraint blocks invalid track types
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        vault.store_track("agent-1", "research", "invalid_track", "key", "value")

def test_get_full_agent_profile(vault):
    vault.store_track("agent-x", "code", "trust", "score", 0.92)
    vault.store_track("agent-x", "code", "capability", "python", "expert")
    vault.store_track("agent-x", "code", "failure_pattern", "syntax", 2)
    
    profile = vault.get_agent_profile("agent-x", "code")
    
    assert profile["trust"]["score"] == 0.92
    assert profile["capability"]["python"] == "expert"
    assert profile["failure_pattern"]["syntax"] == 2
    assert profile["governance"] == {}  # Empty but initialized
'''

# Write Vault
with open(os.path.join(VAULT_DIR, "manager.py"), "w", encoding="utf-8") as f:
    f.write(VAULT_CODE)
print(f"[✅] Created {os.path.join(VAULT_DIR, 'manager.py')}")

# Write Tests
with open(os.path.join(TEST_DIR, "test_manager.py"), "w", encoding="utf-8") as f:
    f.write(TEST_CODE)
print(f"[✅] Created {os.path.join(TEST_DIR, 'test_manager.py')}")

print("\n[🚀] Vault 5-Track Memory Schema Ready.")