import { db } from '@/lib/db'
import { NextResponse } from 'next/server'

type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL'
type LogSource = 'VAULT' | 'GOVERNOR' | 'TOKENS' | 'GMR' | 'SWARM' | 'BRIDGE'

interface UnifiedLogEntry {
  id: string
  level: LogLevel
  source: LogSource
  message: string
  timestamp: string
  metadata?: Record<string, unknown>
}

export async function GET() {
  try {
    const entries: UnifiedLogEntry[] = []

    // 1. Query latest 50 VaultEntry records
    const vaultEntries = await db.vaultEntry.findMany({
      take: 50,
      orderBy: { createdAt: 'desc' },
      include: { agent: { select: { name: true } } },
    })

    for (const ve of vaultEntries) {
      let level: LogLevel = 'INFO'
      let source: LogSource = 'VAULT'

      if (ve.track === 'EVENT') {
        level = 'INFO'
        source = 'VAULT'
      } else if (ve.track === 'TRUST') {
        level = 'INFO'
        source = 'GOVERNOR'
      } else if (ve.track === 'FAIL') {
        level = 'ERROR'
        source = 'VAULT'
      } else if (ve.track === 'GOV') {
        level = 'WARN'
        source = 'GOVERNOR'
      } else if (ve.track === 'CAP') {
        level = 'DEBUG'
        source = 'VAULT'
      }

      const agentName = ve.agent?.name || ve.agentId
      entries.push({
        id: ve.id,
        level,
        source,
        message: `[${ve.track}] ${ve.category}/${ve.key} — ${ve.value} (agent: ${agentName}, score: ${ve.score.toFixed(2)})`,
        timestamp: ve.createdAt.toISOString(),
        metadata: { track: ve.track, category: ve.category, key: ve.key, agentName, score: ve.score },
      })
    }

    // 2. Query latest 20 RateLimitLog records
    try {
      const rateLimitLogs = await db.rateLimitLog.findMany({
        take: 20,
        orderBy: { createdAt: 'desc' },
      })

      for (const rl of rateLimitLogs) {
        const level: LogLevel = rl.wasRateLimited ? 'WARN' : rl.statusCode >= 400 ? 'ERROR' : 'DEBUG'
        const source: LogSource = 'BRIDGE'
        entries.push({
          id: rl.id,
          level,
          source,
          message: `${rl.method} ${rl.endpoint} → ${rl.statusCode}${rl.wasRateLimited ? ' (RATE LIMITED)' : ''}${rl.wasCached ? ' [CACHED]' : ''}${rl.wasDeduped ? ' [DEDUPED]' : ''} (${rl.responseTimeMs}ms)`,
          timestamp: rl.createdAt.toISOString(),
          metadata: {
            provider: rl.provider,
            statusCode: rl.statusCode,
            wasRateLimited: rl.wasRateLimited,
            wasCached: rl.wasCached,
            responseTimeMs: rl.responseTimeMs,
            tokensUsed: rl.tokensUsed,
          },
        })
      }
    } catch {
      // RateLimitLog table might not exist yet — skip gracefully
    }

    // Also get TokenUsageLog for high-usage warnings
    const tokenLogs = await db.tokenUsageLog.findMany({
      take: 20,
      orderBy: { createdAt: 'desc' },
    })

    for (const tl of tokenLogs) {
      const level: LogLevel = tl.totalTokens > 5000 ? 'WARN' : 'DEBUG'
      const source: LogSource = 'TOKENS'
      entries.push({
        id: tl.id,
        level,
        source,
        message: `Token usage: ${tl.totalTokens.toLocaleString()} tokens (${tl.promptTokens}+${tl.completionTokens}) on ${tl.model}${
          tl.agentId ? ` by agent ${tl.agentId}` : ''
        } — cost $${tl.cost.toFixed(4)}`,
        timestamp: tl.createdAt.toISOString(),
        metadata: {
          model: tl.model,
          totalTokens: tl.totalTokens,
          promptTokens: tl.promptTokens,
          completionTokens: tl.completionTokens,
          cost: tl.cost,
          agentId: tl.agentId,
        },
      })
    }

    // 3. Query latest 10 GovernorDecision records
    const decisions = await db.governorDecision.findMany({
      take: 10,
      orderBy: { createdAt: 'desc' },
      include: { agent: { select: { name: true } } },
    })

    for (const gd of decisions) {
      let level: LogLevel = 'INFO'
      if (gd.decision === 'DENIED') level = 'ERROR'
      else if (gd.decision === 'HOLD') level = 'WARN'
      else if (gd.decision === 'ALLOW') level = 'INFO'

      const source: LogSource = 'GOVERNOR'
      const agentName = gd.agent?.name || gd.agentId
      entries.push({
        id: gd.id,
        level,
        source,
        message: `${gd.decision}: ${agentName} → "${gd.action}" (${gd.scope} scope, ${gd.impact} impact)${gd.reason ? ` — ${gd.reason}` : ''} [trust: ${gd.trustAtTime.toFixed(2)}]`,
        timestamp: gd.createdAt.toISOString(),
        metadata: {
          decision: gd.decision,
          action: gd.action,
          scope: gd.scope,
          impact: gd.impact,
          trustAtTime: gd.trustAtTime,
          agentName,
        },
      })
    }

    // Sort all entries by timestamp descending
    entries.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

    return NextResponse.json({ entries })
  } catch (error) {
    return NextResponse.json({ entries: [], error: String(error) }, { status: 500 })
  }
}
