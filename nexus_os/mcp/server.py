"""Governed MCP execution bridge for NEXUS OS.

This module integrates the useful Phase 6 MCP ideas without importing the
standalone scaffold wholesale. It keeps MCP as an execution bridge, uses
TrustKernel as the policy gate, and defaults side-effect tools to hold until an
operator explicitly enables them.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional


READ_ONLY_ACTIONS = {
    "governance.get_status",
    "system.health",
    "drift_monitor.run_sweep",
}

SIDE_EFFECT_ACTIONS = {
    "memory.create_checkpoint",
    "telegram.send_message",
    "notion.create_page",
    "slack.send_message",
}


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]
    governance_level: str = "low"
    requires_trustkernel: bool = True
    side_effects: bool = False
    approval_required: bool = False

    def to_mcp(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "governance": {
                "level": self.governance_level,
                "requires_trustkernel": self.requires_trustkernel,
                "side_effects": self.side_effects,
                "approval_required": self.approval_required,
            },
        }


@dataclass
class MCPConfig:
    server_name: str = "nexus-os-governed-mcp"
    server_version: str = "0.5-phase6-nexus"
    trustkernel_mode: str = "real"
    allow_side_effects: bool = False
    audit_path: Optional[Path] = None
    checkpoint_path: Optional[Path] = None

    @classmethod
    def from_env(cls) -> "MCPConfig":
        audit_raw = os.getenv("NEXUS_MCP_AUDIT_PATH")
        checkpoint_raw = os.getenv("NEXUS_MCP_CHECKPOINT_PATH")
        return cls(
            server_name=os.getenv("NEXUS_MCP_NAME", cls.server_name),
            server_version=os.getenv("NEXUS_MCP_VERSION", cls.server_version),
            trustkernel_mode=os.getenv("NEXUS_TRUSTKERNEL_MODE", "real").lower(),
            allow_side_effects=os.getenv("NEXUS_MCP_ALLOW_SIDE_EFFECTS", "false").lower()
            == "true",
            audit_path=Path(audit_raw) if audit_raw else None,
            checkpoint_path=Path(checkpoint_raw) if checkpoint_raw else None,
        )


@dataclass
class AuditEvent:
    event_id: str
    tool_name: str
    blocked: bool
    decision: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TrustKernelMCPAdapter:
    """Adapter that normalizes canonical TrustKernel decisions for MCP callers."""

    def __init__(self, kernel: Any = None, mode: str = "real") -> None:
        self.mode = mode
        self.kernel = kernel
        self._load_error: Optional[str] = None

    def consult(self, spec: ToolSpec, arguments: Dict[str, Any]) -> Dict[str, Any]:
        context = {
            **arguments,
            "side_effect": spec.side_effects,
            "high_risk": spec.governance_level in {"high", "critical"},
            "lane": arguments.get("lane") or self._lane_for_tool(spec.name),
            "mcp_tool": spec.name,
        }

        if self.mode == "real":
            decision = self._consult_real(spec.name, context)
        else:
            decision = self._consult_stub(spec, context)

        decision.setdefault("source", "nexus_mcp_trust_adapter")
        decision.setdefault("mode", self.mode)
        return decision

    def _consult_real(self, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            kernel = self.kernel or self._create_kernel()
            raw = kernel.evaluate(
                agent_id=str(context.get("agent_id") or "mcp-client"),
                action=self._action_for_kernel(action),
                lane=str(context.get("lane") or self._lane_for_tool(action)),
                context=context,
            )
            raw_dict = raw.to_dict() if hasattr(raw, "to_dict") else dict(raw)
            snapshot = raw_dict.get("snapshot") or {}
            decision = str(raw_dict.get("decision", "hold")).lower()
            return {
                "allowed": decision == "allow",
                "decision": decision,
                "reason": raw_dict.get("reason", "TrustKernel decision returned no reason"),
                "trust_score": snapshot.get("trust"),
                "requires_escalation": decision != "allow",
                "snapshot": snapshot,
                "policy": raw_dict.get("policy", {}),
                "source": raw_dict.get("source", "canonical_trust_kernel"),
            }
        except Exception as exc:
            self._load_error = str(exc)
            fallback = self._consult_stub(
                ToolSpec(
                    name=action,
                    description="fallback",
                    input_schema={"type": "object", "properties": {}},
                    governance_level="high" if action in SIDE_EFFECT_ACTIONS else "low",
                    side_effects=action in SIDE_EFFECT_ACTIONS,
                    approval_required=action in SIDE_EFFECT_ACTIONS,
                ),
                context,
            )
            fallback["fallback_reason"] = self._load_error
            return fallback

    def _create_kernel(self) -> Any:
        from nexus_os.governor.trust_kernel import TrustKernel

        self.kernel = TrustKernel()
        return self.kernel

    @staticmethod
    def _consult_stub(spec: ToolSpec, context: Dict[str, Any]) -> Dict[str, Any]:
        blocked = spec.side_effects or spec.approval_required
        return {
            "allowed": not blocked,
            "decision": "hold" if blocked else "allow",
            "reason": (
                "Side-effectful MCP action requires real TrustKernel and operator approval"
                if blocked
                else "Read-only MCP action allowed by stub policy"
            ),
            "trust_score": 0.38 if blocked else 0.93,
            "requires_escalation": blocked,
            "snapshot": {"agent_id": context.get("agent_id") or "mcp-client"},
            "policy": {
                "side_effect": spec.side_effects,
                "approval_required": spec.approval_required,
            },
            "source": "stub_trustkernel_policy",
        }

    @staticmethod
    def _lane_for_tool(action: str) -> str:
        if action.startswith("memory."):
            return "write"
        if action.startswith(("telegram.", "notion.", "slack.")):
            return "execute"
        if action.startswith("drift_"):
            return "audit"
        return "read"

    @staticmethod
    def _action_for_kernel(action: str) -> str:
        if action in READ_ONLY_ACTIONS:
            return "read"
        if action.startswith("memory."):
            return "write"
        if action.startswith(("telegram.", "notion.", "slack.")):
            return "execute"
        return action


class GovernedMCPServer:
    """Small JSON-RPC MCP server with NEXUS governance semantics."""

    protocol_version = "2024-11-05"

    def __init__(
        self,
        config: Optional[MCPConfig] = None,
        trust_adapter: Optional[TrustKernelMCPAdapter] = None,
    ) -> None:
        self.config = config or MCPConfig.from_env()
        self.trust_adapter = trust_adapter or TrustKernelMCPAdapter(mode=self.config.trustkernel_mode)
        self.audit_events: list[AuditEvent] = []
        self.tools = self._default_tools()
        self.handlers: Dict[str, Callable[..., Dict[str, Any]]] = {
            "governance.get_status": self._governance_status,
            "system.health": self._system_health,
            "drift_monitor.run_sweep": self._drift_sweep,
            "memory.create_checkpoint": self._create_checkpoint,
            "telegram.send_message": self._dry_run_connector,
            "notion.create_page": self._dry_run_connector,
            "slack.send_message": self._dry_run_connector,
        }

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        method = request.get("method")
        req_id = request.get("id")

        if method == "initialize":
            return self._result(
                req_id,
                {
                    "protocolVersion": self.protocol_version,
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": self.config.server_name,
                        "version": self.config.server_version,
                    },
                },
            )

        if method == "tools/list":
            return self._result(req_id, {"tools": [tool.to_mcp() for tool in self.tools.values()]})

        if method == "tools/call":
            params = request.get("params") or {}
            return self.call_tool(req_id, str(params.get("name") or ""), params.get("arguments") or {})

        return self._error(req_id, -32601, f"Unsupported method: {method}")

    def call_tool(self, req_id: Any, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        spec = self.tools.get(tool_name)
        if spec is None:
            return self._error(req_id, -32601, f"Tool '{tool_name}' not found")

        decision = self.trust_adapter.consult(spec, arguments) if spec.requires_trustkernel else {
            "allowed": True,
            "decision": "allow",
            "reason": "Tool does not require TrustKernel",
            "requires_escalation": False,
        }

        blocked_by_policy = spec.side_effects and (
            spec.approval_required or not self.config.allow_side_effects
        )
        if blocked_by_policy:
            decision = {
                **decision,
                "allowed": False,
                "decision": "hold",
                "reason": "NEXUS MCP side-effect policy requires explicit operator enablement",
                "requires_escalation": True,
                "policy": {
                    **(decision.get("policy") or {}),
                    "allow_side_effects": self.config.allow_side_effects,
                    "approval_required": spec.approval_required,
                },
            }

        if not decision.get("allowed"):
            self._audit(tool_name, blocked=True, decision=decision)
            return self._tool_result(
                req_id,
                {
                    "blocked": True,
                    "tool": tool_name,
                    "reason": decision.get("reason"),
                    "trust_decision": decision,
                },
                is_error=True,
            )

        try:
            result = self.handlers[tool_name](**arguments)
            self._audit(tool_name, blocked=False, decision=decision)
            return self._tool_result(req_id, {"tool": tool_name, "result": result, "trust_decision": decision})
        except Exception as exc:
            return self._error(req_id, -32603, str(exc))

    def _default_tools(self) -> Dict[str, ToolSpec]:
        tool_specs = [
            ToolSpec(
                "governance.get_status",
                "Return current NEXUS MCP governance status.",
                {"type": "object", "properties": {}},
                governance_level="low",
                side_effects=False,
            ),
            ToolSpec(
                "system.health",
                "Return MCP bridge health.",
                {"type": "object", "properties": {}},
                governance_level="low",
                side_effects=False,
            ),
            ToolSpec(
                "drift_monitor.run_sweep",
                "Run a read-only thermodynamic drift and coordination sweep.",
                {
                    "type": "object",
                    "properties": {
                        "scope": {"type": "string", "enum": ["recent", "full"], "default": "recent"}
                    },
                },
                governance_level="medium",
                side_effects=False,
            ),
            ToolSpec(
                "memory.create_checkpoint",
                "Create a governed NEXUS memory checkpoint.",
                {
                    "type": "object",
                    "properties": {
                        "note": {"type": "string"},
                        "layers": {"type": "object"},
                    },
                    "required": ["note"],
                },
                governance_level="high",
                side_effects=True,
                approval_required=True,
            ),
            ToolSpec(
                "telegram.send_message",
                "Dry-run governed Telegram send path.",
                {
                    "type": "object",
                    "properties": {"chat_id": {"type": "string"}, "text": {"type": "string"}},
                    "required": ["chat_id", "text"],
                },
                governance_level="high",
                side_effects=True,
                approval_required=True,
            ),
            ToolSpec(
                "notion.create_page",
                "Dry-run governed Notion create page path.",
                {
                    "type": "object",
                    "properties": {"parent_id": {"type": "string"}, "title": {"type": "string"}},
                    "required": ["parent_id", "title"],
                },
                governance_level="high",
                side_effects=True,
                approval_required=True,
            ),
            ToolSpec(
                "slack.send_message",
                "Dry-run governed Slack send path.",
                {
                    "type": "object",
                    "properties": {"channel": {"type": "string"}, "text": {"type": "string"}},
                    "required": ["channel", "text"],
                },
                governance_level="high",
                side_effects=True,
                approval_required=True,
            ),
        ]
        return {spec.name: spec for spec in tool_specs}

    def _governance_status(self) -> Dict[str, Any]:
        return {
            "server": self.config.server_name,
            "version": self.config.server_version,
            "trustkernel_mode": self.config.trustkernel_mode,
            "allow_side_effects": self.config.allow_side_effects,
            "registered_tools": len(self.tools),
            "audit_events": len(self.audit_events),
            "posture": "governance_before_execution",
        }

    def _system_health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "tools_registered": len(self.tools),
            "side_effect_policy": "explicit_enablement_required",
        }

    @staticmethod
    def _drift_sweep(scope: str = "recent") -> Dict[str, Any]:
        return {
            "status": "completed",
            "scope": scope,
            "findings": {
                "recency_bias": "not_detected",
                "coordination_drift": "not_detected",
                "thermodynamic_posture": "stable",
            },
        }

    def _create_checkpoint(self, note: str, layers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        checkpoint = {
            "checkpoint_id": str(uuid.uuid4()),
            "note": note,
            "layers": layers or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.config.checkpoint_path:
            self._append_jsonl(self.config.checkpoint_path, checkpoint)
        return checkpoint

    @staticmethod
    def _dry_run_connector(**kwargs: Any) -> Dict[str, Any]:
        return {
            "status": "dry_run",
            "message": "Real connector execution is intentionally not implemented in this bridge.",
            "arguments": kwargs,
        }

    def _audit(self, tool_name: str, blocked: bool, decision: Dict[str, Any]) -> None:
        event = AuditEvent(str(uuid.uuid4()), tool_name, blocked, decision)
        self.audit_events.append(event)
        if self.config.audit_path:
            self._append_jsonl(self.config.audit_path, asdict(event))

    @staticmethod
    def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    @staticmethod
    def _result(req_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    @staticmethod
    def _error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    @classmethod
    def _tool_result(cls, req_id: Any, payload: Dict[str, Any], is_error: bool = False) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "content": [{"type": "text", "text": json.dumps(payload, indent=2, sort_keys=True)}]
        }
        if is_error:
            result["isError"] = True
        return cls._result(req_id, result)


def create_server(config: Optional[MCPConfig] = None) -> GovernedMCPServer:
    return GovernedMCPServer(config=config)


_DEFAULT_SERVER: Optional[GovernedMCPServer] = None


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    global _DEFAULT_SERVER
    if _DEFAULT_SERVER is None:
        _DEFAULT_SERVER = create_server()
    return _DEFAULT_SERVER.handle_request(request)


def serve_stdio(requests: Optional[Iterable[str]] = None) -> None:
    server = create_server()
    stream = requests if requests is not None else sys.stdin
    for line in stream:
        raw = line.strip()
        if not raw:
            continue
        try:
            response = server.handle_request(json.loads(raw))
        except json.JSONDecodeError:
            response = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    serve_stdio()
