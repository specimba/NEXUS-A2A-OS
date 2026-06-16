"""Top-level NEXUS OS — Sovereign Agent Operating System.

Submodules:
    engine      — Task lifecycle, routing, execution, skill management
    governor    — Governance: KAIJU auth, compliance, trust kernel, proof chain
    vault       — Persistent memory with 5-track schema and MINJA poisoning detection
    bridge      — A2A JSON-RPC 2.0 bridge server with HMAC auth
    swarm       — OpenClaw spawner, foreman, worker, auction
    team        — Team coordinator: Hermes routing + mem0 + skill dispatch
    mcp         — Governed MCP execution bridge with TrustKernel
    monitoring  — Token guard, counters, semantic cache, drift monitor
    security    — Meta-attack detection, shortcut neuron, contamination detection
    observability — Tracing, memory pruning (Squeez)
    cron        — Automated agent cycle runner
    gmr         — Genius Model Rotator for model selection
    twave       — Chimera router v2, Landau-Ginzburg tracker v2
    stresslab   — ISC-Bench safety evaluation runner
    db          — Thread-safe SQLite database manager
    claw        — NEXUSCLAW agent operating subsystem
    relay       — Model relay proxy
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__version__ = "3.0.0"

# Lazy-loaded exports: (module_path, attr_name)
_EXPORTS: dict[str, tuple[str, str]] = {
    # Monitoring (always available)
    "TokenGuard": (".monitoring.token_guard", "TokenGuard"),
    "LocalCounter": (".monitoring.counters", "LocalCounter"),
    "NativeCounter": (".monitoring.counters", "NativeCounter"),
    "TokscaleCounter": (".monitoring.counters", "TokscaleCounter"),
    "SemanticCache": (".monitoring.strategies", "SemanticCache"),
    "hot_path": (".monitoring.strategies", "hot_path"),
    "warm_path": (".monitoring.strategies", "warm_path"),
    # Engine
    "EngineRouter": (".engine.router", "EngineRouter"),
    "TaskRouter": (".engine.router", "EngineRouter"),
    "HermesRouter": (".engine.hermes", "HermesRouter"),
    "HeartbeatMonitor": (".engine.heartbeat", "HeartbeatMonitor"),
    # Governor
    "NexusGovernor": (".governor.base", "NexusGovernor"),
    "KaijuAuthorizer": (".governor.kaiju_auth", "KaijuAuthorizer"),
    "ComplianceEngine": (".governor.compliance", "ComplianceEngine"),
    "TrustKernel": (".governor.trust_kernel", "TrustKernel"),
    "VAPProofChain": (".governor.proof_chain", "VAPProofChain"),
    # Vault
    "VaultManager": (".vault.manager", "VaultManager"),
    "TrustScorer": (".vault.trust", "TrustScorer"),
    "MinjaDetector": (".vault.poisoning", "MinjaDetector"),
    "Mem0Adapter": (".vault.memory_adapter", "Mem0Adapter"),
    "SqueezPruner": (".observability.squeez", "SqueezPruner"),
    # Bridge
    "BridgeServer": (".bridge.server", "BridgeServer"),
    "NexusClient": (".bridge.sdk", "NexusClient"),
    "SecretStore": (".bridge.secrets", "SecretStore"),
    # Swarm
    "OpenClawSpawner": (".swarm.openclaw_spawner", "OpenClawSpawner"),
    "Foreman": (".swarm.foreman", "Foreman"),
    "Worker": (".swarm.worker", "Worker"),
    # Team
    "TeamCoordinator": (".team.coordinator", "TeamCoordinator"),
    # MCP
    "GovernedMCPServer": (".mcp.server", "GovernedMCPServer"),
    "MCPConfig": (".mcp.server", "MCPConfig"),
    "ToolSpec": (".mcp.server", "ToolSpec"),
    # Security
    "MetaAttackDetector": (".security.meta_attack_detector", "MetaAttackDetector"),
    "TerminalSanitizer": (".security.sanitizer", "TerminalSanitizer"),
    # Cron
    "AgentCycleRunner": (".cron.agent_cycle", "AgentCycleRunner"),
    # GMR
    "GeniusModelRotator": (".gmr.rotator", "GeniusModelRotator"),
    "ModelPool": (".gmr.rotator", "ModelPool"),
    # TWAVE
    "ChimeraRouterV2": (".twave.chimera_router_v2", "ChimeraRouterV2"),
    "LandauGinzburgTrackerV2": (".twave.landau_ginzburg_tracker_v2", "LandauGinzburgTrackerV2"),
    # DB
    "DatabaseManager": (".db.manager", "DatabaseManager"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}. "
            f"Available: {', '.join(__all__)}"
        ) from exc

    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
