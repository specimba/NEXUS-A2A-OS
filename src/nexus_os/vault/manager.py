"""vault/manager.py — 5-Track Memory & S-P-E-W Hierarchy"""
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
        self._uri = db_path.startswith("file:")
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(
                self.db_path,
                uri=self._uri,
                check_same_thread=False,
                timeout=30,
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    lane TEXT NOT NULL,
                    track_type TEXT CHECK(track_type IN ('event', 'trust', 'capability', 'failure_pattern', 'governance')),
                    key TEXT NOT NULL,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(agent_id, lane, track_type, key)
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
        
        results = {
            'event': {}, 'trust': {}, 'capability': {}, 
            'failure_pattern': {}, 'governance': {}
        }
        
        for row in cur.fetchall():
            results[row['track_type']][row['key']] = json.loads(row['value'])
            
        return results

    # ── OPUSman v6 memory hooks ─────────────────────────────────────────────────
    def search_before_generation(self, task: str, context: dict) -> list:
        """
        OPUSman v6 hook: recall prior memories before generation.
        Searches event + trust tracks for relevant context.
        Returns list of prior memory dicts.
        """
        if not task:
            return []
        agent_id = (context or {}).get("agent_id", "default")
        lane     = (context or {}).get("lane", "default")
        task_lower = task.lower()
        results = []
        with self.conn:
            cur = self.conn.execute("""
                SELECT key, value FROM agent_memory_tracks
                WHERE agent_id=? AND lane=?
                ORDER BY updated_at DESC
                LIMIT 5
            """, (agent_id, lane))
            for row in cur.fetchall():
                key = row["key"]
                val = json.loads(row["value"])
                # Lightweight keyword relevance filter
                if any(w in key.lower() or (isinstance(val, str) and w in val.lower())
                       for w in task_lower.split()[:5]):
                    results.append({"key": key, "value": val})
        return results

    def add_after_response(self, task: str, summary: str, evidence: list):
        """
        OPUSman v6 hook: persist memory after response.
        Stores the generation outcome in the event track.
        """
        if not task:
            return
        agent_id = "default"
        lane     = "default"
        entry = {"task": task[:200], "summary": summary[:500] if summary else "", "evidence": evidence or []}
        self.store_track(agent_id, lane, "event", f"gen_{int(__import__('time').time())}", entry)


# Minimal stub for test collection
class PoisoningError(Exception): pass

