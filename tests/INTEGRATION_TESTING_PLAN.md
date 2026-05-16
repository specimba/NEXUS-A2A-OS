# NEXUS OS Integration Testing Plan

**Date:** 2026-05-15  
**Scope:** Comprehensive testing for A2A/Zapier MCP, ERNIE MCP governance, Tailscale networking, and TWAVE v2.0  
**Status:** Planning Phase

---

## Test Architecture Overview

### Test Pyramid

```
                    /\
                   /  \
                  / E2E \         ← 15% (End-to-End integration)
                 /______\
                /        \
               / Integration \    ← 35% (Component integration)
              /______________\
             /                \
            /    Unit Tests    \   ← 50% (Individual component tests)
           /__________________\
```

### Test Coverage Targets

| Component | Unit Tests | Integration Tests | E2E Tests | Total |
|-----------|-------------|-------------------|------------|-------|
| MCP Server | 80% | 70% | 50% | 70% |
| Zapier Adapter | 75% | 65% | 40% | 65% |
| ERNIE Governance | 85% | 75% | 60% | 75% |
| Tailscale Networking | 70% | 60% | 50% | 65% |
| TWAVE Calibration | 70% | 50% | 40% | 60% |
| Bridge Integration | 80% | 70% | 60% | 75% |
| **Overall Target** | **77%** | **65%** | **50%** | **68%** |

---

## Part 1: MCP Server Testing

### 1.1 Unit Tests

**File**: `tests/mcp/test_server.py`

```python
import pytest
from nexus_os.bridge.mcp_server import (
    NexusMCPServer, 
    MCPTool, 
    MCPContext
)

class TestMCPToolRegistration:
    """Test MCP tool registration and management"""
    
    def test_register_tool(self):
        """Test tool registration adds tool to registry"""
        server = NexusMCPServer(governor=None, token_guard=None, vault=None)
        tool = MCPTool(
            name="test_tool",
            description="Test tool",
            input_schema={"type": "object"},
            handler=lambda x: {"result": "ok"},
            category="test"
        )
        server.register_tool(tool)
        assert "test_tool" in server._tools
    
    def test_duplicate_tool_override(self):
        """Test that duplicate tool names override existing"""
        server = NexusMCPServer(governor=None, token_guard=None, vault=None)
        tool1 = MCPTool(
            name="test_tool", description="First", input_schema={},
            handler=lambda x: {"result": "1"}, category="test"
        )
        tool2 = MCPTool(
            name="test_tool", description="Second", input_schema={},
            handler=lambda x: {"result": "2"}, category="test"
        )
        server.register_tool(tool1)
        server.register_tool(tool2)
        assert server._tools["test_tool"].description == "Second"


class TestToolDiscovery:
    """Test TSI-aware tool discovery"""
    
    def test_intent_classification(self):
        """Test intent classification from text"""
        context = MCPContext(
            agent_id="test-agent",
            project_id="test-project",
            trace_id="test-trace",
            intent="I need to fix a bug in the GitHub repository",
            capabilities=["coding", "github"],
            trust_score=0.9
        )
        server = NexusMCPServer(governor=None, token_guard=None, vault=None)
        tools = server.discover_tools(context)
        assert len(tools) > 0
        assert all(tool["category"] in ["code", "github"] for tool in tools)
    
    def test_tool_count_limiting(self):
        """Test that tool count is limited to TSI threshold"""
        context = MCPContext(
            agent_id="test-agent",
            project_id="test-project",
            trace_id="test-trace",
            intent="general task",
            capabilities=["general"],
            trust_score=0.5
        )
        server = NexusMCPServer(governor=None, token_guard=None, vault=None)
        tools = server.discover_tools(context)
        assert len(tools) <= 16  # TSI threshold
    
    def test_trust_based_filtering(self):
        """Test that trust score affects tool availability"""
        # Low trust agent
        context_low = MCPContext(
            agent_id="low-trust-agent",
            project_id="test-project",
            trace_id="test-trace",
            intent="critical task",
            capabilities=["admin"],
            trust_score=0.3  # Low trust
        )
        
        # High trust agent
        context_high = MCPContext(
            agent_id="high-trust-agent",
            project_id="test-project",
            trace_id="test-trace",
            intent="critical task",
            capabilities=["admin"],
            trust_score=0.9  # High trust
        )
        
        server = NexusMCPServer(governor=None, token_guard=None, vault=None)
        
        # Register critical tool
        critical_tool = MCPTool(
            name="critical_tool",
            description="Critical action",
            input_schema={},
            handler=lambda x: {"result": "ok"},
            category="admin",
            trust_level="critical"
        )
        server.register_tool(critical_tool)
        
        tools_low = server.discover_tools(context_low)
        tools_high = server.discover_tools(context_high)
        
        # Low trust agent should not see critical tools
        assert not any(t["name"] == "critical_tool" for t in tools_low)
        # High trust agent should see critical tools
        assert any(t["name"] == "critical_tool" for t in tools_high)


class TestToolExecution:
    """Test tool execution with governance integration"""
    
    def test_kaiju_authorization(self):
        """Test that KAIJU authorization is checked"""
        # This test would require a mock governor
        # For now, test the authorization flow
        pass
    
    def test_token_guard_check(self):
        """Test that TokenGuard budget is checked"""
        # This test would require a mock token guard
        # For now, test the budget check flow
        pass
    
    def test_vap_audit_logging(self):
        """Test that all tool calls are logged to VAP"""
        # This test would require a mock vault
        # For now, test the logging flow
        pass
```

