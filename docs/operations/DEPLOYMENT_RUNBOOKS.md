---
id: NODE-MIG-DEPLOYMENT_RUNBOOKS
authority_scope: experimental
origin_sha256: 4611f71e6fc93668dba1850d76a66afd364d35739a4b83c33c274d2c905cff24
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-C3A8ED
---
# NEXUS OS Deployment Runbooks

**Date:** 2026-05-15  
**Version:** 1.0  
 **Scope:** Deployment and operational procedures for hybrid A2A/Zapier/n8n architecture

---

## Table of Contents

1. [Quick Start Deployment](#quick-start-deployment)
2. [Component Deployment Guides](#component-deployment-guides)
3. [Operational Procedures](#operational-procedures)
4. [Troubleshooting Runbooks](#troubleshooting-runbooks)
5. [Maintenance Procedures](#maintenance-procedures)
6. [Emergency Procedures](#emergency-procedures)

---

## Quick Start Deployment

### Prerequisites

- Docker Desktop (latest)
- Supabase account (Free tier sufficient)
- Zapier account (Free tier sufficient)
- Tailscale account (Free tier sufficient)
- 8GB RAM minimum
- Python 3.10+
- Node.js 18+ (for n8n)

### Environment Setup

```bash
# Clone repository
git clone https://github.com/specimba/nexus-alpha
cd nexus-alpha

# Set up Python environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
source venv/Scripts/activate  # Windows

pip install -e .
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
# Required variables:
# SUPABASE_URL=your-project.supabase.co
# SUPABASE_ANON_KEY=your-anon-key
# SUPABASE_SERVICE_KEY=your-service-key
# TAILSCALE_AUTHKEY=tskey-xxxxx
# ZAPIER_API_KEY=your-zapier-key

# Optional variables:
# OPENAI_API_KEY=your-openai-key
# ANTHROPIC_API_KEY=your-anthropic-key
# DEEPSEEK_API_KEY=your-deepseek-key
```

### Database Setup

```bash
# Deploy Supabase schema
cd nexus_os/ernie_mcp
supabase db push

# Verify tables created
supabase db execute "SELECT COUNT(*) FROM agents;"
```

### Core Services Deployment

```bash
# Start Tailscale networking
cd nexus_os/networking/tailscale
docker-compose -f docker-compose.tailscale.yml up -d

# Start NEXUS Bridge with MCP
docker-compose -f docker-compose.nexus.yml up -d

# Start n8n orchestrator
docker-compose -f docker-compose.n8n.yml up -d
```

### Verification

```bash
# Health check
nexusctl doctor

# Component status
nexusctl status

# Test MCP integration
curl http://localhost:7352/mcp/discover \
  -H "Content-Type: application/json" \
  -d '{"intent": "test", "capabilities": ["test"], "trust_score": 0.8}'
```

---

## Component Deployment Guides

### Guide 1: ERNIE MCP Governance Platform

#### Deployment Steps

1. **Deploy Supabase Schema**
```bash
cd nexus_os/ernie_mcp
supabase db push
```

2. **Deploy Edge Functions**
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

3. **Configure Environment Variables**
```bash
# Set Supabase environment for edge functions
supabase secrets set SUPABASE_URL=$SUPABASE_URL
supabase secrets set SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY

# Set Kafka variables (if using)
supabase secrets set KAFKA_PRODUCER_URL=$KAFKA_PRODUCER_URL
supabase secrets set KAFKA_API_KEY=$KAFKA_API_KEY
```

#### Verification

```bash
# Test proposal creation
curl -X POST https://your-project.supabase.co/functions/v1/on_proposal_created \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_id": "test-proposal-001",
    "proposer_id": "claude-nexus-v1",
    "proposed_action": {"type": "test"},
    "description": "Test proposal",
    "governance_level": "standard",
    "trace_id": "test-trace-001"
  }'

# Check database
supabase db execute "SELECT * FROM proposals WHERE proposal_id = 'test-proposal-001';"
```

### Guide 2: Tailscale Networking

#### Deployment Steps

1. **Get Tailscale Auth Key**
```bash
# Navigate to https://login.tailscale.com/admin/settings/keys
# Generate auth key with "Ephemeral" unchecked (for reusable key)
# Copy auth key
```

2. **Deploy Tailscale Container**
```bash
cd nexus_os/networking/tailscale

# Build image
docker build -f Dockerfile.tailscale -t nexus-tailscale:latest .

# Run container
docker run -d --name nexus-tailscale \
  --cap-add=NET_ADMIN \
  --device=/dev/net/tun:/dev/net/tun \
  -e TAILSCALE_AUTHKEY=$TAILSCALE_AUTHKEY \
  -e AGENT_ID=nexus-networking-01 \
  -e NEXUS_HOSTNAME=nexus-networking \
  nexus-tailscale:latest
```

3. **Verify Connection**
```bash
# Check Tailscale status
docker exec nexus-tailscale tailscale status

# Check logs
docker logs nexus-tailscale
```

#### Troubleshooting

**Issue**: Tailscale won't connect
```bash
# Check if device is already registered
docker exec nexus-tailscale tailscale status

# Force re-authentication
docker exec nexus-tailscale tailscale up --authkey=$TAILSCALE_AUTHKEY --reset
```

**Issue**: /dev/net/tun permission denied
```bash
# Add device mapping
docker run --device=/dev/net/tun:/dev/net/tun ...

# On Windows, ensure WSL2 is running and Docker Desktop has WSL2 integration enabled
```

### Guide 3: MCP Server Integration

#### Deployment Steps

1. **Update Bridge Server Configuration**
```python
# In nexus_os/bridge/server.py
class BridgeServer:
    def __init__(self, ..., enable_mcp=True, zapier_api_key=None):
        # MCP initialization will be handled automatically
```

2. **Restart Bridge Server**
```bash
# If running via Docker
docker restart nexus-bridge

# If running via systemd
systemctl restart nexus-bridge

# If running directly
# Stop and restart the process
```

3. **Test MCP Endpoints**
```bash
# Test tool discovery
curl -X POST http://localhost:7352/mcp/discover \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "code generation",
    "capabilities": ["coding", "github"],
    "trust_score": 0.9
  }'

# Test tool execution (requires governance setup)
curl -X POST http://localhost:7352/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "test_tool",
    "arguments": {"param1": "value1"},
    "intent": "test execution",
    "capabilities": ["test"],
    "trust_score": 0.9
  }'
```

### Guide 4: TWAVE v2.0 Calibration

#### Deployment Steps

1. **Install Dependencies**
```bash
pip install torch transformers datasets scipy numpy tqdm
```

2. **Run Calibration**
```bash
# Quick calibration for testing
python benchmarks/calibrate_twave_v2_landau_ginzburg.py --quick

# Full calibration with config
python benchmarks/calibrate_twave_v2_landau_ginzburg.py --config calibration_config.json
```

3. **Review Results**
```bash
# Calibration results will be in:
# - foundry_datasets/twave_calibration/calibration_data.json
# - foundry_datasets/twave_calibration/fitted_parameters/thermodynamic_parameters.json
# - foundry_datasets/twave_calibration/calibration_report.md
```

#### Verification

```bash
# Check that calibration data was generated
ls -la foundry_datasets/twave_calibration/

# Verify thermodynamic parameters
cat foundry_datasets/twave_calibration/fitted_parameters/thermodynamic_parameters.json

# Review calibration report
cat foundry_datasets/twave_calibration/calibration_report.md
```

---

## Operational Procedures

### Procedure 1: Daily Health Checks

#### Purpose
Ensure all system components are functioning correctly

#### Steps
```bash
# Run comprehensive health check
nexusctl doctor

# Check component status
nexusctl status

# Check Tailscale network
docker exec nexus-tailscale tailscale status

# Check Supabase connection
curl $SUPABASE_URL/rest/v1/agents?select=count

# Check Zapier API key validity
curl -X GET "https://api.zapier.com/v1/" \
  -H "Authorization: Bearer $ZAPIER_API_KEY"
```

#### Schedule
- **Frequency**: Daily (automated via cron)
- **Time**: 08:00 UTC
- **Automation**: Add to `nexus_cron/daily_health_check.py`

### Procedure 2: Trust Score Monitoring

#### Purpose
Monitor agent trust scores and identify anomalies

#### Steps
```bash
# Run trust score analysis
python scripts/analyze_trust_scores.py --days 7

# Check for trust collapse
python scripts/detect_trust_collapse.py --threshold -15.0

# Generate trust score report
python scripts/generate_trust_report.py --output reports/trust_$(date +%Y-%m-%d).md
```

#### Schedule
- **Frequency**: Every 6 hours
- **Automation**: Configure ERNIE MCP `compute_trust_delta` edge function

### Procedure 3: Proposal Governance Review

#### Purpose
Review and resolve pending proposals

#### Steps
```bash
# Get pending proposals
python scripts/get_pending_proposals.py

# Review proposals requiring manual attention
python scripts/review_proposals.py --status held

# Resolve holds if appropriate
python scripts/resolve_proposal_hold.py --proposal-id PROPOSAL_ID --decision approve
```

#### Schedule
- **Frequency**: Every 4 hours during business hours
- **Automation**: Manual review required for high-governance proposals

### Procedure 4: Anomaly Response

#### Purpose
Respond to detected system anomalies

#### Steps
```bash
# Get recent anomalies
python scripts/get_recent_anomalies.py --hours 1

# Investigate specific anomaly
python scripts/investigate_anomaly.py --anomaly-id ANOMAL_ID

# Resolve anomaly
python scripts/resolve_anomaly.py --anomaly-id ANOMAL_ID --action auto_resolve
```

#### Schedule
- **Frequency**: Immediate (triggered by anomaly detection)
- **Automation**: Manual review for high-severity anomalies

---

## Troubleshooting Runbooks

### Runbook 1: Bridge Server Not Responding

#### Symptoms
- `curl http://localhost:7352` times out
- Health check shows Bridge as "down"
- API endpoints returning 503 errors

#### Diagnosis
```bash
# Check if Bridge process is running
ps aux | grep nexus-bridge

# Check Bridge logs
docker logs nexus-bridge --tail 50

# Check port availability
netstat -tlnp | grep 7352

# Check database connection
docker exec nexus-bridge python -c "import nexus_os.db.manager; print('DB OK')"
```

#### Solutions

**Issue 1: Process crashed**
```bash
# Restart Bridge
docker restart nexus-bridge

# If using systemd
systemctl restart nexus-bridge
```

**Issue 2: Port conflict**
```bash
# Find process using port 7352
lsof -i :7352

# Kill conflicting process
kill -9 PID

# Restart Bridge
docker restart nexus-bridge
```

**Issue 3: Database connection failed**
```bash
# Check Supabase status
curl $SUPABASE_URL

# Update connection string
# Edit .env file and restart
docker restart nexus-bridge
```

### Runbook 2: Tailscale Network Partition

#### Symptoms
- Agents cannot communicate via Tailscale
- `tailscale ping` times out
- Tailscale status shows peers offline

#### Diagnosis
```bash
# Check Tailscale status
docker exec nexus-tailscale tailscale status

# Check Tailscale logs
docker logs nexus-tailscale --tail 50

# Test internet connectivity
docker exec nexus-tailscale ping -c 4 8.8.8.8

# Check DERP (relay) connectivity
tailscale netcheck
```

#### Solutions

**Issue 1: Tailscale daemon not running**
```bash
# Restart container
docker restart nexus-tailscale

# Check logs for errors
docker logs nexus-tailscale
```

**Issue 2: Auth key expired**
```bash
# Generate new auth key
# Update environment variable
docker exec nexus-tailscale tailscale up --authkey=$NEW_AUTH_KEY --reset

# Update docker-compose.yml with new key
docker-compose up -d
```

**Issue 3: Network firewall blocking**
```bash
# Check local firewall
sudo ufw status

# Temporarily disable for testing (not recommended for production)
sudo ufw disable

# Re-enable after testing
sudo ufw enable

# Better: Add Tailscale rules
sudo ufw allow 41641/tcp
```

### Runbook 3: Zapier Rate Limits

#### Symptoms
- Zapier API calls failing with 429 errors
- Tool execution timeouts
- Rate limit warnings in logs

#### Diagnosis
```bash
# Check Zapier API status
curl -X GET "https://api.zapier.com/v1/" \
  -H "Authorization: Bearer $ZAPIER_API_KEY"

# Check rate limit headers
curl -I "https://api.zapier.com/v1/" \
  -H "Authorization: Bearer $ZAPIER_API_KEY"

# Check usage metrics
curl -X GET "https://api.zapier.com/v1/billing/usage" \
  -H "Authorization: Bearer $ZAPIER_API_KEY"
```

#### Solutions

**Issue 1: Rate limit reached**
```bash
# Implement exponential backoff
# The ZapierMCPAdapter should have this built-in
# If not, upgrade to latest version

# Reduce concurrent requests
# In MCP server configuration, set max_concurrent_requests = 5
```

**Issue 2: API key quota exhausted**
```bash
# Check Zapier billing
# Upgrade plan if needed

# Consider switching to paid plan for higher limits
# Configure cost monitoring alerts
```

**Issue 3: Webhook failures**
```bash
# Check Zapier webhook status
# Re-enable webhooks if disabled

# Test webhook endpoint
curl -X POST YOUR_WEBHOOK_URL -d '{"test": true}'
```

### Runbook 4: ERNIE Edge Function Failures

#### Symptoms
- Edge functions returning 500 errors
- Functions timing out
- Database updates not appearing

#### Diagnosis
```bash
# Check function logs
supabase functions logs on_proposal_created

# Check function status
supabase functions list

# Test function directly
curl -X POST https://your-project.supabase.co/functions/v1/on_proposal_created \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -d '{"test": true}'
```

#### Solutions

**Issue 1: Function timeout**
```bash
# Increase timeout in function
# Add to edge function: timeout: 30

# Check for infinite loops
# Review function logic for potential loops
```

**Issue 2: Database permission errors**
```bash
# Check RLS policies
supabase db execute "SELECT * FROM pg_policies WHERE tablename = 'agents';"

# Grant necessary permissions
supabase db execute "GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;"
```

**Issue 3: Environment variable missing**
```bash
# Check environment variables
supabase secrets list

# Set missing variable
supabase secrets set MISSING_VAR=value

# Redeploy function
supabase functions deploy on_proposal_created --no-verify-jwt
```

---

## Maintenance Procedures

### Procedure 1: Weekly Backup Verification

#### Purpose
Ensure backups are working and can be restored

#### Steps
```bash
# Run backup verification
python scripts/verify_backups.py

# Test restore from backup
python scripts/test_restore.py --backup-id BACKUP_ID
```

### Procedure 2: Monthly Dependency Updates

#### Purpose
Keep dependencies updated for security and performance

#### Steps
```bash
# Update Python dependencies
pip list --outdated
pip install --upgrade package_name

# Update Docker images
docker pull nexus-tailscale:latest
docker compose pull

# Test after updates
nexusctl doctor
pytest tests/integration/
```

### Procedure 3: Quarterly Security Audit

#### Purpose
Review security configurations and compliance

#### Steps
```bash
# Run security scan
python scripts/security_audit.py

# Check for vulnerabilities
# Use Docker Scout
docker scout nexus-tailscale:latest

# Review access logs
python scripts/review_access_logs.py --days 90

# Rotate secrets
python scripts/rotate_secrets.py
```

---

## Emergency Procedures

### Emergency 1: Complete System Outage

#### Triggers
- All services down
- Network partition affecting all nodes
- Database corruption

#### Steps
```bash
# 1. Assess scope
nexusctl doctor

# 2. Check individual components
docker ps
supabase functions list
docker exec nexus-tailscale tailscale status

# 3. Restart services in order
# Database first
# Then networking
# Then application services

# 4. Verify recovery
nexusctl status

# 5. Notify team
python scripts/notify_outage.py --resolved false
```

### Emergency 2: Security Breach

#### Triggers
- Unauthorized access detected
- API keys leaked
- Governance bypassed

#### Steps
```bash
# 1. Immediate containment
# Disable public endpoints
# Revoke API keys

# 2. Investigation
python scripts/investigate_breach.py --from HOURS_AGO

# 3. Remediation
# Rotate all secrets
# Patch vulnerabilities
# Review access logs

# 4. Recovery
# Restore from clean backup
# Monitor for suspicious activity

# 5. Post-incident review
# Document lessons learned
# Update security procedures
```

### Emergency 3: Data Corruption

#### Triggers
- Database integrity check fails
- Inconsistent data detected
- Restore failures

#### Steps
```bash
# 1. Stop writes to affected systems
# Disable edge functions
# Stop Bridge server

# 2. Assess extent of corruption
python scripts/assess_corruption.py

# 3. Restore from backup
python scripts/restore_from_backup.py --backup-id BACKUP_ID

# 4. Validate restore
python scripts/validate_restore.py

# 5. Resume operations
# Enable edge functions
# Start Bridge server
# Verify data consistency
```

---

## Monitoring and Alerting

### Key Metrics to Monitor

| Component | Metric | Threshold | Alert Level |
|-----------|--------|-----------|-------------|
| Bridge Server | Response time | > 1s | Warning |
| Bridge Server | Error rate | > 5% | Critical |
| MCP Server | Tool discovery latency | > 100ms | Warning |
| MCP Server | Tool execution success rate | < 95% | Critical |
| Tailscale | Network latency | > 50ms | Warning |
| Tailscale | Peer availability | < 90% | Critical |
| ERNIE Governance | Proposal processing rate | < 1/min | Warning |
| ERNIE Governance | Trust computation latency | > 2s | Warning |
| Zapier API | Rate limit hit rate | > 10% | Warning |
| Database | Query latency | > 500ms | Warning |
| Database | Connection pool exhaustion | > 80% | Critical |

### Alerting Configuration

**Slack Integration**
```python
# scripts/alert_to_slack.py
import os
import requests

def send_alert(level, component, message):
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    
    color = {
        "info": "36a64f",      # Blue
        "warning": "ff9900",    # Orange
        "critical": "ff0000"   # Red
    }.get(level, "36a64f")
    
    payload = {
        "text": f"[{level.upper()}] {component}: {message}",
        "attachments": [{
            "color": color,
            "title": f"{component} - {level.upper()}",
            "text": message,
            "footer": "NEXUS OS Monitoring"
        }]
    }
    
    requests.post(webhook_url, json=payload)
```

---

## Rollback Procedures

### Rollback 1: Component Rollback

#### When to Use
- New component version causes issues
- Feature rollback required
- Performance degradation detected

#### Steps
```bash
# 1. Identify problematic version
docker ps | grep nexus-bridge
docker images nexus-bridge

# 2. Rollback to previous version
docker tag nexus-bridge:latest nexus-bridge:previous
docker pull nexus-bridge:stable
docker compose up -d

# 3. Verify rollback
nexusctl doctor
```

### Rollback 2: Architecture Rollback

#### When to Use
- Major architecture change causes issues
- Hybrid migration fails
- Need to return to Azure temporarily

#### Steps
```bash
# 1. Switch to Azure mode
export NEXUS_MODE=azure
export AZURE_MODE=enabled

# 2. Restore Azure configuration
source .env.azure.backup

# 3. Restart with Azure components
docker compose -f docker-compose.azure.yml up -d

# 4. Verify
nexusctl status
```

---

## Runbook Maintenance

### Updating Runbooks

Runbooks should be reviewed and updated:
- **Quarterly** or after major changes
- When new components are added
- After incident post-mortems
- When procedures are optimized

### Runbook Testing

Each runbook should be tested:
- **Monthly** for critical runbooks
- **Quarterly** for all runbooks
- After any updates to the runbook

### Feedback Loop

After using runbooks:
1. Document any issues encountered
2. Suggest improvements
3. Update procedures based on learnings
4. Share improvements with team

---

## Contact Information

### Escalation Contacts

| Role | Contact | Availability |
|------|---------|----------------|
| Platform Lead | platform-lead@nexus.os | 9-5 UTC weekdays |
| Infrastructure Lead | infra@nexus.os | 9-5 UTC weekdays |
| Security Team | security@nexus.os | 24/7 |
| On-Call Engineer | oncall@nexus.os | 24/7 |

### Communication Channels

- **Slack**: #nexus-operations
- **Emergency**: oncall@nexus.os
- **Documentation**: docs/handbook/

---

## Conclusion

This deployment and operations guide provides comprehensive procedures for deploying, operating, and maintaining the hybrid NEXUS OS architecture. Regular review and updating of these runbooks ensures continued operational excellence.

**Remember**: Always test changes in a staging environment before applying to production, and always maintain rollback capability for any deployment.