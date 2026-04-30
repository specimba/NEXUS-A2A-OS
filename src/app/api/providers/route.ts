/**
 * GET /api/providers
 *
 * Returns all provider statuses with:
 * - Key health (from api-key-manager)
 * - Available models (from ai-provider-bridge MODEL_ROUTES)
 * - Rate limits (from rate-limiter)
 */

import { NextResponse } from 'next/server'
import { getAllProviderKeyStatus, getProviderKeyStatus } from '@/lib/api-key-manager'
import {
  MODEL_ROUTES,
  getModelForTier,
  getAllProviderStatuses,
  type ModelRoute,
  type ModelTier,
  type ProviderStatus,
} from '@/lib/ai-provider-bridge'
import { getRateLimitStatus, PROVIDER_RATE_LIMITS, type RateLimitResult } from '@/lib/rate-limiter'

export interface ProviderDetailResponse {
  provider: string
  label: string
  isAvailable: boolean
  activeModels: number
  totalModels: number
  health: 'healthy' | 'degraded' | 'down' | 'unknown'
  rateLimitRemaining: number
  avgLatencyMs: number
  models: Array<{
    id: string
    tier: ModelTier
    displayName: string
    actualModel: string
    health: ModelRoute['health']
    latencyMs: number
    totalCalls: number
    successRate: number
    capabilities: string[]
    contextWindow: number
    rateLimitPerMin: number
    isFree: boolean
  }>
  keyStatus: {
    totalKeys: number
    healthyKeys: number
    hasAvailableKey: boolean
    activeKeyMasked: string | null
  }
  rateLimits: {
    rpm: number
    rpd: number
    remaining: { rpm: number; rpd: number }
    isCooldown: boolean
    cooldownRemainingMs: number
    description: string
  }
}

export interface ProvidersListResponse {
  providers: ProviderDetailResponse[]
  modelRoutes: Array<{
    id: string
    tier: ModelTier
    displayName: string
    actualModel: string
    provider: string
    providerLabel: string
    isFree: boolean
    health: ModelRoute['health']
  }>
  tiers: Record<ModelTier, string[]>
  summary: {
    totalProviders: number
    availableProviders: number
    totalModels: number
    healthyModels: number
  }
}

export async function GET() {
  try {
    // Get provider statuses from ai-provider-bridge
    const providerStatuses: ProviderStatus[] = getAllProviderStatuses()

    // Get key statuses from api-key-manager
    const allKeyStatuses = getAllProviderKeyStatus()

    // Get unique providers from MODEL_ROUTES
    const providerSet = new Set(MODEL_ROUTES.map(r => r.provider))

    // Build detailed provider responses
    const providers: ProviderDetailResponse[] = []

    for (const provider of providerSet) {
      const status = providerStatuses.find(s => s.provider === provider)
      const keyStatus = allKeyStatuses[provider]
      let rateLimitInfo: RateLimitResult

      try {
        rateLimitInfo = getRateLimitStatus(provider)
      } catch {
        // Provider might not be in rate limiter config
        const config = PROVIDER_RATE_LIMITS[provider]
        rateLimitInfo = {
          allowed: true,
          retryAfterMs: 0,
          remaining: { rpm: config?.rpm ?? 10, rpd: config?.rpd ?? 100 },
          limits: config ?? {
            rpm: 10,
            rpd: 100,
            description: 'Default limits',
            color: '#6b7280',
            baseUrl: '',
          },
          isCooldown: false,
          isDedup: false,
        }
      }

      // Get models for this provider
      const providerModels = MODEL_ROUTES.filter(r => r.provider === provider).map(r => ({
        id: r.id,
        tier: r.tier,
        displayName: r.displayName,
        actualModel: r.actualModel,
        health: r.health,
        latencyMs: r.latencyMs,
        totalCalls: r.totalCalls,
        successRate: r.successRate,
        capabilities: r.capabilities,
        contextWindow: r.contextWindow,
        rateLimitPerMin: r.rateLimitPerMin,
        isFree: r.isFree,
      }))

      // Get active key masked value
      let activeKeyMasked: string | null = null
      if (keyStatus) {
        const activeKey = keyStatus.keys.find(k => k.isActive && k.health !== 'no_key')
        activeKeyMasked = activeKey?.masked ?? null
      }

      providers.push({
        provider,
        label: status?.label ?? provider,
        isAvailable: status?.isAvailable ?? false,
        activeModels: status?.activeModels ?? 0,
        totalModels: status?.totalModels ?? 0,
        health: status?.health ?? 'unknown',
        rateLimitRemaining: status?.rateLimitRemaining ?? 0,
        avgLatencyMs: status?.avgLatencyMs ?? 0,
        models: providerModels,
        keyStatus: {
          totalKeys: keyStatus?.totalKeys ?? 0,
          healthyKeys: keyStatus?.healthyKeys ?? 0,
          hasAvailableKey: keyStatus?.hasAvailableKey ?? false,
          activeKeyMasked,
        },
        rateLimits: {
          rpm: rateLimitInfo.limits.rpm,
          rpd: rateLimitInfo.limits.rpd,
          remaining: rateLimitInfo.remaining,
          isCooldown: rateLimitInfo.isCooldown,
          cooldownRemainingMs: rateLimitInfo.isCooldown ? rateLimitInfo.retryAfterMs : 0,
          description: rateLimitInfo.limits.description,
        },
      })
    }

    // Build model routes summary (lightweight)
    const modelRoutes = MODEL_ROUTES.map(r => ({
      id: r.id,
      tier: r.tier,
      displayName: r.displayName,
      actualModel: r.actualModel,
      provider: r.provider,
      providerLabel: r.providerLabel,
      isFree: r.isFree,
      health: r.health,
    }))

    // Group models by tier
    const tiers: Record<ModelTier, string[]> = {
      reasoning: MODEL_ROUTES.filter(r => r.tier === 'reasoning').map(r => r.id),
      balanced: MODEL_ROUTES.filter(r => r.tier === 'balanced').map(r => r.id),
      fast: MODEL_ROUTES.filter(r => r.tier === 'fast').map(r => r.id),
      free: MODEL_ROUTES.filter(r => r.tier === 'free').map(r => r.id),
    }

    // Summary stats
    const healthyModels = MODEL_ROUTES.filter(r => r.health === 'healthy').length
    const availableProviders = providers.filter(p => p.isAvailable).length

    const response: ProvidersListResponse = {
      providers,
      modelRoutes,
      tiers,
      summary: {
        totalProviders: providers.length,
        availableProviders,
        totalModels: MODEL_ROUTES.length,
        healthyModels,
      },
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('[/api/providers] Error:', error)
    return NextResponse.json(
      {
        error: 'Failed to fetch provider statuses',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}
