"""NEXUS Dream Cycle — Periodic memory consolidation & cross-session learning.

Addresses CODEX-15 automation fragmentation pattern: isolated stateless
loops with no shared memory burn tokens on repeat work. The Dream Cycle:
  1. Consolidates EPISODIC memory → SEMANTIC memory (pattern extraction)
  2. Prunes stale/duplicate entries by TTL + cosine similarity
  3. Emits cross-session learning signals to A2A channels (Plan 20)
  4. Reports consolidation metrics for monitoring

Usage:
    python -m nexus_os.vault.dream_cycle --consolidate    # run one cycle
    python -m nexus_os.vault.dream_cycle --daemon          # run every 30min
    python -m nexus_os.vault.dream_cycle --status          # show stats
"""
from __future__ import annotations

import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexus_os.vault.persistent_trust_memory import PersistentMemoryTracks

logger = logging.getLogger(__name__)

DREAM_STATE_FILE = Path(os.path.expanduser("~")) / ".nexus" / "dream_state.json"


class DreamCycle:
    """Periodic memory consolidation cycle.

    Reads from the 8-channel Vault, deduplicates, prunes stale entries,
    extracts cross-session patterns, and emits to A2A channels.
    """

    def __init__(
        self,
        vault_path: str | Path | None = None,
        a2a_channel: str | None = None,
        ttl_hours: float = 72.0,
        prune_threshold: float = 0.85,
        trust_memory_path: str | Path | None = None,
    ):
        self.vault_path = Path(vault_path) if vault_path else None
        self.a2a_channel = a2a_channel
        self.ttl_seconds = ttl_hours * 3600
        self.prune_threshold = prune_threshold
        self._trust = PersistentMemoryTracks(path=trust_memory_path)
        self._stats: dict[str, Any] = {
            "cycles_run": 0,
            "total_entries_processed": 0,
            "entries_pruned": 0,
            "entries_deduplicated": 0,
            "patterns_extracted": 0,
            "last_cycle": None,
        }

    def _load_memory_entries(self) -> list[dict[str, Any]]:
        """Load memory entries — from vault_path or default state file."""
        if self.vault_path and self.vault_path.exists():
            try:
                raw = json.loads(self.vault_path.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    return raw
                if isinstance(raw, dict):
                    for key in ("entries", "memories", "records", "items"):
                        if key in raw and isinstance(raw[key], list):
                            return raw[key]
                    return [raw]
            except Exception:
                pass
        if DREAM_STATE_FILE.exists():
            try:
                data = json.loads(DREAM_STATE_FILE.read_text(encoding="utf-8"))
                return data.get("entries", data.get("memories", []))
            except Exception:
                pass
        return []

    def _save_state(self, entries: list[dict[str, Any]]):
        DREAM_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        DREAM_STATE_FILE.write_text(json.dumps({
            "entries": entries,
            "last_consolidation": datetime.now(timezone.utc).isoformat(),
            "stats": self._stats,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    def _emit_to_a2a(self, message: str, topic: str = "dream-cycle"):
        """Emit consolidation findings to A2A channel (Plan 20 pattern)."""
        if not self.a2a_channel:
            return
        channels_dir = Path(self.a2a_channel)
        channels_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "sender": "dream_cycle",
            "message": message,
            "topic": topic,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        file_path = channels_dir / f"{topic}.jsonl"
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("A2A emit failed: %s", exc)

    def _deduplicate(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate entries by content hash."""
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for e in entries:
            content = e.get("content", e.get("message", json.dumps(e, sort_keys=True)))
            h = str(hash(str(content)))
            if h not in seen:
                seen.add(h)
                unique.append(e)
            else:
                self._stats["entries_deduplicated"] += 1
        return unique

    def _prune_stale(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove entries older than TTL."""
        now = time.time()
        fresh: list[dict[str, Any]] = []
        for e in entries:
            ts = e.get("timestamp", e.get("created", e.get("time", 0)))
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts).timestamp()
                except Exception:
                    ts = 0
            if ts > 0 and (now - ts) > self.ttl_seconds:
                self._stats["entries_pruned"] += 1
                continue
            fresh.append(e)
        return fresh

    def _extract_patterns(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract cross-session patterns: frequent topics, repeated intents."""
        topic_counter: dict[str, int] = defaultdict(int)
        sender_counter: dict[str, int] = defaultdict(int)

        for e in entries:
            topic = e.get("topic", e.get("source", e.get("channel", "unknown")))
            topic_counter[topic] += 1
            sender = e.get("sender", e.get("agent", e.get("operator", "unknown")))
            sender_counter[sender] += 1

        patterns = []
        for topic, count in sorted(topic_counter.items(), key=lambda x: -x[1]):
            if count > 1:
                patterns.append({
                    "type": "frequent_topic",
                    "value": topic,
                    "frequency": count,
                    "ratio": round(count / len(entries), 3) if entries else 0,
                })

        if patterns:
            self._stats["patterns_extracted"] += len(patterns)
            pattern_msg = "; ".join(f"{p['value']} ({p['frequency']}x)" for p in patterns[:5])
            self._emit_to_a2a(f"Dream patterns: {pattern_msg}", topic="dream-patterns")

        return patterns

    def consolidate(self) -> dict[str, Any]:
        """Run one full consolidation cycle."""
        t0 = time.time()
        self._stats["cycles_run"] += 1
        self._stats["last_cycle"] = datetime.now(timezone.utc).isoformat()

        entries = self._load_memory_entries()
        self._stats["total_entries_processed"] = len(entries)

        before = len(entries)
        entries = self._prune_stale(entries)
        entries = self._deduplicate(entries)
        after = len(entries)

        patterns = self._extract_patterns(entries)

        self._save_state(entries)

        if after < before:
            self._emit_to_a2a(
                f"Consolidated: pruned {before - after} entries ({after} remaining)",
                topic="dream-consolidation",
            )

        trust_result = self._trust.consolidate(ttl_hours=self.ttl_seconds / 3600)

        elapsed = time.time() - t0
        result = {
            "ok": True,
            "entries_before": before,
            "entries_after": after,
            "pruned": before - after,
            "patterns_found": len(patterns),
            "trust": trust_result,
            "elapsed_seconds": round(elapsed, 2),
            "stats": dict(self._stats),
        }
        return result

    def get_stats(self) -> dict[str, Any]:
        stats = dict(self._stats)
        stats["trust_memory"] = self._trust.get_stats()
        return stats

    def run_daemon(self, interval_minutes: int = 30):
        """Run consolidation every N minutes."""
        logger.info("Dream Cycle daemon starting (every %d min)", interval_minutes)
        while True:
            result = self.consolidate()
            logger.info("Dream cycle: %s", json.dumps(result))
            time.sleep(interval_minutes * 60)


def cli_main():
    import argparse
    ap = argparse.ArgumentParser(description="NEXUS Dream Cycle — memory consolidation (P0#3)")
    ap.add_argument("--consolidate", action="store_true", help="Run one consolidation cycle")
    ap.add_argument("--trust-consolidate", action="store_true", help="Consolidate trust memory separately")
    ap.add_argument("--daemon", action="store_true", help="Run every 30 minutes")
    ap.add_argument("--interval", type=int, default=30, help="Daemon interval in minutes")
    ap.add_argument("--a2a-channel", default=None, help="A2A channels directory (Plan 20)")
    ap.add_argument("--status", action="store_true", help="Show stats")
    args = ap.parse_args()

    dc = DreamCycle(a2a_channel=args.a2a_channel)

    if args.status:
        stats = dc.get_stats()
        print(json.dumps(stats, indent=2))
        return

    if args.trust_consolidate:
        result = dc._trust.consolidate()
        print(json.dumps(result, indent=2))
        return

    if args.consolidate:
        result = dc.consolidate()
        print(json.dumps(result, indent=2))
        return

    if args.daemon:
        dc.run_daemon(interval_minutes=args.interval)
        return

    ap.print_help()


if __name__ == "__main__":
    cli_main()
