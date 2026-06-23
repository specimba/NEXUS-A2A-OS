import pytest
import time
import json
import sqlite3
from typing import Dict, Any
from nexus_os.db.manager import DatabaseManager
from nexus_os.security.t3_guard import T3CrossSessionGuard
from nexus_os.security.guard_router import GuardRouter, RoutingDecision

class MockDBAdapter:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS t3_session_prompts (
                session_id TEXT,
                prompt_hash TEXT,
                timestamp REAL,
                is_system_initiated INTEGER,
                prompt_length INTEGER
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


def test_t3_guard_log_and_check(db_mgr):
    guard = T3CrossSessionGuard(db_mgr, system_threshold=3)

    # Log 3 system prompts
    guard.log_prompt("sess-1", "cron: healthcheck 1", is_system=True)
    guard.log_prompt("sess-1", "cron: healthcheck 2", is_system=True)
    guard.log_prompt("sess-1", "cron: healthcheck 3", is_system=True)

    # Check drift on system prompt - should NOT escalate since it's system-initiated itself
    should_esc, score, reason = guard.check_drift_and_inflation("sess-1", "cron: healthcheck 4")
    assert should_esc is False

    # Check drift on user prompt - should ESCALATE
    should_esc, score, reason = guard.check_drift_and_inflation("sess-1", "user query asking for files")
    assert should_esc is True
    assert "T3-Anomaly" in reason
    assert score > 0.5


def test_t3_guard_spam_detection(db_mgr):
    guard = T3CrossSessionGuard(db_mgr, system_threshold=5)

    # Log 10 prompts in a row to simulate spam/loop
    for i in range(10):
        guard.log_prompt("sess-spam", f"hello {i}", is_system=False)

    should_esc, score, reason = guard.check_drift_and_inflation("sess-spam", "hello 10")
    assert should_esc is True
    assert "starter spam/loop detected" in reason
    assert score >= 0.5


def test_guard_router_t3_integration(db_mgr, monkeypatch):
    # Mock DatabaseManager singleton to return our MockDBManager
    monkeypatch.setattr(DatabaseManager, "get_connection", lambda self: db_mgr.adapter)
    
    # Mock classify to bypass torch model loading in unit tests
    monkeypatch.setattr(GuardRouter, "classify", lambda self, prompt, verbose=False, file_data=None: (RoutingDecision.SAFE, []))

    router = GuardRouter()

    # Log 10 prompts to trigger spam block
    session_id = "sess-integration-123"
    for i in range(9):
        router.route(prompt=f"user prompt {i}", session_id=session_id)

    # The 10th prompt should trigger a T3 block/escalation
    result = router.route(prompt="user prompt 10", session_id=session_id)
    assert result["decision"] == RoutingDecision.UNSAFE
    assert "L0-t3" in [t["tier"] for t in result["tiers"]]
    assert "T3 Temporal Block" in result["refusal"]
