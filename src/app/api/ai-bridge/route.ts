import { NextRequest, NextResponse } from 'next/server'
import {
  getAllRoutes,
  getAllProviderStatuses,
  getModelForTier,
  getRequestOptimization,
  type ModelTier,
  type ModelRoute,
} from '@/lib/ai-provider-bridge'

/**
 * GET /api/ai-bridge
 * Returns all model routes and provider statuses.
 */
export async function GET() {
  try {
    const routes = getAllRoutes()
    const providers = getAllProviderStatuses()

    // Group routes by tier
    const routesByTier = {
      reasoning: routes.filter(r => r.tier === 'reasoning'),
      balanced: routes.filter(r => r.tier === 'balanced'),
      fast: routes.filter(r => r.tier === 'fast'),
      free: routes.filter(r => r.tier === 'free'),
    }

    // Summary stats
    const healthyCount = routes.filter(r => r.health === 'healthy').length
    const degradedCount = routes.filter(r => r.health === 'degraded').length
    const downCount = routes.filter(r => r.health === 'down').length
    const unknownCount = routes.filter(r => r.health === 'unknown').length

    return NextResponse.json({
      routes,
      routesByTier,
      providers,
      summary: {
        totalRoutes: routes.length,
        healthy: healthyCount,
        degraded: degradedCount,
        down: downCount,
        unknown: unknownCount,
        allFree: routes.every(r => r.isFree),
      },
    })
  } catch (error) {
    console.error('AI Bridge GET error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * POST /api/ai-bridge
 * Route a chat request through the AI Provider Bridge.
 *
 * Body: {
 *   tier: ModelTier,
 *   messages: { role: string, content: string }[],
 *   systemPrompt?: string,
 *   maxTokens?: number,
 *   temperature?: number,
 *   preferModel?: string
 * }
 *
 * Response: {
 *   response: string,
 *   model: ModelRoute (sanitized),
 *   latencyMs: number,
 *   optimized: boolean
 * }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { tier, messages, systemPrompt, maxTokens, temperature, preferModel } = body as {
      tier: string
      messages: { role: string; content: string }[]
      systemPrompt?: string
      maxTokens?: number
      temperature?: number
      preferModel?: string
    }

    // Validate tier
    const validTiers: ModelTier[] = ['reasoning', 'balanced', 'fast', 'free']
    if (!tier || !validTiers.includes(tier as ModelTier)) {
      return NextResponse.json(
        {
          error: `Invalid tier: "${tier}". Valid tiers: ${validTiers.join(', ')}`,
          validTiers,
        },
        { status: 400 }
      )
    }

    // Validate messages
    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return NextResponse.json(
        { error: 'Messages array is required and must not be empty' },
        { status: 400 }
      )
    }

    // Validate message format
    for (const msg of messages) {
      if (!msg.role || !msg.content) {
        return NextResponse.json(
          { error: 'Each message must have role and content fields' },
          { status: 400 }
        )
      }
    }

    // Step 1: Check if request can be handled locally (optimization)
    const optimization = getRequestOptimization(messages)
    if (optimization.optimized && optimization.response !== undefined) {
      const model = getModelForTier(tier as ModelTier)
      return NextResponse.json({
        response: optimization.response,
        model: sanitizeModel(model),
        latencyMs: 0,
        optimized: true,
        optimizationReason: optimization.reason,
      })
    }

    // Step 2: Route the request through the appropriate provider
    // We handle z-ai requests directly (using the same pattern as /api/chat)
    // and OpenRouter requests via fetch to the OpenRouter API
    const model = getModelForTier(tier as ModelTier)
    const startTime = Date.now()
    let response: string

    try {
      if (model.provider === 'z-ai') {
        // Use z-ai SDK directly (same pattern as /api/chat which works reliably)
        const ZAI = (await import('z-ai-web-dev-sdk')).default
        const zai = await ZAI.create()

        const systemMsg = systemPrompt
          ? [{ role: 'assistant' as const, content: systemPrompt }]
          : []
        const apiMessages = [
          ...systemMsg,
          ...messages.map(m => ({
            role: m.role === 'assistant' ? ('assistant' as const) : ('user' as const),
            content: m.content,
          })),
        ]

        const completion = await zai.chat.completions.create({
          messages: apiMessages,
          thinking: { type: 'disabled' },
        })

        response = completion.choices?.[0]?.message?.content || ''
      } else if (model.provider === 'openrouter') {
        // Use OpenRouter API via fetch
        const { getActiveKey, recordKeySuccess, recordKey429, recordKeyError } = await import('@/lib/api-key-manager')
        const apiKey = getActiveKey('openrouter')

        if (!apiKey) {
          // Fall back to z-ai if no OpenRouter key
          const ZAI = (await import('z-ai-web-dev-sdk')).default
          const zai = await ZAI.create()
          const apiMessages = messages.map(m => ({
            role: m.role === 'assistant' ? ('assistant' as const) : ('user' as const),
            content: m.content,
          }))
          const completion = await zai.chat.completions.create({
            messages: [{ role: 'assistant' as const, content: systemPrompt || 'You are a helpful assistant.' }, ...apiMessages],
            thinking: { type: 'disabled' },
          })
          response = completion.choices?.[0]?.message?.content || ''
        } else {
          const systemMsg = systemPrompt
            ? [{ role: 'system' as const, content: systemPrompt }]
            : []
          const apiMessages = [
            ...systemMsg,
            ...messages.map(m => ({
              role: m.role === 'assistant' ? ('assistant' as const) : ('user' as const),
              content: m.content,
            })),
          ]

          const orResponse = await fetch('https://openrouter.ai/api/v1/chat/completions', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${apiKey}`,
              'Content-Type': 'application/json',
              'HTTP-Referer': 'https://nexus-os.dev',
              'X-Title': 'NEXUS OS v3.0',
            },
            body: JSON.stringify({
              model: model.actualModel,
              messages: apiMessages,
              max_tokens: maxTokens ?? 4096,
              temperature: temperature ?? 0.7,
            }),
          })

          if (orResponse.status === 429) {
            const retryAfter = parseInt(orResponse.headers.get('retry-after') ?? '60', 10)
            recordKey429('openrouter', retryAfter)
            return NextResponse.json(
              { error: `OpenRouter rate limited (429). Retry after ${retryAfter}s.`, providerStatus: 'degraded' },
              { status: 429 }
            )
          }

          if (!orResponse.ok) {
            const errorBody = await orResponse.text().catch(() => 'Unknown error')
            recordKeyError('openrouter', `${orResponse.status}: ${errorBody.slice(0, 200)}`)
            // Fall back to z-ai
            const ZAI = (await import('z-ai-web-dev-sdk')).default
            const zai = await ZAI.create()
            const fallbackMessages = messages.map(m => ({
              role: m.role === 'assistant' ? ('assistant' as const) : ('user' as const),
              content: m.content,
            }))
            const completion = await zai.chat.completions.create({
              messages: [{ role: 'assistant' as const, content: systemPrompt || 'You are a helpful assistant.' }, ...fallbackMessages],
              thinking: { type: 'disabled' },
            })
            response = completion.choices?.[0]?.message?.content || ''
          } else {
            const data = await orResponse.json()
            response = data.choices?.[0]?.message?.content || ''
            recordKeySuccess('openrouter')
          }
        }
      } else {
        return NextResponse.json({ error: `Unknown provider: ${model.provider}` }, { status: 500 })
      }

      const latencyMs = Date.now() - startTime

      // Update health tracking
      try {
        const { updateRouteHealth } = await import('@/lib/ai-provider-bridge')
        updateRouteHealth(model.id, true, latencyMs)
      } catch { /* health tracking is best-effort */ }

      return NextResponse.json({
        response,
        model: sanitizeModel(model),
        latencyMs,
        optimized: false,
      })
    } catch (error) {
      const latencyMs = Date.now() - startTime

      // Update health tracking on failure
      try {
        const { updateRouteHealth } = await import('@/lib/ai-provider-bridge')
        updateRouteHealth(model.id, false, latencyMs)
      } catch { /* health tracking is best-effort */ }

      throw error
    }
  } catch (error) {
    console.error('AI Bridge POST error:', error)

    const message = error instanceof Error ? error.message : 'Internal server error'
    const status = message.includes('rate limited') ? 429
      : message.includes('No API key') ? 503
      : message.includes('auth error') ? 503
      : message.includes('timed out') ? 504
      : 500

    return NextResponse.json(
      {
        error: message,
        providerStatus: message.includes('rate limited') || message.includes('API key')
          ? 'degraded'
          : 'unknown',
      },
      { status }
    )
  }
}

/** Sanitize model for client response (remove internal fields) */
function sanitizeModel(model: ModelRoute) {
  return {
    id: model.id,
    tier: model.tier,
    displayName: model.displayName,
    actualModel: model.actualModel,
    provider: model.provider,
    providerLabel: model.providerLabel,
    isFree: model.isFree,
    health: model.health,
    latencyMs: model.latencyMs,
    successRate: model.successRate,
    capabilities: model.capabilities,
    contextWindow: model.contextWindow,
  }
}
