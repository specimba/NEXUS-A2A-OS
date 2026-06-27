"""NEXUS Inter-Session A2A Channels — Persistent message bus for agent communication.

Implements Plan 20: a typed channel system in ~/.nexus/a2a_channels/ where
agents write JSONL messages. Integrates with Dream Cycle, Calibrated
Hallucination Detector, and MCP Gateway for cross-session discovery.

Usage:
    bus = A2AChannelBus()
    bus.publish("dream-001", "dream_cycle", "pattern extracted", "dream-patterns")
    messages = bus.subscribe("dream-001")
    print(bus.get_stats())
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

A2A_ROOT = Path(os.path.expanduser("~")) / ".nexus" / "a2a_channels"


@dataclass
class A2AMessage:
    """One message on an A2A channel."""

    sender: str
    message: str
    topic: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    channel_id: str = ""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> A2AMessage:
        return cls(
            sender=d.get("sender", ""),
            message=d.get("message", ""),
            topic=d.get("topic", ""),
            timestamp=d.get("timestamp", datetime.now(timezone.utc).isoformat()),
            channel_id=d.get("channel_id", ""),
            message_id=d.get("message_id", str(uuid.uuid4())),
        )


class A2AChannel:
    """One typed channel — a topic-based message stream backed by JSONL."""

    def __init__(
        self,
        channel_id: str,
        topic: str,
        ttl_hours: float = 72.0,
        max_messages: int = 1000,
    ):
        self.channel_id = channel_id
        self.topic = topic
        self.ttl_hours = ttl_hours
        self.max_messages = max_messages
        self._dir = A2A_ROOT / channel_id
        self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def _file_path(self) -> Path:
        return self._dir / f"{self.topic}.jsonl"

    def publish(self, sender: str, message: str) -> A2AMessage:
        msg = A2AMessage(
            sender=sender,
            message=message,
            topic=self.topic,
            channel_id=self.channel_id,
        )
        line = json.dumps(msg.to_dict(), ensure_ascii=False) + "\n"
        file_path = self._file_path
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(line)
            self._trim()
        except Exception as exc:
            logger.warning("A2AChannel[%s/%s] publish failed: %s", self.channel_id, self.topic, exc)
        return msg

    def _trim(self):
        """Keep only the latest max_messages by trimming the file."""
        file_path = self._file_path
        if not file_path.exists():
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > self.max_messages:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines[-self.max_messages:])
        except Exception as exc:
            logger.warning("A2AChannel[%s/%s] trim failed: %s", self.channel_id, self.topic, exc)

    def subscribe(
        self, since_timestamp: str | None = None, max_messages: int = 100
    ) -> list[A2AMessage]:
        file_path = self._file_path
        if not file_path.exists():
            return []
        messages: list[A2AMessage] = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = A2AMessage.from_dict(json.loads(line))
                        if since_timestamp and msg.timestamp < since_timestamp:
                            continue
                        messages.append(msg)
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            logger.warning("A2AChannel[%s/%s] subscribe failed: %s", self.channel_id, self.topic, exc)
            return []
        return messages[-max_messages:]

    def purge_stale(self) -> int:
        """Remove messages older than ttl_hours. Returns count of purged."""
        file_path = self._file_path
        if not file_path.exists():
            return 0
        cutoff = datetime.now(timezone.utc).timestamp() - (self.ttl_hours * 3600)
        kept: list[str] = []
        purged = 0
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_stripped = line.strip()
                    if not line_stripped:
                        continue
                    try:
                        data = json.loads(line_stripped)
                        ts = data.get("timestamp", "")
                        if ts:
                            msg_ts = datetime.fromisoformat(ts).timestamp()
                            if msg_ts < cutoff:
                                purged += 1
                                continue
                        kept.append(line)
                    except (json.JSONDecodeError, ValueError):
                        kept.append(line)
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(kept)
        except Exception as exc:
            logger.warning("A2AChannel[%s/%s] purge_stale failed: %s", self.channel_id, self.topic, exc)
            return 0
        return purged

    def message_count(self) -> int:
        file_path = self._file_path
        if not file_path.exists():
            return 0
        count = 0
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        count += 1
        except Exception:
            pass
        return count


class A2AChannelBus:
    """Main A2A inter-session message bus.

    Manages channels under ~/.nexus/a2a_channels/{channel_id}/{topic}.jsonl.
    """

    def __init__(self, root: str | Path | None = None):
        self._root = Path(root) if root else A2A_ROOT
        self._root.mkdir(parents=True, exist_ok=True)
        self._channels: dict[str, dict[str, A2AChannel]] = {}

    def _channel_dir(self, channel_id: str) -> Path:
        return self._root / channel_id

    def get_or_create_channel(
        self,
        channel_id: str,
        topic: str,
        ttl_hours: float = 72.0,
        max_messages: int = 1000,
    ) -> A2AChannel:
        if channel_id not in self._channels:
            self._channels[channel_id] = {}
        if topic not in self._channels[channel_id]:
            self._channels[channel_id][topic] = A2AChannel(
                channel_id=channel_id,
                topic=topic,
                ttl_hours=ttl_hours,
                max_messages=max_messages,
            )
        return self._channels[channel_id][topic]

    def publish(
        self,
        channel_id: str,
        sender: str,
        message: str,
        topic: str,
        ttl_hours: float = 72.0,
        max_messages: int = 1000,
    ) -> A2AMessage:
        channel = self.get_or_create_channel(channel_id, topic, ttl_hours, max_messages)
        return channel.publish(sender, message)

    def subscribe(
        self,
        channel_id: str,
        topic: str | None = None,
        since_timestamp: str | None = None,
        max_messages: int = 100,
    ) -> list[A2AMessage]:
        if topic:
            channel = self.get_or_create_channel(channel_id, topic)
            return channel.subscribe(since_timestamp=since_timestamp, max_messages=max_messages)
        results: list[A2AMessage] = []
        topic_dir = self._channel_dir(channel_id)
        if not topic_dir.exists():
            return results
        for jsonl_file in sorted(topic_dir.glob("*.jsonl")):
            topic_name = jsonl_file.stem
            channel = self.get_or_create_channel(channel_id, topic_name)
            results.extend(
                channel.subscribe(since_timestamp=since_timestamp, max_messages=max_messages)
            )
        results.sort(key=lambda m: m.timestamp, reverse=True)
        return results[:max_messages]

    def purge_stale(self, channel_id: str | None = None) -> dict[str, int]:
        purged: dict[str, int] = {}
        if channel_id:
            topic_dir = self._channel_dir(channel_id)
            if topic_dir.exists():
                for jsonl_file in topic_dir.glob("*.jsonl"):
                    topic_name = jsonl_file.stem
                    channel = self.get_or_create_channel(channel_id, topic_name)
                    count = channel.purge_stale()
                    if count:
                        purged[f"{channel_id}/{topic_name}"] = count
        else:
            for ch_dir in self._root.iterdir():
                if ch_dir.is_dir():
                    for jsonl_file in ch_dir.glob("*.jsonl"):
                        topic_name = jsonl_file.stem
                        channel = self.get_or_create_channel(ch_dir.name, topic_name)
                        count = channel.purge_stale()
                        if count:
                            purged[f"{ch_dir.name}/{topic_name}"] = count
        return purged

    def discover(self, topics_filter: list[str] | None = None) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for ch_dir in sorted(self._root.iterdir()):
            if not ch_dir.is_dir():
                continue
            channel_id = ch_dir.name
            topics: dict[str, int] = {}
            for jsonl_file in ch_dir.glob("*.jsonl"):
                topic_name = jsonl_file.stem
                if topics_filter and topic_name not in topics_filter:
                    continue
                topics[topic_name] = sum(
                    1 for _ in jsonl_file.open("r", encoding="utf-8") if _.strip()
                )
            if topics:
                result[channel_id] = {
                    "topics": topics,
                    "total_messages": sum(topics.values()),
                }
        return result

    def consolidate(self) -> dict[str, Any]:
        purged = self.purge_stale()
        discovery = self.discover()
        total_messages = sum(
            ch["total_messages"] for ch in discovery.values()
        )
        return {
            "ok": True,
            "channels": len(discovery),
            "total_messages": total_messages,
            "purged": purged,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_stats(self) -> dict[str, Any]:
        discovery = self.discover()
        total_messages = sum(ch["total_messages"] for ch in discovery.values())
        total_topics = sum(len(ch["topics"]) for ch in discovery.values())
        return {
            "channels": len(discovery),
            "topics": total_topics,
            "total_messages": total_messages,
            "channel_details": discovery,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ── Integration wires ──────────────────────────────────────────────

def wire_to_dream_cycle(
    dream_cycle_instance: Any,
    channel_bus: A2AChannelBus,
    channel_id: str = "dream",
) -> Callable[[], None]:
    """Patch DreamCycle._emit_to_a2a to use A2AChannelBus instead of raw file writes.

    Returns a cleanup callable that restores the original method.
    """
    original_emit = dream_cycle_instance._emit_to_a2a

    def patched_emit(message: str, topic: str = "dream-cycle"):
        try:
            channel_bus.publish(
                channel_id=channel_id,
                sender="dream_cycle",
                message=message,
                topic=topic,
            )
        except Exception as exc:
            logger.warning("wire_to_dream_cycle emit failed: %s", exc)

    dream_cycle_instance._emit_to_a2a = patched_emit

    def cleanup():
        dream_cycle_instance._emit_to_a2a = original_emit

    return cleanup


def wire_to_chd(
    chd_instance: Any,
    channel_bus: A2AChannelBus,
    channel_id: str = "hallucination",
) -> Callable[[], None]:
    """Patch CalibratedHallucinationDetector._emit_a2a to use A2AChannelBus.

    Returns a cleanup callable that restores the original method.
    """
    original_emit = chd_instance._emit_a2a

    def patched_emit(message: str, topic: str = "hallucination"):
        try:
            channel_bus.publish(
                channel_id=channel_id,
                sender="calibrated-hallucination-detector",
                message=message,
                topic=topic,
            )
        except Exception as exc:
            logger.warning("wire_to_chd emit failed: %s", exc)

    chd_instance._emit_a2a = patched_emit

    def cleanup():
        chd_instance._emit_a2a = original_emit

    return cleanup


def wire_to_mcp_gateway(
    mcp_gateway_instance: Any,
    channel_bus: A2AChannelBus,
    channel_id: str = "mcp-gateway",
) -> Callable[[], None]:
    """Patch MCPGateway to publish blocked/allowed stats to A2A.

    Replaces the _audit method to also publish to A2A. Returns a cleanup
    callable that restores the original method.
    """
    original_audit = mcp_gateway_instance._audit

    def patched_audit(entry: dict[str, Any]):
        original_audit(entry)
        try:
            allowed = entry.get("allowed", False)
            topic = "mcp-allowed" if allowed else "mcp-blocked"
            channel_bus.publish(
                channel_id=channel_id,
                sender="mcp_gateway",
                message=json.dumps(entry, ensure_ascii=False),
                topic=topic,
            )
        except Exception as exc:
            logger.warning("wire_to_mcp_gateway emit failed: %s", exc)

    mcp_gateway_instance._audit = patched_audit

    def cleanup():
        mcp_gateway_instance._audit = original_audit

    return cleanup


# ── CLI entry point ─────────────────────────────────────────────────

def cli_main():
    import argparse

    ap = argparse.ArgumentParser(description="NEXUS A2A Channels — inter-session message bus (Plan 20)")
    ap.add_argument("--list", action="store_true", help="List all channels with topics and message counts")
    ap.add_argument("--publish", nargs=3, metavar=("CHANNEL", "TOPIC", "MSG"), default=None,
                    help="Publish a message: --publish CHANNEL TOPIC MSG")
    ap.add_argument("--subscribe", nargs=1, metavar="CHANNEL", default=None,
                    help="Tail recent messages from a channel")
    ap.add_argument("--consolidate", action="store_true", help="Purge stale messages from all channels")
    ap.add_argument("--stats", action="store_true", help="Show summary stats for all channels")
    args = ap.parse_args()

    bus = A2AChannelBus()

    if args.list:
        channels = bus.discover()
        print(json.dumps(channels, indent=2))
        return

    if args.publish:
        channel_id, topic, msg = args.publish
        result = bus.publish(channel_id=channel_id, sender="cli", message=msg, topic=topic)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return

    if args.subscribe:
        channel_id = args.subscribe[0]
        messages = bus.subscribe(channel_id, max_messages=50)
        print(json.dumps([m.to_dict() for m in messages], indent=2, ensure_ascii=False))
        return

    if args.consolidate:
        result = bus.consolidate()
        print(json.dumps(result, indent=2))
        return

    if args.stats:
        stats = bus.get_stats()
        print(json.dumps(stats, indent=2))
        return

    ap.print_help()


if __name__ == "__main__":
    cli_main()
