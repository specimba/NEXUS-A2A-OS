import { db } from '@/lib/db'
import { NextResponse } from 'next/server'

/**
 * TrustEngine v2.2 API Route
 *
 * Provides trust engine data including CDR stages, research metrics,
 * and trust matrix for all agents.
 *
 * GET /api/trust-engine — Full trust matrix + CDR status
 * GET /api/trust-engine?agent=worker-1 — Per-agent research metrics
 */

// CDR Stage definitions (mirrors Python enum)
const CDR_STAGES = [
  { id: 'Normal', severity: 0, color: '#34d399', description: 'Agent operating within normal parameters' },
  { id: 'Degraded Reasoning', severity: 1, color: '#facc15', description: 'Trust < 30 — reasoning quality degrading' },
  { id: 'Memory Corruption', severity: 2, color: '#fb923c', description: '3+ regression events — memory integrity at risk' },
  { id: 'Output Hallucination', severity: 3, color: '#f97316', description: 'Trust < 20 + high regressions — outputs unreliable' },
  { id: 'Cascade', severity: 4, color: '#ef4444', description: 'CRITICAL danger forced — cascading degradation' },
  { id: 'Collapse', severity: 5, color: '#dc2626', description: 'Trust < 15 — agent requires human intervention' },
]

// Danger levels (mirrors Python enum)
const DANGER_LEVELS = [
  { id: 'SAFE', value: 0, color: '#34d399' },
  { id: 'CAUTION', value: 1, color: '#facc15' },
  { id: 'RESTRICTED', value: 2, color: '#fb923c' },
  { id: 'HIGH_RISK', value: 3, color: '#f97316' },
  { id: 'CRITICAL', value: 4, color: '#ef4444' },
]

function computeCDRStage(trust: number, regressions: number): string {
  if (trust < 0.15) return 'Collapse'
  if (trust < 0.30 && regressions >= 5) return 'Output Hallucination'
  if (trust < 0.30) return 'Degraded Reasoning'
  if (regressions >= 3 && trust < 0.50) return 'Memory Corruption'
  return 'Normal'
}

