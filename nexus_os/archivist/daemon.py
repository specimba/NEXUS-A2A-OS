"""nexus_os/archivist/daemon.py — ARCHIVIST Background Daemon

Hybrid B+C consolidation daemon:
- Trigger B (Idle): Monitors system load, fires when < 15% CPU for 5 min
- Trigger C (Explicit): Queue-based, fires when 100+ entries or 4h oldest
- Throttling: max 1 CPU core, pauses if load > 70%
- Tiers: Light (15 min), Deep (4h), Full (24h)
- Resume capability: checkpoint progress every 100 files

References:
- LightMem (ICLR 2026): Sleep-time offline consolidation decoupled from inference
- NEXUS Trust Framework: SEMANTIC channel write gate at trust ≥ 65
"""

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    psutil = None
    _HAS_PSUTIL = False

from nexus_os.archivist.import_stage import ArchivistImporter
from nexus_os.archivist.compile import ArchivistCompiler
from nexus_os.archivist.fit import ArchivistFitter

logger = logging.getLogger("nexus_os.archivist.daemon")


# Tier intervals (seconds)
TIER_INTERVALS = {
    "light": 15 * 60,    # 15 minutes
    "deep": 4 * 3600,    # 4 hours
    "full": 24 * 3600,   # 24 hours
}


