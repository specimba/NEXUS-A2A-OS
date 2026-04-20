"""NEXUS OS — Vault module: S-P-E-W memory (Store/Persist/Earn/Withdraw)."""
from enum import Enum
from typing import List, Dict, Any, Optional
import time

class Track(Enum):
    EVENT = "event"
    TRUST = "trust"
    CAP = "cap"
    FAIL = "fail"
    GOV = "gov"

class Vault:
    def __init__(self):
        self._store: List[Dict[str, Any]] = []

    def store(self, agent: str, track: Track, cat: str, key: str, val: Any, score: float) -> str:
        entry = {
            "id": f"{agent}-{key}-{int(time.time() * 1000)}",
            "agent": agent,
            "track": track.value,
            "cat": cat,
            "key": key,
            "val": val,
            "score": score,
            "ts": time.time(),
        }
        self._store.append(entry)
        return entry["id"]

    def query(self, agent: str, track: Optional[Track] = None, limit: int = 10) -> List[dict]:
        results = [e for e in self._store if e["agent"] == agent]
        if track:
            results = [e for e in results if e["track"] == track.value]
        return sorted(results, key=lambda x: x["ts"], reverse=True)[:limit]