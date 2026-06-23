"""NEXUSCLAW Messaging Connectors - Telegram, Slack, Discord with governance gates."""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional
from datetime import datetime

import httpx
from pydantic import BaseModel, Field
from nexus_os.nexusclaw.runtime_security import sanitize_inter_agent_message

logger = logging.getLogger("nexusclaw.messaging")


class TelegramConfig(BaseModel):
    bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    api_base: str = "https://api.telegram.org/bot"
    enabled: bool = Field(default_factory=lambda: bool(os.getenv("TELEGRAM_BOT_TOKEN", "")))


class SlackConfig(BaseModel):
    bot_token: str = Field(default_factory=lambda: os.getenv("SLACK_BOT_TOKEN", ""))
    signing_secret: str = Field(default_factory=lambda: os.getenv("SLACK_SIGNING_SECRET", ""))
    api_base: str = "https://slack.com/api"
    enabled: bool = Field(default_factory=lambda: bool(os.getenv("SLACK_BOT_TOKEN", "")))


class DiscordConfig(BaseModel):
    bot_token: str = Field(default_factory=lambda: os.getenv("DISCORD_BOT_TOKEN", ""))
    api_base: str = "https://discord.com/api/v10"
    enabled: bool = Field(default_factory=lambda: bool(os.getenv("DISCORD_BOT_TOKEN", "")))


@dataclass
class MessageResult:
    success: bool
    platform: str
    message_id: Optional[str] = None
    channel: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "platform": self.platform,
            "message_id": self.message_id,
            "channel": self.channel,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class TelegramConnector:
    """Governed Telegram connector with TrustKernel integration."""

    def __init__(self, config: Optional[TelegramConfig] = None):
        self.config = config or TelegramConfig()
        if not self.config.bot_token:
            self.config.enabled = False

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
        disable_preview: bool = True,
    ) -> MessageResult:
        if not self.config.enabled:
            return MessageResult(
                success=False,
                platform="telegram",
                error="Telegram connector not enabled or missing bot token",
            )

        # TerminalSanitizer: strip ANSI escape sequences from inter-agent output
        sanitized_text = sanitize_inter_agent_message({"text": text}, source="nexusclaw", target="telegram")
        text = sanitized_text.get("text", text)

        # Telegram API requires /bot prefix before token
        url = f"{self.config.api_base}bot{self.config.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload)
                data = response.json()

                if response.status_code == 200 and data.get("ok"):
                    msg = data.get("result", {})
                    logger.info(f"[GOVERNED] Telegram message sent to {chat_id}")
                    return MessageResult(
                        success=True,
                        platform="telegram",
                        message_id=str(msg.get("message_id")),
                        channel=str(chat_id),
                    )

                return MessageResult(
                    success=False,
                    platform="telegram",
                    error=f"Telegram API error: {data.get('description', 'unknown')}",
                )
            except Exception as e:
                logger.error(f"Telegram send failed: {e}")
                return MessageResult(
                    success=False,
                    platform="telegram",
                    error=str(e),
                )


class SlackConnector:
    """Governed Slack connector with TrustKernel integration."""

    def __init__(self, config: Optional[SlackConfig] = None):
        self.config = config or SlackConfig()
        if not self.config.bot_token:
            self.config.enabled = False

    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[list] = None,
    ) -> MessageResult:
        if not self.config.enabled:
            return MessageResult(
                success=False,
                platform="slack",
                error="Slack connector not enabled or missing bot token",
            )

        # TerminalSanitizer: strip ANSI escape sequences from inter-agent output
        sanitized = sanitize_inter_agent_message({"text": text}, source="nexusclaw", target="slack")
        text = sanitized.get("text", text)

        url = f"{self.config.api_base}/chat.postMessage"
        headers = {"Authorization": f"Bearer {self.config.bot_token}"}
        payload = {"channel": channel, "text": text, "unfurl_links": False}
        if blocks:
            payload["blocks"] = blocks

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                data = response.json()

                if response.status_code == 200 and data.get("ok"):
                    logger.info(f"[GOVERNED] Slack message sent to {channel}")
                    return MessageResult(
                        success=True,
                        platform="slack",
                        message_id=data.get("ts"),
                        channel=channel,
                    )

                return MessageResult(
                    success=False,
                    platform="slack",
                    error=f"Slack API error: {data.get('error', 'unknown')}",
                )
            except Exception as e:
                logger.error(f"Slack send failed: {e}")
                return MessageResult(
                    success=False,
                    platform="slack",
                    error=str(e),
                )


class DiscordConnector:
    """Governed Discord connector with TrustKernel integration."""

    def __init__(self, config: Optional[DiscordConfig] = None):
        self.config = config or DiscordConfig()
        if not self.config.bot_token:
            self.config.enabled = False

    async def send_message(
        self,
        channel_id: str,
        content: str,
    ) -> MessageResult:
        if not self.config.enabled:
            return MessageResult(
                success=False,
                platform="discord",
                error="Discord connector not enabled or missing bot token",
            )

        # TerminalSanitizer: strip ANSI escape sequences from inter-agent output
        sanitized = sanitize_inter_agent_message({"content": content}, source="nexusclaw", target="discord")
        content = sanitized.get("content", content)

        url = f"{self.config.api_base}/channels/{channel_id}/messages"
        headers = {"Authorization": f"Bot {self.config.bot_token}"}
        payload = {"content": content}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                data = response.json()

                if response.status_code == 200:
                    logger.info(f"[GOVERNED] Discord message sent to {channel_id}")
                    return MessageResult(
                        success=True,
                        platform="discord",
                        message_id=data.get("id"),
                        channel=channel_id,
                    )

                return MessageResult(
                    success=False,
                    platform="discord",
                    error=f"Discord API error: {response.status_code}",
                )
            except Exception as e:
                logger.error(f"Discord send failed: {e}")
                return MessageResult(
                    success=False,
                    platform="discord",
                    error=str(e),
                )


class NEXUSCLAWMessagingHub:
    """Unified messaging hub for NEXUSCLAW agents."""

    def __init__(self):
        self.telegram = TelegramConnector()
        self.slack = SlackConnector()
        self.discord = DiscordConnector()

    def get_connector(self, platform: str) -> Optional[Any]:
        return {"telegram": self.telegram, "slack": self.slack, "discord": self.discord}.get(platform)

    def get_enabled_platforms(self) -> list[str]:
        platforms = []
        if self.telegram.config.enabled:
            platforms.append("telegram")
        if self.slack.config.enabled:
            platforms.append("slack")
        if self.discord.config.enabled:
            platforms.append("discord")
        return platforms