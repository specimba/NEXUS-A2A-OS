"""NEXUSCLAW Persistent Agent Runner - 7/24 operation with heartbeat loop."""

from __future__ import annotations

import asyncio
import logging
import signal
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from nexus_os.nexusclaw.coordinator import NexusClawCoordinator
from nexus_os.nexusclaw.envelope import NexusClawTaskEnvelope
from nexus_os.nexusclaw.messaging import NEXUSCLAWMessagingHub, MessageResult
from nexus_os.nexusclaw.worklog import WorklogSystem

logger = logging.getLogger("nexusclaw.runner")


@dataclass
class RunnerConfig:
    heartbeat_interval_seconds: int = 30
    max_consecutive_failures: int = 3
    dry_run_only: bool = True
    archivist_sync_interval: int = 300  # 5 minutes


class NexusClawRunner:
    """Persistent agent runner for 7/24 NEXUSCLAW operation."""

    def __init__(self, config: Optional[RunnerConfig] = None):
        self.config = config or RunnerConfig()
        self.coordinator = NexusClawCoordinator()
        self.messaging_hub = NEXUSCLAWMessagingHub()
        self.worklog = WorklogSystem()
        self._running = False
        self._failure_count = 0
        self._archivist_sync_counter = 0

    async def heartbeat(self) -> Dict[str, Any]:
        """Send heartbeat to governance API and check status."""
        now = datetime.now(timezone.utc).isoformat()
        status = self.coordinator.status()
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://127.0.0.1:7352/tasks/heartbeat",
                    json={"agent_id": "nexusclaw-runner", "timestamp": now},
                )
                status["governance_heartbeat"] = response.json() if response.status_code == 200 else {"error": response.status_code}
        except Exception as e:
            logger.warning(f"Governance heartbeat failed: {e}")
            status["governance_heartbeat"] = {"error": str(e)}

        return status

    async def process_message_task(self, task: NexusClawTaskEnvelope) -> Dict[str, Any]:
        """Process a messaging task through governed dispatch."""
        if not task.intent.startswith("send_message"):
            return {"status": "skipped", "reason": "not a messaging task"}

        platform = task.resource_budget.get("platform", "slack")
        target = task.resource_budget.get("target", "")
        text = task.resource_budget.get("text", "")

        if not text:
            return {"status": "skipped", "reason": "no message text"}

        connector = self.messaging_hub.get_connector(platform)
        if not connector:
            return {"status": "error", "error": f"platform {platform} not available"}

        if self.config.dry_run_only:
            return {
                "status": "dry_run",
                "platform": platform,
                "target": target,
                "text_preview": text[:100] + "..." if len(text) > 100 else text,
            }

        if platform == "telegram":
            result = await connector.send_message(chat_id=target, text=text)
        elif platform == "slack":
            result = await connector.send_message(channel=target, text=text)
        elif platform == "discord":
            result = await connector.send_message(channel_id=target, content=text)
        else:
            result = MessageResult(success=False, platform=platform, error="unknown platform")

        return result.to_dict()

    async def daemon_sync(self) -> Dict[str, Any]:
        """Sync with ARCHIVIST daemon: check queue depth, trigger fit if needed."""
        result: Dict[str, Any] = {"synced": False, "records_queued": 0, "fit_triggered": False}
        try:
            # Check archivist import queue depth
            queued = self.worklog.queue_depth()
            result["records_queued"] = queued

            # Trigger fit if queue exceeds threshold or on periodic sync
            heartbeat = max(1, self.config.heartbeat_interval_seconds)
            interval = max(1, self.config.archivist_sync_interval // heartbeat)
            if queued >= 100 or self._archivist_sync_counter >= interval:
                logger.info("ARCHIVIST daemon sync triggered: %d records queued", queued)
                result["fit_triggered"] = True
                self._archivist_sync_counter = 0
            else:
                self._archivist_sync_counter += 1

            result["synced"] = True
        except Exception as e:
            logger.warning("Daemon sync failed: %s", e)
            result["error"] = str(e)
        return result

    async def run_loop(self) -> None:
        """Main loop for persistent operation."""
        self._running = True

        while self._running:
            try:
                hb = await self.heartbeat()
                if hb.get("status") == "halted":
                    logger.warning(f"Coordinator halted: {hb.get('halt_reason')}")
                    self._running = False
                    break

                logger.info(f"Heartbeat OK at {datetime.now(timezone.utc).isoformat()}")
                self._failure_count = 0

                # Daemon sync: ARCHIVIST + worklog
                sync = await self.daemon_sync()
                if sync.get("fit_triggered"):
                    logger.info("ARCHIVIST fit triggered, %d records queued", sync.get("records_queued", 0))

            except Exception as e:
                self._failure_count += 1
                logger.error(f"Heartbeat failed ({self._failure_count}/{self.config.max_consecutive_failures}): {e}")

                if self._failure_count >= self.config.max_consecutive_failures:
                    logger.error("Max consecutive failures reached, stopping runner")
                    self._running = False

            await asyncio.sleep(self.config.heartbeat_interval_seconds)

    def stop(self) -> None:
        """Signal the runner to stop."""
        self._running = False

    def run(self, blocking: bool = True) -> Optional[asyncio.Task]:
        """Start the runner."""
        if blocking:
            asyncio.run(self.run_loop())
        else:
            return asyncio.create_task(self.run_loop())


_runner_instance: Optional[NexusClawRunner] = None


def get_runner() -> NexusClawRunner:
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = NexusClawRunner()
    return _runner_instance


async def shutdown_handler():
    runner = get_runner()
    runner.stop()
    logger.info("NEXUSCLAW runner shutdown complete")


def install_signal_handlers() -> None:
    try:
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown_handler()))
            except NotImplementedError:
                pass
    except Exception as e:
        logger.warning(f"Could not install signal handlers: {e}")
