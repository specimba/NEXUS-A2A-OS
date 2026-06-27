"""MCP Gateway Pipeline — governed egress for MCP/Browser tool calls.

Wires together:
  - BrowserHTTPDiagnosticRelay.execute_governed() approval chain
  - MetaAttackDetector MCP attack pattern detection
  - ProviderCircuitBreaker health gates
  - Memory sink for Vault audit

Usage:
    gateway = MCPGateway()
    result = gateway.process("https://api.example.com/data")
    # {"allowed": True/False, "reason": "...", "detections": [...]}

The gateway injects itself as the approval_checker for execute_governed():
    relay.execute_governed(url, approval_checker=gateway.check, ...)
"""
from __future__ import annotations

import json
import logging
import os
import time
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SchemaDriftDecision:
    """L1 registry/schema drift decision for governed MCP surfaces."""

    allowed: bool
    reason: str
    registry_schema_hash: str
    duplicate_tools: tuple[str, ...] = ()
    added_tools: tuple[str, ...] = ()
    removed_tools: tuple[str, ...] = ()
    changed_tools: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "registry_schema_hash": self.registry_schema_hash,
            "duplicate_tools": list(self.duplicate_tools),
            "added_tools": list(self.added_tools),
            "removed_tools": list(self.removed_tools),
            "changed_tools": list(self.changed_tools),
        }


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _short_sha256(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()[:16]


def normalize_tool_schema(tool: Mapping[str, Any]) -> dict[str, Any]:
    """Return the canonical schema fields used for registry drift checks."""

    return {
        "name": str(tool.get("name", "")).strip(),
        "description": str(tool.get("description", "")).strip(),
        "input_schema": tool.get("input_schema") or tool.get("parameters") or {},
    }


def tool_schema_hashes(tools: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    """Compute deterministic per-tool schema hashes."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    for raw_tool in tools:
        tool = normalize_tool_schema(raw_tool)
        name = tool["name"]
        if not name:
            continue
        grouped.setdefault(name, []).append(tool)
    hashes: dict[str, str] = {}
    for name, entries in sorted(grouped.items()):
        payload: Any = entries[0] if len(entries) == 1 else sorted(entries, key=_stable_json)
        hashes[name] = _short_sha256(payload)
    return hashes


def registry_schema_hash(tools: Sequence[Mapping[str, Any]]) -> str:
    return _short_sha256(tool_schema_hashes(tools))


def detect_duplicate_tools(tools: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for raw_tool in tools:
        name = str(raw_tool.get("name", "")).strip()
        if not name:
            continue
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    return tuple(sorted(duplicates))


def validate_registry_snapshot(
    current_tools: Sequence[Mapping[str, Any]],
    *,
    pinned_schema_hashes: Mapping[str, str] | None = None,
) -> SchemaDriftDecision:
    """Validate current MCP tool schemas against an optional pinned baseline."""

    current_hashes = tool_schema_hashes(current_tools)
    current_registry_hash = _short_sha256(current_hashes)
    duplicates = detect_duplicate_tools(current_tools)
    if duplicates:
        return SchemaDriftDecision(
            allowed=False,
            reason="duplicate_tool_names",
            registry_schema_hash=current_registry_hash,
            duplicate_tools=duplicates,
        )

    if not pinned_schema_hashes:
        return SchemaDriftDecision(
            allowed=True,
            reason="no_pinned_schema_baseline",
            registry_schema_hash=current_registry_hash,
        )

    current_names = set(current_hashes)
    pinned_names = set(pinned_schema_hashes)
    added = tuple(sorted(current_names - pinned_names))
    removed = tuple(sorted(pinned_names - current_names))
    changed = tuple(
        sorted(
            name
            for name in current_names & pinned_names
            if current_hashes[name] != pinned_schema_hashes[name]
        )
    )
    allowed = not (added or removed or changed)
    return SchemaDriftDecision(
        allowed=allowed,
        reason="ok" if allowed else "schema_drift",
        registry_schema_hash=current_registry_hash,
        added_tools=added,
        removed_tools=removed,
        changed_tools=changed,
    )


def taint_tool_output(
    payload: Mapping[str, Any],
    *,
    tool_name: str,
    source_mcp_server: str,
    risk: str = "untrusted_tool_output",
) -> dict[str, Any]:
    """Attach L3 provenance/taint metadata to externally sourced tool output."""

    return {
        "source_mcp_server": source_mcp_server,
        "tool_name": tool_name,
        "risk": risk,
        "tainted": True,
        "payload_sha256": hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest(),
    }


class MCPGateway:
    """Pipeline that validates MCP egress through MetaAttackDetector + circuit breaker."""

    def __init__(
        self,
        *,
        detector: Any | None = None,
        breaker: Any | None = None,
        audit_log_path: str | Path | None = None,
        default_action: str = "block",
    ):
        self._detector = detector
        self._breaker = breaker
        self._audit_log_path = Path(audit_log_path) if audit_log_path else None
        self.default_action = default_action
        self._stats: dict[str, Any] = {
            "total_requests": 0,
            "allowed": 0,
            "blocked": 0,
            "flagged": 0,
            "by_source": {},
        }

    @property
    def detector(self) -> Any:
        if self._detector is None:
            from nexus_os.security.meta_attack_detector import MetaAttackDetector
            self._detector = MetaAttackDetector()
        return self._detector

    @property
    def breaker(self) -> Any:
        if self._breaker is None:
            from nexus_os.relay.circuit_breaker import ProviderCircuitBreaker
            self._breaker = ProviderCircuitBreaker(failure_threshold=3, cooldown_seconds=60, max_cooldown=3600, persist=True)
        return self._breaker

    def _audit(self, entry: dict[str, Any]):
        if self._audit_log_path:
            try:
                self._audit_log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self._audit_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception as exc:
                logger.warning("audit log write failed: %s", exc)

    def check(self, gate_payload: dict[str, Any]) -> bool:
        """Approval checker callback for BrowserHTTPDiagnosticRelay.execute_governed().
        Returns True to allow, False to block.
        """
        url = gate_payload.get("url", "")
        result = self._scan(url, source="execute_governed", context=gate_payload)
        return result.get("allowed", False)

    def _scan(
        self,
        url: str,
        source: str = "direct",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Core scan: run URL through detector + circuit breaker, return decision."""
        self._stats["total_requests"] += 1
        self._stats.setdefault("by_source", {}).setdefault(source, 0)
        self._stats["by_source"][source] += 1

        now = datetime.now(timezone.utc).isoformat()

        scan_result = self.detector.scan(url)
        provider_id = self._extract_provider(url)

        is_attack = not scan_result.get("safe", True) if hasattr(scan_result, "get") else False
        provider_dead = not self.breaker.can_execute(provider_id) if provider_id else False

        allowed = True
        reasons = []

        if is_attack:
            reasons.append(f"meta_attack_detected: {scan_result.get('reason', 'unknown')}")
            allowed = False
            self._stats["blocked"] += 1

        if provider_dead:
            reasons.append(f"provider_circuit_open: {provider_id}")
            if self.default_action == "block":
                allowed = False
                self._stats["blocked"] += 1

        if allowed:
            self._stats["allowed"] += 1

        result = {
            "allowed": allowed,
            "reason": "; ".join(reasons) if reasons else "ok",
            "detections": [scan_result] if is_attack else [],
            "provider_id": provider_id,
            "provider_dead": provider_dead,
            "source": source,
            "url": url,
            "timestamp": now,
        }

        if is_attack:
            self.breaker.record_failure(provider_id or "mcp_gateway")
            if provider_id:
                try:
                    from nexus_os.bridge.dynamic_ip_rotator import DynamicIPRotator
                    rotator = DynamicIPRotator()
                    rotation_result = rotator.try_rotate_on_block(provider_id)
                    if rotation_result.get("rotated"):
                        logger.info("IP rotated for provider %s: %s", provider_id, rotation_result.get("new_ip"))
                    else:
                        logger.debug("IP rotation skipped for %s: %s", provider_id, rotation_result.get("reason"))
                except Exception as exc:
                    logger.warning("DynamicIPRotator failed for %s: %s", provider_id, exc)
        elif not is_attack and provider_id:
            self.breaker.record_success(provider_id)

        self._audit(result)
        return result

    @staticmethod
    def _extract_provider(url: str) -> str | None:
        """Extract provider name from URL for circuit breaker lookup."""
        known = {
            "inference.baseten.co": "openai-compatible:baseten",
            "api.openai.com": "openai",
            "api.anthropic.com": "anthropic",
            "api.groq.com": "groq",
            "api.nvcf.nvidia.com": "nvidia",
            "api.fireworks.ai": "openai-compatible:fireworks",
            "api.deepinfra.com": "openai-compatible:deepinfra",
            "api.mistral.ai": "openai-compatible:mistral",
            "api.sambanova.ai": "openai-compatible:sambanova",
            "api.siliconflow.cn": "openai-compatible:siliconflow",
            "api.longcat.chat": "longcat",
            "api.internai.com": "internai",
            "api.novita.ai": "novita",
            "api.cohere.ai": "cohere",
            "api.scaleway.ai": "scaleway",
            "generativelanguage.googleapis.com": "googleai",
            "models.inference.ai.azure.com": "openai-compatible:github",
            "api.cloudflare.com": "cloudflare",
        }
        for domain, provider_id in known.items():
            if domain in url:
                return provider_id
        return None

    def process(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        source: str = "direct",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process a URL through the full MCP Gateway pipeline.
        Returns a decision dict with evidence.
        """
        return self._scan(url, source=source, context=context)

    def get_stats(self) -> dict[str, Any]:
        return dict(self._stats)

    def get_circuit_breaker_status(self) -> dict[str, Any]:
        return {"dead_providers": self.breaker.get_dead_providers()}

    def as_approval_checker(self) -> Callable[[dict[str, Any]], bool]:
        """Return the approval_checker callable for execute_governed()."""
        return self.check

    def as_memory_sink(self) -> Callable[[dict[str, Any]], None]:
        """Return a memory_sink callable for execute_governed()."""
        def sink(payload: dict[str, Any]):
            self._audit({"memory_sink": True, **payload})
        return sink
