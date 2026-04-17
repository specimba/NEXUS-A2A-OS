"""tool_discipline.py — Metis v2 Tool Discipline

Tool usage tracking and discipline enforcement.
Tracks tool usage patterns, enforces limits, and provides recommendations.
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """Tool execution status."""
    SUCCESS = "success"
    FAILURE = "failure"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"


@dataclass
class ToolUsage:
    """Record of tool usage."""
    tool_name: str
    status: ToolStatus
    duration_ms: int
    timestamp: float
    error: Optional[str] = None


class ToolDiscipline:
    """
    Metis v2 Tool Discipline system.
    
    Features:
    - Track tool usage patterns
    - Rate limiting per tool
    - Timeout detection
    - Recommendations for tool selection
    """
    
    def __init__(
        self,
        max_calls_per_minute: int = 60,
        max_duration_ms: int = 30000,
    ):
        self.max_calls_per_minute = max_calls_per_minute
        self.max_duration_ms = max_duration_ms
        
        self._usage: Dict[str, List[ToolUsage]] = defaultdict(list)
        self._lock = threading.RLock()
        
        # Tool-specific limits (tool_name -> (max_per_minute, max_duration_ms))
        self._limits: Dict[str, tuple] = {}
    
    def record_call(
        self,
        tool_name: str,
        status: ToolStatus,
        duration_ms: int,
        error: Optional[str] = None,
    ) -> None:
        """Record a tool call."""
        with self._lock:
            usage = ToolUsage(
                tool_name=tool_name,
                status=status,
                duration_ms=duration_ms,
                timestamp=time.time(),
                error=error,
            )
            self._usage[tool_name].append(usage)
            
            # Clean old entries (older than 1 minute)
            self._cleanup(tool_name)
    
    def _cleanup(self, tool_name: str) -> None:
        """Remove entries older than 1 minute."""
        cutoff = time.time() - 60
        self._usage[tool_name] = [
            u for u in self._usage[tool_name]
            if u.timestamp > cutoff
        ]
    
    def can_execute(self, tool_name: str) -> bool:
        """Check if tool can be executed."""
        with self._lock:
            self._cleanup(tool_name)
            
            # Check rate limit
            max_calls = self._limits.get(tool_name, (self.max_calls_per_minute, 0))[0]
            if len(self._usage[tool_name]) >= max_calls:
                return False
            
            return True
    
    def get_stats(self, tool_name: str) -> Dict:
        """Get tool usage statistics."""
        with self._lock:
            self._cleanup(tool_name)
            
            usage_list = self._usage.get(tool_name, [])
            if not usage_list:
                return {
                    "tool_name": tool_name,
                    "total_calls": 0,
                    "success_rate": 0.0,
                    "avg_duration_ms": 0,
                    "rate_limited_count": 0,
                }
            
            successes = sum(1 for u in usage_list if u.status == ToolStatus.SUCCESS)
            failures = sum(1 for u in usage_list if u.status == ToolStatus.FAILURE)
            rate_limited = sum(1 for u in usage_list if u.status == ToolStatus.RATE_LIMITED)
            
            durations = [u.duration_ms for u in usage_list]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                "tool_name": tool_name,
                "total_calls": len(usage_list),
                "success_rate": successes / len(usage_list),
                "avg_duration_ms": avg_duration,
                "failure_count": failures,
                "rate_limited_count": rate_limited,
            }
    
    def set_limits(
        self,
        tool_name: str,
        max_per_minute: int,
        max_duration_ms: Optional[int] = None,
    ) -> None:
        """Set limits for a specific tool."""
        self._limits[tool_name] = (
            max_per_minute,
            max_duration_ms or self.max_duration_ms,
        )
    
    def get_recommendations(self) -> List[Dict]:
        """Get tool usage recommendations."""
        recommendations = []
        
        with self._lock:
            for tool_name, usage_list in self._usage.items():
                stats = self.get_stats(tool_name)
                
                if stats["success_rate"] < 0.5:
                    recommendations.append({
                        "tool": tool_name,
                        "issue": "low_success_rate",
                        "recommendation": "Consider alternative tool",
                    })
                
                if stats["avg_duration_ms"] > self.max_duration_ms * 0.8:
                    recommendations.append({
                        "tool": tool_name,
                        "issue": "slow_execution",
                        "recommendation": "Consider caching or async",
                    })
        
        return recommendations


# ── Singleton ────────────────────────────────────────────────────────────

_discipline_instance: Optional[ToolDiscipline] = None
_discipline_lock = threading.Lock()


def get_tool_discipline() -> ToolDiscipline:
    """Get or create ToolDiscipline singleton."""
    global _discipline_instance
    if _discipline_instance is None:
        with _discipline_lock:
            if _discipline_instance is None:
                _discipline_instance = ToolDiscipline()
    return _discipline_instance


def record_tool_call(
    tool_name: str,
    status: ToolStatus,
    duration_ms: int,
    error: Optional[str] = None,
) -> None:
    """Convenience function for recording tool calls."""
    get_tool_discipline().record_call(tool_name, status, duration_ms, error)