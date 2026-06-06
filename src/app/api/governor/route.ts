import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

export async function GET() {
  try {
    const decisions = await db.governorDecision.findMany({
      take: 50,
      orderBy: { createdAt: 'desc' },
      include: { agent: true },
    })
    const agents = await db.agent.findMany({
      select: { id: true, name: true, trustScore: true, tasksDone: true, tasksFailed: true },
    })

    // Fetch thresholds from SystemConfig
    const thresholdsConfig = await db.systemConfig.findUnique({
      where: { key: 'governor_thresholds' },
    })
    const defaultThresholds = {
      research: 0.30,
      review: 0.50,
      audit: 0.70,
      impl: 0.60,
    }
    const thresholds = thresholdsConfig
      ? JSON.parse(thresholdsConfig.value)
      : defaultThresholds

    // Fetch danger patterns from SystemConfig
    const patternsConfig = await db.systemConfig.findUnique({
      where: { key: 'danger_patterns' },
    })
    const defaultPatterns = [
      { name: 'delete all', severity: 'CRIT', pattern: 'delete all' },
      { name: 'rm -rf', severity: 'CRIT', pattern: 'rm -rf' },
      { name: 'exfiltrate data', severity: 'HIGH', pattern: 'exfiltrate data' },
      { name: 'backdoor install', severity: 'HIGH', pattern: 'backdoor install' },
      { name: 'override constitution', severity: 'CRIT', pattern: 'override constitution' },
    ]
    const patterns = patternsConfig
      ? JSON.parse(patternsConfig.value)
      : defaultPatterns

    // Compute trustStats from agents and decisions
    const trustStats = agents.map((a) => {
      const agentDecisions = decisions.filter((d) => d.agentId === a.id)
      const allowed = agentDecisions.filter((d) => d.decision === 'ALLOW').length
      const denied = agentDecisions.filter((d) => d.decision === 'DENY').length
      const held = agentDecisions.filter((d) => d.decision === 'HOLD').length
      return {
        id: a.id,
        name: a.name,
        trust: a.trustScore,
        decisions: agentDecisions.length,
        allowed,
        denied,
        held,
        tasksDone: a.tasksDone,
        tasksFailed: a.tasksFailed,
      }
    })

    return NextResponse.json({ decisions, trustStats, thresholds, patterns })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action } = body

    if (action === 'appeal') {
      const { decisionId, agentId, reason } = body
      if (!decisionId) {
        return NextResponse.json(
          { error: 'Missing required field: decisionId' },
          { status: 400 }
        )
      }

      // Find the original decision
      const originalDecision = await db.governorDecision.findUnique({
        where: { id: decisionId },
        include: { agent: true },
      })
      if (!originalDecision) {
        return NextResponse.json({ error: 'Decision not found' }, { status: 404 })
      }

      // Create an appeal decision
      const appealDecision = await db.governorDecision.create({
        data: {
          agentId: originalDecision.agentId,
          action: `appeal: ${originalDecision.action}`,
          scope: originalDecision.scope,
          impact: originalDecision.impact,
          decision: 'HOLD',
          reason: reason ?? `Appeal of decision ${decisionId}`,
          trustAtTime: originalDecision.agent?.trustScore ?? 0.5,
        },
        include: { agent: true },
      })

      return NextResponse.json({ decision: appealDecision }, { status: 201 })
    }

    if (action === 'update_threshold') {
      const { thresholds } = body
      if (!thresholds || typeof thresholds !== 'object') {
        return NextResponse.json(
          { error: 'Missing required field: thresholds (object)' },
          { status: 400 }
        )
      }

      const config = await db.systemConfig.upsert({
        where: { key: 'governor_thresholds' },
        update: { value: JSON.stringify(thresholds) },
        create: { key: 'governor_thresholds', value: JSON.stringify(thresholds) },
      })

      return NextResponse.json({ config })
    }

    if (action === 'add_pattern') {
      const { pattern } = body
      if (!pattern || typeof pattern !== 'object') {
        return NextResponse.json(
          { error: 'Missing required field: pattern (object)' },
          { status: 400 }
        )
      }

      // Get existing patterns and append new one
      const existing = await db.systemConfig.findUnique({
        where: { key: 'danger_patterns' },
      })
      const patterns = existing ? JSON.parse(existing.value) : []
      patterns.push(pattern)

      const config = await db.systemConfig.upsert({
        where: { key: 'danger_patterns' },
        update: { value: JSON.stringify(patterns) },
        create: { key: 'danger_patterns', value: JSON.stringify([pattern]) },
      })

      return NextResponse.json({ config })
    }

    return NextResponse.json(
      { error: `Unknown action: ${action}. Valid actions: appeal, update_threshold, add_pattern` },
      { status: 400 }
    )
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
