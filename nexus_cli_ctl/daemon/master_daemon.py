"""
NEXUS Master Daemon
Runs all 24/7 monitoring and integration services:
- Brain API (FastAPI governance on port 7352)
- UnifiedStateManager (CLI/Dashboard sync)
- ProviderHealthMonitor (Model Relay circuit breaker)
- A2ABridgeHealthMonitor (Grok bridge status)
- TailscaleMonitor (Mesh + Zo reachability)
- MimoIntegration (auto-sync + test)
- WikiPipeline + DashboardSync

Single entry point for always-on NEXUS operations.
"""
import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_cli_ctl.control.unified_state.state_manager import get_state_manager
from nexus_os.monitoring.provider_health import get_health_monitor
from nexus_cli_ctl.integrations.a2a.a2a_health_monitor import A2ABridgeHealthMonitor
from nexus_cli_ctl.integrations.zo_computer.tailscale_monitor import TailscaleMonitor
from nexus_cli_ctl.integrations.mimo.mimo_integration import MimoConfig
from nexus_cli_ctl.integrations.wiki_pipeline import WikiPipeline, get_wiki_pipeline
from nexus_cli_ctl.integrations.messaging.messaging_integration import MessagingIntegration, get_messaging_integration
from nexus_cli_ctl.integrations.dashboard_sync import DashboardSync, get_dashboard_sync

logger = logging.getLogger("nexus.master_daemon")

STATE_DIR = Path.home() / ".nexus_pi" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
MASTER_PID_FILE = STATE_DIR / "master_daemon.pid"