### 1.2 Integration Tests

**File**: `tests/integration/test_mcp_integration.py`

```python
import pytest
import httpx
from typing import Dict, Any

class TestMCPBridgeIntegration:
    """Test MCP integration with Bridge server"""
    
    @pytest.fixture
    def bridge_url(self):
        return "http://localhost:7352"
    
    def test_mcp_discover_endpoint(self, bridge_url):
        """Test MCP discover endpoint responds correctly"""
        response = httpx.post(
            f"{bridge_url}/mcp/discover",
            json={
                "intent": "code generation",
                "capabilities": ["coding", "github"],
                "trust_score": 0.8
            },
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)
    
    def test_mcp_call_endpoint(self, bridge_url):
        """Test MCP call endpoint executes tools"""
        response = httpx.post(
            f"{bridge_url}/mcp/call",
            json={
                "tool_name": "test_tool",
                "arguments": {"param1": "value1"},
                "intent": "test execution",
                "capabilities": ["test"],
                "trust_score": 0.9
            },
            timeout=10
        )
        assert response.status_code in [200, 401, 403]  # Success or auth failures
    
    def test_mcp_error_handling(self, bridge_url):
        """Test that MCP handles errors gracefully"""
        # Test invalid tool name
        response = httpx.post(
            f"{bridge_url}/mcp/call",
            json={
                "tool_name": "nonexistent_tool",
                "arguments": {},
                "intent": "test",
                "capabilities": [],
                "trust_score": 0.5
            },
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert not data.get("success", False)
```

---

## Part 2: Zapier MCP Adapter Testing

### 2.1 Unit Tests

**File**: `tests/mcp/test_zapier_adapter.py`

```python
import pytest
from nexus_os.bridge.zapier_mcp_adapter import ZapierMCPAdapter

class TestZapierActionDiscovery:
    """Test Zapier action discovery"""
    
    @pytest.fixture
    def zapier_adapter(self):
        return ZapierMCPAdapter(api_key="test-key", base_url="https://api.zapier.test")
    
    def test_intent_based_discovery(self, zapier_adapter):
        """Test that actions are discovered based on intent"""
        # This would require mocking Zapier API
        # For now, test the discovery logic
        pass
    
    def test_result_limiting(self, zapier_adapter):
        """Test that discovery respects result limits"""
        # Test that limit parameter is respected
        pass
    
    def test_cost_estimation(self, zapier_adapter):
        """Test that action costs are estimated correctly"""
        # Test cost estimation logic
        assert zapier_adapter._estimate_cost({"type": "standard"}) == 0.001
        assert zapier_adapter._estimate_cost({"type": "premium"}) == 0.005
```