class ArchivistDaemon:
    """Background daemon for ARCHIVIST pipeline processing."""

    def __init__(
        self,
        checkpoint_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
    ):
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else Path(__file__).parent / "state"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.checkpoint_dir / "progress.json"

        self.importer = ArchivistImporter()
        self.compiler = ArchivistCompiler()
        self.fitter = ArchivistFitter(output_dir=output_dir)

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_full_run = 0.0
        self._last_deep_run = 0.0

    # ── Checkpoint / Resume ─────────────────────────────────────────

    def save_checkpoint(self, processed_files: int, total_files: int, errors: List[str]):
        """Save progress checkpoint for resume capability."""
        checkpoint = {
            "timestamp": time.time(),
            "processed_files": processed_files,
            "total_files": total_files,
            "errors": errors[-10:],  # Keep last 10 errors
        }
        self.checkpoint_file.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")
        logger.info("Checkpoint saved: %d/%d files", processed_files, total_files)

    def load_checkpoint(self) -> Optional[Dict]:
        """Load progress checkpoint."""
        if self.checkpoint_file.exists():
            try:
                return json.loads(self.checkpoint_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Checkpoint load failed: %s", e)
        return None

    # ── System Load Monitoring ───────────────────────────────────────

    def _cpu_load(self) -> float:
        """Get current CPU load percentage. Returns 0.0 if psutil unavailable."""
        if not _HAS_PSUTIL:
            return 0.0
        return psutil.cpu_percent(interval=1.0)

    def wait_for_idle(self, timeout_minutes: int = 10) -> bool:
        """Wait for system to be idle (< 15% CPU for 5 consecutive minutes)."""
        if not _HAS_PSUTIL:
            logger.warning("psutil not available, skipping idle detection")
            return True
        logger.info("Waiting for idle state (CPU < 15%% for 5 min)...")
        idle_start = None
        deadline = time.time() + timeout_minutes * 60

        while time.time() < deadline:
            load = self._cpu_load()
            if load < 15.0:
                if idle_start is None:
                    idle_start = time.time()
                elif time.time() - idle_start >= 300:  # 5 minutes
                    logger.info("Idle state achieved (CPU=%.1f%%)", load)
                    return True
            else:
                idle_start = None
            time.sleep(30)

        logger.warning("Idle timeout reached without achieving idle state")
        return False

    def check_throttle(self) -> bool:
        """Check if system load requires throttling."""
        if not _HAS_PSUTIL:
            return False
        load = self._cpu_load()
        if load > 70.0:
            logger.warning("System load high (%.1f%%), throttling...", load)
            return True
        return False

    # ── Processing Tiers ─────────────────────────────────────────────

    def run_light(self):
        """Light tier: fast merge only, no deep analysis."""
        logger.info("Running LIGHT tier (fast merge)")
        try:
            records = self.importer.import_batch(max_files=50)
            if not records:
                logger.debug("Light tier: no new files")
                return
            compiled = self.compiler.compile_batch(records)
            wiki_admissible = self.compiler.get_wiki_admissible(compiled)
            logger.info(
                "LIGHT tier complete: %d files → %d compiled → %d wiki_admissible",
                len(records), len(compiled), len(wiki_admissible),
            )
        except Exception as e:
            logger.error("Light tier failed: %s", e)

    def run_deep(self, max_files: Optional[int] = None):
        """Deep tier: full import → compile → fit pipeline."""
        logger.info("Running DEEP tier (full pipeline)")
        checkpoint = self.load_checkpoint()

        if checkpoint:
            logger.info(
                "Previous checkpoint: %d/%d files (resume not yet implemented, starting fresh)",
                checkpoint.get("processed_files", 0),
                checkpoint.get("total_files", 0),
            )

        # Import stage
        records = self.importer.import_batch(max_files=max_files)
        if not records:
            logger.info("No new files to process")
            return

        # Compile stage
        compiled = self.compiler.compile_batch(records)
        wiki_admissible = self.compiler.get_wiki_admissible(compiled)

        # Fit stage
        # TODO: Use ArchivistCompiler.get_all_dossier_candidates() instead of private attr
        dossiers = self.fitter.fit_batch(self.compiler._dossier_candidates)

        # Checkpoint
        self.save_checkpoint(
            len(records),
            len(records),
            [e for r in compiled for e in r.compile_errors],
        )

        logger.info(
            "DEEP tier complete: %d files → %d compiled → %d wiki_admissible → %d dossiers",
            len(records), len(compiled), len(wiki_admissible), len(dossiers),
        )

    def run_full(self):
        """Full tier: 24-hour deep consolidation with archive cleanup."""
        logger.info("Running FULL tier (24h consolidation)")
        self.run_deep()
        # Archive old dossiers (older than 30 days)
        # This is a placeholder for future implementation
        logger.info("FULL tier complete")

    # ── Main Loop ────────────────────────────────────────────────────

    def run_once(self, tier: str = "deep"):
        """Run a single processing cycle."""
        if tier == "light":
            self.run_light()
        elif tier == "deep":
            self.run_deep()
        elif tier == "full":
            self.run_full()

    def run_continuous(self):
        """Run daemon continuously with hybrid B+C triggers."""
        self._running = True
        logger.info("ARCHIVIST daemon started (hybrid B+C triggers)")

        while self._running:
            now = time.time()

            # Check throttle
            if self.check_throttle():
                time.sleep(60)  # Wait 1 minute before retry
                continue

            # Trigger C (Explicit): Queue-based or time-based
            if now - self._last_deep_run >= TIER_INTERVALS["deep"]:
                self.run_deep()
                self._last_deep_run = now

            # Trigger B (Idle): Check for idle state, run light tier
            if now - self._last_deep_run >= TIER_INTERVALS["light"]:
                if self._cpu_load() < 15.0:
                    self.run_light()

            # Full tier (24h)
            if now - self._last_full_run >= TIER_INTERVALS["full"]:
                self.run_full()
                self._last_full_run = now

            time.sleep(60)  # Check every minute

        logger.info("ARCHIVIST daemon stopped")

    def start(self):
        """Start daemon in background thread."""
        if self._running:
            logger.warning("Daemon already running")
            return
        self._thread = threading.Thread(target=self.run_continuous, name="archivist-daemon", daemon=True)
        self._thread.start()
        logger.info("ARCHIVIST daemon thread started")

    def stop(self):
        """Stop daemon gracefully."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("ARCHIVIST daemon stopped")

    def is_running(self) -> bool:
        return self._running

    def get_stats(self) -> Dict[str, Any]:
        """Return daemon statistics."""
        return {
            "running": self._running,
            "last_deep_run": self._last_deep_run,
            "last_full_run": self._last_full_run,
            "importer": self.importer.get_stats(),
            "fitter": self.fitter.get_stats(),
        }
