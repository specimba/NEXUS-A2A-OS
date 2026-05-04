/**
 * GET /api/models
 *
 * Returns all model routes with:
 * - Full model details (capabilities, context window, cost)
 * - Provider information
 * - Tier classification
 * - Health and performance data
 * - Cost per 1k tokens
 */

import { NextResponse } from 'next/server'
import { getAllRoutes, type ModelRoute, type ModelTier } from '@/lib/ai-provider-bridge'

// ── Cost data per provider/model (approximate, per 1k tokens) ─────

const COST_DATA: Record<string, { input: number; output: number }> = {
  // Free providers
  'z-ai/glm-4.7': { input: 0, output: 0 },
  'deepseek/deepseek-r1-0528:free': { input: 0, output: 0 },
  'arcee-ai/trinity-large-preview:free': { input: 0, output: 0 },
  'qwen/qwen3-coder:free': { input: 0, output: 0 },
  'stepfun/step-3.5-flash:free': { input: 0, output: 0 },
  'google/gemma-4-26b-a4b-it:free': { input: 0, output: 0 },
  'moonshotai/kimi-k2:free': { input: 0, output: 0 },
  'nvidia/llama-3.1-nemotron-70b-instruct:free': { input: 0, output: 0 },
  'llama-3.3-70b': { input: 0, output: 0 },
  'llama-3.1-8b': { input: 0, output: 0 },
  'llama-3.3-70b-versatile': { input: 0, output: 0 },
  'meta-llama/llama-4-scout-17b-16e-instruct': { input: 0, output: 0 },
  'deepseek-r1-distill-llama-70b': { input: 0, output: 0 },
  'mistral-large-latest': { input: 0.002, output: 0.006 },
  'mistral-small-latest': { input: 0.0002, output: 0.0006 },
  'codestral-latest': { input: 0, output: 0 },
  'accounts/fireworks/models/deepseek-v3': { input: 0, output: 0 },
  'accounts/fireworks/models/qwen3-vl-30b': { input: 0, output: 0 },
  'accounts/fireworks/models/llama4-maverick-instruct-basic': { input: 0, output: 0 },
  'accounts/fireworks/models/qwen3-235b-a22b': { input: 0, output: 0 },
  'llama-3.3-70b-instruct': { input: 0, output: 0 },
  'qwen-max': { input: 0, output: 0 },
  'qwen-plus-2025-07-28': { input: 0, output: 0 },
  'qwen3-vl-235b-a22b-thinking': { input: 0, output: 0 },
  'qwen2.5-vl-72b-instruct': { input: 0, output: 0 },
  'qwen2.5-14b-instruct': { input: 0, output: 0 },
  'qvq-max-2025-03-25': { input: 0, output: 0 },
  'qwen3-235b-a22b': { input: 0, output: 0 },
  'qwen3-30b-a3b': { input: 0, output: 0 },
  'qwq-32b': { input: 0, output: 0 },
  'deepseek-ai/DeepSeek-R1': { input: 0, output: 0 },
  'Qwen/Qwen3-235B-A22B': { input: 0, output: 0 },
  'meta-llama/Llama-4-Maverick-17B-128E': { input: 0, output: 0 },
}

// ── Domain classification for models ──────────────────────────────

function inferDomain(route: ModelRoute): string {
  if (route.capabilities.includes('vision')) return 'multimodal'
  if (route.capabilities.includes('completion') || route.capabilities.includes('fill')) return 'code-completion'
  if (route.capabilities.includes('tools')) return 'agentic'
  if (route.capabilities.includes('reasoning') && route.capabilities.includes('code')) return 'code-reasoning'
  if (route.capabilities.includes('reasoning')) return 'reasoning'
  if (route.capabilities.includes('code')) return 'code'
  return 'general'
}

// ── Types ──────────────────────────────────────────────────────────

interface ModelDetail {
  id: string
  displayName: string
  actualModel: string
  provider: string
  providerLabel: string
  tier: ModelTier
  domain: string
  isFree: boolean
  health: ModelRoute['health']
  latencyMs: number
  totalCalls: number
  successRate: number
  capabilities: string[]
  contextWindow: number
  rateLimitPerMin: number
  costPer1k: { input: number; output: number }
}

interface ModelsResponse {
  models: ModelDetail[]
  tiers: Record<ModelTier, string[]>
  providers: string[]
  domains: string[]
  summary: {
    totalModels: number
    freeModels: number
    healthyModels: number
    providers: number
  }
}

// ── GET Handler ────────────────────────────────────────────────────

export async function GET() {
  try {
    const allRoutes = getAllRoutes()

    const models: ModelDetail[] = allRoutes.map(route => {
      const cost = COST_DATA[route.actualModel] ?? { input: 0, output: 0 }
      return {
        id: route.id,
        displayName: route.displayName,
        actualModel: route.actualModel,
        provider: route.provider,
        providerLabel: route.providerLabel,
        tier: route.tier,
        domain: inferDomain(route),
        isFree: route.isFree,
        health: route.health,
        latencyMs: route.latencyMs,
        totalCalls: route.totalCalls,
        successRate: route.successRate,
        capabilities: route.capabilities,
        contextWindow: route.contextWindow,
        rateLimitPerMin: route.rateLimitPerMin,
        costPer1k: cost,
      }
    })

    // Group by tier
    const tiers: Record<ModelTier, string[]> = {
      reasoning: allRoutes.filter(r => r.tier === 'reasoning').map(r => r.id),
      balanced: allRoutes.filter(r => r.tier === 'balanced').map(r => r.id),
      fast: allRoutes.filter(r => r.tier === 'fast').map(r => r.id),
      free: allRoutes.filter(r => r.tier === 'free').map(r => r.id),
    }

    // Unique providers and domains
    const providers = [...new Set(allRoutes.map(r => r.provider))].sort()
    const domains = [...new Set(models.map(m => m.domain))].sort()

    const response: ModelsResponse = {
      models,
      tiers,
      providers,
      domains,
      summary: {
        totalModels: allRoutes.length,
        freeModels: allRoutes.filter(r => r.isFree).length,
        healthyModels: allRoutes.filter(r => r.health === 'healthy').length,
        providers: providers.length,
      },
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('[/api/models] Error:', error)
    return NextResponse.json(
      {
        error: 'Failed to fetch model registry',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}
