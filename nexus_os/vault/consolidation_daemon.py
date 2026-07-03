"""nexus_os/vault/consolidation_daemon.py — LightMem 3-Stage Consolidation

Pipeline:
  Stage 1: SENSORY → STM (WORKING)  — compress raw sensory input
  Stage 2: STM → LTM (EPISODIC)     — consolidate working memory into episodic traces
  Stage 3: EPISODIC → SEMANTIC      — extract concepts and patterns into semantic memory

Trigger: Hybrid B+C (idle + explicit queue depth)
  - Idle: CPU < 15% for 5 minutes
  - Explicit: SENSORY queue depth > 100 or WORKING queue depth > 50

Integration:
  - Reads from MemoryChannelManager SENSORY / WORKING channels
  - Writes to WORKING / EPISODIC / SEMANTIC channels
  - Reports to ARCHIVIST daemon for dossier synthesis
  - Logs to NEXUSCLAW worklog
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from nexus_os.vault.memory_channels import MemoryChannelManager, MemoryChannel, get_manager

logger = logging.getLogger("vault.consolidation")


@dataclass
class ConsolidationConfig:
    """Configuration for LightMem consolidation daemon."""
    # Idle trigger thresholds
    cpu_threshold_pct: float = 15.0
    idle_duration_seconds: int = 300  # 5 minutes
    check_interval_seconds: int = 30

    # Explicit queue thresholds
    sensory_queue_threshold: int = 100
    working_queue_threshold: int = 50
    episodic_queue_threshold: int = 200

    # Consolidation batch sizes
    sensory_batch_size: int = 20
    working_batch_size: int = 10
    episodic_batch_size: int = 5

    # Memory limits
    max_sensory_per_agent: int = 1000
    max_working_per_agent: int = 50
    max_episodic_per_agent: int = 500

    # Trust thresholds for consolidation (must be >= this to consolidate)
    min_trust_for_sensory_consolidation: float = 0.0
    min_trust_for_working_consolidation: float = 30.0
    min_trust_for_episodic_consolidation: float = 65.0


@dataclass
class ConsolidationStats:
    """Statistics from a consolidation run."""
    run_id: str
    timestamp: str
    stage: str  # "sensory_to_working", "working_to_episodic", "episodic_to_semantic"
    agent_id: str
    records_read: int = 0
    records_written: int = 0
    records_dropped: int = 0
    duration_ms: float = 0.0
    cpu_before_pct: Optional[float] = None
    cpu_after_pct: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "stage": self.stage,
            "agent_id": self.agent_id,
            "records_read": self.records_read,
            "records_written": self.records_written,
            "records_dropped": self.records_dropped,
            "duration_ms": self.duration_ms,
        }


class LightMemConsolidationDaemon:
    """3-stage memory consolidation daemon."""

    def __init__(
        self,
        manager: Optional[MemoryChannelManager] = None,
        config: Optional[ConsolidationConfig] = None,
    ) -> None:
        self.manager = manager or get_manager()
        self.config = config or ConsolidationConfig()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stats: List[ConsolidationStats] = []
        self._last_cpu_check: float = 0.0
        self._cpu_idle_start: Optional[float] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the daemon in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("LightMem consolidation daemon started")

    def stop(self) -> None:
        """Signal the daemon to stop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("LightMem consolidation daemon stopped")

    def trigger_explicit(self, agent_id: Optional[str] = None) -> List[ConsolidationStats]:
        """Explicitly trigger consolidation (Hybrid B+C — explicit queue path)."""
        return self._run_consolidation(agent_id=agent_id, reason="explicit")

    def get_stats(self, n: int = 10) -> List[ConsolidationStats]:
        """Return the N most recent consolidation stats."""
        return self._stats[-n:]

    def to_json(self) -> str:
        """Serialize all stats to JSON."""
        import json
        return json.dumps([s.to_dict() for s in self._stats], indent=2)

    # ------------------------------------------------------------------
    # Internal run loop
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        """Main loop: checks idle CPU and queue depth, triggers consolidation."""
        while self._running:
            try:
                # Check if explicit trigger needed (queue depth)
                if self._should_trigger_explicit():
                    self._run_consolidation(reason="queue_depth")
                    time.sleep(self.config.check_interval_seconds)
                    continue

                # Check idle CPU trigger
                if self._check_idle_cpu():
                    self._run_consolidation(reason="idle_cpu")

                time.sleep(self.config.check_interval_seconds)
            except Exception as e:
                logger.warning("Consolidation daemon loop error: %s", e)
                time.sleep(self.config.check_interval_seconds)

    # ------------------------------------------------------------------
    # Trigger checks
    # ------------------------------------------------------------------

    def _should_trigger_explicit(self) -> bool:
        """Check if queue depth exceeds explicit thresholds."""
        # Fast check: count records in SENSORY and WORKING buffers
        sensory_count = self._count_buffer_records(MemoryChannel.SENSORY)
        working_count = self._count_buffer_records(MemoryChannel.WORKING)
        return (
            sensory_count >= self.config.sensory_queue_threshold
            or working_count >= self.config.working_queue_threshold
        )

    def _check_idle_cpu(self) -> bool:
        """Check if CPU has been below threshold for the idle duration."""
        cpu_pct = self._get_cpu_percent()
        now = time.time()

        if cpu_pct is None:
            self._cpu_idle_start = None
            return False

        if cpu_pct < self.config.cpu_threshold_pct:
            if self._cpu_idle_start is None:
                self._cpu_idle_start = now
            elif (now - self._cpu_idle_start) >= self.config.idle_duration_seconds:
                self._cpu_idle_start = None  # Reset after trigger
                return True
        else:
            self._cpu_idle_start = None

        return False

    # ------------------------------------------------------------------
    # Consolidation stages
    # ------------------------------------------------------------------

    def _run_consolidation(
        self,
        agent_id: Optional[str] = None,
        reason: str = "scheduled",
    ) -> List[ConsolidationStats]:
        """Run all 3 stages of consolidation."""
        stats: List[ConsolidationStats] = []
        logger.info("Consolidation triggered (%s)", reason)

        # Stage 1: SENSORY → WORKING (STM)
        stats.extend(self._stage_sensory_to_working(agent_id))

        # Stage 2: WORKING → EPISODIC (LTM)
        stats.extend(self._stage_working_to_episodic(agent_id))

        # Stage 3: EPISODIC → SEMANTIC (concept extraction)
        stats.extend(self._stage_episodic_to_semantic(agent_id))

        self._stats.extend(stats)

        # P2-5: snapshot all channel buffers encrypted at rest after each
        # consolidation cycle (fail-closed no-op when no vault key exists).
        try:
            self.manager.save_to_disk()
        except Exception:
            logger.warning("Encrypted channel snapshot failed", exc_info=True)

        logger.info(
            "Consolidation complete: %d stages, %d total records read, %d written",
            len(stats),
            sum(s.records_read for s in stats),
            sum(s.records_written for s in stats),
        )
        return stats

    def _stage_sensory_to_working(
        self, agent_id: Optional[str] = None
    ) -> List[ConsolidationStats]:
        """Stage 1: Compress raw SENSORY into WORKING (STM)."""
        stats: List[ConsolidationStats] = []
        targets = [agent_id] if agent_id else list(self.manager._buffers.keys())

        for aid in targets:
            start = time.time()
            records = self.manager.get_records(aid, MemoryChannel.SENSORY, limit=self.config.sensory_batch_size)
            if not records:
                continue

            read_count = len(records)
            written_count = 0
            dropped_count = 0

            # Simple compression: merge records by source (first topic_tag), keep latest
            compressed: Dict[str, Any] = {}
            for r in records:
                src = r.topic_tags[0] if r.topic_tags else "unknown"
                compressed[src] = {
                    "content": r.content,
                    "source": src,
                    "timestamp": r.timestamp if hasattr(r, "timestamp") else datetime.now(timezone.utc).isoformat(),
                    "compressed_from": compressed.get(src, {}).get("compressed_from", 0) + 1,
                }

            for content in compressed.values():
                try:
                    self.manager.append_working(
                        agent_id=aid,
                        content=content["content"],
                    )
                    written_count += 1
                except Exception as e:
                    logger.warning("Failed to write WORKING for %s: %s", aid, e)
                    dropped_count += 1

            # Clear processed SENSORY records
            try:
                self.manager._buffers[aid][MemoryChannel.SENSORY] = []
            except Exception:
                pass

            stats.append(ConsolidationStats(
                run_id=f"stm-{aid}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage="sensory_to_working",
                agent_id=aid,
                records_read=read_count,
                records_written=written_count,
                records_dropped=dropped_count,
                duration_ms=(time.time() - start) * 1000,
            ))

        return stats

    def _stage_working_to_episodic(
        self, agent_id: Optional[str] = None
    ) -> List[ConsolidationStats]:
        """Stage 2: Consolidate WORKING into EPISODIC (LTM)."""
        stats: List[ConsolidationStats] = []
        targets = [agent_id] if agent_id else list(self.manager._buffers.keys())

        for aid in targets:
            start = time.time()
            records = self.manager.get_records(aid, MemoryChannel.WORKING, limit=self.config.working_batch_size)
            if not records:
                continue

            read_count = len(records)
            written_count = 0
            dropped_count = 0

            # Merge into episodic events: summarize outcomes
            for r in records:
                try:
                    self.manager.append_episodic(
                        agent_id=aid,
                        content=r.content,
                        outcome="consolidated",  # Derived from WORKING memory
                        duration_ms=0.0,
                        token_count=r.tokens if hasattr(r, "tokens") else 0,
                    )
                    written_count += 1
                except Exception as e:
                    logger.warning("Failed to write EPISODIC for %s: %s", aid, e)
                    dropped_count += 1

            # WORKING auto-prunes (keep last 50), so we don't need to clear manually
            stats.append(ConsolidationStats(
                run_id=f"ltm-{aid}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage="working_to_episodic",
                agent_id=aid,
                records_read=read_count,
                records_written=written_count,
                records_dropped=dropped_count,
                duration_ms=(time.time() - start) * 1000,
            ))

        return stats

    def _stage_episodic_to_semantic(
        self, agent_id: Optional[str] = None
    ) -> List[ConsolidationStats]:
        """Stage 3: Extract concepts from EPISODIC into SEMANTIC."""
        stats: List[ConsolidationStats] = []
        targets = [agent_id] if agent_id else list(self.manager._buffers.keys())

        for aid in targets:
            start = time.time()
            records = self.manager.get_records(aid, MemoryChannel.EPISODIC, limit=self.config.episodic_batch_size)
            if not records:
                continue

            read_count = len(records)
            written_count = 0
            dropped_count = 0

            # Extract concepts: simple keyword-based extraction
            concepts: Dict[str, int] = {}
            for r in records:
                # Simple concept extraction: split content into words, count frequency
                words = r.content.lower().split() if r.content else []
                for w in words:
                    if len(w) > 4:  # Only meaningful words
                        concepts[w] = concepts.get(w, 0) + 1

            # Write top concepts to SEMANTIC channel
            for concept, freq in sorted(concepts.items(), key=lambda x: x[1], reverse=True)[:5]:
                try:
                    self.manager.append_semantic(
                        agent_id=aid,
                        content=f"Concept: {concept} (freq={freq}) extracted from {read_count} episodic records",
                        topic_tags=[concept],
                        trust_score=50.0,  # Default trust for semantic extraction
                    )
                    written_count += 1
                except Exception as e:
                    logger.warning("Failed to write SEMANTIC for %s: %s", aid, e)
                    dropped_count += 1

            stats.append(ConsolidationStats(
                run_id=f"sem-{aid}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage="episodic_to_semantic",
                agent_id=aid,
                records_read=read_count,
                records_written=written_count,
                records_dropped=dropped_count,
                duration_ms=(time.time() - start) * 1000,
            ))

        return stats

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _count_buffer_records(self, channel: MemoryChannel) -> int:
        """Count total records across all agents for a channel."""
        total = 0
        for agent_buffers in self.manager._buffers.values():
            total += len(agent_buffers.get(channel, []))
        return total

    def _get_cpu_percent(self) -> Optional[float]:
        """Get current CPU percentage. Returns None if unavailable."""
        try:
            import psutil
            return psutil.cpu_percent(interval=1.0)
        except ImportError:
            return None
        except Exception as e:
            logger.warning("CPU check failed: %s", e)
            return None


# Singleton
daemon_instance: Optional[LightMemConsolidationDaemon] = None


def get_daemon() -> LightMemConsolidationDaemon:
    """Get the singleton LightMem consolidation daemon."""
    global daemon_instance
    if daemon_instance is None:
        daemon_instance = LightMemConsolidationDaemon()
    return daemon_instance
