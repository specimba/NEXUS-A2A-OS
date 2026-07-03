"""Governed memory retrieval for NEXUS agents.

This module connects the canonical TrustKernel resource budget to the live
memory stack:

- SuperLocalMemory is the hot, cheap, local context cache.
- MemoryChannelManager is the canonical 8-channel governance memory surface.
- Mem0Adapter/S-P-E-W is an optional semantic recall path.

The broker is intentionally read-only. It does not promote, mutate, or persist
memories; it only builds a bounded context pack according to TrustKernel's
nonlinear budget class and memory depth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Sequence

from nexus_os.governor.trust_engine_v2 import CDRStage
from nexus_os.governor.trust_kernel import (
    ResourceBudgetClass,
    TrustKernel,
    TrustResourceBudget,
    get_trust_kernel,
)
from nexus_os.vault.memory import MemoryEntry, SuperLocalMemory, get_memory
from nexus_os.vault.memory_channels import MemoryChannelManager, get_manager


class SemanticMemory(Protocol):
    """Minimal semantic memory API used by the broker."""

    def search(
        self,
        query: str,
        agent_id: Optional[str] = None,
        limit: int = 5,
        layer: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ...


class MemoryPath(Enum):
    HOT_SUPERLOCAL = "hot_superlocal"
    CANONICAL_5TRACK = "canonical_5track"
    SEMANTIC_MEM0 = "semantic_mem0"
    CLOUD_COLD = "cloud_cold"


@dataclass(frozen=True)
class GovernedMemoryBrokerConfig:
    """Operator-facing defaults for governed context assembly."""

    default_context_tokens: int = 2000
    semantic_min_depth: int = 4
    max_hot_entries: int = 12
    max_track_records: int = 8
    max_semantic_results: int = 8
    allow_cloud_cold_path: bool = False


@dataclass(frozen=True)
class GovernedMemoryPlan:
    """Explains which memory paths were used or denied."""

    agent_id: str
    lane: str
    action: str
    query: str
    budget_class: str
    memory_query_depth: int
    token_budget: int
    hot_limit: int
    track_limit: int
    semantic_limit: int
    enabled_paths: Sequence[str]
    denied_paths: Sequence[str]
    trust_budget: Dict[str, Any]
    provenance: str = "nexus_os.vault.governed_memory_broker"


@dataclass(frozen=True)
class GovernedMemoryContext:
    """Bounded context returned to routers, tools, and agents."""

    plan: GovernedMemoryPlan
    hot_entries: List[Dict[str, Any]] = field(default_factory=list)
    track_records: Dict[str, Any] = field(default_factory=dict)
    semantic_entries: List[Dict[str, Any]] = field(default_factory=list)
    context_text: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan": asdict(self.plan),
            "hot_entries": self.hot_entries,
            "track_records": self.track_records,
            "semantic_entries": self.semantic_entries,
            "context_text": self.context_text,
            "metrics": self.metrics,
        }


class GovernedMemoryBroker:
    """Build trust-bounded memory context without triggering model polling.

    The broker deliberately does not instantiate Mem0Adapter by default because
    that adapter may attempt cloud initialization when API keys exist. Callers
    must inject a semantic memory implementation when the cold semantic path is
    explicitly approved.
    """

    def __init__(
        self,
        *,
        trust_kernel: Optional[TrustKernel] = None,
        hot_memory: Optional[SuperLocalMemory] = None,
        channel_memory: Optional[MemoryChannelManager] = None,
        semantic_memory: Optional[SemanticMemory] = None,
        config: Optional[GovernedMemoryBrokerConfig] = None,
    ) -> None:
        self.trust_kernel = trust_kernel or get_trust_kernel()
        self.hot_memory = hot_memory or get_memory()
        self.channel_memory = channel_memory or get_manager()
        self.semantic_memory = semantic_memory
        self.config = config or GovernedMemoryBrokerConfig()

    def build_context(
        self,
        *,
        agent_id: str,
        lane: str,
        query: str,
        action: str = "read",
        requested_tokens: Optional[int] = None,
        include_semantic: bool = True,
    ) -> GovernedMemoryContext:
        """Return a context pack constrained by the agent's trust budget."""

        budget = self.trust_kernel.derive_resource_budget(
            agent_id=agent_id,
            lane=lane,
            action=action,
            context={"required_tokens": requested_tokens} if requested_tokens else None,
        )
        token_budget = self._derive_context_token_budget(budget, requested_tokens)
        depth = max(0, int(budget.memory_query_depth))
        denied: List[str] = []
        enabled: List[str] = []

        if budget.budget_class == ResourceBudgetClass.LOCKED or depth <= 0 or token_budget <= 0:
            denied.extend(
                [
                    f"{MemoryPath.HOT_SUPERLOCAL.value}:trust_budget_locked",
                    f"{MemoryPath.CANONICAL_5TRACK.value}:trust_budget_locked",
                    f"{MemoryPath.SEMANTIC_MEM0.value}:trust_budget_locked",
                    f"{MemoryPath.CLOUD_COLD.value}:disabled_by_default",
                ]
            )
            return self._empty_context(agent_id, lane, action, query, budget, token_budget, denied)

        hot_limit = min(self.config.max_hot_entries, max(1, depth * 2))
        track_limit = min(self.config.max_track_records, max(1, depth))
        semantic_limit = self._semantic_limit(budget, include_semantic, denied)

        hot_entries = self._read_hot(query=query, limit=hot_limit)
        if hot_entries:
            enabled.append(MemoryPath.HOT_SUPERLOCAL.value)

        track_records = self._read_tracks(agent_id=agent_id, lane=lane, limit=track_limit)
        if track_records:
            enabled.append(MemoryPath.CANONICAL_5TRACK.value)

        semantic_entries: List[Dict[str, Any]] = []
        if semantic_limit > 0:
            semantic_entries = self._read_semantic(
                query=query,
                agent_id=agent_id,
                limit=semantic_limit,
                denied=denied,
            )
            if semantic_entries:
                enabled.append(MemoryPath.SEMANTIC_MEM0.value)

        if self.config.allow_cloud_cold_path and budget.allow_cloud_fallback:
            denied.append(f"{MemoryPath.CLOUD_COLD.value}:not_implemented_without_kaiju_vap")
        else:
            denied.append(f"{MemoryPath.CLOUD_COLD.value}:disabled_by_default")

        plan = GovernedMemoryPlan(
            agent_id=agent_id,
            lane=lane,
            action=action,
            query=query,
            budget_class=budget.budget_class.value,
            memory_query_depth=depth,
            token_budget=token_budget,
            hot_limit=hot_limit,
            track_limit=track_limit,
            semantic_limit=semantic_limit,
            enabled_paths=tuple(enabled),
            denied_paths=tuple(denied),
            trust_budget=budget.to_dict(),
        )
        context_text = self._render_context(
            plan=plan,
            hot_entries=hot_entries,
            track_records=track_records,
            semantic_entries=semantic_entries,
        )
        context_text = self._clip_chars(context_text, token_budget * 4)

        return GovernedMemoryContext(
            plan=plan,
            hot_entries=hot_entries,
            track_records=track_records,
            semantic_entries=semantic_entries,
            context_text=context_text,
            metrics={
                "hot_count": len(hot_entries),
                "track_sections": len(track_records),
                "semantic_count": len(semantic_entries),
                "enabled_path_count": len(enabled),
                "denied_path_count": len(denied),
                "char_budget": token_budget * 4,
            },
        )

    def _derive_context_token_budget(
        self,
        budget: TrustResourceBudget,
        requested_tokens: Optional[int],
    ) -> int:
        requested = requested_tokens or self.config.default_context_tokens
        if budget.max_tokens <= 0:
            return 0
        return max(0, min(int(requested), int(budget.max_tokens)))

    def _semantic_limit(
        self,
        budget: TrustResourceBudget,
        include_semantic: bool,
        denied: List[str],
    ) -> int:
        if not include_semantic:
            denied.append(f"{MemoryPath.SEMANTIC_MEM0.value}:disabled_by_request")
            return 0
        if self.semantic_memory is None:
            denied.append(f"{MemoryPath.SEMANTIC_MEM0.value}:not_configured")
            return 0
        if budget.budget_class in {
            ResourceBudgetClass.REVIEW_ONLY,
            ResourceBudgetClass.QUARANTINED,
            ResourceBudgetClass.LOCKED,
        }:
            denied.append(f"{MemoryPath.SEMANTIC_MEM0.value}:budget_class_{budget.budget_class.value}")
            return 0
        if budget.memory_query_depth < self.config.semantic_min_depth:
            denied.append(f"{MemoryPath.SEMANTIC_MEM0.value}:trust_depth_below_semantic_floor")
            return 0
        return min(self.config.max_semantic_results, int(budget.memory_query_depth))

    def _read_hot(self, *, query: str, limit: int) -> List[Dict[str, Any]]:
        entries = self.hot_memory.query(pattern=query, limit=limit)
        return [self._entry_to_dict(entry) for entry in entries]

    def _read_tracks(self, *, agent_id: str, lane: str, limit: int) -> Dict[str, Any]:
        summary = self.channel_memory.get_buffer_summary(agent_id)
        from nexus_os.vault.memory_channels import MemoryChannel
        events = self.channel_memory.get_records(agent_id, MemoryChannel.EPISODIC, limit=limit)
        trust_history = self.channel_memory.get_trust_history(agent_id, lane=lane)[-limit:]
        capability = self.channel_memory.get_capability(agent_id)
        failures = self.channel_memory.get_failures(agent_id)
        critical_failures = self.channel_memory.get_critical_failures(agent_id)

        return {
            "summary": summary,
            "latest_trust": self.channel_memory.get_latest_trust(agent_id, lane=lane),
            "events": [self._jsonable(record) for record in events],
            "trust_history": [self._jsonable(record) for record in trust_history],
            "capability": self._jsonable(capability),
            "failures": {key: self._jsonable(value) for key, value in failures.items()},
            "critical_failures": [self._jsonable(item) for item in critical_failures],
        }

    def _read_semantic(
        self,
        *,
        query: str,
        agent_id: str,
        limit: int,
        denied: List[str],
    ) -> List[Dict[str, Any]]:
        try:
            return self.semantic_memory.search(query=query, agent_id=agent_id, limit=limit)
        except Exception as exc:  # pragma: no cover - defensive guard
            denied.append(f"{MemoryPath.SEMANTIC_MEM0.value}:search_error:{type(exc).__name__}")
            return []

    def _render_context(
        self,
        *,
        plan: GovernedMemoryPlan,
        hot_entries: List[Dict[str, Any]],
        track_records: Dict[str, Any],
        semantic_entries: List[Dict[str, Any]],
    ) -> str:
        lines = [
            "## Governed Memory Context",
            (
                f"Budget: {plan.budget_class}; depth={plan.memory_query_depth}; "
                f"tokens={plan.token_budget}; cloud_cold=disabled"
            ),
        ]

        if hot_entries:
            lines.append("### Hot SuperLocal")
            for entry in hot_entries:
                lines.append(
                    f"- [{entry.get('channel')}] {entry.get('key')}: "
                    f"{self._summarize(entry.get('value'))}"
                )

        if track_records:
            lines.append("### Canonical 8-Channel")
            summary = track_records.get("summary", {})
            lines.append(f"- summary: {summary}")
            if track_records.get("latest_trust") is not None:
                lines.append(f"- latest_trust: {track_records['latest_trust']}")
            for record in track_records.get("events", []):
                lines.append(f"- event: {self._summarize(record.get('content'))}")
            for record in track_records.get("trust_history", []):
                lines.append(
                    f"- trust[{record.get('lane')}]: "
                    f"{record.get('trust_score')} n={record.get('evidence_count')}"
                )
            if track_records.get("capability"):
                lines.append(f"- capability: {self._summarize(track_records['capability'])}")
            if track_records.get("critical_failures"):
                lines.append(f"- critical_failures: {self._summarize(track_records['critical_failures'])}")

        if semantic_entries:
            lines.append("### Semantic S-P-E-W / Mem0")
            for item in semantic_entries:
                layer = item.get("layer", "unknown")
                score = item.get("score", "")
                content = item.get("content") or item.get("memory") or ""
                lines.append(f"- [{layer} score={score}] {self._summarize(content)}")

        if plan.denied_paths:
            lines.append("### Denied Paths")
            for denied in plan.denied_paths:
                lines.append(f"- {denied}")

        return "\n".join(lines)

    def _empty_context(
        self,
        agent_id: str,
        lane: str,
        action: str,
        query: str,
        budget: TrustResourceBudget,
        token_budget: int,
        denied: List[str],
    ) -> GovernedMemoryContext:
        plan = GovernedMemoryPlan(
            agent_id=agent_id,
            lane=lane,
            action=action,
            query=query,
            budget_class=budget.budget_class.value,
            memory_query_depth=max(0, int(budget.memory_query_depth)),
            token_budget=token_budget,
            hot_limit=0,
            track_limit=0,
            semantic_limit=0,
            enabled_paths=(),
            denied_paths=tuple(denied),
            trust_budget=budget.to_dict(),
        )
        return GovernedMemoryContext(
            plan=plan,
            context_text="",
            metrics={
                "hot_count": 0,
                "track_sections": 0,
                "semantic_count": 0,
                "enabled_path_count": 0,
                "denied_path_count": len(denied),
                "char_budget": 0,
            },
        )

    @staticmethod
    def _entry_to_dict(entry: MemoryEntry) -> Dict[str, Any]:
        return {
            "channel": entry.channel.value,
            "key": entry.key,
            "value": GovernedMemoryBroker._jsonable(entry.value),
            "timestamp": entry.timestamp,
            "metadata": GovernedMemoryBroker._jsonable(entry.metadata),
        }

    @staticmethod
    def _jsonable(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, Enum):
            return value.value
        if is_dataclass(value):
            return {
                key: GovernedMemoryBroker._jsonable(item)
                for key, item in asdict(value).items()
            }
        if isinstance(value, dict):
            return {
                str(key): GovernedMemoryBroker._jsonable(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple, set)):
            return [GovernedMemoryBroker._jsonable(item) for item in value]
        return value

    @staticmethod
    def _summarize(value: Any, limit: int = 220) -> str:
        text = str(value)
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 3)] + "..."

    @staticmethod
    def _clip_chars(text: str, char_budget: int) -> str:
        if char_budget <= 0:
            return ""
        if len(text) <= char_budget:
            return text
        suffix = "\n[context clipped by TrustKernel memory budget]"
        return text[: max(0, char_budget - len(suffix))] + suffix
