import { NextRequest, NextResponse } from 'next/server'
import {
  checkRateLimit,
  recordRequest,
  enterCooldown,
  recordSuccess,
  recordError,
  dequeueNextRequest,
  completeQueuedRequest,
  failQueuedRequest,
  PROVIDER_RATE_LIMITS,
  type RateLimitResult,
} from '@/lib/rate-limiter'
import { getAuthHeaders, recordKeySuccess, recordKey429, recordKeyError } from '@/lib/api-key-manager'
import { apiCache, buildCacheKey, CACHE_TTL } from '@/lib/api-cache'
import { db } from '@/lib/db'

/**
 * API Proxy Route — All external API calls go through this proxy.
 * Applies rate limiting, caching, queueing, and logging.
 *
 * POST /api/proxy
 * Body: { provider, endpoint, method?, body?, headers?, cacheTtl?, dedupTtl? }
 */

interface ProxyRequestBody {
  provider: string
  endpoint: string
  method?: string
  body?: unknown
  headers?: Record<string, string>
  cacheTtl?: number
  dedupTtl?: number
}

export async function POST(request: NextRequest) {
  const startTime = Date.now()

  try {
    const body: ProxyRequestBody = await request.json()
    const {
      provider,
      endpoint,
      method = 'POST',
      body: requestBody,
      headers: extraHeaders,
      cacheTtl,
      dedupTtl,
    } = body

    if (!provider || !endpoint) {
      return NextResponse.json({ success: false, error: 'Missing required fields: provider, endpoint' }, { status: 400 })
    }

    const providerKey = provider.toLowerCase()
    const config = PROVIDER_RATE_LIMITS[providerKey]

    if (!config) {
      return NextResponse.json(
        { success: false, error: `Unknown provider: ${provider}. Valid: ${Object.keys(PROVIDER_RATE_LIMITS).join(', ')}` },
        { status: 400 }
      )
    }

    // ── Check Cache First ───────────────────────────────────────
    const cacheKey = buildCacheKey(providerKey, endpoint, JSON.stringify(requestBody ?? ''))
    if (cacheTtl !== 0) {
      const cached = apiCache.get(cacheKey)
      if (cached) {
        const responseTimeMs = Date.now() - startTime
        void logToDatabase({ provider: providerKey, endpoint, method, statusCode: 200, wasRateLimited: false, wasCached: true, wasDeduped: false, responseTimeMs })
        const rateLimitResult = checkRateLimit(providerKey)
        return NextResponse.json({
          success: true, status: 200, data: cached,
          meta: { provider: providerKey, endpoint, wasCached: true, wasDeduped: false, wasRateLimited: false, wasQueued: false, responseTimeMs, rateLimit: { remaining: rateLimitResult.remaining, limits: { rpm: config.rpm, rpd: config.rpd } } },
        })
      }
    }

    // ── Check Rate Limit ────────────────────────────────────────
    const bodyStr = requestBody ? JSON.stringify(requestBody) : undefined
    const rateLimitResult: RateLimitResult = checkRateLimit(providerKey, endpoint, bodyStr, dedupTtl)

    // ── Handle Dedup Hit ────────────────────────────────────────
    if (rateLimitResult.isDedup && rateLimitResult.dedupResult !== undefined) {
      const responseTimeMs = Date.now() - startTime
      void logToDatabase({ provider: providerKey, endpoint, method, statusCode: 200, wasRateLimited: false, wasCached: false, wasDeduped: true, responseTimeMs })
      return NextResponse.json({
        success: true, status: 200, data: rateLimitResult.dedupResult,
        meta: { provider: providerKey, endpoint, wasCached: false, wasDeduped: true, wasRateLimited: false, wasQueued: false, responseTimeMs, rateLimit: { remaining: rateLimitResult.remaining, limits: { rpm: config.rpm, rpd: config.rpd } } },
      })
    }

    // ── Handle Rate Limited ─────────────────────────────────────
    if (!rateLimitResult.allowed) {
      const responseTimeMs = Date.now() - startTime
      void logToDatabase({ provider: providerKey, endpoint, method, statusCode: 429, wasRateLimited: true, wasCached: false, wasDeduped: false, responseTimeMs, errorMessage: `Rate limited. Retry after ${Math.ceil(rateLimitResult.retryAfterMs / 1000)}s` })

      if (rateLimitResult.queueId) {
        return NextResponse.json({
          success: false, status: 202,
          error: `Rate limited. Request queued (position: ${rateLimitResult.queuePosition}). Retry after ${Math.ceil(rateLimitResult.retryAfterMs / 1000)}s`,
          meta: { provider: providerKey, endpoint, wasCached: false, wasDeduped: false, wasRateLimited: true, wasQueued: true, queueId: rateLimitResult.queueId, responseTimeMs, rateLimit: { remaining: rateLimitResult.remaining, limits: { rpm: config.rpm, rpd: config.rpd } } },
        }, { status: 202 })
      }

      return NextResponse.json({
        success: false, status: 429,
        error: `Rate limited. Retry after ${Math.ceil(rateLimitResult.retryAfterMs / 1000)}s`,
        meta: { provider: providerKey, endpoint, wasCached: false, wasDeduped: false, wasRateLimited: true, wasQueued: false, responseTimeMs, rateLimit: { remaining: rateLimitResult.remaining, limits: { rpm: config.rpm, rpd: config.rpd } } },
      }, { status: 429 })
    }

    // ── Forward Request to Provider ─────────────────────────────
    const authHeaders = getAuthHeaders(providerKey)
    if (!authHeaders) {
      return NextResponse.json({ success: false, error: `No API key configured for provider: ${provider}` }, { status: 403 })
    }

    const url = `${config.baseUrl}${endpoint}`
    const fetchHeaders: Record<string, string> = { 'Content-Type': 'application/json', ...authHeaders, ...extraHeaders }

    try {
      const fetchResponse = await fetch(url, {
        method,
        headers: fetchHeaders,
        body: method !== 'GET' ? JSON.stringify(requestBody) : undefined,
      })

      const responseTimeMs = Date.now() - startTime
      let responseData: unknown
      try { responseData = await fetchResponse.json() } catch { responseData = await fetchResponse.text() }

      // ── Handle 429 from Provider ─────────────────────────────
      if (fetchResponse.status === 429) {
        const retryAfter = fetchResponse.headers.get('retry-after')
        const retryAfterSeconds = retryAfter ? parseInt(retryAfter, 10) : 60
        enterCooldown(providerKey, retryAfterSeconds)
        recordKey429(providerKey, retryAfterSeconds)
        recordError(providerKey, '429 Too Many Requests')
        void logToDatabase({ provider: providerKey, endpoint, method, statusCode: 429, wasRateLimited: true, wasCached: false, wasDeduped: false, responseTimeMs, errorMessage: 'Provider returned 429' })
        return NextResponse.json({
          success: false, status: 429, error: `Provider rate limit hit. Retry after ${retryAfterSeconds}s. Key rotated.`, data: responseData,
          meta: { provider: providerKey, endpoint, wasCached: false, wasDeduped: false, wasRateLimited: true, wasQueued: false, responseTimeMs, rateLimit: { remaining: { rpm: 0, rpd: 0 }, limits: { rpm: config.rpm, rpd: config.rpd } } },
        }, { status: 429 })
      }

      // ── Handle Other Errors ───────────────────────────────────
      if (!fetchResponse.ok) {
        recordKeyError(providerKey, `${fetchResponse.status} ${fetchResponse.statusText}`)
        recordError(providerKey, `${fetchResponse.status}: ${JSON.stringify(responseData).slice(0, 200)}`)
        void logToDatabase({ provider: providerKey, endpoint, method, statusCode: fetchResponse.status, wasRateLimited: false, wasCached: false, wasDeduped: false, responseTimeMs, errorMessage: `${fetchResponse.status} ${fetchResponse.statusText}` })
        return NextResponse.json({
          success: false, status: fetchResponse.status, error: `Provider returned ${fetchResponse.status}`, data: responseData,
          meta: { provider: providerKey, endpoint, wasCached: false, wasDeduped: false, wasRateLimited: false, wasQueued: false, responseTimeMs, rateLimit: { remaining: rateLimitResult.remaining, limits: { rpm: config.rpm, rpd: config.rpd } } },
        }, { status: fetchResponse.status })
      }

      // ── Success ──────────────────────────────────────────────
      recordRequest(providerKey, endpoint, bodyStr, responseData, dedupTtl)
      recordSuccess(providerKey)
      recordKeySuccess(providerKey)

      const effectiveCacheTtl = cacheTtl ?? CACHE_TTL.DEFAULT
      if (effectiveCacheTtl > 0) {
        apiCache.set(cacheKey, responseData, effectiveCacheTtl)
      }

      const tokensUsed = extractTokensUsed(responseData)
      void logToDatabase({ provider: providerKey, endpoint, method, statusCode: fetchResponse.status, wasRateLimited: false, wasCached: false, wasDeduped: false, responseTimeMs, tokensUsed })
      void processQueue(providerKey)

      return NextResponse.json({
        success: true, status: fetchResponse.status, data: responseData,
        meta: { provider: providerKey, endpoint, wasCached: false, wasDeduped: false, wasRateLimited: false, wasQueued: false, responseTimeMs, rateLimit: { remaining: rateLimitResult.remaining, limits: { rpm: config.rpm, rpd: config.rpd } } },
      })

    } catch (fetchError) {
      const responseTimeMs = Date.now() - startTime
      const errorMessage = fetchError instanceof Error ? fetchError.message : String(fetchError)
      recordKeyError(providerKey, errorMessage)
      recordError(providerKey, errorMessage)
      void logToDatabase({ provider: providerKey, endpoint, method, statusCode: 0, wasRateLimited: false, wasCached: false, wasDeduped: false, responseTimeMs, errorMessage })
      return NextResponse.json({
        success: false, status: 502, error: `Provider request failed: ${errorMessage}`,
        meta: { provider: providerKey, endpoint, wasCached: false, wasDeduped: false, wasRateLimited: false, wasQueued: false, responseTimeMs, rateLimit: { remaining: rateLimitResult.remaining, limits: { rpm: config.rpm, rpd: config.rpd } } },
      }, { status: 502 })
    }
  } catch (error) {
    return NextResponse.json({ success: false, error: `Internal proxy error: ${error instanceof Error ? error.message : String(error)}` }, { status: 500 })
  }
}

