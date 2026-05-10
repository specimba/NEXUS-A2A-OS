import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

// ─── Governance Audit API ───
// Computes audit data from existing GovernorDecision + VaultEntry (GOV track) entries.
// No new DB tables are created — everything is derived from existing data.

export async function GET() {
  try {
    // ─── Fetch raw data ───
    const [decisions, govVaultEntries, agents] = await Promise.all([
      db.governorDecision.findMany({
        take: 200,
        orderBy: { createdAt: 'desc' },
        include: { agent: { select: { id: true, name: true, trustScore: true } } },
      }),
      db.vaultEntry.findMany({
        where: { track: 'GOV' },
        take: 200,
        orderBy: { createdAt: 'desc' },
        include: { agent: { select: { id: true, name: true } } },
      }),
      db.agent.findMany({
        select: {
          id: true,
          name: true,
          trustScore: true,
          tasksDone: true,
          tasksFailed: true,
          decisions: true,
        },
      }),
    ])

    // ─── Compliance Stats ───
    const allowCount = decisions.filter((d) => d.decision === 'ALLOW').length
    const denyCount = decisions.filter((d) => d.decision === 'DENY').length
    const holdCount = decisions.filter((d) => d.decision === 'HOLD').length
    const totalDecisions = allowCount + denyCount + holdCount
    const complianceScore = totalDecisions > 0
      ? Math.round((allowCount / totalDecisions) * 100)
      : 100

    // Trend: compare last 24h vs prior 24h
    const now = new Date()
    const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)
    const twoDaysAgo = new Date(now.getTime() - 48 * 60 * 60 * 1000)

    const recentDecisions = decisions.filter((d) => new Date(d.createdAt) >= oneDayAgo)
    const priorDecisions = decisions.filter(
      (d) => new Date(d.createdAt) >= twoDaysAgo && new Date(d.createdAt) < oneDayAgo
    )

    const recentAllow = recentDecisions.filter((d) => d.decision === 'ALLOW').length
    const priorAllow = priorDecisions.filter((d) => d.decision === 'ALLOW').length
    const recentTotal = recentDecisions.length
    const priorTotal = priorDecisions.length

    const recentRate = recentTotal > 0 ? recentAllow / recentTotal : 1
    const priorRate = priorTotal > 0 ? priorAllow / priorTotal : 1
    const trendDirection: 'up' | 'down' | 'stable' =
      recentRate > priorRate + 0.02 ? 'up' : recentRate < priorRate - 0.02 ? 'down' : 'stable'
    const trendDelta = priorRate > 0 ? Math.round(((recentRate - priorRate) / priorRate) * 100) : 0

    // ─── Threat Patterns from Vault Entries with Low Scores ───
    const threatEntries = govVaultEntries.filter((v) => v.score < 0.5)
    const threatCategories: Record<string, number> = {}
    for (const entry of threatEntries) {
      threatCategories[entry.category] = (threatCategories[entry.category] || 0) + 1
    }

    // Severity distribution from vault scores
    const critical = govVaultEntries.filter((v) => v.score === 0).length
    const high = govVaultEntries.filter((v) => v.score > 0 && v.score < 0.3).length
    const medium = govVaultEntries.filter((v) => v.score >= 0.3 && v.score < 0.6).length
    const low = govVaultEntries.filter((v) => v.score >= 0.6 && v.score < 0.8).length
    const clean = govVaultEntries.filter((v) => v.score >= 0.8).length

    // ─── Per-Agent Compliance Ranking ───
    const agentCompliance = agents.map((agent) => {
      const agentDecisions = decisions.filter((d) => d.agentId === agent.id)
      const aAllow = agentDecisions.filter((d) => d.decision === 'ALLOW').length
      const aDeny = agentDecisions.filter((d) => d.decision === 'DENY').length
      const aHold = agentDecisions.filter((d) => d.decision === 'HOLD').length
      const aTotal = aAllow + aDeny + aHold
      const complianceRate = aTotal > 0 ? aAllow / aTotal : 1
      const violationRate = aTotal > 0 ? (aDeny + aHold) / aTotal : 0

      return {
        id: agent.id,
        name: agent.name,
        trust: agent.trustScore,
        totalDecisions: aTotal,
        allowed: aAllow,
        denied: aDeny,
        held: aHold,
        complianceRate: Math.round(complianceRate * 100),
        violationRate: Math.round(violationRate * 100),
      }
    }).sort((a, b) => b.complianceRate - a.complianceRate)

    // ─── Policy Violation Timeline (by hour for last 24h) ───
    const violationTimeline: { hour: string; deny: number; hold: number }[] = []
    for (let i = 23; i >= 0; i--) {
      const hourStart = new Date(now.getTime() - i * 60 * 60 * 1000)
      const hourEnd = new Date(now.getTime() - (i - 1) * 60 * 60 * 1000)
      const hourLabel = hourStart.toLocaleTimeString('en-US', { hour: '2-digit', hour12: false })

      const hourDecisions = decisions.filter((d) => {
        const dt = new Date(d.createdAt)
        return dt >= hourStart && dt < hourEnd
      })

      violationTimeline.push({
        hour: hourLabel,
        deny: hourDecisions.filter((d) => d.decision === 'DENY').length,
        hold: hourDecisions.filter((d) => d.decision === 'HOLD').length,
      })
    }

    // ─── Recent Audit Events ───
    const auditEvents = [
      ...decisions.slice(0, 30).map((d) => ({
        id: d.id,
        type: 'decision' as const,
        agent: d.agent?.name ?? 'unknown',
        severity: d.impact === 'CRIT' ? 'critical' : d.impact === 'HIGH' ? 'high' : d.impact === 'MED' ? 'medium' : 'low',
        decision: d.decision,
        action: d.action,
        scope: d.scope,
        trust: d.trustAtTime,
        reason: d.reason,
        timestamp: d.createdAt,
      })),
      ...govVaultEntries.slice(0, 20).map((v) => ({
        id: v.id,
        type: 'vault_event' as const,
        agent: v.agent?.name ?? 'unknown',
        severity: v.score === 0 ? 'critical' : v.score < 0.3 ? 'high' : v.score < 0.6 ? 'medium' : 'low',
        decision: undefined as string | undefined,
        action: `${v.category}: ${v.key}`,
        scope: v.track,
        trust: v.score,
        reason: v.value.length > 80 ? v.value.slice(0, 80) + '...' : v.value,
        timestamp: v.createdAt,
      })),
    ]
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 50)

    return NextResponse.json({
      compliance: {
        score: complianceScore,
        allowCount,
        denyCount,
        holdCount,
        totalDecisions,
        trend: { direction: trendDirection, delta: trendDelta },
      },
      threats: {
        categories: Object.entries(threatCategories).map(([name, count]) => ({ name, count })),
        severityDistribution: { critical, high, medium, low, clean },
      },
      agentCompliance,
      violationTimeline,
      auditEvents,
    })
  } catch (error) {
    console.error('Governance Audit GET error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { agentId, category, key, value, score } = body

    if (!agentId || !category || !key) {
      return NextResponse.json(
        { error: 'Missing required fields: agentId, category, key' },
        { status: 400 }
      )
    }

    // Verify agent exists
    const agent = await db.agent.findFirst({
      where: { name: agentId },
    })
    if (!agent) {
      return NextResponse.json(
        { error: `Agent not found: ${agentId}` },
        { status: 404 }
      )
    }

    const vaultEntry = await db.vaultEntry.create({
      data: {
        agentId: agent.id,
        track: 'GOV',
        category,
        key: `gov:audit:${key}`,
        value: JSON.stringify(value),
        score: score ?? 1.0,
      },
    })

    return NextResponse.json({ vaultEntry }, { status: 201 })
  } catch (error) {
    console.error('Governance Audit POST error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
