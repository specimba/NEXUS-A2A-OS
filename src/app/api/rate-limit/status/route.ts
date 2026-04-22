import { NextRequest, NextResponse } from 'next/server'
import {
  getAllProviderFullStatus,
  getProviderFullStatus,
  getAllQueueDetails,
  getQueueDetails,
  getDedupStats,
  PROVIDER_RATE_LIMITS,
} from '@/lib/rate-limiter'
import { getAllProviderKeyStatus, getProviderKeyStatus } from '@/lib/api-key-manager'
import { apiCache } from '@/lib/api-cache'
import { db } from '@/lib/db'

/**
 * Rate Limit Status API
 * GET /api/rate-limit/status — Comprehensive rate limit status
 * GET /api/rate-limit/status?provider=openrouter — Specific provider status
 */

export async function GET(request: NextRequest) {
  try {
    const provider = request.nextUrl.searchParams.get('provider')
    if (provider) {
      return NextResponse.json(await getSingleProviderStatus(provider))
    }
    return NextResponse.json(await getAllStatus())
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

async function getSingleProviderStatus(provider: string) {
  const status = getProviderFullStatus(provider)
  const keyStatus = getProviderKeyStatus(provider)
  const queueDetails = getQueueDetails(provider)
  const cacheStats = apiCache.getStats()

  const recentLogs = await db.rateLimitLog.findMany({ where: { provider }, take: 50, orderBy: { createdAt: 'desc' } })

  const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000)
  const usageHistory = await db.rateLimitLog.findMany({ where: { provider, createdAt: { gte: twentyFourHoursAgo } }, orderBy: { createdAt: 'asc' } })
  const hourlyUsage = groupByHour(usageHistory)

  return { provider: status, keys: keyStatus, queue: queueDetails, cache: cacheStats, recentLogs, hourlyUsage }
}

async function getAllStatus() {
  const providerStatuses = getAllProviderFullStatus()
  const keyStatuses = getAllProviderKeyStatus()
  const queueDetails = getAllQueueDetails()
  const dedupStats = getDedupStats()
  const cacheStats = apiCache.getStats()

  const totalRequests = await db.rateLimitLog.count()
  const rateLimitedCount = await db.rateLimitLog.count({ where: { wasRateLimited: true } })
  const cachedCount = await db.rateLimitLog.count({ where: { wasCached: true } })
  const dedupedCount = await db.rateLimitLog.count({ where: { wasDeduped: true } })
  const errorCount = await db.rateLimitLog.count({ where: { statusCode: { gte: 400 } } })

  const providerStats: Record<string, { total: number; rateLimited: number; cached: number; errors: number; avgResponseTime: number }> = {}

  for (const p of Object.keys(PROVIDER_RATE_LIMITS)) {
    const logs = await db.rateLimitLog.findMany({ where: { provider: p }, take: 100, orderBy: { createdAt: 'desc' } })
    providerStats[p] = {
      total: logs.length,
      rateLimited: logs.filter(l => l.wasRateLimited).length,
      cached: logs.filter(l => l.wasCached).length,
      errors: logs.filter(l => l.statusCode >= 400).length,
      avgResponseTime: logs.length > 0 ? Math.round(logs.reduce((s, l) => s + l.responseTimeMs, 0) / logs.length) : 0,
    }
  }

  const summary = {
    totalProviders: providerStatuses.length,
    healthyProviders: providerStatuses.filter(p => !p.isCooldown).length,
    rateLimitedProviders: providerStatuses.filter(p => p.isCooldown).length,
    totalRequests,
    rateLimitedCount,
    cachedCount,
    dedupedCount,
    errorCount,
    totalQueueSize: Object.values(queueDetails).reduce((sum, q) => sum + q.length, 0),
    cacheHitRate: cacheStats.hitRate,
    dedupSize: dedupStats.size,
  }

  return { timestamp: new Date().toISOString(), summary, providers: providerStatuses, keys: keyStatuses, queues: queueDetails, dedup: dedupStats, cache: { ...cacheStats, maxSize: cacheStats.maxSize, evictions: cacheStats.evictions }, providerStats }
}

function groupByHour(logs: Array<{ createdAt: Date; statusCode: number; wasRateLimited: boolean; responseTimeMs: number }>): Array<{ hour: string; requests: number; errors: number; rateLimited: number; avgResponseTime: number }> {
  const groups: Record<string, { requests: number; errors: number; rateLimited: number; totalTime: number }> = {}

  for (const log of logs) {
    const hour = new Date(log.createdAt).toISOString().slice(0, 13) + ':00'
    if (!groups[hour]) groups[hour] = { requests: 0, errors: 0, rateLimited: 0, totalTime: 0 }
    groups[hour].requests++
    if (log.statusCode >= 400) groups[hour].errors++
    if (log.wasRateLimited) groups[hour].rateLimited++
    groups[hour].totalTime += log.responseTimeMs
  }

  return Object.entries(groups).map(([hour, data]) => ({
    hour, requests: data.requests, errors: data.errors, rateLimited: data.rateLimited,
    avgResponseTime: data.requests > 0 ? Math.round(data.totalTime / data.requests) : 0,
  }))
}
