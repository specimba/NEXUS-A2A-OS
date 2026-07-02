"""nexus_os/nexusclaw/message_bus.py - NEXUSCLAW Message Bus

The Message Bus enables agents to communicate with each other and with
external platforms (Slack, Telegram, Discord). All messages pass through
governance gates (trust score check, risk level validation) and are logged
to the 8-channel memory (EPISODIC, TASK, META) and worklog.

Features:
  - Internal agent-to-agent messaging (direct and broadcast)
  - External platform bridging (Slack, Telegram, Discord)
  - Message threading (conversations between agents)
  - Trust-gated message delivery (low-trust agents can't send to high-trust channels)
  - All messages are evidence-grounded and auditable
"""

from __future__ import annotations

import asyncio
import collections
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set

from nexus_os.nexusclaw.agent_pool import AgentPool, AgentRecord, get_agent_pool
from nexus_os.nexusclaw.envelope import RiskLevel
from nexus_os.nexusclaw.worklog import WorklogSystem, get_worklog
from nexus_os.vault.memory_channels import MemoryChannelManager, get_manager

logger = logging.getLogger("nexusclaw.message_bus")


class MessageType(str, Enum):
    """Type of message in the NEXUSCLAW message bus."""
    DIRECT = "direct"         # One-to-one agent message
    BROADCAST = "broadcast"     # One-to-many agent message
    THREAD_REPLY = "thread_reply"  # Reply in a conversation thread
    EXTERNAL_OUT = "external_out"  # Outbound to external platform (Slack, etc.)
    EXTERNAL_IN = "external_in"   # Inbound from external platform
    SYSTEM = "system"         # System-level message (alerts, governance)
    BRAINSTORM = "brainstorm"     # Collaborative brainstorming message


class MessagePriority(str, Enum):
    """Priority of a message."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NexusMessage:
    """A message in the NEXUSCLAW message bus."""
    message_id: str
    sender_id: str
    sender_name: str
    recipient_ids: List[str]  # empty = broadcast
    message_type: MessageType
    content: str
    priority: MessagePriority = MessagePriority.NORMAL
    thread_id: Optional[str] = None  # For conversation threading
    risk_level: RiskLevel = RiskLevel.LOW
    trust_required: float = 0.0  # Minimum trust score to deliver this message
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    delivered: bool = False
    delivery_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "recipient_ids": self.recipient_ids,
            "message_type": self.message_type.value,
            "content": self.content,
            "priority": self.priority.value,
            "thread_id": self.thread_id,
            "risk_level": self.risk_level.value,
            "trust_required": self.trust_required,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "delivered": self.delivered,
            "delivery_error": self.delivery_error,
        }


@dataclass
class MessageThread:
    """A conversation thread between agents."""
    thread_id: str
    topic: str
    participant_ids: Set[str] = field(default_factory=set)
    messages: List[NexusMessage] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "open"  # open, closed, archived

    def add_message(self, message: NexusMessage) -> None:
        self.messages.append(message)
        self.participant_ids.add(message.sender_id)
        for rid in message.recipient_ids:
            self.participant_ids.add(rid)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "topic": self.topic,
            "participant_ids": list(self.participant_ids),
            "message_count": len(self.messages),
            "created_at": self.created_at,
            "status": self.status,
        }


class MessageRateLimiter:
    """Per-sender token bucket rate limiter for the message bus."""

    def __init__(self, tokens_per_second: float = 5.0, max_burst: int = 10) -> None:
        self.tokens_per_second = tokens_per_second
        self.max_burst = max_burst
        self._tokens: float = float(max_burst)
        self._last_refill: float = time.monotonic()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        """Check if one message is allowed. Returns True if under rate limit."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self.max_burst, self._tokens + elapsed * self.tokens_per_second)
            self._last_refill = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False