### 2.2 Integration Tests

**File**: `tests/integration/test_zapier_integration.py`

```python
import pytest
import os

class TestZapierLiveIntegration:
    """Test live Zapier integration (requires API key)"""
    
    @pytest.fixture
    def zapier_api_key(self):
        return os.environ.get("ZAPIER_API_KEY")
    
    @pytest.mark.skipif(not os.environ.get("ZAPIER_API_KEY"), reason="No Zapier API key")
    def test_real_action_discovery(self, zapier_api_key):
        """Test real Zapier action discovery"""
        adapter = ZapierMCPAdapter(api_key=zapier_api_key)
        
        # Discover email actions
        actions = adapter.discover_actions("send email", limit=5)
        assert len(actions) <= 5
        assert all("name" in action for action in actions)
    
    @pytest.mark.skipif(not os.environ.get("ZAPIER_API_KEY"), reason="No Zapier API key")
    def test_real_action_execution(self, zapier_api_key):
        """Test real Zapier action execution"""
        adapter = ZapierMCPAdapter(api_key=zapier_api_key)
        
        # Execute a simple action (would need real parameters)
        # This test should use a test Zapier account to avoid side effects
        pass
```

---

## Part 3: ERNIE MCP Governance Testing

### 3.1 Unit Tests

**File**: `tests/ernie/test_edge_functions.py`

```python
import pytest

class TestProposalCreation:
    """Test proposal creation edge function"""
    
    def test_proposal_validation(self):
        """Test that proposal structure is validated"""
        # Test validation logic
        valid_proposal = {
            "proposal_id": "test-001",
            "proposer_id": "claude-nexus-v1",
            "proposed_action": {"type": "test"},
            "description": "Test proposal",
            "governance_level": "standard",
            "trace_id": "test-trace"
        }
        # Test that validation passes
        assert True  # Placeholder
    
    def test_trust_threshold_check(self):
        """Test that trust thresholds are enforced"""
        # Test that low-trust agents cannot create critical proposals
        pass
    
    def test_voting_period_calculation(self):
        """Test that voting periods are set correctly"""
        # Test voting period calculation based on governance level
        pass


class TestProposalExecution:
    """Test proposal execution edge function"""
    
    def test_consensus_calculation(self):
        """Test that consensus is calculated correctly"""
        # Test weighted voting consensus logic
        pass
    
    def test_execution_action(self):
        """Test that proposals are executed correctly"""
        # Test action execution logic
        pass
    
    def test_trust_score_adjustment(self):
        """Test that trust scores are adjusted correctly"""
        # Test trust score delta application
        pass


class TestAnomalyDetection:
    """Test anomaly detection edge function"""
    
    def test_spam_detection(self):
        """Test that spam attacks are detected"""
        # Test spam detection logic
        pass
    
    def test_trust_collapse_detection(self):
        """Test that trust collapse is detected"""
        # Test trust collapse detection logic
        pass
    
    def test_network_partition_detection(self):
        """Test that network partitions are detected"""
        # Test network partition detection logic
        pass
```

### 3.2 Integration Tests

**File**: `tests/integration/test_ernie_integration.py`

