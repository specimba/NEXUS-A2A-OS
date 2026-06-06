# A2A/Zapier MCP Integration Architecture for NEXUS OS

**Date:** 2026-05-15  
**Status:** Design Phase  
**Purpose:** Integrate Zapier MCP and A2A protocol into NEXUS OS to solve Tool Space Interference and enable distributed specialist server model

---

## Executive Summary

This document defines the integration architecture for adding Zapier MCP and A2A (Agent-to-Agent) protocol capabilities to NEXUS OS. The integration solves the critical **Tool Space Interference (TSI)** problem where >20 functions per agent cause context window saturation and reasoning degradation.

### Key Objectives

1. **Solve TSI**: Distribute tool capabilities across specialist servers instead of loading all tools into single agent context
2. **Map 3 Horseman Roles**: Align distributed architecture with OPUSman (implementer), DeepSeek (researcher), Grok (router)
3. **Preserve Governance**: Maintain KAIJU authorization, VAP audit trails, and TrustEngine oversight
4. **Enable Massive Tool Access**: Leverage Zapier's 30,000+ actions across 9,000+ apps via governed MCP layer
5. **Support Multi-Agent Ecosystem**: Unify Grok 4.3, ChatGPT 5.5, Gemini, Z.ai GLM 5.1, local systems

---

## Current NEXUS OS Architecture Analysis

### Existing Integration Points

| Component | Port | Protocol | Current Purpose | Integration Potential |
|-----------|------|----------|-----------------|---------------------|
| Bridge Server | 7352 | JSON-RPC 2.0 over HTTP | Agent-to-agent communication, KAIJU auth, task execution | **Primary MCP integration point** |
| NexusGovernor | Internal | Python API | KAIJU 4-variable authorization, CVA, compliance | **Extend for external tool authorization** |
| Vault | Internal | 5-track schema | EVENT/TRUST/CAP/FAIL/GOV memory | **Store A2A negotiation state** |
| TokenGuard | Internal | Budget enforcement | Token budget management | **Extend for Zapier cost tracking** |
| Engine/GMR | Internal | DAG routing | Model selection, task routing | **Route to appropriate specialist servers** |

### Bridge Server Capabilities

The existing Bridge server (`nexus_os/bridge/server.py`) already provides:

```python
# Current Bridge endpoints
POST /tasks/submit    # Submit task for execution  
POST /tasks/status    # Query task status
POST /vault/read      # Query Vault memory
POST /vault/write     # Write to Vault memory
POST /                # JSON-RPC 2.0 router
```

**Key Integration Features:**
- HMAC-SHA256 authentication via SecretStore
- KAIJU 4-variable authorization (scope × clearance, impact × clearance, intent × action)
- TokenGuard integration with budget enforcement
- Structured JSON-RPC 2.0 responses
- Task execution via TaskExecutor (currently stub/mock)

---

## A2A/Zapier MCP Integration Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    NEXUS OS GOVERNANCE LAYER                    │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ KAIJU    │  │ TrustEngine│ │ VAP Chain │  │  TokenGuard   │  │
│  │ Governor │  │ v2.2     │  │ (Audit)   │  │  (Budget)     │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   BRIDGE SERVER (Port 7352)                     │
│                  Enhanced with MCP Server Layer                 │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              MCP Server Implementation                   │  │
│  │  - Tool registration & discovery                         │  │
│  │  - Dynamic tool filtering (TSI solution)                │  │
│  │  - A2A protocol negotiation                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬───────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
│  Zapier MCP      │ │   n8n        │ │  Direct A2A     │
│  (30K+ actions)  │ │  Orchestrator│ │  (Local/Cloud)  │
│  - Notion        │ │  - Multi-LM  │ │  - Grok 4.3      │
│  - GitHub        │ │  - Routing   │ │  - ChatGPT 5.5   │
│  - Slack         │ │  - Workflows │ │  - Gemini       │
│  - 9,000+ apps   │ │              │ │  - Z.ai GLM 5.1  │
└──────────────────┘ └──────────────┘ └─────────────────┘
```

### 3 Horseman Role Mapping

| Horseman Role | NEXUS OS Component | A2A/Zapier Integration | Specialist Server Focus |
|---------------|-------------------|------------------------|------------------------|
| **OPUSman** (Implementer) | Engine/Executor | Code execution tools, GitHub Actions, CI/CD | Implementation & execution |
| **DeepSeek** (Researcher) | GMR/Router | Research APIs, web search, knowledge bases | Information retrieval & analysis |
| **Grok** (Router) | Bridge/Governor | Zapier routing, n8n orchestration, task distribution | Coordination & routing |

---

## MCP Server Implementation Design

### MCP Server Architecture

```python
# nexus_os/bridge/mcp_server.py
"""
MCP Server Implementation for NEXUS OS Bridge

Implements Model Context Protocol server with:
- Tool registration & discovery
- Dynamic tool filtering (TSI solution)
- A2A protocol negotiation
- KAIJU authorization integration
- VAP audit trail integration
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class MCPTool:
    """Represents a tool in the MCP protocol."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: callable
    category: str  # For dynamic filtering
    trust_level: str = "standard"  # standard, elevated, critical
    cost_per_call: float = 0.0  # For Zapier cost tracking

