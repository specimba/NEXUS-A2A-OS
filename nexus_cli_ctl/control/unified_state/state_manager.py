"""
NEXUS Unified State Manager
Central state coordination for CLI Terminal, Browser Dashboard,
NEXUSCLAW Brain, Wiki/DoppelGround, and external integrations.
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable, Any
from collections import defaultdict
from dataclasses import dataclass, field, asdict
import aiohttp
from aiohttp import web

logger = logging.getLogger("nexus.unified_state")

STATE_DIR = Path.home() / ".nexus_pi" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = STATE_DIR / "unified_state.json"


@dataclass
class StateChange:
    topic: str
    data: dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "unknown"


class UnifiedStateManager:
    """
    Central state coordination hub.
    - CLI Terminal (nexusctl) subscribes/publishes
    - Browser Dashboard connects via WebSocket
    - NEXUSCLAW orchestrator pushes state updates
    - Wiki/DoppelGround notifies of dossier changes
    - External integrations (A2A, Tailscale, etc.) report status
    """

    WS_PORT = 8765
    HTTP_PORT = 8766
    # NOTE: These ports must be registered in PortRegistry.CANONICAL_PORTS

    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._ws_clients: Set[web.WebSocketResponse] = set()
        self._running = False
        self._ws_app = None
        self._ws_runner = None
        self._http_app = None
        self._http_runner = None
        self._lock = asyncio.Lock()
        self._publish_timestamps: List[float] = []
        self._ws_flood_limit = 100  # Max WS broadcasts per second

        # Load persisted state
        self._load_state()

        # Initialize state sections
        self._state.setdefault("cli", {"last_command": None, "history": []})
        self._state.setdefault("dashboard", {"connected_clients": 0})
        self._state.setdefault("nexusclaw", {"agents": {}, "tasks": {}, "metrics": {}})
        self._state.setdefault("model_relay", {"providers": {}, "models": {}})
        self._state.setdefault("wiki", {"pages": 0, "dossiers": 0, "last_update": None})
        self._state.setdefault("integrations", {
            "a2a_bridge": {"url": None, "alive": False},
            "tailscale": {"connected": False, "peers": 0},
            "zo_computer": {"reachable": False},
            "mimo_cli": {"configured": False, "models_synced": 0},
            "slack": {"connected": False},
            "telegram": {"connected": False},
            "discord": {"connected": False}
        })
        self._state.setdefault("metrics", {
            "uptime_start": datetime.now().isoformat(),
            "total_events": 0,
            "last_heartbeat": None
        })

    def _load_state(self):
        """Load persisted state from disk"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self._state = loaded
                    else:
                        logger.warning("State file contains non-dict type: %s, resetting", type(loaded).__name__)
                        self._state = {}
            except json.JSONDecodeError as e:
                logger.warning("State file corrupted (JSON error): %s, resetting", e)
                self._state = {}
            except Exception as e:
                logger.warning("Failed to load state: %s", e)
                self._state = {}

    def _save_state(self):
        """Persist state to disk"""
        try:
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save state: {e}")

    async def start(self):
        """Start the unified state manager (WebSocket + HTTP servers)"""
        if self._running:
            return
        self._running = True

        # WebSocket server for real-time updates
        self._ws_app = web.Application()
        self._ws_app.router.add_get('/ws', self._handle_ws)
        self._ws_runner = web.AppRunner(self._ws_app)
        await self._ws_runner.setup()
        ws_site = web.TCPSite(self._ws_runner, '0.0.0.0', self.WS_PORT)
        await ws_site.start()
        logger.info(f"WebSocket server started on port {self.WS_PORT}")

        # HTTP API for state queries
        self._http_app = web.Application()
        self._http_app.router.add_get('/state', self._handle_http_state)
        self._http_app.router.add_get('/health', self._handle_http_health)
        self._http_app.router.add_post('/publish', self._handle_http_publish)
        self._http_runner = web.AppRunner(self._http_app)
        await self._http_runner.setup()
        http_site = web.TCPSite(self._http_runner, '0.0.0.0', self.HTTP_PORT)
        await http_site.start()
        logger.info(f"HTTP API started on port {self.HTTP_PORT}")

    async def stop(self):
        """Stop the state manager"""
        self._running = False
        if self._ws_runner:
            await self._ws_runner.cleanup()
        if self._http_runner:
            await self._http_runner.cleanup()
        async with self._lock:
            self._save_state()

    async def publish(self, topic: str, data: dict, source: str = "unknown"):
        """Publish a state change to all subscribers"""
        async with self._lock:
            # Update state
            # NOTE: Topic format is "section.key". Nested keys like "wiki.pages.index"
            # are stored as self._state["wiki"]["pages.index"] = data (flat, not nested).
            # For nested state, use the section directly: topic="wiki" stores full dict.
            section, key = topic.split('.', 1) if '.' in topic else (topic, '_')
            if section not in self._state:
                self._state[section] = {}
            if isinstance(self._state[section], dict):
                self._state[section][key] = data

            self._state["metrics"]["total_events"] += 1
            self._state["metrics"]["last_heartbeat"] = datetime.now().isoformat()

            # Persist
            self._save_state()

            change = StateChange(topic=topic, data=data, source=source)

        # Notify Python subscribers
        for callback in self._subscribers.get(topic, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(change)
                else:
                    callback(change)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")

        # WS flood protection: skip broadcast if rate exceeds limit
        now = time.time()
        self._publish_timestamps = [t for t in self._publish_timestamps if now - t < 1.0]
        self._publish_timestamps.append(now)
        should_broadcast = len(self._publish_timestamps) <= self._ws_flood_limit

        # Broadcast to WebSocket clients (with drain protection)
        if should_broadcast:
            message = json.dumps({
                "type": "state_change",
                "topic": topic,
                "data": data,
                "source": source,
                "timestamp": change.timestamp
            })
            stale = []
            for ws in list(self._ws_clients):
                try:
                    if ws.closed:
                        stale.append(ws)
                        continue
                    await ws.send_str(message)
                except Exception:
                    stale.append(ws)
            for ws in stale:
                self._ws_clients.discard(ws)

    def subscribe(self, topic: str, callback: Callable):
        """Subscribe to state changes on a topic"""
        self._subscribers[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable) -> bool:
        """Unsubscribe a callback from a topic. Returns True if removed."""
        if topic in self._subscribers:
            try:
                self._subscribers[topic].remove(callback)
                if not self._subscribers[topic]:
                    del self._subscribers[topic]
                return True
            except ValueError:
                return False
        return False

    def get_state(self, section: Optional[str] = None) -> dict:
        """Get current state (or a section). Returns a shallow copy."""
        if section:
            return dict(self._state.get(section, {}))
        return dict(self._state)

    async def _handle_ws(self, request):
        """WebSocket handler for dashboard connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._ws_clients.add(ws)

        # Send initial state
        await ws.send_str(json.dumps({
            "type": "initial_state",
            "state": self._state
        }))

        try:
            async for msg in ws:
                if msg.type == web.MsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        if data.get("type") == "publish":
                            await self.publish(
                                data["topic"],
                                data["data"],
                                source=data.get("source", "dashboard")
                            )
                    except Exception as e:
                        logger.error(f"WS message error: {e}")
        finally:
            self._ws_clients.discard(ws)

        return ws

    async def _handle_http_state(self, request):
        """HTTP handler for state queries"""
        section = request.query.get("section")
        state = self.get_state(section) if section else self._state
        return web.json_response(state)

    async def _handle_http_health(self, request):
        """HTTP handler for health check"""
        return web.json_response({
            "status": "healthy",
            "uptime_start": self._state["metrics"]["uptime_start"],
            "total_events": self._state["metrics"]["total_events"],
            "ws_clients": len(self._ws_clients)
        })

    async def _handle_http_publish(self, request):
        """HTTP handler for publishing state changes"""
        try:
            data = await request.json()
            await self.publish(
                data["topic"],
                data["data"],
                source=data.get("source", "http")
            )
            return web.json_response({"status": "published"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)


# Global instance
_state_manager: Optional[UnifiedStateManager] = None


def get_state_manager() -> UnifiedStateManager:
    """Get the global state manager instance"""
    global _state_manager
    if _state_manager is None:
        _state_manager = UnifiedStateManager()
    return _state_manager


async def main():
    """CLI entry point for state manager"""
    import argparse
    parser = argparse.ArgumentParser(description="NEXUS Unified State Manager")
    parser.add_argument("--start", action="store_true", help="Start state manager daemon")
    parser.add_argument("--status", action="store_true", help="Show current state")
    parser.add_argument("--publish", nargs=2, metavar=('TOPIC', 'JSON_DATA'), help="Publish state change")
    args = parser.parse_args()

    sm = get_state_manager()

    if args.start:
        await sm.start()
        logger.info("State manager running. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            await sm.stop()
    elif args.status:
        print(json.dumps(sm.get_state(), indent=2, default=str))
    elif args.publish:
        topic, data_json = args.publish
        data = json.loads(data_json)
        await sm.publish(topic, data, source="cli")
        print(f"Published to {topic}")
    else:
        parser.print_help()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(main())
