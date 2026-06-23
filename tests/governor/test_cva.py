import pytest
import sqlite3
import json
from typing import Dict, Any
from nexus_os.governor.base import _CVAVerifier, DatabaseManager

class MockDBAdapter:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_registry (
                agent_id TEXT PRIMARY KEY,
                model_id TEXT,
                capabilities TEXT,
                traits TEXT,
                status TEXT DEFAULT 'active'
            )
        """)

    def execute(self, query, params=()):
        return self.conn.execute(query, params)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

class MockDBManager:
    def __init__(self):
        self.adapter = MockDBAdapter()

    def get_connection(self):
        return self.adapter

    def close(self):
        self.adapter.close()


@pytest.fixture
def db_mgr():
    mgr = MockDBManager()
    yield mgr
    mgr.close()


@pytest.fixture
def verifier(db_mgr):
    return _CVAVerifier(db_mgr)


def test_prohibited_actions(verifier):
    # Action matching prohibited pattern from constitution.yaml should fail
    is_ok, reason = verifier.verify_alignment("agent-1", "rm -rf /", {})
    assert is_ok is False
    assert "prohibited pattern" in reason


def test_admin_system_default_traits(verifier):
    # admin agent should have default high-privilege traits and pass critical checks
    is_ok, reason = verifier.verify_alignment("admin", "delete_vault", {})
    assert is_ok is True
    assert reason == "OK"


def test_cva_traits_lookup_text(db_mgr, verifier):
    # Save agent traits as a comma-separated string
    db_mgr.adapter.execute(
        "INSERT INTO agent_registry (agent_id, model_id, traits) VALUES (?, ?, ?)",
        ("agent-coder", "model-1", "coder, contributor")
    )
    db_mgr.adapter.commit()

    # Medium risk action should be allowed for a coder
    is_ok, reason = verifier.verify_alignment("agent-coder", "write_file", {})
    assert is_ok is True
    assert reason == "OK"

    # Critical risk action should be blocked for a coder
    is_ok, reason = verifier.verify_alignment("agent-coder", "delete_something", {})
    assert is_ok is False
    assert "requires one of" in reason


def test_cva_traits_lookup_json_list(db_mgr, verifier):
    # Save agent traits as a JSON list
    db_mgr.adapter.execute(
        "INSERT INTO agent_registry (agent_id, model_id, traits) VALUES (?, ?, ?)",
        ("agent-authority", "model-1", json.dumps(["authority", "reviewer"]))
    )
    db_mgr.adapter.commit()

    # Critical action allowed for authority
    is_ok, reason = verifier.verify_alignment("agent-authority", "delete_something", {})
    assert is_ok is True
    assert reason == "OK"


def test_cva_fallback_capabilities(db_mgr, verifier):
    # Save traits inside JSON-serialized capabilities
    caps = {"traits": ["analyst"]}
    db_mgr.adapter.execute(
        "INSERT INTO agent_registry (agent_id, model_id, capabilities) VALUES (?, ?, ?)",
        ("agent-analyst", "model-1", json.dumps(caps))
    )
    db_mgr.adapter.commit()

    # Medium risk action allowed for analyst
    is_ok, reason = verifier.verify_alignment("agent-analyst", "write_file", {})
    assert is_ok is True
    assert reason == "OK"


def test_cva_unaligned_agent(db_mgr, verifier):
    # Agent with empty traits
    db_mgr.adapter.execute(
        "INSERT INTO agent_registry (agent_id, model_id, traits) VALUES (?, ?, ?)",
        ("agent-guest", "model-1", "")
    )
    db_mgr.adapter.commit()

    # Medium risk action blocked for guest with empty traits
    is_ok, reason = verifier.verify_alignment("agent-guest", "write_file", {})
    assert is_ok is False
    assert "requires traits" in reason
