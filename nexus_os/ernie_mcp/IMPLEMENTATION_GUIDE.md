# ERNIE MCP Governance Platform - Implementation Guide

**Version:** 1.0  
**Date:** 2026-05-15  
**Purpose:** Complete implementation guide for the ERNIE MCP governance platform on NEXUS OS

---

## Overview

The ERNIE MCP governance platform provides a complete proposal governance, trust scoring, and anomaly detection system for NEXUS OS. It uses Supabase for the database and edge functions for serverless logic.

### Key Components

1. **Supabase Database Schema** - Complete governance data model
2. **Edge Functions** - Serverless functions for governance logic
3. **Trust Scoring System** - Bayesian trust engine with automatic adjustments
4. **Anomaly Detection** - Real-time monitoring and alerts
5. **Proposal Governance** - Weighted voting with consensus thresholds

---

## Prerequisites

### Required Accounts

- **Supabase Account** (Free tier sufficient for development)
- **Confluent Cloud** (Optional - for Kafka integration)
- **Docker Desktop** (for local development)

### Required Environment Variables

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Kafka (Optional)
KAFKA_PRODUCER_URL=https://pkc-xxxx.us-west1.gcp.confluent.cloud/v1/produce
KAFKA_API_KEY=your-confluent-api-key

# Tailscale (Optional, for networking)
TAILSCALE_AUTHKEY=tskey-xxxxxxxxxxxxxxxx
```

---

## Quick Start (48-Hour Implementation Plan)

### Hour 0-2: Supabase Setup

#### 1. Create Supabase Project

```bash
# Install Supabase CLI
npm install -g supabase

# Login to Supabase
supabase login

# Initialize project
supabase init

# Link to existing project
supabase link --project-ref your-project-id
```

#### 2. Apply Database Schema

```bash
# Navigate to ERNIE MCP directory
cd nexus_os/ernie_mcp

# Apply the schema
supabase db push

# Verify tables created
supabase db reset
```

#### 3. Seed Initial Data

The schema includes initial agent data. You can customize this:

```sql
-- Add your own agents
INSERT INTO agents (id, name, trust_score, capabilities, status) VALUES
    ('your-agent-id', 'Your Agent Name', 80.0, ARRAY['capability1', 'capability2'], 'active');
```

---

### Hour 2-4: Edge Functions Deployment

#### 1. Deploy Individual Functions

```bash
# Deploy proposal creation handler
supabase functions deploy on_proposal_created

# Deploy proposal executor
supabase functions deploy execute_approved_proposal

# Deploy trust delta computation (scheduled)
supabase functions deploy compute_trust_delta --schedule "*/5 * * * *"

# Deploy anomaly detection (scheduled)
supabase functions deploy detect_anomalies --schedule "*/30 * * * *"
```

#### 2. Set Environment Variables for Functions

```bash
# Set Supabase environment variables for edge functions
supabase secrets set SUPABASE_URL=$SUPABASE_URL
supabase secrets set SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY

# Set Kafka variables (if using)
supabase secrets set KAFKA_PRODUCER_URL=$KAFKA_PRODUCER_URL
supabase secrets set KAFKA_API_KEY=$KAFKA_API_KEY
```

---

### Hour 4-6: Testing Governance Flow

#### 1. Test Proposal Creation

```bash
# Test proposal creation edge function
curl -i --location --request POST 'https://your-project.supabase.co/functions/v1/on_proposal_created' \
  --header 'Authorization: Bearer YOUR_ANON_KEY' \
  --header 'Content-Type: application/json' \
  --data '{
    "proposal_id": "test-proposal-001",
    "proposer_id": "claude-nexus-v1",
    "proposed_action": {
      "type": "configuration",
      "target": "system",
      "parameters": {"setting": "value"}
    },
    "description": "Test proposal for governance",
    "governance_level": "standard",
    "trace_id": "trace-001"
  }'
```

#### 2. Test Proposal Execution

```bash
# Test proposal execution
curl -i --location --request POST 'https://your-project.supabase.co/functions/v1/execute_approved_proposal' \
  --header 'Authorization: Bearer YOUR_ANON_KEY' \
  --header 'Content-Type: application/json' \
  --data '{
    "proposal_id": "test-proposal-001"
  }'
```

#### 3. Verify Database State

```bash
# Check proposals table
supabase db execute "SELECT * FROM proposals WHERE id = 'test-proposal-001';"