@dataclass
class MCPContext:
    """Context for MCP tool execution."""
    agent_id: str
    project_id: str
    trace_id: str
    intent: str
    capabilities: List[str]  # Agent's advertised capabilities
    trust_score: float

class NexusMCPServer:
    """
    NEXUS OS MCP Server with TSI-aware tool filtering.
    
    Key features:
    - Register tools from multiple sources (Zapier, n8n, direct A2A)
    - Dynamic tool filtering based on agent intent & capabilities
    - KAIJU authorization integration
    - VAP audit trail for all tool calls
    - TokenGuard cost tracking for Zapier actions
    """
    
    def __init__(self, governor, token_guard, vault):
        self.governor = governor
        self.token_guard = token_guard
        self.vault = vault
        self._tools: Dict[str, MCPTool] = {}
        self._tool_categories: Dict[str, List[str]] = {}
        
    def register_tool(self, tool: MCPTool):
        """Register a tool with the MCP server."""
        self._tools[tool.name] = tool
        if tool.category not in self._tool_categories:
            self._tool_categories[tool.category] = []
        self._tool_categories[tool.category].append(tool.name)
        logger.info(f"MCP: Registered tool {tool.name} in category {tool.category}")
        
    def discover_tools(self, context: MCPContext) -> List[Dict[str, Any]]:
        """
        Discover tools relevant to the current context (TSI solution).
        
        Instead of returning all 160+ tools, analyze:
        1. Agent's advertised capabilities
        2. Task intent classification
        3. Trust score requirements
        4. Category relevance
        
        Returns only relevant tools to prevent context saturation.
        """
        relevant_tools = []
        
        # Intent classification (simple keyword-based, can be enhanced with LLM)
        intent_keywords = {
            "code": ["github", "git", "code", "pr", "issue", "deploy"],
            "research": ["search", "fetch", "query", "analyze", "paper"],
            "communication": ["slack", "email", "notify", "message"],
            "data": ["database", "storage", "file", "upload", "download"],
        }
        
        detected_intents = []
        for intent, keywords in intent_keywords.items():
            if any(keyword in context.intent.lower() for keyword in keywords):
                detected_intents.append(intent)
        
        # If no intent detected, return safe default tools
        if not detected_intents:
            detected_intents = ["communication"]  # Default fallback
        
        # Collect tools from relevant categories
        for intent in detected_intents:
            if intent in self._tool_categories:
                for tool_name in self._tool_categories[intent]:
                    tool = self._tools[tool_name]
                    
                    # Trust level filtering
                    if tool.trust_level == "critical" and context.trust_score < 0.8:
                        continue
                    if tool.trust_level == "elevated" and context.trust_score < 0.6:
                        continue
                    
                    relevant_tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.input_schema,
                        "category": tool.category,
                    })
        
        # Limit to top 16 tools (TSI threshold)
        relevant_tools = relevant_tools[:16]
        
        logger.info(
            f"MCP: Discovered {len(relevant_tools)} tools for agent {context.agent_id} "
            f"(intents: {detected_intents}, trust: {context.trust_score})"
        )
        
        return relevant_tools
    
    def call_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any], 
        context: MCPContext
    ) -> Dict[str, Any]:
        """
        Execute a tool call with full governance integration.
        
        Pipeline:
        1. KAIJU authorization check
        2. TokenGuard budget check
        3. Tool execution
        4. VAP audit logging
        5. Result return
        """
        if tool_name not in self._tools:
            return {
                "error": f"Tool not found: {tool_name}",
                "success": False
            }
        
        tool = self._tools[tool_name]
        
        # Step 1: KAIJU authorization
        auth_result = self.governor.check_access(
            agent_id=context.agent_id,
            project_id=context.project_id,
            action=f"tool:{tool_name}",
            scope="project",
            intent=f"Execute tool {tool_name} for {context.intent}",
            impact="medium" if tool.trust_level == "standard" else "high",
            clearance="contributor",
            trace_id=context.trace_id,
            context={"tool_category": tool.category}
        )
        
        if auth_result.decision.value != "ALLOW":
            return {
                "error": f"Authorization denied: {auth_result.reason}",
                "success": False,
                "auth_decision": auth_result.decision.value
            }
        
        # Step 2: TokenGuard budget check (for Zapier cost tracking)
        if tool.cost_per_call > 0:
            if not self.token_guard.check(context.agent_id, int(tool.cost_per_call * 1000)):
                return {
                    "error": "Token budget exceeded for this tool",
                    "success": False,
                    "cost": tool.cost_per_call
                }
        
        # Step 3: Execute tool
        try:
            result = tool.handler(arguments)
            
            # Step 4: Track costs
            if tool.cost_per_call > 0:
                self.token_guard.track(
                    context.agent_id, 
                    int(tool.cost_per_call * 1000),
                    operation=f"zapier:{tool_name}",
                    context={"project_id": context.project_id}
                )
            
            # Step 5: VAP audit logging
            self.vault.store_track(
                track="EVENT",
                agent_id=context.agent_id,
                data={
                    "event_type": "tool_execution",
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "result_summary": str(result)[:500],  # Truncated for storage
                    "auth_decision": auth_result.decision.value,
                    "cost": tool.cost_per_call,
                    "trace_id": context.trace_id
                }
            )
            
            return {
                "result": result,
                "success": True,
                "auth_decision": auth_result.decision.value
            }
            
        except Exception as e:
            logger.error(f"MCP tool execution failed: {tool.name}: {e}")
            return {
                "error": str(e),
                "success": False
            }