```python
import pytest
import httpx
from typing import Dict, Any

class TestERNIEGovernanceFlow:
    """Test complete ERNIE governance flow"""
    
    @pytest.fixture
    def supabase_url(self):
        return os.environ.get("SUPABASE_URL")
    
    @pytest.fixture
    def supabase_key(self):
        return os.environ.get("SUPABASE_ANON_KEY")
    
    def test_complete_proposal_lifecycle(self, supabase_url, supabase_key):
        """Test complete proposal lifecycle from creation to execution"""
        # 1. Create proposal
        # 2. Add votes
        # 3. Check consensus
        # 4. Execute proposal
        # 5. Verify trust score changes
        pass
    
    def test_edge_function_triggering(self, supabase_url, supabase_key):
        """Test that edge functions are triggered correctly"""
        # Test edge function HTTP triggers
        pass
    
    def test_database_consistency(self, supabase_url, supabase_key):
        """Test that database remains consistent during operations"""
        # Test database consistency checks
        pass
```

---

## Part 4: Tailscale Networking Testing

### 4.1 Unit Tests

**File**: `tests/networking/test_tailscale_manager.py`

```python
import pytest
from nexus_os.networking.tailscale_integrator import (
    TailscaleManager,
    TailscaleNetworkState,
    NexusTailscaleIntegrator
)

class TestTailscaleManager:
    """Test Tailscale manager functionality"""
    
    @pytest.fixture
    def tailscale_manager(self):
        # This would require actual Tailscale installation
        # For CI, use mock
        pass
    
    def test_status_checking(self, tailscale_manager):
        """Test that Tailscale status is retrieved correctly"""
        # Test status checking logic
        pass
    
    def test_peer_discovery(self, tailscale_manager):
        """Test that peers are discovered correctly"""
        # Test peer discovery logic
        pass
    
    def test_connect_disconnect(self, tailscale_manager):
        """Test connect/disconnect functionality"""
        # Test connect/disconnect logic
        pass


class TestNexusTailscaleIntegrator:
    """Test NEXUS-Tailscale integration"""
    
    def test_peer_caching(self):
        """Test that peer information is cached correctly"""
        # Test caching logic
        pass
    
    def test_channel_establishment(self):
        """Test that secure channels are established correctly"""
        # Test channel establishment logic
        pass
    
    def test_network_health_calculation(self):
        """Test that network health is calculated correctly"""
        # Test health calculation logic
        pass
```

### 4.2 Integration Tests

**File**: `tests/integration/test_tailscale_integration.py`

```python
import pytest

class TestTailscaleNetworkConnectivity:
    """Test Tailscale network connectivity"""
    
    @pytest.fixture
    def tailscale_auth_key(self):
        return os.environ.get("TAILSCALE_AUTH_KEY")
    
    @pytest.mark.skipif(not os.environ.get("TAILSCALE_AUTH_KEY"), reason="No Tailscale auth key")
    def test_real_network_connection(self, tailscale_auth_key):
        """Test real Tailscale network connection"""
        # Test actual Tailscale connection
        pass
    
    @pytest.mark.skipif(not os.environ.get("TAILSCALE_AUTH_KEY"), reason="No Tailscale auth key")
    def test_peer_ping_test(self, tailscale_auth_key):
        """Test peer ping functionality"""
        # Test ping between Tailscale nodes
        pass
    
    @pytest.mark.skipif(not os.environ.get("TAILSCALE_AUTH_KEY"), reason="No Tailscale auth key")
    def test_docker_tailscale_integration(self, tailscale_auth_key):
        """Test Tailscale integration with Docker"""
        # Test Docker container with Tailscale
        pass
```

---

## Part 5: TWAVE v2.0 Calibration Testing

### 5.1 Unit Tests

**File**: `tests/twave/test_calibration.py`

```python
import pytest
import numpy as np
from benchmarks.calibrate_twave_v2_landau_ginzburg import (
    TWAVECalibrationEngine,
    CalibrationConfig,
    TokenDynamics
)

class TestThermodynamicCalculations:
    """Test thermodynamic calculations"""
    
    def test_entropy_calculation(self):
        """Test that entropy is calculated correctly"""
        # Test entropy calculation from logits
        pass
    
    def test_free_energy_calculation(self):
        """Test that free energy is calculated correctly"""
        # Test F = -T * S calculation
        T = 0.7
        S = 2.5
        F_expected = -T * S
        assert F_expected == -1.75
    
    def test_healing_length_estimation(self):
        """Test that healing length is estimated correctly"""
        # Test healing length estimation
        pass


class TestCalibrationDataGeneration:
    """Test calibration data generation"""
    
    def test_temperature_sweep(self):
        """Test that temperature sweep generates correct data"""
        # Test temperature sweep logic
        pass
    
    def test_token_dynamics_extraction(self):
        """Test that token dynamics are extracted correctly"""
        # Test token dynamics extraction
        pass
    
    def test_hallucination_detection(self):
        """Test that hallucinations are detected correctly"""
        # Test hallucination detection logic
        pass
```

