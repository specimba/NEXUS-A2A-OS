"""nexus_os/observability/metrics.py - Prometheus Metrics Exporter (Phase E4).

Exports NEXUSCLAW metrics for Prometheus scraping.
Tracks trust scores, task routing, brainstorm sessions, worker health.
"""

from __future__ import annotations

import logging
from typing import Dict, Any
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    CollectorRegistry,
    generate_latest,
)

logger = logging.getLogger(__name__)

# ── Metrics Definitions ──────────────────────────────────────────────────────────

# Counter metrics (cumulative)
TASK_ROUTED_TOTAL = Counter(
    'nexusclaw_task_routed_total',
    'Total number of tasks routed',
    ['lane', 'risk_level', 'status'],
)

TRUST_UPDATE_TOTAL = Counter(
    'nexusclaw_trust_update_total',
    'Total trust updates',
    ['agent_id', 'lane', 'outcome'],  # outcome: success, failure, degraded
)

BRAINSTEM_PROPOSAL_TOTAL = Counter(
    'nexusclaw_brainstorm_proposal_total',
    'Total brainstorm proposals',
    ['session_id', 'phase'],
)

# Gauge metrics (current state)
AGENT_POOL_SIZE = Gauge(
    'nexusclaw_agent_pool_size',
    'Current agent pool size',
    ['status'],  # status: online, busy, error, offline
)

TRUST_SCORE_GAUGE = Gauge(
    'nexusclaw_trust_score',
    'Current trust score for agent',
    ['agent_id', 'lane'],
)

BRAINSTEM_ACTIVE_SESSIONS = Gauge(
    'nexusclaw_brainstorm_active_sessions',
    'Number of active brainstorm sessions',
)

WORKER_POOL_SIZE = Gauge(
    'nexusclaw_worker_pool_size',
    'Current worker pool size',
    ['state'],  # state: idle, running, paused, stopped, failed, halted
)

# Histogram metrics (distribution)
TASK_ROUTING_DURATION = Histogram(
    'nexusclaw_task_routing_duration_seconds',
    'Task routing duration',
    ['lane'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

BRAINSTEM_CONSENSUS_TIME = Histogram(
    'nexusclaw_brainstorm_consensus_duration_seconds',
    'Time to reach consensus in brainstorm',
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

# Summary metrics (quantiles)
INTERVENTION_LATENCY = Summary(
    'nexusclaw_intervention_latency_seconds',
    'Operator intervention latency',
    ['intervention_type'],
)


# ── Metric Recording Functions ───────────────────────────────────────────────────

def record_task_routed(lane: str, risk_level: str, status: str, duration: float) -> None:
    """Record a task routing event."""
    TASK_ROUTED_TOTAL.labels(lane=lane, risk_level=risk_level, status=status).inc()
    TASK_ROUTING_DURATION.labels(lane=lane).observe(duration)


def record_trust_update(agent_id: str, lane: str, outcome: str) -> None:
    """Record a trust update event."""
    TRUST_UPDATE_TOTAL.labels(agent_id=agent_id, lane=lane, outcome=outcome).inc()


def record_brainstorm_proposal(session_id: str, phase: str) -> None:
    """Record a brainstorm proposal event."""
    BRAINSTEM_PROPOSAL_TOTAL.labels(session_id=session_id, phase=phase).inc()


def update_agent_pool_stats(stats: Dict[str, int]) -> None:
    """Update agent pool size gauges."""
    for status in ['online', 'busy', 'error', 'offline']:
        count = stats.get(status, 0)
        AGENT_POOL_SIZE.labels(status=status).set(count)


def update_trust_score(agent_id: str, lane: str, score: float) -> None:
    """Update trust score gauge for an agent."""
    TRUST_SCORE_GAUGE.labels(agent_id=agent_id, lane=lane).set(score)


def update_brainstorm_sessions(count: int) -> None:
    """Update active brainstorm sessions gauge."""
    BRAINSTEM_ACTIVE_SESSIONS.set(count)


def update_worker_pool_stats(stats: Dict[str, int]) -> None:
    """Update worker pool size gauges."""
    for state in ['idle', 'running', 'paused', 'stopped', 'failed', 'halted']:
        count = stats.get(state, 0)
        WORKER_POOL_SIZE.labels(state=state).set(count)


def record_intervention_latency(intervention_type: str, duration: float) -> None:
    """Record operator intervention latency."""
    INTERVENTION_LATENCY.labels(intervention_type=intervention_type).observe(duration)


# ── Prometheus Endpoint ──────────────────────────────────────────────────────────

def generate_metrics() -> bytes:
    """Generate Prometheus metrics endpoint response."""
    return generate_latest()


# ── Grafana Dashboard JSON Template ──────────────────────────────────────────────

GRAFANA_DASHBOARD_JSON = {
    "dashboard": {
        "title": "NEXUSCLAW Observability",
        "panels": [
            {
                "title": "Agent Pool Status",
                "targets": [
                    {"expr": "nexusclaw_agent_pool_size{status=\"online\"}", "legendFormat": "Online"},
                    {"expr": "nexusclaw_agent_pool_size{status=\"busy\"}", "legendFormat": "Busy"},
                    {"expr": "nexusclaw_agent_pool_size{status=\"error\"}", "legendFormat": "Error"},
                ],
                "type": "graph",
            },
            {
                "title": "Trust Score Distribution",
                "targets": [
                    {"expr": "nexusclaw_trust_score", "legendFormat": "{{agent_id}} ({{lane}})"},
                ],
                "type": "gauge",
            },
            {
                "title": "Task Routing Latency",
                "targets": [
                    {"expr": "histogram_quantile(0.95, rate(nexusclaw_task_routing_duration_seconds_bucket[5m]))", "legendFormat": "95th percentile"},
                ],
                "type": "graph",
            },
            {
                "title": "Brainstorm Active Sessions",
                "targets": [
                    {"expr": "nexusclaw_brainstorm_active_sessions"},
                ],
                "type": "stat",
            },
        ],
    }
}