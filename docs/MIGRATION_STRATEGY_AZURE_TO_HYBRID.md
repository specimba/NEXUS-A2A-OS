# Migration Strategy: Azure-Dead to Hybrid A2A/Zapier/n8n Architecture

**Date:** 2026-05-15  
**Status:** Strategic Planning Phase  
**Purpose:** Complete migration roadmap from deprecated Azure Foundry to hybrid multi-agent architecture

---

## Executive Summary

### Migration Objective
Replace all Azure-dependent components in NEXUS OS with a hybrid architecture combining:
- **A2A Protocol** for agent-to-agent communication
- **Zapier MCP** for 30,000+ tool integrations
- **n8n** for multi-agent orchestration
- **Local-first execution** with Tailscale networking
- **ERNIE MCP governance** for proposal-based decision making

### Current State Assessment
- **Azure Status**: DEAD (subscription blocked 2026-05-15)
- **Dependencies Affected**: 13 Azure models, Foundry pipelines, custom model imports
- **Risk Level**: HIGH - Production workflows may be broken
- **Timeline**: 8-week phased migration

---

## Migration Architecture Comparison

### Before (Azure-Dependent)

```
┌─────────────────────────────────────────────────────────────────┐
│                     NEXUS OS (Azure)                            │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │  Azure   │  │ Foundry │  │  Azure   │  │  Custom       │  │
│  │  Models  │  │  Agents  │  │  Storage │  │  Model Import │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │
│         │            │            │                │            │
│         └────────────┼────────────┼────────────────┘            │
│                      ▼             ▼                             │
│              ┌────────────────────────────┐                   │
│              │   Azure Cloud Manager     │                   │
│              │   (NOW DEAD - BLOCKED)    │                   │
│              └────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

### After (Hybrid A2A/Zapier/n8n)

```
┌─────────────────────────────────────────────────────────────────┐
│                   NEXUS OS (Hybrid)                             │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │   Grok   │  │ ChatGPT  │  │  Gemini  │  │  Z.ai GLM     │  │
│  │  4.3     │  │  5.5     │  │          │  │    5.1        │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │
│         │            │            │                │            │
│         └────────────┼────────────┼────────────────┘            │
│                      ▼             ▼                             │
│              ┌────────────────────────────┐                   │
│              │   ERNIE MCP Governor       │                   │
│              │   (Supabase + Edge Funcs)  │                   │
│              └────────────┬───────────────┘                   │
│                           │                                    │
│         ┌─────────────────┼─────────────────┐                  │
│         │                 ▼                 │                  │
│    ┌──────────┐  ┌──────────────┐  ┌─────────────┐             │
│    │ Zapier   │  │     n8n      │  │  Direct A2A │             │
│    │ MCP      │  │ Orchestrator │  │  (Local)    │             │
│    │ 30K+     │  │              │  │             │             │
│    │ actions  │  │              │  │             │             │
│    └──────────┘  └──────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Assessment & Planning (Weeks 1-2)

### 1.1 Dependency Audit

**Objective**: Identify all Azure dependencies in NEXUS OS

**Actions**:
- [ ] Scan codebase for Azure SDK references
- [ ] Audit environment variables for Azure keys
- [ ] Review database for Azure resource references
- [ ] Identify all Azure model usage patterns
- [ ] Document Azure API endpoints in use

**Deliverables**:
- `azure_dependency_audit.json` - Complete dependency mapping
- `azure_replacement_matrix.md` - Replacement strategy per dependency

**Commands**:
```bash
# Scan for Azure references
grep -r "azure" --include="*.py" --include="*.ts" --include="*.json" .

# Check environment variables
grep -r "AZURE" --include="*.env*" --include="*.yaml" .

# Azure SDK references
grep -r "azure.ai" --include="*.py" .
```

### 1.2 Service Decommissioning

**Objective**: Safely decommission Azure services

**Actions**:
- [ ] Verify no active workloads depend on Azure
- [ ] Export critical data from Azure Storage
- [ ] Cancel Azure subscriptions
- [ ] Remove Azure credentials from all systems
- [ ] Update DNS and load balancer configurations

**Risk Mitigation**:
- Read-only backup of all Azure resources
- 30-day data retention window
- Emergency rollback plan documented

---

## Phase 2: Foundation Services (Weeks 3-4)