### 5.2 Integration Tests

**File**: `tests/integration/test_twave_integration.py`

```python
import pytest

class TestTWAVECalibrationIntegration:
    """Test TWAVE v2.0 calibration integration"""
    
    @pytest.fixture
    def calibration_config(self):
        return CalibrationConfig(
            model_name="gpt2",
            num_prompts=5,  # Small number for testing
            num_temperature_points=5  # Reduced for testing
        )
    
    def test_calibration_sweep(self, calibration_config):
        """Test complete calibration sweep"""
        # Test actual calibration with small dataset
        pass
    
    def test_parameter_fitting(self, calibration_config):
        """Test that thermodynamic parameters are fitted correctly"""
        # Test parameter fitting logic
        pass
    
    def test_calibration_quality(self, calibration_config):
        """Test that calibration quality is evaluated correctly"""
        # Test quality evaluation logic
        pass
```

---

## Part 6: End-to-End Integration Testing

### 6.1 E2E Test Scenarios

**File**: `tests/e2e/test_complete_scenarios.py`

```python
import pytest
import httpx
import time

class TestCompleteGovernanceFlow:
    """Test complete governance flow with all components"""
    
    def test_proposal_to_execution_with_governance(self):
        """Test complete flow: proposal → vote → execute → trust update"""
        # 1. Create proposal via Bridge MCP
        # 2. Add votes via governance
        # 3. Execute proposal via ERNIE
        # 4. Verify trust score updates
        # 5. Verify audit trail
        pass
    
    def test_multi_agent_orchestration_via_n8n(self):
        """Test multi-agent orchestration through n8n"""
        # 1. Trigger n8n workflow
        # 2. Route to appropriate agents
        # 3. Execute tasks
        # 4. Aggregate results
        # 5. Log to governance
        pass
    
    def test_zapier_tool_execution_with_governance(self):
        """Test Zapier tool execution with full governance"""
        # 1. Request Zapier tool via MCP
        # 2. KAIJU authorization
        # 3. TokenGuard budget check
        # 4. Execute Zapier action
        # 5. Log to VAP audit trail
        pass


class TestDisasterRecoveryScenarios:
    """Test disaster recovery scenarios"""
    
    def test_supabase_failover(self):
        """Test behavior when Supabase is unavailable"""
        # 1. Simulate Supabase outage
        # 2. Verify graceful degradation
        # 3. Verify data caching works
        # 4. Verify recovery
        pass
    
    def test_tailscale_partition_recovery(self):
        """Test recovery from Tailscale network partition"""
        # 1. Simulate network partition
        # 2. Verify fallback mechanisms
        # 3. Verify recovery when network returns
        pass
    
    def test_zapier_rate_limit_handling(self):
        """Test handling of Zapier rate limits"""
        # 1. Trigger Zapier rate limit
        # 2. Verify exponential backoff
        # 3. Verify queue management
        # 4. Verify retry logic
        pass
```

---

## Part 7: Performance Testing

### 7.1 Load Testing

**File**: `tests/load/test_performance.py`

