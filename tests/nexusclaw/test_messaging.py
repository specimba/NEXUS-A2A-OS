"""NEXUSCLAW Messaging Layer Tests."""

import pytest

from nexus_os.nexusclaw.messaging import (
    TelegramConnector,
    SlackConnector,
    DiscordConnector,
    NEXUSCLAWMessagingHub,
    MessageResult,
)


class TestTelegramConnector:
    def test_telegram_connector_disabled_without_token(self):
        connector = TelegramConnector()
        assert connector.config.enabled is False

    def test_telegram_connector_enabled_with_token(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-123")
        connector = TelegramConnector()
        assert connector.config.enabled is True

    @pytest.mark.asyncio
    async def test_telegram_send_returns_dry_run_result(self):
        connector = TelegramConnector()
        result = await connector.send_message(chat_id="123", text="test message")
        assert result.success is False
        assert "not enabled" in result.error


class TestSlackConnector:
    def test_slack_connector_disabled_without_token(self):
        connector = SlackConnector()
        assert connector.config.enabled is False

    def test_slack_connector_enabled_with_token(self, monkeypatch):
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
        connector = SlackConnector()
        assert connector.config.enabled is True

    @pytest.mark.asyncio
    async def test_slack_send_returns_dry_run_result(self):
        connector = SlackConnector()
        result = await connector.send_message(channel="#general", text="test")
        assert result.success is False
        assert "not enabled" in result.error


class TestDiscordConnector:
    def test_discord_connector_disabled_without_token(self):
        connector = DiscordConnector()
        assert connector.config.enabled is False

    def test_discord_connector_enabled_with_token(self, monkeypatch):
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "discord-token-xyz")
        connector = DiscordConnector()
        assert connector.config.enabled is True

    @pytest.mark.asyncio
    async def test_discord_send_returns_dry_run_result(self):
        connector = DiscordConnector()
        result = await connector.send_message(channel_id="123", content="test")
        assert result.success is False
        assert "not enabled" in result.error


class TestMessagingHub:
    def test_hub_get_disabled_connectors(self):
        hub = NEXUSCLAWMessagingHub()
        assert hub.get_connector("telegram").config.enabled is False
        assert hub.get_connector("slack").config.enabled is False
        assert hub.get_connector("discord").config.enabled is False

    def test_hub_get_enabled_platforms(self):
        hub = NEXUSCLAWMessagingHub()
        enabled = hub.get_enabled_platforms()
        assert "telegram" not in enabled
        assert "slack" not in enabled
        assert "discord" not in enabled


class TestMessageResult:
    def test_message_result_to_dict(self):
        result = MessageResult(
            success=True,
            platform="slack",
            message_id="123.456",
            channel="#general",
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["platform"] == "slack"
        assert d["message_id"] == "123.456"
        assert d["channel"] == "#general"
        assert "timestamp" in d

    def test_message_result_error_case(self):
        result = MessageResult(
            success=False,
            platform="telegram",
            error="connection failed",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] is not None