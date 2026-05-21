import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

const METRIC_SAMPLE_LIMIT = 500

/**
 * Unified metrics endpoint that powers Custom Dashboard widgets.
 *
 * Query: ?source=<dataSource>
 *
 * Supported dataSources & response shapes:
 *   agents.byStatus       -> { type:'categorical', data:[{name,value}] }
 *   agents.tokenLeaders   -> { type:'series',     data:[{name,value}] }
 *   agents.byDomain       -> { type:'categorical', data:[{name,value}] }
 *   agents.list           -> { type:'table',  columns,rows }
 *   agents.totalCount     -> { type:'kpi', value, label }
 *   tokens.budget         -> { type:'kpi', value,label,total,pct }
 *   tokens.history        -> { type:'timeseries', data }
 *   tokens.burnRate       -> { type:'kpi', value,label,delta }
 *   tokens.byModel        -> { type:'categorical', data }
 *   tokens.lastHour       -> { type:'kpi', value, label }
 *   governor.decisions    -> { type:'table', columns,rows }
 *   governor.approvalRate -> { type:'kpi', value, label, suffix }
 *   governor.byDecision   -> { type:'categorical', data }
 *   vault.size            -> { type:'kpi', value, label }
 *   vault.byTrack         -> { type:'categorical', data }
 *   swarm.byStatus        -> { type:'series', data }
 *   swarm.trustAverage    -> { type:'kpi', value, label }
 *   models.health         -> { type:'table', columns,rows }
 *   models.byProvider     -> { type:'categorical', data }
 *   tests.passRate        -> { type:'kpi', value,label,suffix,total }
 *   tests.recent          -> { type:'table', columns,rows }
 *   tests.byStatus        -> { type:'series', data }
 *   research.papers       -> { type:'kpi', value, label }
 *   research.byCategory   -> { type:'categorical', data }
 *   rateLimit.recent      -> { type:'table', columns,rows }
 */