```python
import pytest
import asyncio
import httpx
import statistics

class TestMCPPerformance:
    """Test MCP server performance under load"""
    
    async def test_concurrent_tool_discovery(self):
        """Test tool discovery with concurrent requests"""
        async with httpx.AsyncClient() as client:
            tasks = [
                client.post(
                    "http://localhost:7352/mcp/discover",
                    json={"intent": "test", "capabilities": ["test"], "trust_score": 0.8}
                )
                for _ in range(100)
            ]
            responses = await asyncio.gather(*tasks)
            
        assert all(r.status_code == 200 for r in responses)
        # Verify latency < 100ms
        latencies = [r.elapsed.total_seconds() for r in responses]
        assert statistics.mean(latencies) < 0.1
    
    async def test_tool_execution_throughput(self):
        """Test tool execution throughput"""
        # Test that server can handle N tool calls per second
        pass


class TestGovernancePerformance:
    """Test governance system performance"""
    
    def test_proposal_processing_rate(self):
        """Test proposal processing rate"""
        # Test that governance can handle N proposals per minute
        pass
    
    def test_trust_computation_performance(self):
        """Test trust delta computation performance"""
        # Test that trust computation completes in reasonable time
        pass
```

---

## Test Execution Plan

### Continuous Integration

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov
      - name: Run unit tests
        run: pytest tests/mcp/ tests/ernie/ tests/networking/ tests/twave/ -v
  
  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
      supabase:
        image: supabase/supabase:latest
    steps:
      - uses: actions/checkout@v2
      - name: Run integration tests
        run: pytest tests/integration/ -v
  
  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    steps:
      - uses: actions/checkout@v2
      - name: Run E2E tests
        run: pytest tests/e2e/ -v
```

### Local Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific component tests
pytest tests/mcp/ -v
pytest tests/ernie/ -v
pytest tests/networking/ -v

# Run with coverage
pytest tests/ --cov=nexus_os --cov-report=html

# Run integration tests only
pytest tests/integration/ -v

# Run E2E tests only
pytest tests/e2e/ -v

# Run performance tests
pytest tests/load/ -v
```

---

## Test Data Management

### Test Datasets

**Location**: `tests/data/`

**Datasets**:
- `test_prompts.json` - Sample prompts for calibration testing
- `test_proposals.json` - Sample proposal data
- `test_anomalies.json` - Sample anomaly patterns
- `test_network_config.json` - Sample network configurations

### Test Fixtures

**Location**: `tests/fixtures/`

**Fixtures**:
- `mock_governor.py` - Mock governor for testing
- `mock_token_guard.py` - Mock token guard for testing
- `mock_vault.py` - Mock vault for testing
- `zapier_responses.json` - Mock Zapier API responses

---

## Success Criteria

### Test Coverage Targets

- **Unit Test Coverage**: ≥ 77%
- **Integration Test Coverage**: ≥ 65%
- **E2E Test Coverage**: ≥ 50%
- **Overall Coverage**: ≥ 68%

### Performance Targets

- **MCP Tool Discovery Latency**: < 50ms
- **Tool Execution Latency**: < 200ms
- **Proposal Creation Latency**: < 100ms
- **Trust Computation Latency**: < 500ms
- **Anomaly Detection Latency**: < 200ms

### Reliability Targets

- **Test Success Rate**: ≥ 95%
- **Flaky Test Rate**: < 5%
- **Test Execution Time**: < 10 minutes for full suite

---

## Test Reporting

### Automated Reporting

Test results will be automatically reported to:
- **GitHub Actions**: PR comments with test results
- **Supabase Dashboard**: Test metrics visualization
- **Slack**: Daily test summaries to #nexus-testing

### Manual Reporting

Weekly test reports will include:
- Test coverage trends
- Performance metrics
- Flaky test analysis
- Blocked tests status
- Recommendations for improvement

---

## Next Steps

1. **Implement unit tests** for all new components
2. **Set up test fixtures** and mocks
3. **Configure CI/CD pipeline** for automated testing
4. **Create test datasets** for integration testing
5. **Implement load testing** scenarios
6. **Establish test reporting** and monitoring

This testing plan ensures that all new components are thoroughly validated before production deployment, providing confidence in the hybrid architecture migration.