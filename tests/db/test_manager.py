"""tests/db/test_manager.py — DatabaseManager v3 tests

Covers:
- StandardAdapter CRUD
- DatabaseManager connection lifecycle
- Schema setup (all 6 tables)
- Connection pool limits
- Thread safety (multi-thread access)
- Close/cleanup
- Unencrypted fallback policy
"""

import os
import sqlite3
import threading
import pytest

from nexus_os.db.manager import (
    DBConfig,
    DatabaseManager,
    StandardAdapter,
)


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def adapter(db_path):
    a = StandardAdapter(db_path)
    yield a
    a.close()


@pytest.fixture
def db_manager(db_path):
    config = DBConfig(db_path=db_path, passphrase="", encrypted=False, allow_unencrypted=True)
    mgr = DatabaseManager(config)
    yield mgr
    mgr.close()


# ── StandardAdapter ──────────────────────────────────────────────────

class TestStandardAdapter:
    def test_create_and_query(self, adapter):
        adapter.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
        adapter.execute("INSERT INTO test VALUES (1, 'hello')")
        adapter.commit()
        cursor = adapter.execute("SELECT val FROM test WHERE id = 1")
        row = adapter.fetchone(cursor)
        assert row == ("hello",)

    def test_executemany(self, adapter):
        adapter.execute("CREATE TABLE nums (n INTEGER)")
        adapter.executemany("INSERT INTO nums VALUES (?)", [(i,) for i in range(100)])
        adapter.commit()
        cursor = adapter.execute("SELECT COUNT(*) FROM nums")
        assert adapter.fetchone(cursor)[0] == 100

    def test_fetchall(self, adapter):
        adapter.execute("CREATE TABLE items (name TEXT)")
        for name in ["a", "b", "c"]:
            adapter.execute("INSERT INTO items VALUES (?)", (name,))
        adapter.commit()
        cursor = adapter.execute("SELECT name FROM items ORDER BY name")
        rows = adapter.fetchall(cursor)
        assert len(rows) == 3
        assert rows[0] == ("a",)

    def test_pragma_wal_mode(self, adapter):
        cursor = adapter.execute("PRAGMA journal_mode")
        mode = adapter.fetchone(cursor)[0]
        assert mode == "wal"


# ── DatabaseManager ──────────────────────────────────────────────────

class TestDatabaseManager:
    def test_get_connection(self, db_manager):
        conn = db_manager.get_connection()
        assert conn is not None

    def test_setup_schema(self, db_manager):
        result = db_manager.setup_schema()
        assert result is True

    def test_schema_tables_exist(self, db_manager):
        db_manager.setup_schema()
        conn = db_manager.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in conn.fetchall(cursor)]
        assert "agent_registry" in tables
        assert "tasks" in tables
        assert "audit_logs" in tables
        assert "agent_reputation" in tables
        assert "memory_records" in tables
        assert "task_dependencies" in tables

    def test_schema_idempotent(self, db_manager):
        db_manager.setup_schema()
        db_manager.setup_schema()  # should not raise

    def test_close(self, db_path):
        config = DBConfig(db_path=db_path, passphrase="", encrypted=False, allow_unencrypted=True)
        mgr = DatabaseManager(config)
        mgr.get_connection()
        mgr.close()
        assert mgr._connection_count == 0

    def test_close_all_alias(self, db_manager):
        db_manager.get_connection()
        db_manager.close_all()
        assert db_manager._connection_count == 0


# ── Connection Pool ──────────────────────────────────────────────────

class TestConnectionPool:
    def test_pool_limit_enforcement(self, db_path):
        config = DBConfig(db_path=db_path, passphrase="", encrypted=False, allow_unencrypted=True)
        mgr = DatabaseManager(config)
        mgr._max_connections = 3
        connections = []
        for _ in range(3):
            connections.append(mgr.get_connection())
        with pytest.raises(RuntimeError, match="Connection limit"):
            mgr.get_connection()
        mgr.close()


# ── Encryption Fallback ─────────────────────────────────────────────

class TestEncryptionPolicy:
    def test_encrypted_without_sqlcipher_hard_fails(self, db_path):
        config = DBConfig(
            db_path=db_path, passphrase="secret",
            encrypted=True, allow_unencrypted=False,
        )
        mgr = DatabaseManager(config)
        with pytest.raises(ImportError):
            mgr.get_connection()

    def test_encrypted_fallback_when_allowed(self, db_path):
        config = DBConfig(
            db_path=db_path, passphrase="secret",
            encrypted=True, allow_unencrypted=True,
        )
        mgr = DatabaseManager(config)
        conn = mgr.get_connection()
        assert conn is not None
        mgr.close()


# ── Thread Safety ────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_schema_setup(self, db_path):
        config = DBConfig(db_path=db_path, passphrase="", encrypted=False, allow_unencrypted=True)
        mgr = DatabaseManager(config)
        mgr._max_connections = 10
        errors = []

        def worker():
            try:
                mgr.setup_schema()
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        mgr.close()
        assert len(errors) == 0, f"Errors: {errors}"
