"""GMR Telemetry Refresh Scheduler"""
import time
import threading
from typing import Callable, List, Optional
from datetime import datetime, timezone

class RefreshScheduler:
    def __init__(self, ingest, interval_seconds: int = 300):
        self.ingest = ingest
        self.interval = interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable] = []
    
    def on_refresh(self, callback: Callable):
        self._callbacks.append(callback)
        
    def start(self):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        self._running = False
        if self._thread: self._thread.join(timeout=5)
        
    def _loop(self):
        while self._running:
            try:
                self.ingest.fetch()
                for cb in self._callbacks:
                    try: cb(self.ingest.cache)
                    except: pass
                time.sleep(self.interval)
            except:
                time.sleep(10)
