"""
NEXUS CLI-CTL Messaging Integration
Wraps NEXUSCLAWMessagingHub for master_daemon + Brain API consumption.
Provides governed send, broadcast, and status for Telegram/Slack/Discord.
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from nexus_os.nexusclaw.messaging import (
    NEXUSCLAWMessagingHub,
    TelegramConnector,
    SlackConnector,
    DiscordConnector,
    MessageResult,
)

logger = logging.getLogger("nexus_cli_ctl.integrations.messaging")


class MessagingIntegration:
    """Unified messaging adapter wired into master daemon + state manager."""

    SYNC_INTERVAL = 60  # seconds between status refresh

    def __init__(self, state_manager=None):
        self.sm = state_manager
        self.hub = NEXUSCLAWMessagingHub()
        self._history: List[Dict] = []
        self._max_history = 200
        self.running = False

    async def start(self):
        if self.running:
            return
        self.running = True
        asyncio.create_task(self._status_loop())
        enabled = self.hub.get_enabled_platforms()
        logger.info(f"Messaging Integration started (enabled: {enabled or 'none'})")

    async def stop(self):
        self.running = False

    async def send(self, platform: str, channel: str, text: str, **kwargs) -> Dict:
        """Send a governed message to a specific platform + channel."""
        connector = self.hub.get_connector(platform)
        if not connector:
            return {"success": False, "platform": platform, "error": f"Unknown platform: {platform}"}

        if platform == "telegram":
            result: MessageResult = await connector.send_message(channel, text, **kwargs)
        elif platform == "slack":
            result = await connector.send_message(channel, text, **kwargs)
        elif platform == "discord":
            result = await connector.send_message(channel, text, **kwargs)
        else:
            return {"success": False, "error": f"No send handler for {platform}"}

        entry = result.to_dict()
        self._record(entry)

        if self.sm:
            await self.sm.publish(
                "messaging.last_send",
                entry,
                source="messaging"
            )

        return entry

    async def broadcast(self, text: str, channels: Optional[Dict[str, List[str]]] = None) -> List[Dict]:
        """Broadcast a message to specified or all enabled platforms.
        channels format: {"telegram": ["chat_id_1"], "slack": ["#channel"]}
        If channels is None, sends to all enabled platforms (no targets = status only).
        """
        results = []
        if channels is None:
            channels = {}

        target_platforms = list(channels.keys()) if channels else self.hub.get_enabled_platforms()
        for platform in target_platforms:
            targets = channels.get(platform, [])
            for target in targets:
                result = await self.send(platform, target, text)
                results.append(result)

        if self.sm:
            await self.sm.publish(
                "messaging.broadcast",
                {"text_preview": text[:100], "results_count": len(results), "timestamp": datetime.now().isoformat()},
                source="messaging"
            )

        return results

    def get_status(self) -> Dict:
        """Current messaging status"""
        enabled = self.hub.get_enabled_platforms()
        return {
            "running": self.running,
            "enabled_platforms": enabled,
            "telegram": self.hub.telegram.config.enabled,
            "slack": self.hub.slack.config.enabled,
            "discord": self.hub.discord.config.enabled,
            "history_size": len(self._history),
        }

    def get_history(self, limit: int = 20) -> List[Dict]:
        """Recent messaging history"""
        return self._history[-limit:]

    def _record(self, entry: Dict):
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    async def _status_loop(self):
        """Periodically publish messaging status to state manager"""
        while self.running:
            try:
                if self.sm:
                    await self.sm.publish(
                        "messaging.status",
                        self.get_status(),
                        source="messaging"
                    )
            except Exception as e:
                logger.debug(f"Messaging status loop error: {e}")
            await asyncio.sleep(self.SYNC_INTERVAL)


_messaging_integration: Optional[MessagingIntegration] = None


def get_messaging_integration(state_manager=None) -> MessagingIntegration:
    global _messaging_integration
    if _messaging_integration is None:
        _messaging_integration = MessagingIntegration(state_manager=state_manager)
    elif state_manager and _messaging_integration.sm is None:
        _messaging_integration.sm = state_manager
    return _messaging_integration