### 2.1 Supabase Infrastructure Setup

**Objective**: Replace Azure backend services with Supabase

**Migration Map**:
| Azure Service | Supabase Replacement | Migration Effort |
|---------------|----------------------|-------------------|
| Azure SQL | Supabase PostgreSQL | Low |
| Azure Blob Storage | Supabase Storage | Low |
| Azure Functions | Supabase Edge Functions | Medium |
| Azure Key Vault | Supabase Secrets Manager | Low |

**Actions**:
```bash
# Create Supabase project
supabase projects create --name "nexus-os-migration"

# Apply database schema
cd nexus_os/ernie_mcp
supabase db push

# Deploy edge functions
supabase functions deploy on_proposal_created
supabase functions deploy execute_approved_proposal
supabase functions deploy compute_trust_delta
supabase functions deploy detect_anomalies
```

**Validation**:
- [ ] All 8 governance tables created
- [ ] Edge functions respond to test requests
- [ ] Database connections working from NEXUS components
- [ ] API latency < 100ms

### 2.2 Tailscale Network Setup

**Objective**: Establish secure networking for agent communication

**Actions**:
```bash
# Get Tailscale auth key
# Navigate to https://login.tailscale.com/admin/settings/keys

# Test Tailscale setup
cd nexus_os/networking/tailscale
export TAILSCALE_AUTHKEY=your-auth-key
export AGENT_ID=nexus-migration-test

docker build -f Dockerfile.tailscale -t nexus-tailscale:test .
docker run --rm \
  --cap-add=NET_ADMIN \
  --device=/dev/net/tun:/dev/net/tun \
  -e TAILSCALE_AUTHKEY \
  -e AGENT_ID \
  nexus-tailscale:test
```

**Validation**:
- [ ] Tailscale daemon starts successfully
- [ ] Node appears in Tailscale admin console
- [ ] Can ping other test nodes
- [ ] Network latency < 10ms

---

## Phase 3: Core Service Migration (Weeks 5-6)

### 3.1 Bridge Server Enhancement

**Objective**: Enhance Bridge Server to support MCP and A2A protocols

**Migration Steps**:
1. Integrate MCP server into existing Bridge (7352)
2. Add Zapier MCP adapter
3. Implement A2A protocol negotiation
4. Add Tailscale networking support
5. Update API documentation

**Code Changes**:
```python
# nexus_os/bridge/server.py - Add MCP integration
class BridgeServer:
    def __init__(self, ..., enable_mcp=True, zapier_api_key=None):
        # Add MCP server initialization
        if enable_mcp:
            from nexus_os.bridge.mcp_server import NexusMCPServer
            self.mcp_server = NexusMCPServer(governor, token_guard, vault)
            
            if zapier_api_key:
                self._register_zapier_tools(zapier_api_key)
    
    # Add MCP endpoints
    async def handle_mcp_discover(self, body, headers):
        # Tool discovery with TSI filtering
        
    async def handle_mcp_call(self, body, headers):
        # Tool execution with governance
```

**Testing**:
```bash
# Test MCP discovery
curl -X POST http://localhost:7352/mcp/discover \
  -H "Content-Type: application/json" \
  -d '{"intent": "code generation", "capabilities": ["coding"]}'

# Test Zapier tool execution
curl -X POST http://localhost:7352/mcp/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "zapier_gmail_send_email", "arguments": {...}}'
```

### 3.2 Model Provider Migration

**Objective**: Replace Azure models with alternative providers

**Migration Map**:
| Azure Model | Replacement Provider | Cost Savings |
|-------------|---------------------|--------------|
| Claude Opus 4.7 | Anthropic API Direct | 40% |
| DeepSeek R1 | DeepSeek API | 70% |
| Kimi K2.5 | Fireworks API (catalog) | 30% |
| Custom fine-tunes | Local Ollama + LoRA | 80% |

**Actions**:
```bash
# Update environment variables
# Replace AZURE_API_KEY with provider-specific keys

# Update model routing in GMR
# nexus_os/gmr/model_rotator.py
PROVIDER_ROUTES = {
    "code_generation": ["anthropic", "openai"],
    "research": ["deepseek", "gemini"],
    "local": ["ollama"],
    "fallback": ["huggingface"]
}
```