# Check trust events
supabase db execute "SELECT * FROM trust_events ORDER BY created_at DESC LIMIT 5;"
```

---

### Hour 6-8: Integration Testing

#### 1. Complete Governance Flow Test

```python
# Python test script
import requests
import time

# Base URL
BASE_URL = "https://your-project.supabase.co"
ANON_KEY = "your-anon-key"
HEADERS = {
    "Authorization": f"Bearer {ANON_KEY}",
    "Content-Type": "application/json"
}

def test_governance_flow():
    # 1. Create proposal
    proposal_data = {
        "proposal_id": "test-governance-001",
        "proposer_id": "claude-nexus-v1",
        "proposed_action": {
            "type": "code",
            "target": "test-target",
            "parameters": {"param1": "value1"}
        },
        "description": "Complete governance flow test",
        "governance_level": "standard",
        "trace_id": "governance-test-001"
    }
    
    response = requests.post(
        f"{BASE_URL}/functions/v1/on_proposal_created",
        headers=HEADERS,
        json=proposal_data
    )
    print(f"Proposal creation: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # 2. Simulate voting (direct database insert for testing)
    # In production, voting would go through a separate endpoint
    
    # 3. Execute proposal (skip consensus check for testing)
    execution_data = {
        "proposal_id": "test-governance-001",
        "force_execute": True
    }
    
    response = requests.post(
        f"{BASE_URL}/functions/v1/execute_approved_proposal",
        headers=HEADERS,
        json=execution_data
    )
    print(f"Proposal execution: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # 4. Check trust score changes
    time.sleep(5)  # Wait for trust delta computation
    # Query trust events to verify

if __name__ == "__main__":
    test_governance_flow()
```

#### 2. Load Testing

```python
# Load test script
import requests
import concurrent.futures
import time

def create_proposal(i):
    try:
        response = requests.post(
            f"{BASE_URL}/functions/v1/on_proposal_created",
            headers=HEADERS,
            json={
                "proposal_id": f"load-test-{i}",
                "proposer_id": f"agent-{i % 3}",
                "proposed_action": {"type": "test", "target": f"target-{i}"},
                "description": f"Load test proposal {i}",
                "governance_level": "standard",
                "trace_id": f"trace-{i}"
            },
            timeout=10
        )
        return response.status_code
    except:
        return None

def run_load_test(proposal_count=100):
    start = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_proposal, i) for i in range(proposal_count)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    elapsed = time.time() - start
    success = len([r for r in results if r == 200])
    
    print(f"Load test: {success}/{proposal_count} successful in {elapsed:.1f}s")
    print(f"Throughput: {success/elapsed:.1f} proposals/second")

if __name__ == "__main__":
    run_load_test(100)
```

---

### Hour 8-12: Advanced Configuration

#### 1. Configure Governance Thresholds

```sql
-- Adjust consensus thresholds per governance level
-- These are currently in the edge function logic, but can be made configurable

-- Update edge function or add configuration table
CREATE TABLE IF NOT EXISTS governance_config (
    id TEXT PRIMARY KEY DEFAULT 'default',
    consensus_threshold_standard REAL DEFAULT 0.50,
    consensus_threshold_elevated REAL DEFAULT 0.66,
    consensus_threshold_critical REAL DEFAULT 0.75,
    trust_threshold_standard REAL DEFAULT 0.0,
    trust_threshold_elevated REAL DEFAULT 50.0,
    trust_threshold_critical REAL DEFAULT 75.0,
    voting_period_standard_hours INTEGER DEFAULT 24,
    voting_period_elevated_hours INTEGER DEFAULT 48,
    voting_period_critical_hours INTEGER DEFAULT 72,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO governance_config VALUES (
    'default',
    0.50, 0.66, 0.75,
    0.0, 50.0, 75.0,
    24, 48, 72,
    CURRENT_TIMESTAMP
);
```

#### 2. Set Up Kafka Integration

```bash
# Install Kafka client libraries
npm install @confluentinc/kafka-node

# Update edge function to use configuration table
# (Modify edge functions to read from governance_config table)
```

#### 3. Configure Anomaly Detection Thresholds

```sql
-- Add anomaly detection configuration
CREATE TABLE IF NOT EXISTS anomaly_config (
    id TEXT PRIMARY KEY DEFAULT 'default',
    spam_threshold_per_minute INTEGER DEFAULT 10,
    trust_collapse_threshold_hourly REAL DEFAULT -10.0,
    network_partition_threshold REAL DEFAULT 0.33,
    voting_anomaly_threshold_5min INTEGER DEFAULT 20,
    proposal_anomaly_threshold_hourly INTEGER DEFAULT 5,
    behavioral_negative_ratio_threshold REAL DEFAULT 0.70,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO anomaly_config VALUES (
    'default',
    10, -10.0, 0.33, 20, 5, 0.70,
    CURRENT_TIMESTAMP
);
```

---

### Hour 12-18: Disaster Recovery Testing

#### 1. Test Disaster Scenarios

```python
# Disaster recovery test script
import requests
import time

def test_scenario_1_database_failure():
    """Test: Simulate database connectivity loss"""
    print("Scenario 1: Database connectivity loss")
    # This would require database admin access
    # Test edge function behavior when database is unavailable
    
def test_scenario_2_kafka_failure():
    """Test: Kafka connectivity loss"""
    print("Scenario 2: Kafka connectivity loss")
    # Temporarily disable Kafka endpoint
    # Verify edge functions still work (with logging)
    
def test_scenario_3_high_load():
    """Test: System under high load"""
    print("Scenario 3: High load test")
    # Run load test with 1000+ proposals per minute
    
def test_scenario_4_agent_compromise():
    """Test: Simulated agent compromise"""
    print("Scenario 4: Agent compromise")
    # Set agent trust to 0
    # Verify proposals are rejected
    
def test_scenario_5_network_partition():
    """Test: Network partition simulation"""
    print("Scenario 5: Network partition")
    # Create proposal with no voting participation
    # Verify anomaly detection triggers

if __name__ == "__main__":
    test_scenario_1_database_failure()
    test_scenario_2_kafka_failure()
    test_scenario_3_high_load()
    test_scenario_4_agent_compromise()
    test_scenario_5_network_partition()
```

---

### Hour 18-24: Security Hardening

#### 1. Enable Row Level Security (RLS)

The schema includes RLS policies. Customize them for your auth system:

```sql
-- Example: Allow service role full access
CREATE POLICY "Service role full access" ON proposals
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Example: Allow agents to read their own proposals
CREATE POLICY "Agents can read own proposals" ON proposals
    FOR SELECT USING (auth.jwt() ->> 'agent_id' = proposer_id);
```

#### 2. Enable Database Encryption

```bash
# Supabase automatically encrypts data at rest
# Verify encryption is enabled in Supabase dashboard
```

#### 3. Set Up Audit Logging

```sql
-- Audit logging is already in the governance_log table
-- Create a view for easy audit review
CREATE OR REPLACE VIEW v_recent_governance_actions AS
SELECT 
    gl.id,
    gl.actor_id,
    a.name AS actor_name,
    gl.action,
    gl.resource_id,
    gl.decision,
    gl.reason,
    gl.trace_id,
    gl.created_at
FROM governance_log gl
JOIN agents a ON gl.actor_id = a.id
ORDER BY gl.created_at DESC
LIMIT 100;
```

---

### Hour 24-48: Production Deployment

#### 1. Pre-Deployment Checklist

- [ ] All tests passing
- [ ] Disaster recovery scenarios tested
- [ ] Security hardening applied
- [ ] Monitoring and alerting configured
- [ ] Backup strategy in place
- [ ] Rollback plan documented
- [ ] Team trained on runbooks
- [ ] Documentation complete

#### 2. Production Deployment

```bash
# Deploy to production Supabase project
supabase link --project-ref your-production-project-id
supabase db push
supabase functions deploy

# Set production environment variables
supabase secrets set SUPABASE_URL=$PROD_SUPABASE_URL
supabase secrets set SUPABASE_SERVICE_KEY=$PROD_SUPABASE_SERVICE_KEY
supabase secrets set KAFKA_PRODUCER_URL=$PROD_KAFKA_URL
supabase secrets set KAFKA_API_KEY=$PROD_KAFKA_API_KEY
```

#### 3. Post-Deployment Verification

```bash
# Run health checks
curl -f https://your-production-project.supabase.co/functions/v1/detect_anomalies || exit 1

# Verify database state
supabase db execute "SELECT COUNT(*) FROM agents WHERE status = 'active';"
supabase db execute "SELECT COUNT(*) FROM proposals WHERE status = 'voting';"
```

---

## Monitoring and Operations

### Key Metrics to Monitor

1. **Proposal Flow Rate** - Proposals created per hour
2. **Consensus Rate** - Percentage of proposals reaching consensus
3. **Trust Score Distribution** - Distribution of agent trust scores
4. **Anomaly Rate** - Anomalies detected per hour
5. **Edge Function Latency** - Function execution times

### Monitoring Queries

```sql
-- Proposal flow rate (last hour)
SELECT 
    COUNT(*) AS proposals_last_hour,
    COUNT(*) FILTER (WHERE status = 'approved') AS approved,
    COUNT(*) FILTER (WHERE status = 'rejected') AS rejected
FROM proposals
WHERE created_at >= NOW() - INTERVAL '1 hour';

-- Trust score distribution
SELECT 
    CASE 
        WHEN trust_score >= 80 THEN 'high'
        WHEN trust_score >= 50 THEN 'medium'
        ELSE 'low'
    END AS trust_band,
    COUNT(*) AS agent_count
FROM agents
WHERE status = 'active'
GROUP BY trust_band;

-- Recent anomalies
SELECT 
    anomaly_type,
    severity,
    COUNT(*) AS count
FROM anomalies
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY anomaly_type, severity
ORDER BY count DESC;
```

---

## Troubleshooting

### Common Issues

#### 1. Edge Function Not Responding

```bash
# Check function logs
supabase functions logs on_proposal_created

# Check environment variables
supabase secrets list

# Redeploy function
supabase functions deploy on_proposal_created --no-verify-jwt
```

#### 2. Database Connection Issues

```bash
# Check database status
supabase status

# Test database connection
supabase db execute "SELECT 1;"
```

#### 3. Trust Scores Not Updating

```sql
-- Check if trust delta function is running
SELECT * FROM trust_events 
WHERE event_type = 'trust_delta_computed' 
ORDER BY created_at DESC 
LIMIT 5;

-- Manually trigger trust computation
CALL compute_agent_trust_delta('agent-id');
```

---

## Integration with NEXUS OS

### Connect to Existing Bridge Server

The ERNIE MCP platform can be integrated with the existing NEXUS OS Bridge server:

```python
# nexus_os/bridge/ernie_integration.py
"""
ERNIE MCP integration for NEXUS OS Bridge
"""

import httpx
from typing import Dict, Any, Optional

class ErnestMCPClient:
    """Client for interacting with ERNIE MCP governance platform"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    async def create_proposal(
        self,
        proposer_id: str,
        proposed_action: Dict[str, Any],
        description: str,
        governance_level: str = "standard",
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a governance proposal"""
        proposal_id = f"proposal-{uuid.uuid4().hex[:12]}"
        
        response = await self.client.post(
            f"{self.supabase_url}/functions/v1/on_proposal_created",
            json={
                "proposal_id": proposal_id,
                "proposer_id": proposer_id,
                "proposed_action": proposed_action,
                "description": description,
                "governance_level": governance_level,
                "trace_id": trace_id or f"trace-{uuid.uuid4().hex[:8]}"
            }
        )
        
        response.raise_for_status()
        return response.json()
    
    async def check_proposal_status(self, proposal_id: str) -> Dict[str, Any]:
        """Check the status of a proposal"""
        response = await self.client.get(
            f"{self.supabase_url}/rest/v1/proposals?id=eq.{proposal_id}",
            headers=self.client.headers
        )
        
        response.raise_for_status()
        return response.json()[0] if response.json() else {}
    
    async def get_agent_trust_score(self, agent_id: str) -> float:
        """Get the current trust score for an agent"""
        response = await self.client.get(
            f"{self.supabase_url}/rest/v1/agents?id=eq.{agent_id}&select=trust_score",
            headers=self.client.headers
        )
        
        response.raise_for_status()
        data = response.json()
        return data[0]['trust_score'] if data else 0.0
```

---

## Next Steps

1. **Complete Tailscale integration** (next task in this implementation)
2. **Build dataset calibration script** (for TWAVE v2.0)
3. **Complete migration strategy documentation**
4. **Create comprehensive testing plan**
5. **Generate deployment runbooks**

This implementation guide provides a complete 48-hour path from zero to production-ready governance platform for NEXUS OS.