```

### Zapier MCP Integration

```python
# nexus_os/bridge/zapier_mcp_adapter.py
"""
Zapier MCP Adapter for NEXUS OS

Integrates with Zapier's MCP server to provide:
- 30,000+ actions across 9,000+ apps
- Governed access via KAIJU authorization
- Cost tracking via TokenGuard
- Dynamic tool filtering to prevent TSI
"""

import httpx
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class ZapierMCPAdapter:
    """
    Adapter for Zapier's MCP server.
    
    Uses Zapier's natural language actions interface:
    https://mcp.zapier.com/api/v1/connect
    """
    
    def __init__(self, api_key: str, base_url: str = "https://mcp.zapier.com/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0
        )
    
    async def discover_actions(self, intent: str, limit: int = 16) -> List[Dict[str, Any]]:
        """
        Discover relevant Zapier actions based on intent.
        
        Zapier's API supports natural language action discovery.
        This prevents loading all 30,000+ actions at once.
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/actions/discover",
                json={
                    "intent": intent,
                    "limit": limit
                }
            )
            response.raise_for_status()
            actions = response.json()
            
            # Transform to MCP tool format
            mcp_tools = []
            for action in actions.get("actions", [])[:limit]:
                mcp_tools.append({
                    "name": f"zapier_{action['id']}",
                    "description": action.get("description", ""),
                    "input_schema": action.get("input_schema", {}),
                    "category": "zapier",
                    "cost_per_call": self._estimate_cost(action)
                })
            
            return mcp_tools
            
        except Exception as e:
            logger.error(f"Zapier action discovery failed: {e}")
            return []
    
    async def execute_action(
        self, 
        action_id: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Zapier action with parameters."""
        try:
            response = await self.client.post(
                f"{self.base_url}/actions/{action_id}/execute",
                json=parameters
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Zapier action execution failed: {e}")
            return {"error": str(e), "success": False}
    
    def _estimate_cost(self, action: Dict[str, Any]) -> float:
        """Estimate cost per call based on action type."""
        # Zapier pricing varies by action type
        # This is a simplified estimation model
        action_type = action.get("type", "standard")
        cost_map = {
            "standard": 0.001,
            "premium": 0.005,
            "enterprise": 0.02
        }
        return cost_map.get(action_type, 0.001)
```

---

## n8n Integration for Multi-Agent Orchestration

### n8n Workflow Architecture

```python
# nexus_os/bridge/n8n_orchestrator.py
"""
n8n Orchestrator for NEXUS OS

Integrates with n8n for:
- Multi-agent workflow coordination
- Dynamic model routing (Grok → coding, Gemini → research)
- Local system bridges via webhooks
- Complex multi-step orchestrations
"""

import httpx
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class N8NOrchestrator:
    """
    n8n orchestrator for multi-agent workflows.
    
    Key capabilities:
    - Route tasks to appropriate models/agents
    - Bridge local CLI/swarm tools via webhooks
    - Coordinate multi-step workflows
    - Integrate with NEXUS governance layer
    """
    
    def __init__(self, webhook_url: str, api_key: str):
        self.webhook_url = webhook_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0
        )
    
    async def route_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a task to the appropriate agent/model based on task type.
        
        Routing logic:
        - Code tasks → Grok 4.3 / Claude
        - Research tasks → Gemini / DeepSeek
        - Analysis tasks → GLM 5.1 / ChatGPT 5.5
        - Local CLI tasks → Local OpenCode CLI / Autoclaw
        - Cloud tasks → Cloud Claw / KiloClaw
        """
        task_type = self._classify_task(task)
        
        routing_map = {
            "code": {"agent": "grok-4.3", "fallback": "claude-3.5"},
            "research": {"agent": "gemini-pro", "fallback": "deepseek-v3"},
            "analysis": {"agent": "glm-5.1", "fallback": "gpt-5.5"},
            "local_cli": {"agent": "opencode-cli", "fallback": "autoclaw-local"},
            "cloud": {"agent": "kiloclaw", "fallback": "cloud-claw"}
        }
        
        target = routing_map.get(task_type, {"agent": "grok-4.3", "fallback": "claude-3.5"})
        
        # Trigger n8n workflow with routing decision
        try:
            response = await self.client.post(
                self.webhook_url,
                json={
                    "task": task,
                    "routing_decision": target,
                    "trace_id": task.get("trace_id")
                }
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"n8n task routing failed: {e}")
            return {"error": str(e), "success": False}
    
    def _classify_task(self, task: Dict[str, Any]) -> str:
        """Classify task type for routing."""
        description = task.get("description", "").lower()
        context = task.get("context", {})
        
        # Simple keyword-based classification (can be enhanced with LLM)
        if any(keyword in description for keyword in ["code", "github", "pr", "deploy", "function"]):
            return "code"
        elif any(keyword in description for keyword in ["research", "paper", "search", "analyze", "study"]):
            return "research"
        elif any(keyword in description for keyword in ["cli", "local", "command", "execute"]):
            return "local_cli"
        elif any(keyword in description for keyword in ["cloud", "api", "web service"]):
            return "cloud"
        else:
            return "analysis"
```

---

## Integration with Existing Bridge Server

### Enhanced Bridge Server

```python
# nexus_os/bridge/server.py (enhanced)

class BridgeServer:
    """Enhanced Bridge Server with MCP integration."""
    
    def __init__(
        self,
        secret_store=None,
        governor=None,
        executor=None,
        token_guard=None,
        enable_mcp: bool = True,
        zapier_api_key: Optional[str] = None,
        n8n_webhook_url: Optional[str] = None,
    ):
        # ... existing initialization ...
        
        # MCP Server integration
        self.enable_mcp = enable_mcp
        if enable_mcp:
            from nexus_os.bridge.mcp_server import NexusMCPServer
            self.mcp_server = NexusMCPServer(
                governor=governor,
                token_guard=token_guard,
                vault=self.vault
            )
            
            # Register Zapier tools if API key provided
            if zapier_api_key:
                self._register_zapier_tools(zapier_api_key)
            
            # Register n8n orchestrator if webhook URL provided
            if n8n_webhook_url:
                from nexus_os.bridge.n8n_orchestrator import N8NOrchestrator
                self.n8n_orchestrator = N8NOrchestrator(
                    webhook_url=n8n_webhook_url,
                    api_key=self.secret_store.get_secret("n8n")
                )
    
    def _register_zapier_tools(self, api_key: str):
        """Register Zapier tools with MCP server."""
        from nexus_os.bridge.zapier_mcp_adapter import ZapierMCPAdapter
        import asyncio
        
        async def register():
            adapter = ZapierMCPAdapter(api_key)
            # Register common Zapier tools as MCP tools
            common_actions = [
                "gmail_send_email",
                "slack_send_message", 
                "github_create_issue",
                "notion_create_page",
                "google_drive_upload"
            ]
            
            for action in common_actions:
                # Would normally call Zapier to get action schemas
                # This is simplified for the architecture document
                from nexus_os.bridge.mcp_server import MCPTool
                self.mcp_server.register_tool(MCPTool(
                    name=f"zapier_{action}",
                    description=f"Execute Zapier action: {action}",
                    input_schema={"type": "object"},
                    handler=lambda args: asyncio.run(adapter.execute_action(action, args)),
                    category="zapier",
                    trust_level="standard",
                    cost_per_call=0.001
                ))
        
        # Run async registration
        asyncio.run(register())
    
    # Add MCP-specific endpoints
    def handle_mcp_discover(self, body: bytes, headers: Dict[str, str]) -> tuple:
        """Handle MCP tool discovery request."""
        try:
            req = self.parse_request(body, headers)
            req.method = "mcp/discover"
            self._authenticate(req)
            self._authorize(req)
            
            from nexus_os.bridge.mcp_server import MCPContext
            context = MCPContext(
                agent_id=req.agent_id,
                project_id=req.project_id,
                trace_id=req.trace_id,
                intent=req.payload.get("intent", ""),
                capabilities=req.payload.get("capabilities", []),
                trust_score=self.governor.get_trust_score(req.agent_id)
            )
            
            tools = self.mcp_server.discover_tools(context)
            
            return 200, jsonrpc_result({
                "tools": tools,
                "count": len(tools),
                "agent_context": {
                    "agent_id": context.agent_id,
                    "trust_score": context.trust_score,
                    "intent": context.intent
                }
            }, req.trace_id)
            
        except (AuthError, ForbiddenError, ParseError) as e:
            return e.http_status, jsonrpc_error(e.code, e.message)
        except Exception as e:
            return 500, jsonrpc_error(-32603, f"Internal error: {e}")
    
    def handle_mcp_call(self, body: bytes, headers: Dict[str, str]) -> tuple:
        """Handle MCP tool execution request."""
        try:
            req = self.parse_request(body, headers)
            req.method = "mcp/call"
            self._authenticate(req)
            self._authorize(req)
            
            from nexus_os.bridge.mcp_server import MCPContext
            context = MCPContext(
                agent_id=req.agent_id,
                project_id=req.project_id,
                trace_id=req.trace_id,
                intent=req.payload.get("intent", ""),
                capabilities=req.payload.get("capabilities", []),
                trust_score=self.governor.get_trust_score(req.agent_id)
            )
            
            tool_name = req.payload.get("tool_name")
            arguments = req.payload.get("arguments", {})
            
            result = self.mcp_server.call_tool(tool_name, arguments, context)
            
            return 200, jsonrpc_result(result, req.trace_id)
            
        except (AuthError, ForbiddenError, ParseError) as e:
            return e.http_status, jsonrpc_error(e.code, e.message)
        except Exception as e:
            return 500, jsonrpc_error(-32603, f"Internal error: {e}")
```

---

## Governance Integration

### Extended KAIJU Authorization

```python
# nexus_os/governor/base.py (enhanced)

class NexusGovernor:
    """Enhanced Governor with external tool authorization."""
    
    def check_external_tool_access(
        self,
        agent_id: str,
        tool_name: str,
        tool_category: str,
        project_id: str,
        trace_id: Optional[str] = None,
    ) -> AuthResult:
        """
        Specialized authorization check for external tool access.
        
        Additional considerations:
        - Tool category risk assessment
        - External provider trust zones
        - Cost/budget implications
        - Data residency requirements
        """
        # Base KAIJU check
        base_result = self.check_access(
            agent_id=agent_id,
            project_id=project_id,
            action=f"external_tool:{tool_name}",
            scope="cross_project" if tool_category == "zapier" else "project",
            intent=f"Access external tool {tool_name} in category {tool_category}",
            impact="high" if tool_category in ["zapier", "critical"] else "medium",
            clearance="maintainer" if tool_category == "critical" else "contributor",
            trace_id=trace_id,
            context={"tool_category": tool_category, "external_provider": True}
        )
        
        if base_result.decision != Decision.ALLOW:
            return base_result
        
        # Additional checks for external tools
        if tool_category == "zapier":
            # Check Zapier-specific budget
            zapier_budget_ok = self._check_zapier_budget(agent_id)
            if not zapier_budget_ok:
                return AuthResult(
                    Decision.DENY,
                    "Zapier budget exceeded for agent",
                    trace_id
                )
        
        return base_result
    
    def _check_zapier_budget(self, agent_id: str) -> bool:
        """Check Zapier-specific budget limits."""
        # Implement Zapier budget tracking logic
        # Could use TokenGuard with separate budget category
        return True  # Placeholder
```

---

## Migration Strategy from Azure-Dead to Hybrid Architecture

### Phase 1: Foundation (Week 1-2)

1. **Implement MCP Server Foundation**
   - Create `nexus_os/bridge/mcp_server.py`
   - Implement basic tool registration & discovery
   - Add TSI-aware dynamic tool filtering
   - Integrate with existing KAIJU authorization

2. **Zapier MCP Integration**
   - Create `nexus_os/bridge/zapier_mcp_adapter.py`
   - Implement Zapier API client
   - Add cost tracking integration
   - Test with 5-10 common Zapier actions

3. **Enhanced Bridge Server**
   - Add MCP endpoints to existing Bridge server
   - Integrate MCP server with Bridge authentication/authorization
   - Update API documentation

### Phase 2: Orchestration (Week 3-4)

1. **n8n Integration**
   - Create `nexus_os/bridge/n8n_orchestrator.py`
   - Implement task routing logic
   - Add webhook integration
   - Test multi-agent workflows

2. **3 Horseman Role Mapping**
   - Define specialist server configurations
   - Implement role-based routing
   - Add capability negotiation

3. **Multi-Agent Ecosystem**
   - Add Grok 4.3 integration
   - Add ChatGPT 5.5 integration
   - Add Gemini integration
   - Add Z.ai GLM 5.1 integration

### Phase 3: Local Integration (Week 5-6)

1. **Local System Bridges**
   - Zo computer CLI integration
   - OpenCode CLI integration
   - Meta Spark integration
   - Autoclaw swarm integration

2. **Security Hardening**
   - Cross-agent security measures
   - Output sanitization
   - PTY isolation
   - VAP audit trail enhancement

### Phase 4: Testing & Documentation (Week 7-8)

1. **Integration Testing**
   - End-to-end workflow testing
   - Load testing with TSI scenarios
   - Security testing
   - Cost tracking validation

2. **Documentation**
   - API documentation
   - Deployment guides
   - Runbooks
   - Troubleshooting guides

---

## Cost & Risk Analysis

### Cost Considerations

| Component | Cost Model | Estimation | Mitigation |
|-----------|------------|------------|------------|
| Zapier MCP | Per-action | $0.001-$0.02 per call | TokenGuard budget limits |
| n8n Self-Hosted | Infrastructure | $20-50/month (VPS) | Use existing infrastructure |
| Additional AI APIs | Per-token | Varies by provider | GMR routing optimization |
| Local Systems | Fixed | Hardware amortization | Use existing hardware |

### Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| TSI not fully resolved | High | Dynamic tool filtering + testing |
| Zapier cost overruns | High | TokenGuard hard stops + monitoring |
| External API dependencies | Medium | Fallback to local tools |
| Multi-agent coordination failure | Medium | n8n workflow error handling |
| Governance bypass attempts | Critical | KAIJU + VAP + audit trails |

---

## Success Criteria

### Technical Metrics

- [ ] MCP server handles 100+ tool registrations without performance degradation
- [ ] Dynamic tool filtering reduces context window usage by >70%
- [ ] TSI eliminated: no reasoning degradation with 160+ available tools
- [ ] KAIJU authorization adds <50ms latency to tool calls
- [ ] Zapier cost tracking accuracy within 5%
- [ ] Multi-agent workflows complete with >95% success rate

### Integration Metrics

- [ ] All 3 Horseman roles operational with specialist servers
- [ ] 4 major AI providers integrated (Grok, ChatGPT, Gemini, GLM)
- [ ] Local systems (Zo, OpenCode, Autoclaw) bridged successfully
- [ ] Azure dependencies fully removed
- [ ] Governance coverage 100% for external tool access

---

## Next Steps

1. **Review and approve this architecture document**
2. **Begin Phase 1 implementation** (MCP server foundation)
3. **Set up Zapier API account and testing**
4. **Configure n8n instance for orchestration testing**
5. **Define 3 Horseman specialist server specifications**

This architecture provides a clear path from Azure-dead to a hybrid, governed, multi-agent ecosystem while preserving NEXUS OS's core governance principles.