"""memory.py — SuperLocalMemory v2

8-channel local memory for agent context.
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


class MemoryChannel(Enum):
    """8 memory channels."""
    EVENT = "event"          # 0: Events
    TRUST = "trust"         # 1: Trust scores  
    CAPABILITY = "capability" # 2: Capabilities
    FAILURE_PATTERN = "failure"  # 3: Failure patterns
    GOVERNANCE = "governance"   # 4: Governance
    TASK = "task"          # 5: Task history
    CONTEXT = "context"    # 6: Context window
    CUSTOM = "custom"      # 7: Custom/pinned


@dataclass
class MemoryEntry:
    """Memory entry."""
    channel: MemoryChannel
    key: str
    value: Any
    timestamp: float
    metadata: Dict = field(default_factory=dict)


class SuperLocalMemory:
    """
    8-channel local memory system.
    
    Channels:
    0. EVENT  - Event log
    1. TRUST  - Trust scores by lane
    2. CAPABILITY - Ability/capability records
    3. FAILURE_PATTERN - Known failure patterns
    4. GOVERNANCE - Governance flags/rules
    5. TASK - Task execution history
    6. CONTEXT - Rolling context window
    7. CUSTOM - Custom/pinned entries
    """
    
    def __init__(
        self,
        max_per_channel: int = 100,
    ):
        self.max_per_channel = max_per_channel
        
        # Each channel is a deque
        self._memory: Dict[MemoryChannel, deque] = {
            channel: deque(maxlen=max_per_channel)
            for channel in MemoryChannel
        }
        
        self._lock = threading.RLock()
        
        # Index for fast lookup
        self._index: Dict[str, List] = {}  # key -> [(channel, timestamp), ...]
    
    def store(
        self,
        channel: MemoryChannel,
        key: str,
        value: Any,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Store entry in channel."""
        entry = MemoryEntry(
            channel=channel,
            key=key,
            value=value,
            timestamp=time.time(),
            metadata=metadata or {},
        )
        
        with self._lock:
            self._memory[channel].append(entry)
            
            # Update index
            if key not in self._index:
                self._index[key] = []
            self._index[key].append((channel, entry.timestamp))
    
    def retrieve(
        self,
        channel: MemoryChannel,
        key: str,
    ) -> List[Any]:
        """Retrieve values by key from channel."""
        with self._lock:
            return [
                entry.value
                for entry in self._memory[channel]
                if entry.key == key
            ]
    
    def query(
        self,
        channel: Optional[MemoryChannel] = None,
        pattern: Optional[str] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """Query memory with optional filters."""
        with self._lock:
            entries = []
            
            channels = [channel] if channel else list(MemoryChannel)
            
            for ch in channels:
                for entry in self._memory[ch]:
                    if pattern and pattern.lower() not in entry.key.lower():
                        continue
                    entries.append(entry)
                    
                    if len(entries) >= limit:
                        break
            
            # Sort by timestamp descending
            entries.sort(key=lambda e: e.timestamp, reverse=True)
            return entries[:limit]
    
    def get_channel(self, channel: MemoryChannel) -> List[MemoryEntry]:
        """Get all entries in a channel."""
        with self._lock:
            return list(self._memory[channel])
    
    def get_latest(
        self,
        channel: MemoryChannel,
        count: int = 5,
    ) -> List[Any]:
        """Get latest N values from channel."""
        with self._lock:
            entries = list(self._memory[channel])[-count:]
            return [e.value for e in reversed(entries)]
    
    def clear_channel(self, channel: MemoryChannel) -> int:
        """Clear a channel."""
        with self._lock:
            count = len(self._memory[channel])
            self._memory[channel].clear()
            return count
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        with self._lock:
            return {
                channel.value: len(self._memory[channel])
                for channel in MemoryChannel
            }


# ── Singleton ────────────────────────────────────────────────────────────

_memory_instance: Optional[SuperLocalMemory] = None
_memory_lock = threading.Lock()


def get_memory() -> SuperLocalMemory:
    """Get or create SuperLocalMemory singleton."""
    global _memory_instance
    if _memory_instance is None:
        with _memory_lock:
            if _memory_instance is None:
                _memory_instance = SuperLocalMemory()
    return _memory_instance


def memory_store(
    channel: MemoryChannel,
    key: str,
    value: Any,
    metadata: Optional[Dict] = None,
) -> None:
    """Convenience function for storing."""
    get_memory().store(channel, key, value, metadata)


def memory_retrieve(
    channel: MemoryChannel,
    key: str,
) -> List[Any]:
    """Convenience function for retrieving."""
    return get_memory().retrieve(channel, key)