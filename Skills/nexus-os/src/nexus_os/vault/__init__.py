"""NEXUS OS — Vault module: S-P-E-W memory (Store/Persist/Earn/Withdraw).

P1b upgrade: 8-channel SuperLocalMemory v2 model.
Added TEMPORAL_CAUSAL (channel 7) + ONTOLOGICAL (channel 8).
"""
from enum import Enum
from typing import List, Dict, Any, Optional
import time


class Channel(Enum):
    """8 memory channels (SuperLocalMemory v2)."""
    SEMANTIC       = 0   # long-term facts, concepts
    EPISODIC       = 1   # session events, timestamped
    WORKING        = 2   # short-term context
    PROCEDURAL     = 3   # skills, how-to
    INTENTIONAL    = 4   # goals, plans, motivations
    AFFECTIVE      = 5   # emotional valence, preference signals
    TEMPORAL_CAUSAL = 6  # causal chains between decisions (NEW: v2)
    ONTOLOGICAL    = 7   # entity hierarchies, type relationships (NEW: v2)


class Track(Enum):
    EVENT = "event"
    TRUST = "trust"
    CAP   = "cap"
    FAIL  = "fail"
    GOV   = "gov"


class Vault:
    def __init__(self):
        self._store: List[Dict[str, Any]] = []

    def store(
        self,
        agent: str,
        track: Track,
        cat: str,
        key: str,
        val: Any,
        score: float,
        channel: Optional[Channel] = None,
    ) -> str:
        entry = {
            "id": f"{agent}-{key}-{int(time.time() * 1000)}",
            "agent": agent,
            "track": track.value,
            "cat": cat,
            "key": key,
            "val": val,
            "score": score,
            "ts": time.time(),
            "channel": channel.value if channel else None,
        }
        self._store.append(entry)
        return entry["id"]

    def query(
        self,
        agent: str,
        track: Optional[Track] = None,
        limit: int = 10,
    ) -> List[dict]:
        results = [e for e in self._store if e["agent"] == agent]
        if track:
            results = [e for e in results if e["track"] == track.value]
        return sorted(results, key=lambda x: x["ts"], reverse=True)[:limit]

    # ── P1b: 8-channel queries ──────────────────────────────────────────

    def store_causal(
        self,
        agent: str,
        cause: str,
        effect: str,
        evidence: str,
        score: float = 0.8,
    ) -> str:
        """Channel 6 — TEMPORAL_CAUSAL: store causal dependency between memories."""
        return self.store(
            agent, Track.GOV, "causal",
            f"{cause}→{effect}",
            {"cause": cause, "effect": effect, "evidence": evidence},
            score,
            channel=Channel.TEMPORAL_CAUSAL,
        )

    def store_ontology(
        self,
        agent: str,
        entity: str,
        parent: str,
        rel: str = "is-a",
        score: float = 0.8,
    ) -> str:
        """Channel 7 — ONTOLOGICAL: store entity hierarchy relationship."""
        return self.store(
            agent, Track.GOV, "ontology",
            f"{entity}:{rel}:{parent}",
            {"entity": entity, "parent": parent, "rel": rel},
            score,
            channel=Channel.ONTOLOGICAL,
        )

    def query_channel(
        self,
        agent: str,
        channel: Channel,
        limit: int = 10,
    ) -> List[dict]:
        """Query all entries in a specific channel."""
        results = [
            e for e in self._store
            if e["agent"] == agent and e.get("channel") == channel.value
        ]
        return sorted(results, key=lambda x: x["ts"], reverse=True)[:limit]
