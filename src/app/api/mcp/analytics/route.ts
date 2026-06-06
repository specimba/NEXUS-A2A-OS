import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

// GET /api/mcp/analytics?hours=24
// Returns aggregated metrics for the analytics view: events-over-time
// (per-minute buckets), top topics, error rate, and per-connection counts.
export async function GET(req: NextRequest) {
  try {
    const url = new URL(req.url)
    const hours = Math.max(1, Math.min(parseInt(url.searchParams.get('hours') ?? '24', 10) || 24, 168))
    const since = new Date(Date.now() - hours * 60 * 60 * 1000)

    const [events, connections] = await Promise.all([
      db.mcpEvent.findMany({
        where: { occurredAt: { gt: since } },
        select: { topic: true, level: true, occurredAt: true, connectionId: true },
        orderBy: { occurredAt: 'asc' },
      }),
      db.mcpConnection.findMany({
        select: { id: true, name: true, status: true, totalEvents: true, errorCount: true },
      }),
    ])

    // Bucket events by hour for the timeseries. For multi-day windows we
    // aggregate by hour; for <= 6h we aggregate by 5-minute buckets.
    const bucketMs = hours <= 6 ? 5 * 60 * 1000 : 60 * 60 * 1000
    type LevelKey = 'info' | 'warn' | 'error' | 'debug'
    type Bucket = { ts: number; info: number; warn: number; error: number; debug: number }
    const series = new Map<number, Bucket>()
    for (const e of events) {
      const bucket = Math.floor(e.occurredAt.getTime() / bucketMs) * bucketMs
      let row = series.get(bucket)
      if (!row) {
        row = { ts: bucket, info: 0, warn: 0, error: 0, debug: 0 }
        series.set(bucket, row)
      }
      const lvl: LevelKey = (['info', 'warn', 'error', 'debug'] as const).includes(e.level as LevelKey)
        ? (e.level as LevelKey)
        : 'info'
      row[lvl] += 1
    }
    const timeseries = Array.from(series.values()).sort((a, b) => a.ts - b.ts)

    // Top topics by count.
    const topicCounts = new Map<string, number>()
    for (const e of events) topicCounts.set(e.topic, (topicCounts.get(e.topic) ?? 0) + 1)
    const topTopics = Array.from(topicCounts.entries())
      .map(([topic, count]) => ({ topic, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10)

    // Error rate
    const total = events.length
    const errors = events.filter((e) => e.level === 'error').length
    const errorRate = total > 0 ? errors / total : 0

    // Per-connection event totals (within window)
    const perConnection = new Map<string, number>()
    for (const e of events) perConnection.set(e.connectionId, (perConnection.get(e.connectionId) ?? 0) + 1)
    const byConnection = connections.map((c) => ({
      id: c.id,
      name: c.name,
      status: c.status,
      eventsInWindow: perConnection.get(c.id) ?? 0,
      lifetimeEvents: c.totalEvents,
      lifetimeErrors: c.errorCount,
    }))

    return NextResponse.json({
      windowHours: hours,
      total,
      errors,
      errorRate,
      connectedCount: connections.filter((c) => c.status === 'connected').length,
      totalConnections: connections.length,
      timeseries,
      topTopics,
      byConnection,
    })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