/** GET /api/proxy — Get proxy status and queue information */
export async function GET() {
  try {
    const { getAllProviderFullStatus, getAllQueueDetails, getDedupStats } = await import('@/lib/rate-limiter')
    const { getAllProviderKeyStatus } = await import('@/lib/api-key-manager')
    const { apiCache: cache } = await import('@/lib/api-cache')

    const providerStatuses = getAllProviderFullStatus()
    const keyStatuses = getAllProviderKeyStatus()
    const queueDetails = getAllQueueDetails()
    const dedupStats = getDedupStats()
    const cacheStats = cache.getStats()

    const recentLogs = await db.rateLimitLog.findMany({ take: 20, orderBy: { createdAt: 'desc' } })

    return NextResponse.json({
      timestamp: new Date().toISOString(),
      providers: providerStatuses,
      keys: keyStatuses,
      queues: queueDetails,
      dedup: dedupStats,
      cache: cacheStats,
      recentLogs: recentLogs.map(log => ({
        id: log.id, provider: log.provider, endpoint: log.endpoint, statusCode: log.statusCode,
        wasRateLimited: log.wasRateLimited, wasCached: log.wasCached, wasDeduped: log.wasDeduped,
        responseTimeMs: log.responseTimeMs, createdAt: log.createdAt,
      })),
      summary: {
        totalProviders: providerStatuses.length,
        healthyProviders: providerStatuses.filter(p => !p.isCooldown).length,
        rateLimitedProviders: providerStatuses.filter(p => p.isCooldown).length,
        totalQueueSize: Object.values(queueDetails).reduce((sum, q) => sum + q.length, 0),
        cacheHitRate: cacheStats.hitRate,
      },
    })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

// ── Helpers ───────────────────────────────────────────────────────

interface LogEntry {
  provider: string; endpoint: string; method: string; statusCode: number
  wasRateLimited: boolean; wasCached: boolean; wasDeduped: boolean
  responseTimeMs: number; tokensUsed?: number; errorMessage?: string; requestBody?: string
}

async function logToDatabase(entry: LogEntry): Promise<void> {
  try {
    await db.rateLimitLog.create({
      data: {
        provider: entry.provider, endpoint: entry.endpoint, method: entry.method,
        statusCode: entry.statusCode, wasRateLimited: entry.wasRateLimited,
        wasCached: entry.wasCached, wasDeduped: entry.wasDeduped,
        responseTimeMs: entry.responseTimeMs, tokensUsed: entry.tokensUsed ?? 0,
        errorMessage: entry.errorMessage, requestBody: entry.requestBody,
      },
    })
  } catch { /* don't fail request if logging fails */ }
}

function extractTokensUsed(response: unknown): number {
  if (!response || typeof response !== 'object') return 0
  const obj = response as Record<string, unknown>
  const usage = obj.usage as Record<string, unknown> | undefined
  if (usage && typeof usage.total_tokens === 'number') return usage.total_tokens
  return 0
}

async function processQueue(provider: string): Promise<void> {
  const nextRequest = dequeueNextRequest(provider)
  if (!nextRequest) return
  const rateCheck = checkRateLimit(provider)
  if (!rateCheck.allowed) {
    failQueuedRequest(provider, nextRequest.id, 'Still rate limited')
    return
  }
  completeQueuedRequest(provider, nextRequest.id, { status: 'ready_for_retry' })
}
