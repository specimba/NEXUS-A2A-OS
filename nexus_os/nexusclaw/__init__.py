"""NexusClaw Core V1: governed multi-agent orchestration, coordination, and communication.

NexusClaw V1 is a unified multi-agent coordination layer for NEXUS OS, providing:
  - AgentPool: registry of all agents (internal + external)
  - TaskRouter: intelligent task matching and dispatch
  - MessageBus: inter-agent communication (internal + external platforms)
  - BrainstormEngine: collaborative deliberation and consensus
  - Orchestrator: central coordination tying all components together
  - Coordinator: governance dry-run validation
  - Runner: 24/7 persistent operation
  - WorklogSystem: triple-sink audit trail (memory + archivist + markdown)
"""

from nexus_os.nexusclaw.agent_pool import (
    AgentPool,
    AgentRecord,
    AgentStatus,
    AgentType,
    AgentCapability,
    get_agent_pool,
)
from nexus_os.nexusclaw.browser_ai import BrowserAINexusClawBridge, BrowserAIRoutingPacket
from nexus_os.nexusclaw.brainstorm import (
    BrainstormEngine,
    BrainstormMode,
    BrainstormPhase,
    BrainstormSession,
    Proposal,
    VoteChoice,
)
from nexus_os.nexusclaw.coordinator import NexusClawCoordinator, NexusClawRuntimeConfig
from nexus_os.nexusclaw.envelope import NexusClawResultEnvelope, NexusClawTaskEnvelope, RiskLevel, ResultStatus
from nexus_os.nexusclaw.message_bus import (
    MessageBus,
    NexusMessage,
    MessageType,
    MessagePriority,
    MessageThread,
)
from nexus_os.nexusclaw.messaging import (
    TelegramConnector,
    SlackConnector,
    DiscordConnector,
    NEXUSCLAWMessagingHub,
    MessageResult,
)
from nexus_os.nexusclaw.model_intake import NexusClawModelArena, ModelIntakeRequest
from nexus_os.nexusclaw.orchestrator import (
    NexusClawOrchestrator,
    OrchestratorStatus,
    get_orchestrator,
)
from nexus_os.nexusclaw.runner import NexusClawRunner, RunnerConfig, get_runner
from nexus_os.nexusclaw.task_router import (
    TaskRouter,
    RoutingStrategy,
    RoutingDecision,
    TaskAssignment,
)
from nexus_os.nexusclaw.tool_bridge import (
    MCPToolBridge,
    ExternalMCPServer,
    BridgedTool,
    ToolBridgeResult,
    get_tool_bridge,
    load_mcp_bridge_from_env,
)
from nexus_os.nexusclaw.worklog import WorklogEntry, WorklogSystem

# Phase D: ARCHIVIST Evidence Integration
from nexus_os.nexusclaw.research_synthesis import ResearchIntegrationEngine
from nexus_os.nexusclaw.external_connectors import ExternalConnectorManager, get_external_connectors
from nexus_os.nexusclaw.security_evidence import SecurityEvidencePipeline
from nexus_os.nexusclaw.model_observatory import ModelObservatory, get_model_observatory
from nexus_os.nexusclaw.temporal_synthesis import TemporalEvidenceSynthesizer, get_temporal_synthesizer

__all__ = [
    # Agent Pool
    "AgentPool",
    "AgentRecord",
    "AgentStatus",
    "AgentType",
    "AgentCapability",
    "get_agent_pool",
    # Browser-AI Supervisor Bridge
    "BrowserAINexusClawBridge",
    "BrowserAIRoutingPacket",
    # Brainstorm Engine
    "BrainstormEngine",
    "BrainstormMode",
    "BrainstormPhase",
    "BrainstormSession",
    "Proposal",
    "VoteChoice",
    # Core Coordinator
    "NexusClawCoordinator",
    "NexusClawRuntimeConfig",
    "NexusClawResultEnvelope",
    "NexusClawTaskEnvelope",
    "RiskLevel",
    "ResultStatus",
    # Message Bus
    "MessageBus",
    "NexusMessage",
    "MessageType",
    "MessagePriority",
    "MessageThread",
    # External Messaging
    "TelegramConnector",
    "SlackConnector",
    "DiscordConnector",
    "NEXUSCLAWMessagingHub",
    "MessageResult",
    # Model Intake
    "NexusClawModelArena",
    "ModelIntakeRequest",
    # Orchestrator
    "NexusClawOrchestrator",
    "OrchestratorStatus",
    "get_orchestrator",
    # Runner
    "NexusClawRunner",
    "RunnerConfig",
    "get_runner",
    # Task Router
    "TaskRouter",
    "RoutingStrategy",
    "RoutingDecision",
    "TaskAssignment",
    # Tool Bridge
    "MCPToolBridge",
    "ExternalMCPServer",
    "BridgedTool",
    "ToolBridgeResult",
    "get_tool_bridge",
    "load_mcp_bridge_from_env",
    # Worklog
    "WorklogEntry",
    "WorklogSystem",
    # Phase D: ARCHIVIST Evidence Integration
    "ResearchIntegrationEngine",
    "ExternalConnectorManager",
    "get_external_connectors",
    "SecurityEvidencePipeline",
    "ModelObservatory",
    "get_model_observatory",
    "TemporalEvidenceSynthesizer",
    "get_temporal_synthesizer",
    # ModelRelay transport
    "select_model_for_task",
]
