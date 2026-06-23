"""
NEXUS Dashboard WebSocket Sync
Bridges the Brain API WebSocket to the browser dashboard at localhost:3001.
Keeps dashboard state in sync with unified state manager in real-time.
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set

import httpx

logger = logging.getLogger("nexus_cli_ctl.integrations.dashboard_sync")

DASHBOARD_URL = os.getenv("NEXUS_DASHBOARD_URL", "http://localhost:3001")
BRAIN_API_WS = os.getenv("NEXUS_BRAIN_WS", "ws://127.0.0.1:7352/ws")
BRAIN_API_HTTP = os.getenv("NEXUS_BRAIN_HTTP", "http://127.0.0.1:7352")


class DashboardSync:
    """Keeps the browser dashboard in sync with NEXUS unified state."""

    SYNC_INTERVAL = 5  # seconds between HTTP polling fallback
    PROBE_INTERVAL = 30  # seconds between dashboard health checks

    TOPICS = {
        "system", "agents", "tasks", "messages", "brainstorm",
        "model_relay", "providers", "integrations", "wiki", "messaging",
        "trust", "interventions",
    }

    def __init__(self, state_manager=None):
        self.sm = state_manager
        self.running = False
        self._ws_connected = False
        self._dashboard_reachable = False
        self._last_sync: Dict[str, str] = {}

    async def start(self):
        if self.running:
            return
        self.running = True
        asyncio.create_task(self._probe_loop())
        asyncio.create_task(self._sync_loop())
        logger.info("Dashboard Sync started")

    async def stop(self):
        self.running = False

    def get_status(self) -> Dict:
        return {
            "running": self.running,
            "ws_connected": self._ws_connected,
            "dashboard_reachable": self._dashboard_reachable,
            "dashboard_url": DASHBOARD_URL,
            "brain_api": BRAIN_API_HTTP,
            "topics": list(self.TOPICS),
            "last_sync": self._last_sync,
        }

    async def _probe_loop(self):
        """Periodically check if dashboard is reachable"""
        while self.running:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{DASHBOARD_URL}/")
                    self._dashboard_reachable = resp.status_code < 500
                    if self._dashboard_reachable and not self._ws_connected:
                        asyncio.create_task(self._connect_ws())
            except Exception:
                self._dashboard_reachable = False
                self._ws_connected = False
            await asyncio.sleep(self.PROBE_INTERVAL)

    async def _connect_ws(self):
        """Attempt WebSocket connection to Brain API for live sync"""
        retry_delay = 1.0
        max_delay = 60.0
        while self.running:
            try:
                import websockets
                async with websockets.connect(BRAIN_API_WS) as ws:
                    self._ws_connected = True
                    retry_delay = 1.0
                    await ws.send(json.dumps({
                        "type": "subscribe",
                        "topics": list(self.TOPICS),
                    }))
                    logger.info("Dashboard WS connected to Brain API")

                    while self.running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        if data.get("type") != "ping":
                            await self._push_to_dashboard(data)
            except Exception as e:
                logger.debug(f"Dashboard WS connection failed: {e}")
                self._ws_connected = False
                if not self.running:
                    break
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)

    async def _sync_loop(self):
        """HTTP polling fallback when WS is not connected"""
        while self.running:
            if not self._ws_connected and self.sm:
                try:
                    state = self.sm.get_state()
                    await self._push_to_dashboard({
                        "type": "state_sync",
                        "data": state,
                        "timestamp": datetime.now().isoformat(),
                    })
                except Exception as e:
                    logger.debug(f"Dashboard sync error: {e}")
            await asyncio.sleep(self.SYNC_INTERVAL)

    async def _push_to_dashboard(self, data: Dict):
        """Push data to dashboard via HTTP POST"""
        if not self._dashboard_reachable:
            return
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                await client.post(
                    f"{DASHBOARD_URL}/api/sync",
                    json=data,
                )
                topic = data.get("type", "unknown")
                self._last_sync[topic] = datetime.now().isoformat()
        except Exception:
            self._dashboard_reachable = False


_dashboard_sync: Optional[DashboardSync] = None


def get_dashboard_sync(state_manager=None) -> DashboardSync:
    global _dashboard_sync
    if _dashboard_sync is None:
        _dashboard_sync = DashboardSync(state_manager=state_manager)
    elif state_manager and _dashboard_sync.sm is None:
        _dashboard_sync.sm = state_manager
    return _dashboard_sync