**Validation**:
- [ ] All model calls route to new providers
- [ ] TokenGuard budget tracking works
- [ ] Latency acceptable (<2s for most queries)
- [ ] Cost within budget

---

## Phase 4: Advanced Features (Weeks 7-8)

### 4.1 n8n Orchestration Integration

**Objective**: Implement multi-agent workflow coordination

**Actions**:
```bash
# Install n8n (self-hosted)
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# Create NEXUS workflow template
# Import workflow definitions
```

**Workflow Templates**:
1. **Code Review Pipeline**
   - Trigger: GitHub PR opened
   - Route to Grok 4.3 for code analysis
   - DeepSeek for documentation generation
   - Human approval via Slack
   - Merge to main

2. **Research Synthesis**
   - Trigger: New research papers added
   - Route to Gemini for analysis
   - Extract key findings
   - Update knowledge base
   - Notify team

3. **Local Execution Orchestration**
   - Trigger: Local CLI task
   - Route to OpenCode CLI via Tailscale
   - Execute in isolated sandbox
   - Return results to governance
   - Log to Vault

### 4.2 3 Horseman Role Implementation

**Objective**: Implement specialist server architecture

**Specialist Server Configurations**:

**OPUSman (Implementer)**:
```python
OPUSMAN_CONFIG = {
    "name": "opusman",
    "models": ["grok-4.3", "claude-3.5"],
    "capabilities": ["code_generation", "execution", "deployment"],
    "tools": ["github", "gitlab", "vercel", "docker"],
    "governance_level": "elevated"
}
```

**DeepSeek (Researcher)**:
```python
DEEPSEEK_CONFIG = {
    "name": "deepseek-researcher",
    "models": ["deepseek-v3", "gemini-pro"],
    "capabilities": ["research", "analysis", "documentation"],
    "tools": ["arxiv", "scholar", "wikipedia", "notion"],
    "governance_level": "standard"
}
```

**Grok (Router)**:
```python
GROK_CONFIG = {
    "name": "grok-router",
    "models": ["grok-4.3", "gpt-5.5"],
    "capabilities": ["orchestration", "routing", "coordination"],
    "tools": ["zapier", "n8n", "slack", "telegram"],
    "governance_level": "critical"
}
```

---

## Phase 5: Data Migration & Testing (Weeks 9-10)

### 5.1 Data Migration

**Objective**: Migrate critical data from Azure to Supabase

**Migration Steps**:

1. **Proposals and Governance Data**
```bash
# Export from Azure
# Import to Supabase
cd nexus_os/ernie_mcp
python scripts/migrate_azure_to_supabase.py \
  --azure-connection-string "$AZURE_CONNECTION_STRING" \
  --supabase-url "$SUPABASE_URL" \
  --supabase-key "$SUPABASE_SERVICE_KEY"
```

2. **Vault Memory Tracks**
```bash
# Export 5-track memory
# Import to Supabase vault tables
```

3. **Trust History**
```bash
# Export trust events
# Import with timestamp preservation
```

### 5.2 Integration Testing

**Test Plan**:

1. **Unit Tests**
```bash
# Test MCP server components
pytest tests/mcp/test_server.py
pytest tests/mcp/test_zapier_adapter.py
pytest tests/mcp/test_n8n_orchestrator.py
```

2. **Integration Tests**
```bash
# Test full proposal flow
pytest tests/integration/test_proposal_flow.py

# Test model routing
pytest tests/integration/test_model_routing.py

# Test Tailscale networking
pytest tests/integration/test_tailscale_networking.py
```

3. **Load Tests**
```bash
# Test with 100 concurrent agents
python tests/load/test_agent_swarm.py --agents 100 --duration 300

# Test Zapier rate limits
python tests/load/test_zapier_limits.py
```

---

## Phase 6: Cutover & Validation (Weeks 11-12)

### 6.1 Parallel Operation

**Objective**: Run Azure and hybrid systems in parallel

**Actions**:
- [ ] Deploy hybrid architecture to staging environment
- [ ] Configure canary routing (10% to hybrid)
- [ ] Monitor error rates and latency
- [ ] Validate governance decisions match
- [ ] Gradually increase hybrid traffic (25%, 50%, 75%, 100%)

