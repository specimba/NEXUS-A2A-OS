import { NextResponse } from 'next/server'
import { getAllRateLimitStatus, PROVIDER_RATE_LIMITS } from '@/lib/rate-limiter'

/**
 * Bridge Health API Route
 *
 * Exposes SecretStore.check_health() equivalent data to the frontend.
 * Shows per-provider API key pool status, rate limits, and health.
 * Now includes rate limit status (remaining requests) per provider.
 *
 * GET /api/health/bridge — Full bridge health report
 */

// Provider configuration (mirrors Python PROVIDER_CONFIG from bridge/secrets.py)
const PROVIDER_CONFIG = {
  openrouter: {
    base_url: process.env.OPENROUTER_BASE_URL || 'https://openrouter.ai/api/v1',
    rpm_limit: 20,
    rpd_limit: 500,
    description: 'Primary multi-model provider. Routes to 200+ models.',
  },
  jina: {
    base_url: 'https://api.jina.ai/v1',
    rpm_limit: 20,
    rpd_limit: 500,
    description: 'Search and reader API for web content extraction.',
  },
  kilocode: {
    base_url: 'https://proxy.kilocode.ai/v1',
    rpm_limit: 20,
    rpd_limit: 500,
    description: 'Secondary multi-model provider. Backup for OpenRouter.',
  },
  cerebras: {
    base_url: 'https://api.cerebras.ai/v1',
    rpm_limit: 30,
    rpd_limit: 1000,
    description: 'Ultra-fast inference provider for low-latency tasks.',
  },
  openai: {
    base_url: 'https://api.openai.com/v1',
    rpm_limit: 10,
    rpd_limit: 200,
    description: 'OpenAI direct API for GPT-4 and o-series models.',
  },
} as const

// Simulated health state based on environment variables (keys present = healthy)
function getProviderHealth() {
  const envKeys: Record<string, string> = {
    openrouter: process.env.OPENROUTER_API_KEY ?? '',
    jina: process.env.JINA_API_KEY ?? '',
    kilocode: process.env.KILOCODE_API_KEY ?? '',
    cerebras: process.env.CEREBRAS_API_KEY ?? '',
    openai: process.env.OPENAI_API_KEY ?? '',
  }

  // Get rate limit statuses for all providers
  const rateLimitStatuses = getAllRateLimitStatus()

  return Object.entries(PROVIDER_CONFIG).map(([provider, config]) => {
    const hasKey = Boolean(envKeys[provider])
    const keyPrefix = envKeys[provider] ? envKeys[provider].slice(0, 8) + '...' : 'N/A'
    const rateLimitStatus = rateLimitStatuses[provider]
    const rateLimitConfig = PROVIDER_RATE_LIMITS[provider]

    return {
      provider,
      status: hasKey ? 'Active' : 'No Keys',
      pool_size: hasKey ? 1 : 0,
      active_key_masked: keyPrefix,
      rpm_limit: config.rpm_limit,
      rpd_limit: config.rpd_limit,
      description: config.description,
      healthy: hasKey,
      base_url: config.base_url,
      circuit_breaker: hasKey ? 'CLOSED' as const : 'OPEN' as const,
      // Rate limit information
      rate_limit: rateLimitStatus
        ? {
            remaining_rpm: rateLimitStatus.remaining.rpm,
            remaining_rpd: rateLimitStatus.remaining.rpd,
            is_rate_limited: !rateLimitStatus.allowed,
            retry_after_ms: rateLimitStatus.retryAfterMs,
            conservative_rpm_limit: rateLimitConfig?.rpm ?? 10,
            conservative_rpd_limit: rateLimitConfig?.rpd ?? 200,
          }
        : null,
    }
  })
}

export async function GET() {
  try {
    const providers = getProviderHealth()
    const healthyCount = providers.filter(p => p.healthy).length
    const degradedCount = providers.filter(p => !p.healthy).length
    const allHealthy = degradedCount === 0
    const rateLimitedCount = providers.filter(p => p.rate_limit?.is_rate_limited).length

    return NextResponse.json({
      timestamp: new Date().toISOString(),
      overall_status: allHealthy ? 'ALL_HEALTHY' : 'SOME_DEGRADED',
      rate_limit_status: rateLimitedCount > 0 ? 'RATE_LIMITED' : 'NOMINAL',
      providers,
      summary: {
        total: providers.length,
        healthy: healthyCount,
        degraded: degradedCount,
        health_percentage: Math.round((healthyCount / providers.length) * 100),
        rate_limited_providers: rateLimitedCount,
      },
      circuit_breakers: providers.reduce<Record<string, string>>((acc, p) => {
        acc[p.provider] = p.circuit_breaker
        return acc
      }, {}),
      rate_limits: providers.reduce<Record<string, {
        remaining_rpm: number
        remaining_rpd: number
        is_rate_limited: boolean
      }>>((acc, p) => {
        if (p.rate_limit) {
          acc[p.provider] = {
            remaining_rpm: p.rate_limit.remaining_rpm,
            remaining_rpd: p.rate_limit.remaining_rpd,
            is_rate_limited: p.rate_limit.is_rate_limited,
          }
        }
        return acc
      }, {}),
      last_check: Date.now(),
    })
  } catch (error) {
    console.error('Bridge Health API error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
