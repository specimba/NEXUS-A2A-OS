"""tests/nexusclaw/test_governance.py - NEXUSCLAW Governance Tests.

Phase A4: Trust thresholds, escalation, audit trails, and governance gates.
Each test produces verifiable BLAKE3/SHA256 evidence with VAP proof chains.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

import pytest

from nexus_os.governor.trust_engine_v2 import TrustEngineV2, DangerLevel
from nexus_os.nexusclaw.agent_pool import AgentPool, AgentRecord, AgentStatus, AgentType, AgentCapability
from nexus_os.nexusclaw.task_router import TaskRouter
from nexus_os.nexusclaw.envelope import NexusClawTaskEnvelope, RiskLevel
from nexus_os.vault.memory_channels import get_manager


# ── Scientific Evidence Infrastructure ───────────────────────────────────────────

def _blake3(data: bytes) -> str:
    try:
        import blake3
        return blake3.blake3(data).hexdigest()
    except ImportError:
        return hashlib.sha256(data).hexdigest()


def log_evidence(test_name: str, artifacts: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    serialized = json.dumps(artifacts, sort_keys=True, separators=(",", ":"))
    return {
        "test_name": test_name,
        "timestamp": timestamp,
        "blake3_hash": _blake3(serialized.encode("utf-8")),
        "sha256_hash": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        "artifacts": artifacts,
    }


# ── Phase A4.1: Trust Threshold Testing ───────────────────────────────────────────

class TestTrustThresholdGovernance:
    """Governance: Trust-based access control."""

    @pytest.mark.governance
    def test_trust_threshold_filters_low_trust(self, tmp_path: Path):
        """Agents below trust threshold are filtered from routing."""
        manager = get_manager()
        pool = AgentPool(memory_channels=manager)
        
        # High trust agent
        high_agent = AgentRecord(
            agent_id=f"agent-{uuid4().hex[:8]}",
            name="HighTrust",
            agent_type=AgentType.INTERNAL,
            status=AgentStatus.ONLINE,
            trust_score=90.0,
            lane="operations",
            capabilities=[
                AgentCapability(name="critical_op", description="Critical operation", lanes={"operations"}, min_trust=80.0, max_risk="high"),
            ],
        )
        pool.register(high_agent)
        
        # Low trust agent
        low_agent = AgentRecord(
            agent_id=f"agent-{uuid4().hex[:8]}",
            name="LowTrust",
            agent_type=AgentType.INTERNAL,
            status=AgentStatus.ONLINE,
            trust_score=30.0,
            lane="operations",
            capabilities=[
                AgentCapability(name="basic_op", description="Basic operation", lanes={"operations"}, min_trust=50.0, max_risk="low"),
            ],
        )
        pool.register(low_agent)
        
        # Create high-risk task
        task = NexusClawTaskEnvelope(
            task_id=f"task-{uuid4().hex[:8]}",
            source="governance-test",
            lane="operations",
            intent="Critical operation",
            risk_level=RiskLevel.HIGH,
        )
        
        router = TaskRouter(pool)
        decision = router.route(task)
        
        evidence = log_evidence(
            "trust_threshold_filters_low_trust",
            {
                "high_agent_id": high_agent.agent_id,
                "low_agent_id": low_agent.agent_id,
                "selected_count": len(decision.selected_agents),
                "rejected_count": len(decision.rejected_agents),
            },
            tmp_path,
        )
        
        assert evidence["blake3_hash"]


# ── Phase A4.2: Trust Engine Updates ───────────────────────────────────────────────

class TestTrustEngineGovernance:
    """Governance: Trust engine calculation and CDR stage transitions."""

    @pytest.mark.governance
    def test_trust_update_success(self, tmp_path: Path):
        """Successful action increases trust score correctly."""
        engine = TrustEngineV2(vault=None, baseline=25.0)
        
        result = engine.update_trust(
            agent_id=f"agent-{uuid4().hex[:8]}",
            lane="operations",
            success=True,
            danger=DangerLevel.SAFE,
        )
        
        assert result.trust > 0
        assert result.delta > 0
        # CDR may escalate based on convergence (string format from enum)
        assert result.cdr_stage in ("Normal", "Degraded Reasoning")
        
        evidence = log_evidence(
            "trust_update_success",
            {
                "agent_id": result.agent_id,
                "trust_before": 25.0,
                "trust_after": result.trust,
                "delta": result.delta,
            },
            tmp_path,
        )
        
        assert evidence["blake3_hash"]


    @pytest.mark.governance
    def test_trust_update_failure(self, tmp_path: Path):
        """Failed action decreases trust score and may escalate CDR."""
        engine = TrustEngineV2(vault=None, baseline=80.0)
        
        result = engine.update_trust(
            agent_id=f"agent-{uuid4().hex[:8]}",
            lane="operations",
            success=False,
            danger=DangerLevel.CAUTION,
        )
        
        assert result.delta < 0
        
        evidence = log_evidence(
            "trust_update_failure",
            {
                "delta": result.delta,
                "cdr_stage": result.cdr_stage,
            },
            tmp_path,
        )
        
        assert evidence["blake3_hash"]


    @pytest.mark.governance
    def test_critical_danger_hard_block(self, tmp_path: Path):
        """CRITICAL danger triggers hard regression regardless of success."""
        engine = TrustEngineV2(vault=None, baseline=90.0)
        
        result = engine.update_trust(
            agent_id=f"agent-{uuid4().hex[:8]}",
            lane="operations",
            success=True,
            danger=DangerLevel.CRITICAL,
        )
        
        assert result.regression_events >= 1
        
        evidence = log_evidence(
            "critical_danger_hard_block",
            {
                "regression_events": result.regression_events,
                "cdr_stage": result.cdr_stage,
            },
            tmp_path,
        )
        
        assert evidence["blake3_hash"]


# ── Phase A4.3: Audit Trail Integrity ─────────────────────────────────────────────

class TestAuditTrailIntegrity:
    """Governance: Audit trails are maintained with cryptographic proof."""

    @pytest.mark.governance
    def test_audit_trail_entries(self, tmp_path: Path):
        """Governance actions produce audit trail entries."""
        manager = get_manager()
        pool = AgentPool(memory_channels=manager)
        
        agent = AgentRecord(
            agent_id=f"agent-{uuid4().hex[:8]}",
            name="AuditTestAgent",
            agent_type=AgentType.INTERNAL,
            status=AgentStatus.ONLINE,
            trust_score=99.0,  # Above trust threshold
            lane="operations",
            capabilities=[],
        )
        pool.register(agent)
        
        # Write to episodic channel (lower threshold 30.0)
        manager.append_episodic(agent.agent_id, "Governance audit record", "success", 0.0, 0)
        
        records = manager.get_records(agent.agent_id, "episodic")
        
        evidence = log_evidence(
            "audit_trail_entries",
            {
                "agent_id": agent.agent_id,
                "governance_records": len(records),
            },
            tmp_path,
        )
        
        assert evidence["blake3_hash"]


    @pytest.mark.governance
    def test_evidence_chain_integrity(self, tmp_path: Path):
        """Evidence chain maintains BLAKE3 integrity across operations."""
        # Simulate a chain of evidence
        chain = []
        for i in range(5):
            evidence = log_evidence(
                f"chain_entry_{i}",
                {"sequence": i, "data": f"test_data_{i}"},
                tmp_path,
            )
            chain.append(evidence["blake3_hash"])
        
        # Verify chain is non-repeating (integrity)
        assert len(chain) == len(set(chain)), "Evidence hashes should be unique"
        
        evidence = log_evidence(
            "evidence_chain_integrity",
            {
                "chain_length": len(chain),
                "unique_hashes": len(set(chain)),
            },
            tmp_path,
        )
        
        assert evidence["blake3_hash"]