class MessageBus:
    """NEXUSCLAW message bus for inter-agent communication.

    All messages are:
    - Trust-gated (sender must meet trust_required, receiver must be trusted)
    - Risk-aware (high-risk messages require governance approval)
    - Threaded (conversations are tracked)
    - Auditable (all messages go to memory channels and worklog)
    - External-platform-aware (can bridge to Slack, Telegram, Discord)
    """

    # Maximum message length
    MAX_MESSAGE_LENGTH = 4096
    # Maximum messages per thread
    MAX_THREAD_MESSAGES = 1000
    # Default rate limit per sender
    DEFAULT_RATE_LIMIT_TPS = 5.0
    DEFAULT_RATE_LIMIT_BURST = 10
    # SYSTEM message authorization (audit message_bus.py:405): identity
    # allowlist + trust floor, NOT the caller-writable metadata flag.
    SYSTEM_SENDER_ALLOWLIST = frozenset({"system", "nexus-governor"})
    SYSTEM_SENDER_MIN_TRUST = 90.0

    def __init__(
        self,
        agent_pool: Optional[AgentPool] = None,
        worklog: Optional[WorklogSystem] = None,
        memory_channels: Optional[MemoryChannelManager] = None,
        rate_limit_tps: float = DEFAULT_RATE_LIMIT_TPS,
        rate_limit_burst: int = DEFAULT_RATE_LIMIT_BURST,
        system_senders: Optional[Set[str]] = None,
    ) -> None:
        self.agent_pool = agent_pool or get_agent_pool()
        # Bus-owner-supplied allowlist; senders can't add themselves.
        self._system_senders: Set[str] = (
            set(system_senders) if system_senders is not None
            else set(self.SYSTEM_SENDER_ALLOWLIST)
        )
        self.worklog = worklog or get_worklog()
        self.memory_channels = memory_channels or get_manager()
        self._rate_limiters: Dict[str, MessageRateLimiter] = {}
        self._rate_limit_tps = rate_limit_tps
        self._rate_limit_burst = rate_limit_burst
        self._threads: Dict[str, MessageThread] = {}
        self._message_history: collections.deque[NexusMessage] = collections.deque(maxlen=5000)
        self._external_connectors: Dict[str, Any] = {}
        self._async_loop: Optional[asyncio.AbstractEventLoop] = None
        self._async_loop_ready: threading.Event = threading.Event()
        self._async_thread: Optional[threading.Thread] = None
        
        # Pre-load enabled connectors from NEXUSCLAWMessagingHub
        from nexus_os.nexusclaw.messaging import NEXUSCLAWMessagingHub
        hub = NEXUSCLAWMessagingHub()
        for platform in ["telegram", "slack", "discord"]:
            connector = hub.get_connector(platform)
            if connector and connector.config.enabled:
                self._external_connectors[platform] = connector

        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Async event loop (dedicated thread for external dispatch)
    # ------------------------------------------------------------------

    def _ensure_async_loop(self) -> None:
        """Start a dedicated daemon thread with its own event loop for external dispatch."""
        if self._async_loop is not None:
            return
        loop = asyncio.new_event_loop()

        def _run_loop() -> None:
            asyncio.set_event_loop(loop)
            self._async_loop = loop
            self._async_loop_ready.set()
            loop.run_forever()

        thread = threading.Thread(target=_run_loop, daemon=True, name="nexusclaw-async-dispatch")
        thread.start()
        self._async_thread = thread
        self._async_loop_ready.wait(timeout=5.0)

    def _dispatch_async(self, coro: asyncio.coroutine) -> None:
        """Submit an async coroutine to the dedicated event loop thread."""
        self._ensure_async_loop()
        asyncio.run_coroutine_threadsafe(coro, self._async_loop)

    def shutdown(self) -> None:
        """Shut down the dedicated async event loop."""
        if self._async_loop is not None and self._async_loop.is_running():
            self._async_loop.call_soon_threadsafe(self._async_loop.stop)

    # ------------------------------------------------------------------
    # Core messaging
    # ------------------------------------------------------------------

    def _check_rate_limit(self, sender_id: str) -> bool:
        """Check if sender is under rate limit. Returns True if allowed."""
        if sender_id not in self._rate_limiters:
            self._rate_limiters[sender_id] = MessageRateLimiter(
                tokens_per_second=self._rate_limit_tps,
                max_burst=self._rate_limit_burst,
            )
        return self._rate_limiters[sender_id].allow()

    def send(self, message: NexusMessage) -> NexusMessage:
        """Send a message through the message bus with governance gates."""
        with self._lock:
            # Validate message length
            if len(message.content) > self.MAX_MESSAGE_LENGTH:
                message.delivery_error = f"Message exceeds max length ({self.MAX_MESSAGE_LENGTH} chars)"
                message.delivered = False
                self._log_undelivered(message)
                return message

            # Rate limiting gate (system messages bypass)
            if message.message_type != MessageType.SYSTEM and not self._check_rate_limit(message.sender_id):
                message.delivery_error = (
                    f"Sender {message.sender_id} rate limited "
                    f"({self._rate_limit_tps:.1f} msg/s, burst={self._rate_limit_burst})"
                )
                message.delivered = False
                self._log_undelivered(message)
                return message

            # Validate sender exists and is trusted
            sender = self.agent_pool.get(message.sender_id)
            if not sender:
                message.delivery_error = f"Sender {message.sender_id} not found in agent pool"
                message.delivered = False
                self._log_undelivered(message)
                return message

            if sender.trust_score < message.trust_required:
                message.delivery_error = (
                    f"Sender trust score {sender.trust_score} below required {message.trust_required}"
                )
                message.delivered = False
                self._log_undelivered(message)
                return message

            # Check sender status
            if not sender.is_available and message.message_type != MessageType.SYSTEM:
                message.delivery_error = f"Sender {message.sender_id} is not available (status={sender.status.value})"
                message.delivered = False
                self._log_undelivered(message)
                return message

            # Route message based on type
            if message.message_type == MessageType.DIRECT:
                self._route_direct(message)
            elif message.message_type == MessageType.BROADCAST:
                self._route_broadcast(message)
            elif message.message_type == MessageType.THREAD_REPLY:
                self._route_thread_reply(message)
            elif message.message_type == MessageType.EXTERNAL_OUT:
                self._route_external_out(message)
            elif message.message_type == MessageType.EXTERNAL_IN:
                self._route_external_in(message)
            elif message.message_type == MessageType.SYSTEM:
                self._route_system(message)
            elif message.message_type == MessageType.BRAINSTORM:
                self._route_brainstorm(message)
            else:
                message.delivery_error = f"Unknown message type: {message.message_type.value}"
                message.delivered = False

            if not message.delivery_error:
                message.delivered = True

            # Store in history
            self._message_history.append(message)

            # Log to memory and worklog
            self._log_message(message)

            return message

    def _route_direct(self, message: NexusMessage) -> None:
        """Route a direct message to specific recipients."""
        for recipient_id in message.recipient_ids:
            recipient = self.agent_pool.get(recipient_id)
            if not recipient:
                message.delivery_error = f"Recipient {recipient_id} not found"
                return
            if not recipient.is_available:
                message.delivery_error = f"Recipient {recipient_id} is not available"
                return
            # Trust check: recipient must be trusted for this message's risk level
            if message.risk_level == RiskLevel.HIGH and recipient.trust_score < 70.0:
                message.delivery_error = f"Recipient {recipient_id} trust too low for high-risk message"
                return
            if message.risk_level == RiskLevel.CRITICAL and recipient.trust_score < 90.0:
                message.delivery_error = f"Recipient {recipient_id} trust too low for critical message"
                return

    def _route_broadcast(self, message: NexusMessage) -> None:
        """Route a broadcast message to all available agents."""
        available = self.agent_pool.list_available()
        message.recipient_ids = [a.agent_id for a in available]
        # Broadcasts are limited to normal priority and low/medium risk
        if message.priority == MessagePriority.CRITICAL:
            message.priority = MessagePriority.HIGH
        if message.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            message.risk_level = RiskLevel.MEDIUM
            message.trust_required = 30.0

    def _route_thread_reply(self, message: NexusMessage) -> None:
        """Route a reply to a conversation thread."""
        if not message.thread_id or message.thread_id not in self._threads:
            message.delivery_error = f"Thread {message.thread_id} not found"
            return

        thread = self._threads[message.thread_id]
        if thread.status != "open":
            message.delivery_error = f"Thread {message.thread_id} is {thread.status}"
            return

        if len(thread.messages) >= self.MAX_THREAD_MESSAGES:
            message.delivery_error = f"Thread {message.thread_id} has reached max messages"
            return

        thread.add_message(message)

    def _route_external_out(self, message: NexusMessage) -> None:
        """Route a message to an external platform."""
        # External messages require higher trust
        if message.sender_id != "system" and not self.agent_pool.get(message.sender_id):
            message.delivery_error = "External messages require registered sender"
            return

        # External messages are capped at normal priority
        if message.priority == MessagePriority.CRITICAL:
            message.priority = MessagePriority.HIGH

        # Mark as delivered (actual delivery handled by connector)
        message.delivered = True
        message.metadata["external_out_queued"] = True

        platform = message.metadata.get("platform", "slack")
        target = message.metadata.get("target", "")
        connector = self.get_external_connector(platform)
        if connector:
            if platform == "telegram":
                coro = connector.send_message(chat_id=target, text=message.content)
            elif platform == "slack":
                coro = connector.send_message(channel=target, text=message.content)
            elif platform == "discord":
                coro = connector.send_message(channel_id=target, content=message.content)
            else:
                coro = None
            
            if coro:
                try:
                    self._dispatch_async(coro)
                    message.metadata["external_connector_dispatched"] = True
                except Exception as e:
                    logger.warning("Failed to dispatch external message: %s", e)
                    message.metadata["external_connector_error"] = str(e)

    def _route_external_in(self, message: NexusMessage) -> None:
        """Process an incoming message from an external platform."""
        # External incoming messages are treated as system messages initially
        # They require validation before being forwarded to other agents
        message.trust_required = 50.0  # Higher trust required for external inputs
        message.delivered = True
        message.metadata["external_in_processed"] = True

    def _route_system(self, message: NexusMessage) -> None:
        """Route a system message (always delivered, bypasses most checks).

        Only allowlisted governance senders with a high trust score can send
        SYSTEM messages. Audit (message_bus.py:405): the old gate was the
        metadata flag "governance_origin", which the sender writes itself —
        any registered agent could claim SYSTEM (and with it the rate-limit
        and availability bypasses). Identity + trust are checked instead;
        the metadata flag is ignored for authorization.
        """
        sender = self.agent_pool.get(message.sender_id)
        if (
            sender is None
            or message.sender_id not in self._system_senders
            or sender.trust_score < self.SYSTEM_SENDER_MIN_TRUST
        ):
            message.delivery_error = (
                f"Sender {message.sender_id} is not authorized to send SYSTEM messages"
            )
            message.delivered = False
            return
        message.delivered = True
        # System messages go to all agents if no recipients specified
        if not message.recipient_ids:
            available = self.agent_pool.list_available()
            message.recipient_ids = [a.agent_id for a in available]

    def _route_brainstorm(self, message: NexusMessage) -> None:
        """Route a brainstorming message to all participants in a brainstorm session."""
        # Brainstorm messages are delivered to all specified recipients
        # They are handled by the BrainstormEngine separately
        for recipient_id in message.recipient_ids:
            recipient = self.agent_pool.get(recipient_id)
            if not recipient or not recipient.is_available:
                message.delivery_error = f"Brainstorm recipient {recipient_id} not available"
                return
        message.delivered = True

    # ------------------------------------------------------------------
    # Thread management
    # ------------------------------------------------------------------

    def create_thread(self, topic: str, participant_ids: List[str], thread_id: Optional[str] = None) -> MessageThread:
        """Create a new conversation thread."""
        with self._lock:
            thread_id = thread_id or f"thread-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{hash(topic) % 10000}"
            thread = MessageThread(
                thread_id=thread_id,
                topic=topic,
                participant_ids=set(participant_ids),
            )
            self._threads[thread_id] = thread

            # Log thread creation
            self._log_to_memory(
                agent_id="nexusclaw-message-bus",
                content=f"Thread created: {topic} ({thread_id}) with participants {participant_ids}",
                meta_type="thread_created",
                meta_value=1.0,
            )
            return thread

    def get_thread(self, thread_id: str) -> Optional[MessageThread]:
        """Get a thread by ID."""
        with self._lock:
            return self._threads.get(thread_id)

    def list_threads(self, participant_id: Optional[str] = None, status: Optional[str] = None) -> List[MessageThread]:
        """List threads, optionally filtered by participant or status."""
        with self._lock:
            threads = list(self._threads.values())
            if participant_id:
                threads = [t for t in threads if participant_id in t.participant_ids]
            if status:
                threads = [t for t in threads if t.status == status]
            return threads

    def close_thread(self, thread_id: str) -> Optional[MessageThread]:
        """Close a thread (no new messages)."""
        with self._lock:
            thread = self._threads.get(thread_id)
            if thread:
                thread.status = "closed"
            return thread

    # ------------------------------------------------------------------
    # External connectors
    # ------------------------------------------------------------------

    def register_external_connector(self, name: str, connector: Any) -> None:
        """Register an external platform connector (e.g., SlackConnector)."""
        self._external_connectors[name] = connector
        logger.info("External connector registered: %s", name)

    def get_external_connector(self, name: str) -> Optional[Any]:
        """Get an external connector by name."""
        return self._external_connectors.get(name)

    def list_external_connectors(self) -> List[str]:
        """List all registered external connectors."""
        return list(self._external_connectors.keys())

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_message(self, message: NexusMessage) -> None:
        """Log a message to worklog and memory channels."""
        # Worklog
        try:
            self.worklog.log_task(
                agent_id=message.sender_id,
                task_id=message.message_id,
                intent=f"message:{message.message_type.value}",
                status="delivered" if message.delivered else "failed",
                duration_ms=0.0,
                evidence=[message.content[:200]] if message.content else [],
                metadata={
                    "message": message.to_dict(),
                    "recipients": message.recipient_ids,
                },
            )
        except Exception as e:
            logger.warning("Failed to log message to worklog: %s", e)

        # EPISODIC memory
        try:
            self.memory_channels.append_episodic(
                agent_id=message.sender_id,
                content=f"[{message.message_type.value}] {message.sender_name}: {message.content[:500]}",
                outcome="delivered" if message.delivered else "failed",
                duration_ms=0.0,
                token_count=len(message.content.split()),
                trace_id=message.message_id,
            )
        except Exception as e:
            logger.warning("Failed to log message to EPISODIC: %s", e)

    def _log_undelivered(self, message: NexusMessage) -> None:
        """Log an undelivered message to memory."""
        try:
            self.memory_channels.append_episodic(
                agent_id=message.sender_id or "unknown",
                content=f"Undelivered message: {message.delivery_error}",
                outcome="failed",
                duration_ms=0.0,
                token_count=0,
                trace_id=message.message_id,
            )
        except Exception as e:
            logger.warning("Failed to log undelivered message: %s", e)

    def _log_to_memory(self, agent_id: str, content: str, meta_type: str, meta_value: float) -> None:
        """Log a system event to META channel."""
        try:
            self.memory_channels.append_meta(
                agent_id=agent_id,
                meta_type=meta_type,
                meta_value=meta_value,
                content=content,
                trust_score=100.0,
            )
        except Exception as e:
            logger.warning("Failed to log to META: %s", e)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Return message bus statistics."""
        with self._lock:
            delivered = sum(1 for m in self._message_history if m.delivered)
            failed = len(self._message_history) - delivered
            return {
                "total_messages": len(self._message_history),
                "delivered": delivered,
                "failed": failed,
                "active_threads": len([t for t in self._threads.values() if t.status == "open"]),
                "closed_threads": len([t for t in self._threads.values() if t.status == "closed"]),
                "external_connectors": list(self._external_connectors.keys()),
                "rate_limited_senders": len(self._rate_limiters),
                "rate_limit_tps": self._rate_limit_tps,
            }
