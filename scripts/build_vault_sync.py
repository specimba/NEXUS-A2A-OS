#!/usr/bin/env python3
"""Phase 1.7: Trust DB Sync & Mira Decay Builder"""
import os

VAULT_DIR = os.path.join("src", "nexus_os", "vault")
TEST_DIR = os.path.join("tests", "vault")

SYNC_CODE = '''"""vault/trust_store.py — Persistent Trust Cache Layer"""
from typing import Dict, Any
from nexus_os.vault.manager import VaultManager
from nexus_os.monitoring.strategies import warm_path

class TrustStore:
    """Cache layer over persistent DB for agent trust tracking."""
    def __init__(self, vault: VaultManager):
        self.vault = vault
        self._cache: Dict[str, Dict[str, float]] = {}

    def load_agent_trust(self, agent_id: str, lane: str) -> Dict[str, float]:
        """Load from Vault (Cold/Warm) or Cache (Hot)."""
        cache_key = f"{agent_id}::{lane}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        val = self.vault.retrieve_track(agent_id, lane, "trust", "alpha_beta")
        default_trust = {"alpha": 1.0, "beta": 1.0}
        
        self._cache[cache_key] = val or default_trust
        return self._cache[cache_key]

    @warm_path
    def persist_trust(self, agent_id: str, lane: str, alpha: float, beta: float):
        """Asynchronously flush updated trust to the persistent 5-Track DB."""
        cache_key = f"{agent_id}::{lane}"
        trust_data = {"alpha": alpha, "beta": beta}
        self._cache[cache_key] = trust_data
        
        self.vault.store_track(agent_id, lane, "trust", "alpha_beta", trust_data)
        return {"status": "persisting"}
'''

DECAY_CODE = '''"""vault/decay_worker.py — Mira Earn-or-Fade Decay Worker"""
import logging
from typing import Dict, Any
from nexus_os.vault.manager import VaultManager

logger = logging.getLogger(__name__)

class MiraDecayWorker:
    """Applies time-based decay to agent trust and wisdom tracks."""
    def __init__(self, vault: VaultManager, decay_rate: float = 0.05):
        self.vault = vault
        self.decay_rate = decay_rate

    def apply_decay(self) -> int:
        """Cold path execution: Scans DB and applies decay to stagnant trust scores."""
        records_updated = 0
        with self.vault.conn:
            # Fetch all trust records
            cur = self.vault.conn.execute("SELECT agent_id, lane, value FROM agent_memory_tracks WHERE track_type = 'trust' AND key = 'alpha_beta'")
            rows = cur.fetchall()
            
            import json
            for row in rows:
                try:
                    data = json.loads(row['value'])
                    alpha = data.get('alpha', 1.0)
                    # Only decay alpha (success), leaving beta (failures/baseline) intact
                    if alpha > 1.0:
                        new_alpha = max(1.0, alpha * (1.0 - self.decay_rate))
                        if new_alpha != alpha:
                            data['alpha'] = new_alpha
                            self.vault.conn.execute(
                                "UPDATE agent_memory_tracks SET value = ? WHERE agent_id = ? AND lane = ? AND track_type = 'trust' AND key = 'alpha_beta'",
                                (json.dumps(data), row['agent_id'], row['lane'])
                            )
                            records_updated += 1
                except Exception as e:
                    logger.error(f"Failed to decay trust for {row['agent_id']}: {e}")
                    
        return records_updated
'''

TEST_CODE = '''"""tests/vault/test_trust_sync.py — DB Sync & Decay Diagnostics"""
import pytest
import time
from nexus_os.vault.manager import VaultManager
from nexus_os.vault.trust_store import TrustStore
from nexus_os.vault.decay_worker import MiraDecayWorker

@pytest.fixture
def vault():
    return VaultManager()

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
'''

# Write Files
with open(os.path.join(VAULT_DIR, "trust_store.py"), "w", encoding="utf-8") as f:
    f.write(SYNC_CODE)
with open(os.path.join(VAULT_DIR, "decay_worker.py"), "w", encoding="utf-8") as f:
    f.write(DECAY_CODE)
with open(os.path.join(TEST_DIR, "test_trust_sync.py"), "w", encoding="utf-8") as f:
    f.write(TEST_CODE)

print("[✅] Created trust_store.py, decay_worker.py, and test_trust_sync.py")
print("Next: pytest tests/vault/test_trust_sync.py -v")