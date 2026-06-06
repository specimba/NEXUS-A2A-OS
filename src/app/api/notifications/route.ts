import { db } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function GET() {
  try {
    // Build notifications from real system events
    const notifications: {
      id: string
      severity: 'error' | 'warn' | 'info' | 'success'
      message: string
      timestamp: string
      source: string
    }[] = []

    // 1. Error-state agents
    const errorAgents = await db.agent.findMany({ where: { status: 'error' } })
    for (const agent of errorAgents) {
      notifications.push({
        id: `agent-error-${agent.id}`,
        severity: 'error',
        message: `Agent ${agent.name} is in ERROR state — trust: ${agent.trustScore}, failed: ${agent.tasksFailed}`,
        timestamp: agent.updatedAt?.toISOString() || new Date().toISOString(),
        source: 'Swarm',
      })
    }

    // 2. Unhealthy models
    const unhealthyModels = await db.modelEntry.findMany({ where: { health: { lt: 80 }, isActive: true } })
    for (const model of unhealthyModels) {
      notifications.push({
        id: `model-health-${model.id}`,
        severity: 'warn',
        message: `Model ${model.name} health degraded: ${model.health}% (latency: ${model.latencyMs}ms)`,
        timestamp: model.lastChecked?.toISOString() || new Date().toISOString(),
        source: 'GMR',
      })
    }

    // 3. Recent governance denials
    const deniedDecisions = await db.governorDecision.findMany({
      where: { decision: 'DENY' },
      take: 3,
      orderBy: { createdAt: 'desc' },
      include: { agent: { select: { name: true } } },
    })
    for (const d of deniedDecisions) {
      notifications.push({
        id: `gov-deny-${d.id}`,
        severity: d.scope === 'CRIT' ? 'error' : 'warn',
        message: `Governor DENIED ${d.agent?.name || 'unknown'}: ${d.action} (${d.scope}) — ${d.reason?.slice(0, 60) || 'No reason'}`,
        timestamp: d.createdAt.toISOString(),
        source: 'Governor',
      })
    }

    // 4. Budget warnings
    const budget = await db.sessionBudget.findFirst({ where: { isActive: true } })
    if (budget) {
      const pct = (budget.usedBudget / budget.totalBudget) * 100
      if (pct > 80) {
        notifications.push({
          id: `budget-warn-${budget.id}`,
          severity: 'error',
          message: `Token budget critically low: ${Math.round(pct)}% used (${budget.remainingBudget.toLocaleString()} remaining)`,
          timestamp: new Date().toISOString(),
          source: 'Monitor',
        })
      } else if (pct > 60) {
        notifications.push({
          id: `budget-info-${budget.id}`,
          severity: 'warn',
          message: `Token budget at ${Math.round(pct)}% — ${budget.remainingBudget.toLocaleString()} tokens remaining`,
          timestamp: new Date().toISOString(),
          source: 'Tokens',
        })
      }
    }

    // 5. Failed stress tests
    const failedRuns = await db.testRun.findMany({
      where: { status: 'failed' },
      take: 3,
      orderBy: { createdAt: 'desc' },
    })
    for (const run of failedRuns) {
      notifications.push({
        id: `stress-fail-${run.id}`,
        severity: 'warn',
        message: `StressLab test failed — model: ${run.modelName}, collapse: ${run.collapseDetected ? 'YES' : 'no'}`,
        timestamp: run.createdAt.toISOString(),
        source: 'StressLab',
      })
    }

    // 6. Unvetted papers count
    const unvettedCount = await db.paper.count({ where: { isVetted: false } })
    if (unvettedCount > 0) {
      notifications.push({
        id: 'research-unvetted',
        severity: 'info',
        message: `${unvettedCount} papers awaiting vetting in research pipeline`,
        timestamp: new Date().toISOString(),
        source: 'Research',
      })
    }

    // 7. Low-trust agents
    const lowTrustAgents = await db.agent.findMany({ where: { trustScore: { lt: 0.5 } } })
    for (const agent of lowTrustAgents) {
      notifications.push({
        id: `agent-lowtrust-${agent.id}`,
        severity: 'warn',
        message: `Agent ${agent.name} trust score low: ${agent.trustScore.toFixed(2)} (below 0.5 threshold)`,
        timestamp: agent.updatedAt?.toISOString() || new Date().toISOString(),
        source: 'Governor',
      })
    }

    // 8. Passed stress tests (success notifications)
    const recentPassedRuns = await db.testRun.findMany({
      where: { status: 'passed' },
      take: 2,
      orderBy: { createdAt: 'desc' },
    })
    for (const run of recentPassedRuns) {
      notifications.push({
        id: `stress-pass-${run.id}`,
        severity: 'success',
        message: `StressLab test passed — model: ${run.modelName}, mode: ${run.mode}`,
        timestamp: run.createdAt.toISOString(),
        source: 'StressLab',
      })
    }

    // 9. Allowed governance decisions (success notifications)
    const allowedDecisions = await db.governorDecision.findMany({
      where: { decision: 'ALLOW' },
      take: 2,
      orderBy: { createdAt: 'desc' },
      include: { agent: { select: { name: true } } },
    })
    for (const d of allowedDecisions) {
      notifications.push({
        id: `gov-allow-${d.id}`,
        severity: 'success',
        message: `Governor ALLOWED ${d.agent?.name || 'unknown'}: ${d.action} (${d.scope})`,
        timestamp: d.createdAt.toISOString(),
        source: 'Governor',
      })
    }

    // Sort by timestamp (newest first), limit to 20
    notifications.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

    return NextResponse.json({ notifications: notifications.slice(0, 20) })
  } catch (error) {
    return NextResponse.json({ notifications: [], error: String(error) }, { status: 500 })
  }
}
