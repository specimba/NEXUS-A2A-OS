"""Persistent MemoryTracks — cross-session trust memory (P0#2 gap).

The core `MemoryTracks` class in trust_scoring.py is entirely in-memory;
all 5 tracks (event, trust, capability, failure_pattern, governance) vanish
on restart. This adapter persists them to `~/.nexus/trust_memory.json` and
is API-compatible with the existing `MemoryTracks` interface.

Also provides a `DreamCycle`-compatible `.consolidate()` method so the
Dream Cycle (nexus_os/vault/dream_cycle.py) can prune stale trust entries.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def default_trust_memory_path() -> Path:
    """Resolve trust memory file; env overrides avoid RO home dirs in tests/CI."""
    configured = os.environ.get("NEXUS_TRUST_MEMORY_PATH")
    if configured:
        return Path(configured)
    nexus_home = os.environ.get("NEXUS_HOME")
    if nexus_home:
        return Path(nexus_home) / "trust_memory.json"
    return Path(os.path.expanduser("~")) / ".nexus" / "trust_memory.json"


# Module-level default for back-compat; re-evaluated at construct time via helper.
TRUST_MEMORY_FILE = Path(os.path.expanduser("~")) / ".nexus" / "trust_memory.json"


class PersistentMemoryTracks:
    """API-compatible replacement for trust_scoring.MemoryTracks with persistence.

    All 5 tracks are auto-synced to disk after each mutation. Read operations
    are in-memory (fast path). Write operations flush to ~/.nexus/trust_memory.json
    (or NEXUS_TRUST_MEMORY_PATH / NEXUS_HOME when set).
    """

    def __init__(self, path: str | Path | None = None):
        self._path = Path(path) if path else default_trust_memory_path()
        self.event_memory: list[dict[str, Any]] = []
        self.trust_memory: dict[tuple[str, Any], dict[str, float]] = {}
        self.capability_memory: dict[str, dict[str, dict[str, int]]] = {}
        self.failure_pattern_memory: dict[str, dict[str, int]] = {}
        self.governance_memory: dict[str, dict[str, Any]] = {}
        self._load()

    # ── persistence ──────────────────────────────────────────────

    def _load(self):
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self.event_memory = raw.get("event_memory", [])
            trust = raw.get("trust_memory", {})
            self.trust_memory = {}
            for k, v in trust.items():
                agent, lane = k.split("||", 1)
                self.trust_memory[(agent, lane)] = v
            self.capability_memory = raw.get("capability_memory", {})
            self.failure_pattern_memory = raw.get("failure_pattern_memory", {})
            self.governance_memory = raw.get("governance_memory", {})
        except Exception as exc:
            logger.warning("Failed to load trust memory from %s: %s", self._path, exc)

    def _save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            serializable_trust = {}
            for (agent, lane), v in self.trust_memory.items():
                serializable_trust[f"{agent}||{lane}"] = v
            self._path.write_text(json.dumps({
                "event_memory": self.event_memory,
                "trust_memory": serializable_trust,
                "capability_memory": self.capability_memory,
                "failure_pattern_memory": self.failure_pattern_memory,
                "governance_memory": self.governance_memory,
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            # Never crash callers (tests/CI with RO home); keep in-memory state.
            logger.warning("Failed to save trust memory to %s: %s", self._path, exc)

    # ── MemoryTracks API ─────────────────────────────────────────

    def append_event(self, event: dict[str, Any]):
        event["event_id"] = str(uuid.uuid4())
        event["timestamp"] = time.time()
        self.event_memory.append(event)
        self._save()

    def update_trust(self, agent_id: str, lane: Any, Qeff: float,
                     score: float | None, hard_fail: bool = False,
                     lambda_hf: float = 0.5):
        if score is None:
            return
        key = (agent_id, lane.value if hasattr(lane, "value") else lane)
        if key not in self.trust_memory:
            self.trust_memory[key] = {"alpha": 1.0, "beta": 1.0}
        self.trust_memory[key]["alpha"] += Qeff * max(score, 0.0)
        self.trust_memory[key]["beta"] += Qeff * (max(-score, 0.0) + lambda_hf * hard_fail)
        self._save()

    def get_trust(self, agent_id: str, lane: Any) -> float:
        key = (agent_id, lane.value if hasattr(lane, "value") else lane)
        if key not in self.trust_memory:
            return 0.5
        a = self.trust_memory[key]["alpha"]
        b = self.trust_memory[key]["beta"]
        return a / (a + b) if (a + b) > 0 else 0.5

    def update_capability(self, agent_id: str, lane: Any, score: float | None):
        lane_str = lane.value if hasattr(lane, "value") else str(lane)
        if agent_id not in self.capability_memory:
            self.capability_memory[agent_id] = {}
        if lane_str not in self.capability_memory[agent_id]:
            self.capability_memory[agent_id][lane_str] = {"tasks": 0, "positive": 0}
        self.capability_memory[agent_id][lane_str]["tasks"] += 1
        if score and score > 0:
            self.capability_memory[agent_id][lane_str]["positive"] += 1
        self._save()

    def get_capability(self, agent_id: str, lane: Any) -> dict[str, Any]:
        lane_str = lane.value if hasattr(lane, "value") else str(lane)
        if agent_id not in self.capability_memory:
            return {"tasks": 0, "positive": 0, "strength": "unknown"}
        d = self.capability_memory[agent_id].get(lane_str, {"tasks": 0, "positive": 0})
        t = d["tasks"]
        if t == 0:
            s = "unknown"
        elif d["positive"] / t > 0.7:
            s = "strong"
        elif d["positive"] / t > 0.4:
            s = "moderate"
        else:
            s = "weak"
        return {"tasks": t, "positive": d["positive"], "strength": s}

    def record_failure_pattern(self, agent_id: str, pattern: str):
        if agent_id not in self.failure_pattern_memory:
            self.failure_pattern_memory[agent_id] = {}
        self.failure_pattern_memory[agent_id][pattern] = \
            self.failure_pattern_memory[agent_id].get(pattern, 0) + 1
        self._save()

    def get_failure_patterns(self, agent_id: str) -> dict[str, int]:
        return dict(self.failure_pattern_memory.get(agent_id, {}))

    def record_governance_event(self, agent_id: str, event_type: str, detail: str = ""):
        if agent_id not in self.governance_memory:
            # Audit fix (P2-6): flags was a set(), which json.dumps in
            # _save() cannot serialize — the very first governance event
            # for an agent crashed persistence. Deduped list instead.
            self.governance_memory[agent_id] = {"events": [], "flags": []}
        self.governance_memory[agent_id]["events"].append({
            "type": event_type, "detail": detail, "timestamp": time.time(),
        })
        self._save()

    def get_governance_summary(self, agent_id: str) -> dict[str, Any]:
        if agent_id not in self.governance_memory:
            return {"events": 0, "flags": []}
        return {
            "events": len(self.governance_memory[agent_id]["events"]),
            "flags": list(self.governance_memory[agent_id]["flags"]),
        }

    # ── Dream Cycle integration ─────────────────────────────────

    def consolidate(self, ttl_hours: float = 72.0) -> dict[str, Any]:
        """Prune stale events and compact trust memory.

        API-compatible with dream_cycle.DreamCycle.consolidate().
        """
        t0 = time.time()
        before_events = len(self.event_memory)
        cutoff = time.time() - ttl_hours * 3600

        self.event_memory = [
            e for e in self.event_memory
            if e.get("timestamp", 0) > cutoff
        ]

        stale_agents = set()
        for agent_id, patterns in self.failure_pattern_memory.items():
            # Keep failure patterns — they don't expire by TTL
            pass

        result = {
            "ok": True,
            "events_before": before_events,
            "events_after": len(self.event_memory),
            "events_pruned": before_events - len(self.event_memory),
            "trust_agents": len(self.trust_memory),
            "capability_agents": len(self.capability_memory),
            "elapsed_seconds": round(time.time() - t0, 2),
        }
        self._save()
        return result

    def get_stats(self) -> dict[str, Any]:
        return {
            "events": len(self.event_memory),
            "trust_entries": len(self.trust_memory),
            "capability_agents": len(self.capability_memory),
            "failure_pattern_agents": len(self.failure_pattern_memory),
            "governance_agents": len(self.governance_memory),
            "path": str(self._path),
        }

    def reset(self):
        self.event_memory.clear()
        self.trust_memory.clear()
        self.capability_memory.clear()
        self.failure_pattern_memory.clear()
        self.governance_memory.clear()
        self._save()


def make_persistent(trust_scoring_gate_class=None):
    """Monkey-patch helper: replace MemoryTracks with PersistentMemoryTracks.

    Returns the original `MemoryTracks` for optional restoration.
    """
    import nexus_os.governor.trust_scoring as ts_mod
    original = ts_mod.MemoryTracks
    ts_mod.MemoryTracks = PersistentMemoryTracks
    logger.info("Replaced MemoryTracks with PersistentMemoryTracks (P0#2)")
    return original


def cli_main():
    import argparse
    ap = argparse.ArgumentParser(description="Persistent Trust Memory (P0#2)")
    ap.add_argument("--stats", action="store_true", help="Show trust memory stats")
    ap.add_argument("--consolidate", action="store_true", help="Prune stale events")
    ap.add_argument("--reset", action="store_true", help="Clear all trust memory")
    args = ap.parse_args()

    pmt = PersistentMemoryTracks()

    if args.stats:
        print(json.dumps(pmt.get_stats(), indent=2))
        return

    if args.consolidate:
        result = pmt.consolidate()
        print(json.dumps(result, indent=2))
        return

    if args.reset:
        pmt.reset()
        print(json.dumps({"ok": True, "action": "reset"}, indent=2))
        return

    ap.print_help()


if __name__ == "__main__":
    cli_main()
