"""vault/trust_store.py — Persistent Trust Cache Layer"""
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