export async function GET(req: NextRequest) {
  const source = req.nextUrl.searchParams.get('source')
  if (!source) {
    return NextResponse.json({ error: 'source param required' }, { status: 400 })
  }

  try {
    switch (source) {
      // ─── Agents ───
      case 'agents.byStatus': {
        const agents = await db.agent.findMany({
          take: METRIC_SAMPLE_LIMIT,
          orderBy: { lastActive: 'desc' },
          select: { status: true },
        })
        return NextResponse.json({
          type: 'categorical',
          data: groupBy(agents, 'status'),
        })
      }
      case 'agents.byDomain': {
        const agents = await db.agent.findMany({
          take: METRIC_SAMPLE_LIMIT,
          orderBy: { lastActive: 'desc' },
          select: { domain: true },
        })
        return NextResponse.json({
          type: 'categorical',
          data: groupBy(
            agents.map((a) => ({ domain: a.domain ?? 'unspecified' })),
            'domain',
          ),
        })
      }
      case 'agents.tokenLeaders': {
        const agents = await db.agent.findMany({
          orderBy: { totalTokens: 'desc' },
          take: 10,
          select: { name: true, totalTokens: true },
        })
        return NextResponse.json({
          type: 'series',
          data: agents.map((a) => ({ name: a.name, value: a.totalTokens })),
        })
      }
      case 'agents.list': {
        const agents = await db.agent.findMany({
          take: 50,
          orderBy: { lastActive: 'desc' },
        })
        return NextResponse.json({
          type: 'table',
          columns: ['Agent', 'Status', 'Trust', 'Tokens', 'Last Active'],
          rows: agents.map((a) => [
            a.name,
            a.status,
            a.trustScore.toFixed(2),
            a.totalTokens.toLocaleString(),
            new Date(a.lastActive).toLocaleString(),
          ]),
        })
      }
      case 'agents.totalCount': {
        const count = await db.agent.count()
        return NextResponse.json({ type: 'kpi', value: count, label: 'active agents' })
      }

      // ─── Tokens ───
      case 'tokens.budget': {
        const budget = await db.sessionBudget.findFirst({ where: { isActive: true } })
        if (!budget) {
          return NextResponse.json({
            type: 'kpi',
            value: 0,
            label: 'no active budget',
            total: 0,
            pct: 0,
          })
        }
        const pct = budget.totalBudget
          ? (budget.usedBudget / budget.totalBudget) * 100
          : 0
        return NextResponse.json({
          type: 'kpi',
          value: budget.usedBudget,
          label: `of ${budget.totalBudget.toLocaleString()}`,
          total: budget.totalBudget,
          pct: Math.round(pct),
        })
      }
      case 'tokens.history': {
        const since = new Date(Date.now() - 24 * 60 * 60 * 1000)
        const logs = await db.tokenUsageLog.findMany({
          where: { createdAt: { gte: since } },
          take: METRIC_SAMPLE_LIMIT,
          orderBy: { createdAt: 'desc' },
          select: { createdAt: true, totalTokens: true },
        })
        const buckets: Record<string, number> = {}
        for (let i = 23; i >= 0; i--) {
          const d = new Date(Date.now() - i * 60 * 60 * 1000)
          const key = `${d.getHours().toString().padStart(2, '0')}:00`
          buckets[key] = 0
        }
        logs.forEach((l) => {
          const d = new Date(l.createdAt)
          const key = `${d.getHours().toString().padStart(2, '0')}:00`
          if (key in buckets) buckets[key] += l.totalTokens
        })
        return NextResponse.json({
          type: 'timeseries',
          data: Object.entries(buckets).map(([name, value]) => ({ name, value })),
        })
      }
      case 'tokens.burnRate': {
        const snap = await db.tokenSnapshot.findFirst({
          orderBy: { recordedAt: 'desc' },
        })
        return NextResponse.json({
          type: 'kpi',
          value: snap ? Math.round(snap.burnRate * 10) / 10 : 0,
          label: 'tokens/min',
          delta: snap?.tokensLastHour ?? 0,
        })
      }
      case 'tokens.byModel': {
        const logs = await db.tokenUsageLog.findMany({
          take: METRIC_SAMPLE_LIMIT,
          orderBy: { createdAt: 'desc' },
          select: { model: true, totalTokens: true },
        })
        const groups = logs.reduce<Record<string, number>>((acc, l) => {
          acc[l.model] = (acc[l.model] ?? 0) + l.totalTokens
          return acc
        }, {})
        return NextResponse.json({
          type: 'categorical',
          data: Object.entries(groups)
            .map(([name, value]) => ({ name, value }))
            .sort((a, b) => b.value - a.value)
            .slice(0, 8),
        })
      }
      case 'tokens.lastHour': {
        const since = new Date(Date.now() - 60 * 60 * 1000)
        const sum = await db.tokenUsageLog.aggregate({
          where: { createdAt: { gte: since } },
          _sum: { totalTokens: true },
        })
        return NextResponse.json({
          type: 'kpi',
          value: sum._sum.totalTokens ?? 0,
          label: 'tokens last hour',
        })
      }

      // ─── Governor ───
      case 'governor.decisions': {
        const decisions = await db.governorDecision.findMany({
          take: 20,
          orderBy: { createdAt: 'desc' },
          include: { agent: { select: { name: true } } },
        })
        return NextResponse.json({
          type: 'table',
          columns: ['Agent', 'Action', 'Scope', 'Impact', 'Decision', 'When'],
          rows: decisions.map((d) => [
            d.agent?.name ?? '—',
            d.action,
            d.scope,
            d.impact,
            d.decision,
            new Date(d.createdAt).toLocaleString(),
          ]),
        })
      }
      case 'governor.approvalRate': {
        const recent = await db.governorDecision.findMany({
          take: 100,
          orderBy: { createdAt: 'desc' },
          select: { decision: true },
        })
        const approved = recent.filter((d) => d.decision === 'ALLOW').length
        const pct = recent.length ? Math.round((approved / recent.length) * 100) : 0
        return NextResponse.json({
          type: 'kpi',
          value: pct,
          label: 'ALLOW rate',
          suffix: '%',
          total: recent.length,
        })
      }
      case 'governor.byDecision': {
        const decisions = await db.governorDecision.findMany({
          take: METRIC_SAMPLE_LIMIT,
          orderBy: { createdAt: 'desc' },
          select: { decision: true },
        })
        return NextResponse.json({
          type: 'categorical',
          data: groupBy(decisions, 'decision'),
        })
      }

      // ─── Vault ───
      case 'vault.size': {
        const count = await db.vaultEntry.count()
        return NextResponse.json({ type: 'kpi', value: count, label: 'vault items' })
      }
      case 'vault.byTrack': {
        const items = await db.vaultEntry.findMany({
          take: METRIC_SAMPLE_LIMIT,
          orderBy: { createdAt: 'desc' },
          select: { track: true },
        })
        return NextResponse.json({
          type: 'categorical',
          data: groupBy(items, 'track'),
        })
      }

      // ─── Swarm / Agents alt ───
      case 'swarm.byStatus': {
        const agents = await db.agent.findMany({
          take: METRIC_SAMPLE_LIMIT,
          orderBy: { lastActive: 'desc' },
          select: { status: true },
        })
        return NextResponse.json({
          type: 'series',
          data: groupBy(agents, 'status'),
        })
      }
      case 'swarm.trustAverage': {
        const agents = await db.agent.findMany({
          take: METRIC_SAMPLE_LIMIT,
          orderBy: { lastActive: 'desc' },
          select: { trustScore: true },
        })
        const avg = agents.length
          ? agents.reduce((s, a) => s + a.trustScore, 0) / agents.length
          : 0
        return NextResponse.json({
          type: 'kpi',
          value: Math.round(avg * 100) / 100,
          label: 'avg trust score',
        })
      }

      // ─── Models ───
      case 'models.health': {
        const models = await db.modelEntry.findMany({
          take: 25,
          orderBy: { lastChecked: 'desc' },
        })
        return NextResponse.json({
          type: 'table',
          columns: ['Model', 'Provider', 'Tier', 'Health %', 'Latency (ms)'],
          rows: models.map((m) => [
            m.name,
            m.provider,
            m.tier.toString(),
            m.health.toFixed(1),
            m.latencyMs.toString(),
          ]),
        })
      }
      case 'models.byProvider': {
        const models = await db.modelEntry.findMany({
          take: METRIC_SAMPLE_LIMIT,
          orderBy: { lastChecked: 'desc' },
          select: { provider: true },
        })
        return NextResponse.json({
          type: 'categorical',
          data: groupBy(models, 'provider'),
        })
      }

      // ─── Tests ───
      case 'tests.passRate': {
        const tests = await db.testRun.findMany({
          take: 100,
          orderBy: { createdAt: 'desc' },
          select: { status: true },
        })
        const passed = tests.filter((t) => t.status === 'passed').length
        const pct = tests.length ? Math.round((passed / tests.length) * 100) : 0
        return NextResponse.json({
          type: 'kpi',
          value: pct,
          label: 'pass rate',
          suffix: '%',
          total: tests.length,
        })
      }
      case 'tests.recent': {
        const tests = await db.testRun.findMany({
          take: 20,
          orderBy: { createdAt: 'desc' },
          include: { template: { select: { name: true, domain: true } } },
        })
        return NextResponse.json({
          type: 'table',
          columns: ['Test', 'Domain', 'Model', 'Status', 'Duration'],
          rows: tests.map((t) => [
            t.template?.name ?? '—',
            t.template?.domain ?? '—',
            t.modelName,
            t.status,
            t.durationMs ? `${t.durationMs}ms` : '—',
          ]),
        })
      }
      case 'tests.byStatus': {
        const tests = await db.testRun.findMany({
          take: METRIC_SAMPLE_LIMIT,
          orderBy: { createdAt: 'desc' },
          select: { status: true },
        })
        return NextResponse.json({
          type: 'series',
          data: groupBy(tests, 'status'),
        })
      }

      // ─── Research ───
      case 'research.papers': {
        const count = await db.paper.count()
        return NextResponse.json({
          type: 'kpi',
          value: count,
          label: 'papers indexed',
        })
      }
      case 'research.byCategory': {
        const papers = await db.paper.findMany({
          select: { category: true },
          take: 500,
        })
        return NextResponse.json({
          type: 'categorical',
          data: groupBy(
            papers.map((p) => ({ category: p.category ?? 'uncategorized' })),
            'category',
          ).slice(0, 8),
        })
      }

      // ─── Rate Limit ───
      case 'rateLimit.recent': {
        const logs = await db.rateLimitLog.findMany({
          take: 20,
          orderBy: { createdAt: 'desc' },
        })
        return NextResponse.json({
          type: 'table',
          columns: ['Provider', 'Endpoint', 'Status', 'RT (ms)', 'When'],
          rows: logs.map((l) => [
            l.provider,
            l.endpoint,
            l.wasRateLimited ? '429' : l.statusCode.toString(),
            l.responseTimeMs.toString(),
            new Date(l.createdAt).toLocaleString(),
          ]),
        })
      }

      default:
        return NextResponse.json(
          { error: `Unknown source: ${source}` },
          { status: 400 },
        )
    }
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

function groupBy<T extends Record<string, unknown>>(
  rows: T[],
  key: keyof T,
): { name: string; value: number }[] {
  const groups = rows.reduce<Record<string, number>>((acc, r) => {
    const k = String(r[key] ?? 'unknown')
    acc[k] = (acc[k] ?? 0) + 1
    return acc
  }, {})
  return Object.entries(groups)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
}
