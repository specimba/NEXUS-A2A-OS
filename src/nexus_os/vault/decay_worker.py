"""vault/decay_worker.py — Mira Earn-or-Fade Decay Worker"""
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
