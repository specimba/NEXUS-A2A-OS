import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'

/**
 * Rate Limit Logs API
 * GET /api/rate-limit/logs — Get rate limit event logs from database
 * Query params: provider, limit, hours
 */
export async function GET(request: NextRequest) {
  try {
    const provider = request.nextUrl.searchParams.get('provider')
    const limit = parseInt(request.nextUrl.searchParams.get('limit') ?? '100', 10)
    const hours = parseInt(request.nextUrl.searchParams.get('hours') ?? '24', 10)

    const since = new Date(Date.now() - hours * 60 * 60 * 1000)

    const where: Record<string, unknown> = {
      createdAt: { gte: since },
    }
    if (provider) {
      where.provider = provider
    }

    const logs = await db.rateLimitLog.findMany({
      where,
      take: Math.min(limit, 500),
      orderBy: { createdAt: 'desc' },
      select: {
        id: true,
        provider: true,
        endpoint: true,
        method: true,
        statusCode: true,
        wasRateLimited: true,
        wasCached: true,
        wasDeduped: true,
        responseTimeMs: true,
        tokensUsed: true,
        errorMessage: true,
        createdAt: true,
      },
    })

    // Compute per-provider stats
    const providerStats: Record<string, {
      total: number
      rateLimited: number
      cached: number
      deduped: number
      errors: number
      avgResponseTime: number
      totalTokensUsed: number
    }> = {}

    for (const log of logs) {
      if (!providerStats[log.provider]) {
        providerStats[log.provider] = {
          total: 0, rateLimited: 0, cached: 0, deduped: 0,
          errors: 0, avgResponseTime: 0, totalTokensUsed: 0,
        }
      }
      const stats = providerStats[log.provider]
      stats.total++
      if (log.wasRateLimited) stats.rateLimited++
      if (log.wasCached) stats.cached++
      if (log.wasDeduped) stats.deduped++
      if (log.statusCode >= 400) stats.errors++
      stats.avgResponseTime += log.responseTimeMs
      stats.totalTokensUsed += log.tokensUsed
    }

    for (const stats of Object.values(providerStats)) {
      stats.avgResponseTime = stats.total > 0 ? Math.round(stats.avgResponseTime / stats.total) : 0
    }

    // Compute hourly breakdown for chart data
    const hourlyData: Array<{
      hour: string
      total: number
      rateLimited: number
      cached: number
      errors: number
      avgResponseTime: number
    }> = []

    const hourMap: Record<string, { total: number; rateLimited: number; cached: number; errors: number; totalTime: number }> = {}
    for (const log of logs) {
      const hour = new Date(log.createdAt).toISOString().slice(0, 13) + ':00'
      if (!hourMap[hour]) hourMap[hour] = { total: 0, rateLimited: 0, cached: 0, errors: 0, totalTime: 0 }
      const h = hourMap[hour]
      h.total++
      if (log.wasRateLimited) h.rateLimited++
      if (log.wasCached) h.cached++
      if (log.statusCode >= 400) h.errors++
      h.totalTime += log.responseTimeMs
    }

    for (const [hour, data] of Object.entries(hourMap)) {
      hourlyData.push({
        hour,
        total: data.total,
        rateLimited: data.rateLimited,
        cached: data.cached,
        errors: data.errors,
        avgResponseTime: data.total > 0 ? Math.round(data.totalTime / data.total) : 0,
      })
    }

    const totalLogs = logs.length
    const rateLimitedLogs = logs.filter(l => l.wasRateLimited).length
    const cachedLogs = logs.filter(l => l.wasCached).length
    const dedupedLogs = logs.filter(l => l.wasDeduped).length
    const errorLogs = logs.filter(l => l.statusCode >= 400).length

    return NextResponse.json({
      logs,
      providerStats,
      hourlyData,
      summary: {
        total: totalLogs,
        rateLimited: rateLimitedLogs,
        cached: cachedLogs,
        deduped: dedupedLogs,
        errors: errorLogs,
        rateLimitHitRate: totalLogs > 0 ? Math.round((rateLimitedLogs / totalLogs) * 1000) / 10 : 0,
        cacheHitRate: totalLogs > 0 ? Math.round((cachedLogs / totalLogs) * 1000) / 10 : 0,
        dedupRate: totalLogs > 0 ? Math.round((dedupedLogs / totalLogs) * 1000) / 10 : 0,
        errorRate: totalLogs > 0 ? Math.round((errorLogs / totalLogs) * 1000) / 10 : 0,
        avgResponseTime: totalLogs > 0 ? Math.round(logs.reduce((s, l) => s + l.responseTimeMs, 0) / totalLogs) : 0,
        totalTokensUsed: logs.reduce((s, l) => s + l.tokensUsed, 0),
      },
      timeRange: { hours, since },
    })
  } catch (error) {
    console.error('Rate limit logs API error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
