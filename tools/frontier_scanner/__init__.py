"""
NEXUS Frontier Scanner — silent-first watcher for new model discoveries.

Pipeline:
    SIGNAL (10 channels, catalog pull every 15min)
       ↓
    DELTA DETECT (vs known_provider_catalogue.json)
       ↓
    ONE-SHOT VALIDATE (single 200-token call, 4hr cycle)
       ↓
    WATCHLIST (3-day monitor, 1 call/day per ID)
       ↓
    STABILIZED (auto-add to registry in quarantine lane per NEXUS Modal Strategy)
"""
__version__ = "0.1.0"