**Monitoring**:
```bash
# Compare Azure vs hybrid performance
python scripts/compare_performance.py \
  --azure-metrics azure_metrics.json \
  --hybrid-metrics hybrid_metrics.json
```

### 6.2 Final Cutover

**Objective**: Complete migration to hybrid architecture

**Cutover Checklist**:
- [ ] All tests passing
- [ ] Performance validated (no degradation)
- [ ] Cost savings realized
- [ ] Team trained on new architecture
- [ ] Documentation complete
- [ ] Backup and rollback plan tested
- [ ] Stakeholder sign-off

**Cutover Commands**:
```bash
# Final switch
export NEXUS_MODE=hybrid
export AZURE_MODE=disabled

# Restart services
systemctl restart nexus-bridge
systemctl restart nexus-twave
systemctl restart nexus-websocket

# Validate
nexusctl doctor
nexusctl status
```

---

## Risk Management

### High-Risk Items

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Zapier API limits exceeded | Medium | High | Implement rate limiting, cost monitoring |
| Tailscale network partition | Low | High | Fallback to direct HTTP, test partitions |
| Data migration corruption | Low | Critical | Backup data, validate checksums, dry-run |
| Model provider outages | Medium | Medium | Multiple provider fallbacks |
| Governance decisions diverge | Low | Critical | Parallel operation, decision audit |

### Rollback Plan

**Trigger Conditions**:
- Error rate > 5% for 15 minutes
- Latency > 3x Azure baseline
- Governance decisions invalid
- Cost > 2x Azure baseline

**Rollback Steps**:
```bash
# Emergency rollback to Azure
export NEXUS_MODE=azure
export AZURE_MODE=enabled

# Restore Azure environment variables
source .env.azure.backup

# Restart services
systemctl restart nexus-bridge
systemctl restart nexus-twave

# Validate
nexusctl doctor
```

---

## Cost Analysis

### Azure Monthly Costs (Pre-Migration)
- Compute: $1,200
- Storage: $300
- Database: $400
- Bandwidth: $200
- Support: $150
- **Total: $2,250/month**

### Hybrid Monthly Costs (Post-Migration)
- Supabase: $25 (Pro plan)
- Zapier: $50-150 (usage-based)
- n8n: $0 (self-hosted)
- Model APIs: $300-800 (usage-based)
- Tailscale: $0 (personal tier)
- **Total: $375-975/month**

**Savings**: 60-85% reduction

---

## Timeline Summary

| Phase | Weeks | Key Deliverables |
|-------|-------|-----------------|
| Assessment | 1-2 | Dependency audit, service decommissioning |
| Foundation | 3-4 | Supabase setup, Tailscale networking |
| Core Migration | 5-6 | Bridge enhancement, model migration |
| Advanced Features | 7-8 | n8n integration, 3 Horseman roles |
| Data Migration | 9-10 | Data migration, integration testing |
| Cutover | 11-12 | Parallel operation, final cutover |

---

## Post-Migration Optimization

### Week 13-14: Performance Tuning

**Actions**:
- Optimize MCP tool filtering algorithms
- Fine-tune model routing based on cost/performance
- Implement caching for repeated operations
- Optimize Tailscale network routes

### Week 15-16: Feature Expansion

**Actions**:
- Add more specialist servers
- Integrate additional tool providers
- Implement advanced governance policies
- Add multi-cloud redundancy

---

## Success Criteria

### Technical Metrics
- [ ] All Azure dependencies removed
- [ ] Hybrid system performance ≥ Azure baseline
- [ ] Governance decisions consistent
- [ ] Data integrity preserved
- [ ] Cost reduction ≥ 50%

### Operational Metrics
- [ ] Team trained on new architecture
- [ ] Documentation complete
- [ ] Monitoring and alerting operational
- [ ] Backup and restore procedures validated

---

## Conclusion

This migration strategy provides a comprehensive path from Azure-dependent architecture to a resilient, cost-effective hybrid system. The phased approach minimizes risk while delivering immediate cost savings and long-term architectural improvements.

**Next Steps**:
1. Review and approve this migration strategy
2. Begin Phase 1 (Assessment & Planning)
3. Set up parallel development environment
4. Initialize Supabase project
5. Begin Tailscale network testing

This migration positions NEXUS OS for sustainable growth while eliminating the risks associated with single-cloud dependencies.