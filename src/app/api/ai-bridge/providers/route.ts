import { NextRequest, NextResponse } from 'next/server'
import {
  getAllProviderStatuses,
  getProviderStatus,
  healthCheckProvider,
} from '@/lib/ai-provider-bridge'

/**
 * GET /api/ai-bridge/providers
 * Returns all provider statuses with health, rate limits, and model counts.
 */
export async function GET() {
  try {
    const providers = getAllProviderStatuses()

    const availableCount = providers.filter(p => p.isAvailable).length
    const totalProviders = providers.length

    return NextResponse.json({
      providers,
      summary: {
        totalProviders,
        available: availableCount,
        down: totalProviders - availableCount,
        overallHealth: providers.every(p => p.health === 'healthy')
          ? 'healthy'
          : providers.some(p => p.health === 'down')
            ? 'degraded'
            : 'unknown',
      },
    })
  } catch (error) {
    console.error('AI Bridge Providers GET error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * POST /api/ai-bridge/providers
 * Health check a specific provider by making a test request.
 *
 * Body: { provider: string }
 * Valid providers: 'z-ai', 'openrouter'
 *
 * Response: {
 *   provider: string,
 *   isAvailable: boolean,
 *   latencyMs: number,
 *   testedModel: string,
 *   error?: string,
 *   updatedStatus: ProviderStatus
 * }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { provider } = body as { provider: string }

    if (!provider) {
      return NextResponse.json(
        { error: 'Missing required field: provider' },
        { status: 400 }
      )
    }

    const validProviders = ['z-ai', 'openrouter']
    if (!validProviders.includes(provider)) {
      return NextResponse.json(
        {
          error: `Invalid provider: "${provider}". Valid providers: ${validProviders.join(', ')}`,
          validProviders,
        },
        { status: 400 }
      )
    }

    const healthResult = await healthCheckProvider(provider)
    const updatedStatus = getProviderStatus(provider)

    return NextResponse.json({
      ...healthResult,
      updatedStatus,
    })
  } catch (error) {
    console.error('AI Bridge Providers POST error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    )
  }
}
