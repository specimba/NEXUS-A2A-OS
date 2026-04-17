"""GMR Telemetry Refresh Scheduler"""
import time
import threading
import logging
from typing import Callable, List, Optional

logger = logging.getLogger("nexus.gmr.scheduler")


class RefreshScheduler:
    """Schedule periodic telemetry refresh.
    
    TRIGGER: Cron every 5min OR webhook on latency spike > 2000ms
    SAFETY: Atomic os.replace() for zero-downtime overwrite
    """

    def __init__(
        self,
        ingest,  # TelemetryIngest instance
        interval_seconds: int = 300,
        on_refresh: Optional[Callable] = None,
    ):
        self.ingest = ingest
        self.interval = interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable] = []
        if on_refresh:
            self._callbacks.append(on_refresh)

    def on_refresh(self, callback: Callable):
        """Register callback for after each refresh."""
        self._callbacks.append(callback)

    def start(self):
        """Start the refresh loop in background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"GMR scheduler started (interval={self.interval}s)")

    def stop(self):
        """Stop the refresh loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self):
        while self._running:
            try:
                self.ingest.fetch()
                for callback in self._callbacks:
                    try:
                        callback(self.ingest.cache)
                    except Exception as e:
                        logger.warning(f"Refresh callback error: {e}")
            except Exception as e:
                logger.error(f"Refresh loop error: {e}")
            time.sleep(self.interval)
