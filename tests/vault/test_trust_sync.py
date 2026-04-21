import pytest
"""tests/vault/test_trust_sync.py — DB Sync & Decay Diagnostics"""
import pytest
import time
from nexus_os.vault.manager import VaultManager
from nexus_os.vault.trust_store import TrustStore
from nexus_os.vault.decay_worker import MiraDecayWorker

@pytest.fixture
def vault(tmp_path):
    vault = VaultManager(str(tmp_path / "trust_sync.db"))
    vault.conn.execute("""
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
    vault.conn.commit()
    return vault

def test_trust_store_loads_defaults(vault):
    store = TrustStore(vault)
    trust = store.load_agent_trust("agent-new", "code")
    assert trust["alpha"] == 1.0
    assert trust["beta"] == 1.0

def test_trust_store_persists_async(vault):
    store = TrustStore(vault)
    
    # Fire async persist
    res = store.persist_trust("agent-1", "research", 5.5, 2.0)
    assert res["status"] == "queued"
    
    # Wait briefly for warm_path thread to finish writing
    time.sleep(0.1)
    
    # Verify it hit the DB
    db_val = vault.retrieve_track("agent-1", "research", "trust", "alpha_beta")
    assert db_val["alpha"] == 5.5
    assert db_val["beta"] == 2.0

def test_mira_decay_worker(vault):
    store = TrustStore(vault)
    # Persist high trust
    store.persist_trust("agent-x", "ops", 10.0, 1.0)
    time.sleep(0.1) # allow thread to write
    
    worker = MiraDecayWorker(vault, decay_rate=0.10) # 10% decay
    updated = worker.apply_decay()
    
    assert updated == 1
    db_val = vault.retrieve_track("agent-x", "ops", "trust", "alpha_beta")
    assert db_val["alpha"] == 9.0  # 10.0 * 0.9
    assert db_val["beta"] == 1.0   # Beta remains untouched
