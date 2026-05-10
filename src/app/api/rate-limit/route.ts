import { NextRequest, NextResponse } from 'next/server'
import { checkRateLimit, recordRequest, enterCooldown, getAllRateLimitStatus, getRateLimitStatus, PROVIDER_RATE_LIMITS } from '@/lib/rate-limiter'

/**
 * Rate Limit API Route
 *
 * GET  /api/rate-limit — Get all provider rate limit statuses
 * GET  /api/rate-limit?provider=openrouter — Get specific provider status
 * POST /api/rate-limit — Check if a request is allowed (body: { provider, action: 'check' | 'record' | 'cooldown' })
 */

export async function GET(request: NextRequest) {
  try {
    const provider = request.nextUrl.searchParams.get('provider')

    if (provider) {
      const status = getRateLimitStatus(provider)
      return NextResponse.json({
        provider,
        ...status,
        limits: status.limits,
      })
    }

    // Return all provider statuses
    const allStatus = getAllRateLimitStatus()
    const summary = {
      total_providers: Object.keys(PROVIDER_RATE_LIMITS).length,
      providers_allowed: Object.values(allStatus).filter(s => s.allowed).length,
      providers_rate_limited: Object.values(allStatus).filter(s => !s.allowed).length,
      providers_in_cooldown: Object.values(allStatus).filter(s => s.isCooldown).length,
    }

    return NextResponse.json({
      summary,
      providers: allStatus,
    })
  } catch (error) {
    console.error('Rate Limit API error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { provider, action, retryAfterSeconds } = body

    if (!provider) {
      return NextResponse.json(
        { error: 'Missing required field: provider' },
        { status: 400 }
      )
    }

    switch (action) {
      case 'check': {
        const result = checkRateLimit(provider)
        return NextResponse.json({ provider, ...result })
      }
      case 'record': {
        recordRequest(provider)
        const result = checkRateLimit(provider)
        return NextResponse.json({ provider, recorded: true, ...result })
      }
      case 'cooldown': {
        enterCooldown(provider, retryAfterSeconds || 60)
        const result = checkRateLimit(provider)
        return NextResponse.json({ provider, cooldown: true, ...result })
      }
      default:
        return NextResponse.json(
          { error: `Invalid action: ${action}. Valid: check, record, cooldown` },
          { status: 400 }
        )
    }
  } catch (error) {
    console.error('Rate Limit API error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