class NEXUSMasterDaemon:
    """
    The NEXUS master daemon coordinates all always-on services.
    Single process manages:
    - State Manager (WebSocket + HTTP servers)
    - Provider Health Monitoring
    - A2A Bridge Health
    - Tailscale Network Status
    - Mimo CLI Auto-sync
    """

    def __init__(self):
        self.running = False
        self.services: Dict[str, any] = {}
        self._tasks: List[asyncio.Task] = []

    async def start(self):
        """Start all services"""
        if self.running:
            logger.warning("Master daemon already running")
            return

        self.running = True
        self._write_pid_file()
        logger.info("=" * 60)
        logger.info("NEXUS Master Daemon Starting")
        logger.info("=" * 60)

        try:
            # 1. Start Unified State Manager
            sm = get_state_manager()
            await sm.start()
            self.services["state_manager"] = sm
            logger.info("✓ Unified State Manager: WS:8765, HTTP:8766")

            # 2. Start Provider Health Monitor
            health = get_health_monitor()
            await health.start()
            self.services["health_monitor"] = health
            logger.info("✓ Provider Health Monitor (circuit breaker active)")

            # 3. Start A2A Bridge Monitor
            a2a = A2ABridgeHealthMonitor(state_manager=sm)
            await a2a.start()
            self.services["a2a_monitor"] = a2a
            logger.info("✓ A2A Bridge Health Monitor")

            # 4. Start Tailscale Monitor
            ts = TailscaleMonitor(state_manager=sm)
            await ts.start()
            self.services["tailscale_monitor"] = ts
            logger.info("✓ Tailscale Network Monitor")

            # 5. Start Brain API (uvicorn)
            brain_task = await self._start_brain_api()
            if brain_task:
                self._tasks.append(brain_task)
                logger.info("✓ Brain API (uvicorn on port 7352)")

            # 6. Schedule Mimo auto-sync
            self._tasks.append(asyncio.create_task(self._mimo_sync_loop(sm)))
            logger.info("✓ Mimo CLI auto-sync scheduler")

            # 7. Schedule periodic state snapshots
            self._tasks.append(asyncio.create_task(self._snapshot_loop()))
            logger.info("✓ State snapshot scheduler")

            # 8. Schedule periodic health reporting
            self._tasks.append(asyncio.create_task(self._health_report_loop(sm, health)))
            logger.info("✓ Health report broadcaster")

            # 9. Start Wiki Pipeline
            wiki = get_wiki_pipeline(state_manager=sm)
            await wiki.start()
            self.services["wiki_pipeline"] = wiki
            logger.info(f"✓ Wiki/DoppelGround Pipeline ({wiki._page_count} pages)")

            # 10. Start Messaging Integration
            msg = get_messaging_integration(state_manager=sm)
            await msg.start()
            self.services["messaging"] = msg
            enabled = msg.hub.get_enabled_platforms()
            logger.info(f"✓ Messaging Integration (platforms: {enabled or 'none configured'})")

            # 11. Schedule wiki + messaging status pushes
            self._tasks.append(asyncio.create_task(self._wiki_messaging_loop(sm, wiki, msg)))
            logger.info("✓ Wiki + Messaging status broadcaster")

            # 12. Start Dashboard WebSocket Sync
            dash = get_dashboard_sync(state_manager=sm)
            await dash.start()
            self.services["dashboard_sync"] = dash
            logger.info("✓ Dashboard Sync (WS + HTTP polling)")

            logger.info("=" * 60)
            logger.info("All NEXUS services running. Press Ctrl+C to stop.")
            logger.info("=" * 60)

            # Wait forever (or until interrupted)
            while self.running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Received interrupt, stopping...")
        except Exception as e:
            logger.error(f"Master daemon error: {e}", exc_info=True)
        finally:
            await self.stop()

    async def stop(self):
        """Stop all services"""
        if not self.running:
            return
        self.running = False

        logger.info("Stopping NEXUS Master Daemon...")

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

        # Stop services
        if "a2a_monitor" in self.services:
            await self.services["a2a_monitor"].stop()
        if "tailscale_monitor" in self.services:
            await self.services["tailscale_monitor"].stop()
        if "health_monitor" in self.services:
            await self.services["health_monitor"].stop()
        if "state_manager" in self.services:
            await self.services["state_manager"].stop()
        if "wiki_pipeline" in self.services:
            await self.services["wiki_pipeline"].stop()
        if "messaging" in self.services:
            await self.services["messaging"].stop()
        if "brain_api_server" in self.services:
            self.services["brain_api_server"].should_exit = True

        self._remove_pid_file()
        logger.info("NEXUS Master Daemon stopped")

    async def _start_brain_api(self):
        """Start Brain API as a uvicorn subprocess"""
        try:
            import uvicorn
            from nexus_os.api.brain_api import app

            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=7352,
                log_level="warning",
                loop="asyncio",
            )
            server = uvicorn.Server(config)

            async def _serve():
                await server.serve()

            self.services["brain_api_server"] = server
            return asyncio.create_task(_serve())
        except Exception as e:
            logger.warning(f"Brain API start skipped: {e}")
            return None

    async def _mimo_sync_loop(self, sm):
        """Periodically sync Mimo CLI models"""
        mimo = MimoConfig()
        while self.running:
            try:
                result = await mimo.sync_models()
                await sm.publish(
                    "integrations.mimo_cli",
                    {
                        "configured": True,
                        "models_synced": result.get("models_synced", 0),
                        "last_sync": datetime.now().isoformat()
                    },
                    source="mimo_sync"
                )
                logger.info(f"Mimo sync: {result.get('models_synced', 0)} models")
            except Exception as e:
                logger.error(f"Mimo sync error: {e}")
            await asyncio.sleep(300)  # Every 5 minutes

    async def _snapshot_loop(self):
        """Take state snapshots every hour"""
        while self.running:
            try:
                sm = get_state_manager()
                snapshot = sm.get_state()
                snapshot_file = STATE_DIR / f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(snapshot_file, 'w') as f:
                    json.dump(snapshot, f, indent=2, default=str)
                logger.debug(f"State snapshot: {snapshot_file}")
            except Exception as e:
                logger.error(f"Snapshot error: {e}")
            await asyncio.sleep(3600)

    async def _health_report_loop(self, sm, health):
        """Broadcast health summary every 30 seconds"""
        while self.running:
            try:
                status = health.get_status()
                await sm.publish(
                    "model_relay.providers",
                    status.get("providers", {}),
                    source="health_monitor"
                )
            except Exception as e:
                logger.error(f"Health report error: {e}")
            await asyncio.sleep(30)

    async def _wiki_messaging_loop(self, sm, wiki, msg):
        """Combine wiki + messaging status pushes"""
        while self.running:
            try:
                await sm.publish("wiki", wiki.get_status(), source="wiki_pipeline")
                await sm.publish("messaging", msg.get_status(), source="messaging")
            except Exception as e:
                logger.debug(f"Wiki/msg status loop error: {e}")
            await asyncio.sleep(60)

    def _write_pid_file(self):
        MASTER_PID_FILE.write_text(str(os.getpid()))

    def _remove_pid_file(self):
        try:
            MASTER_PID_FILE.unlink()
        except Exception:
            pass


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="NEXUS Master Daemon")
    parser.add_argument("--start", action="store_true", help="Start master daemon")
    parser.add_argument("--stop", action="store_true", help="Stop running daemon")
    parser.add_argument("--status", action="store_true", help="Show status")
    args = parser.parse_args()

    if args.stop:
        if MASTER_PID_FILE.exists():
            pid = int(MASTER_PID_FILE.read_text().strip())
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Sent SIGTERM to PID {pid}")
            except Exception as e:
                print(f"Failed to stop: {e}")
        else:
            print("Master daemon not running (no PID file)")
        return

    if args.status:
        if MASTER_PID_FILE.exists():
            pid = MASTER_PID_FILE.read_text().strip()
            print(f"Master daemon running (PID {pid})")
        else:
            print("Master daemon not running")
        return

    if args.start:
        daemon = NEXUSMasterDaemon()
        await daemon.start()
    else:
        parser.print_help()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
