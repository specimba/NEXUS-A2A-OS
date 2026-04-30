/**
 * GET /api/providers/quotas
 *
 * Returns quota information for each provider, estimated from
 * the rate limiter state. Shows:
 * - Rate limit remaining (RPM + RPD)
 * - Cooldown status
 * - Total requests made
 * - Key health summary
 */

import { NextResponse } from 'next/server'
import { getAllProviderKeyStatus } from '@/lib/api-key-manager'
import {
  getRateLimitStatus,
  getProviderFullStatus,
  getAllProviderFullStatus,
  PROVIDER_RATE_LIMITS,
  type ProviderFullStatus,
} from '@/lib/rate-limiter'
import { getAllRoutes, type ModelTier } from '@/lib/ai-provider-bridge'

// ── Types ──────────────────────────────────────────────────────────

interface ProviderQuotaInfo {
  provider: string
  description: string
  rateLimits: {
    rpm: {
      limit: number
      used: number
      remaining: number
      percentUsed: number
    }
    rpd: {
      limit: number
      used: number
      remaining: number
      percentUsed: number
    }
  }
  cooldown: {
    isActive: boolean
    until: number | null
    remainingMs: number
    reason: string | null
  }
  requestStats: {
    totalRequests: number
    totalRejected: number
    consecutive429s: number
  }
  keyHealth: {
    totalKeys: number
    healthyKeys: number
    hasAvailableKey: boolean
    primaryMasked: string | null
  }
  models: Array<{
    id: string
    displayName: string
    tier: ModelTier
    rateLimitPerMin: number
  }>
  queue: {
    pending: number
    processing: number
    completed: number
  }
  cache: {
    size: number
    hitRate: number
    hits: number
    misses: number
  }
}

interface QuotasResponse {
  providers: ProviderQuotaInfo[]
  summary: {
    totalProviders: number
    providersInCooldown: number
    totalRequestsToday: number
    totalKeysAvailable: number
    overallHealth: 'healthy' | 'degraded' | 'critical'
  }
}

// ── GET Handler ────────────────────────────────────────────────────

export async function GET() {
  try {
    const allKeyStatuses = getAllProviderKeyStatus()
    const allProviderStatuses = getAllProviderFullStatus()

    // Get all unique providers from both rate limiter config and routes
    const allRoutes = getAllRoutes()
    const providerSet = new Set<string>()
    for (const provider of Object.keys(PROVIDER_RATE_LIMITS)) {
      providerSet.add(provider)
    }
    for (const route of allRoutes) {
      providerSet.add(route.provider)
    }

    const providers: ProviderQuotaInfo[] = []

    for (const provider of providerSet) {
      // Get full status from rate limiter
      let fullStatus: ProviderFullStatus
      try {
        fullStatus = getProviderFullStatus(provider)
      } catch {
        // Provider not in rate limiter, build minimal status
        const config = PROVIDER_RATE_LIMITS[provider] ?? {
          rpm: 10,
          rpd: 100,
          description: 'Default limits',
          color: '#6b7280',
          baseUrl: '',
        }
        fullStatus = {
          provider,
          config,
          rpm: { used: 0, limit: config.rpm, remaining: config.rpm, percentUsed: 0 },
          rpd: { used: 0, limit: config.rpd, remaining: config.rpd, percentUsed: 0 },
          isCooldown: false,
          cooldownUntil: 0,
          cooldownRemainingMs: 0,
          consecutive429s: 0,
          lastError: null,
          totalRequests: 0,
          totalRejected: 0,
          queue: { pending: 0, processing: 0, completed: 0 },
          dedup: { size: 0, hitRate: 0 },
          cache: { size: 0, hitRate: 0, hits: 0, misses: 0 },
          keyHealth: { hasKey: false, keyMasked: 'N/A', lastUsed: null },
        }
      }

      // Get key status
      const keyStatus = allKeyStatuses[provider]

      // Get models for this provider
      const providerModels = allRoutes
        .filter(r => r.provider === provider)
        .map(r => ({
          id: r.id,
          displayName: r.displayName,
          tier: r.tier,
          rateLimitPerMin: r.rateLimitPerMin,
        }))

      // Build quota info
      providers.push({
        provider,
        description: fullStatus.config.description,
        rateLimits: {
          rpm: {
            limit: fullStatus.rpm.limit,
            used: fullStatus.rpm.used,
            remaining: fullStatus.rpm.remaining,
            percentUsed: fullStatus.rpm.percentUsed,
          },
          rpd: {
            limit: fullStatus.rpd.limit,
            used: fullStatus.rpd.used,
            remaining: fullStatus.rpd.remaining,
            percentUsed: fullStatus.rpd.percentUsed,
          },
        },
        cooldown: {
          isActive: fullStatus.isCooldown,
          until: fullStatus.cooldownUntil > 0 ? fullStatus.cooldownUntil : null,
          remainingMs: fullStatus.cooldownRemainingMs,
          reason: fullStatus.lastError,
        },
        requestStats: {
          totalRequests: fullStatus.totalRequests,
          totalRejected: fullStatus.totalRejected,
          consecutive429s: fullStatus.consecutive429s,
        },
        keyHealth: {
          totalKeys: keyStatus?.totalKeys ?? 0,
          healthyKeys: keyStatus?.healthyKeys ?? 0,
          hasAvailableKey: keyStatus?.hasAvailableKey ?? false,
          primaryMasked: fullStatus.keyHealth.keyMasked !== 'N/A'
            ? fullStatus.keyHealth.keyMasked
            : null,
        },
        models: providerModels,
        queue: {
          pending: fullStatus.queue.pending,
          processing: fullStatus.queue.processing,
          completed: fullStatus.queue.completed,
        },
        cache: {
          size: fullStatus.cache.size,
          hitRate: fullStatus.cache.hitRate,
          hits: fullStatus.cache.hits,
          misses: fullStatus.cache.misses,
        },
      })
    }

    // Build summary
    const providersInCooldown = providers.filter(p => p.cooldown.isActive).length
    const totalRequestsToday = providers.reduce((sum, p) => sum + p.rateLimits.rpd.used, 0)
    const totalKeysAvailable = providers.filter(p => p.keyHealth.hasAvailableKey).length

    let overallHealth: 'healthy' | 'degraded' | 'critical'
    if (providersInCooldown === 0 && totalKeysAvailable >= providers.length * 0.5) {
      overallHealth = 'healthy'
    } else if (providersInCooldown > providers.length * 0.5 || totalKeysAvailable === 0) {
      overallHealth = 'critical'
    } else {
      overallHealth = 'degraded'
    }

    const response: QuotasResponse = {
      providers,
      summary: {
        totalProviders: providers.length,
        providersInCooldown,
        totalRequestsToday,
        totalKeysAvailable,
        overallHealth,
      },
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('[/api/providers/quotas] Error:', error)
    return NextResponse.json(
      {
        error: 'Failed to fetch quota information',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}