function computeTrustVelocity(trust: number, regressions: number, totalDecisions: number): number {
  if (totalDecisions === 0) return 0
  const baseVelocity = Math.abs(trust - 0.25) / 10
  const regressionPenalty = regressions * 0.15
  return Math.round((baseVelocity + regressionPenalty) * 1000) / 1000
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const agentId = searchParams.get('agent')

    // Fetch agents with trust scores
    const agents = await db.agent.findMany({
      select: {
        id: true,
        name: true,
        trustScore: true,
        tasksDone: true,
        tasksFailed: true,
        totalTokens: true,
      },
    })

    // Fetch recent governor decisions for context
    const recentDecisions = await db.governorDecision.findMany({
      take: 50,
      orderBy: { createdAt: 'desc' },
      select: {
        id: true,
        agentId: true,
        decision: true,
        impact: true,
        createdAt: true,
      },
    })

    // Compute trust matrix for all agents
    const lanes = ['research', 'review', 'audit', 'impl'] as const
    const trustMatrix = agents.map((agent) => {
      const agentDecisions = recentDecisions.filter((d) => d.agentId === agent.id)
      const denied = agentDecisions.filter((d) => d.decision === 'DENY').length
      const highImpact = agentDecisions.filter(
        (d) => d.impact === 'HIGH' || d.impact === 'CRIT'
      ).length
      const regressions = denied + highImpact

      // Determine primary lane
      const trust = agent.trustScore
      let lane = 'research'
      if (agent.name.includes('coordinator')) lane = 'impl'
      else if (agent.name.includes('research')) lane = 'research'
      else if (trust >= 0.80) lane = 'audit'
      else if (trust >= 0.60) lane = 'review'

      const cdrStage = computeCDRStage(trust, regressions)
      const velocity = computeTrustVelocity(trust, regressions, agentDecisions.length)

      // Compute per-lane trust (simplified — same base with lane modifier)
      const laneTrust = lanes.map((l) => {
        const modifier = l === 'audit' ? -0.05 : l === 'review' ? 0.0 : l === 'impl' ? 0.02 : -0.03
        const lt = Math.max(0, Math.min(0.995, trust + modifier))
        const lCdr = computeCDRStage(lt, regressions)
        return {
          lane: l,
          trust: Math.round(lt * 1000) / 1000,
          cdr_stage: lCdr,
          convergence_turns: Math.floor(lt * 10),
          regression_events: regressions,
          total_validations: agentDecisions.length,
          trust_velocity: velocity,
          asymptotic_plateau: lt < 0.995,
        }
      })

      return {
        agent_id: agent.name,
        agent_id_raw: agent.id,
        overall_trust: Math.round(trust * 1000) / 1000,
        cdr_stage: cdrStage,
        cdr_severity: CDR_STAGES.find((s) => s.id === cdrStage)?.severity ?? 0,
        primary_lane: lane,
        convergence_turns: Math.floor(trust * 10),
        regression_events: regressions,
        total_validations: agentDecisions.length,
        peak_trust: Math.min(0.995, trust + 0.05),
        trust_velocity: velocity,
        asymptotic_plateau: trust < 0.995,
        disagreement_rate: Math.min(1, regressions / Math.max(1, agentDecisions.length)),
        lane_details: laneTrust,
        total_tokens: agent.totalTokens,
      }
    })

    // If specific agent requested, return research metrics
    if (agentId) {
      const agentData = trustMatrix.find(
        (a) => a.agent_id === agentId || a.agent_id_raw === agentId
      )
      if (!agentData) {
        return NextResponse.json(
          { error: `Agent '${agentId}' not found` },
          { status: 404 }
        )
      }

      return NextResponse.json({
        research_metrics: {
          convergence_rate: agentData.convergence_turns,
          regression_rate: agentData.regression_events,
          trust_velocity: agentData.trust_velocity,
          current_trust: agentData.overall_trust,
          cdr_stage: agentData.cdr_stage,
          cdr_severity: agentData.cdr_severity,
          asymptotic_plateau: agentData.asymptotic_plateau,
          total_validations: agentData.total_validations,
          peak_score: agentData.peak_trust,
          disagreement_rate: agentData.disagreement_rate,
        },
        lane_details: agentData.lane_details,
        hardwall_config: {
          baseline_score: 0.25,
          max_score: 0.995,
          success_base_delta: 0.04,
          failure_delta: -0.10,
          critical_delta: -0.20,
          logistic_center: 0.50,
          logistic_steepness: 0.10,
          base_decay_lambda: 0.02,
          cdr_collapse_threshold: 0.15,
          cdr_escalation_threshold: 0.30,
        },
      })
    }

    // CDR stage distribution
    const cdrDistribution = CDR_STAGES.map((stage) => ({
      ...stage,
      count: trustMatrix.filter((a) => a.cdr_stage === stage.id).length,
    }))

    // Overall health summary
    const healthyAgents = trustMatrix.filter((a) => a.cdr_stage === 'Normal').length
    const degradedAgents = trustMatrix.filter((a) => a.cdr_severity >= 1).length
    const collapsedAgents = trustMatrix.filter((a) => a.cdr_severity >= 4).length
    const avgTrust =
      trustMatrix.length > 0
        ? trustMatrix.reduce((s, a) => s + a.overall_trust, 0) / trustMatrix.length
        : 0

    return NextResponse.json({
      trust_matrix: trustMatrix,
      cdr_stages: CDR_STAGES,
      cdr_distribution: cdrDistribution,
      danger_levels: DANGER_LEVELS,
      health_summary: {
        total_agents: trustMatrix.length,
        healthy: healthyAgents,
        degraded: degradedAgents,
        collapsed: collapsedAgents,
        avg_trust: Math.round(avgTrust * 1000) / 1000,
        system_cdr: collapsedAgents > 0 ? 'CASCADE' : degradedAgents > 0 ? 'DEGRADED' : 'NORMAL',
      },
      hardwall_config: {
        baseline_score: 0.25,
        max_score: 0.995,
        success_base_delta: 0.04,
        failure_delta: -0.10,
        critical_delta: -0.20,
        logistic_center: 0.50,
        logistic_steepness: 0.10,
        base_decay_lambda: 0.02,
        cdr_collapse_threshold: 0.15,
        cdr_escalation_threshold: 0.30,
      },
    })
  } catch (error) {
    console.error('TrustEngine API error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
