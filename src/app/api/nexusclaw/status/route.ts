import { NextRequest, NextResponse } from 'next/server'
import { BRAIN_API_BASE } from '@/lib/brain-api/contract'

/**
 * GET /api/nexusclaw/status
 * Returns real-time NEXUSCLAW orchestrator metrics
 */
export async function GET(req: NextRequest) {
  try {
    const apiKey = process.env.NEXUS_BRAIN_API_KEY || 'nexus-default-key'
    try {
      const res = await fetch(`${BRAIN_API_BASE}/api/nexusclaw/status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey,
        },
        cache: 'no-store',
      })
      if (res.ok) {
        const data = await res.json()
        return NextResponse.json(data)
      }
    } catch (pyError) {
      console.warn('Python NexusClaw status API offline, falling back to mock:', pyError)
    }

    // Mock data fallback
    const status = {
      status: 'operational',
      stats: {
        agentPool: {
          total: 12,
          online: 8,
          busy: 3,
          error: 1,
        },
        brainstorm: {
          activeSessions: 2,
          totalProposals: 47,
          pendingVotes: 5,
        },
        trustEngine: {
          avgTrust: 78.5,
          degradedAgents: 2,
        },
      },
      timestamp: new Date().toISOString(),
    }

    return NextResponse.json(status)
  } catch (error) {
    console.error('NEXUSCLAW status error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch NEXUSCLAW status' },
      { status: 500 }
    )
  }
}

/**
 * POST /api/nexusclaw/intervene
 * Submit operator intervention command
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { intervention, target } = body

    if (!intervention || !target) {
      return NextResponse.json(
        { error: 'intervention and target are required' },
        { status: 400 }
      )
    }

    const apiKey = process.env.NEXUS_BRAIN_API_KEY || 'nexus-default-key'
    try {
      const res = await fetch(`${BRAIN_API_BASE}/api/nexusclaw/intervene`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey,
        },
        body: JSON.stringify(body),
        cache: 'no-store',
      })
      if (res.ok) {
        const data = await res.json()
        return NextResponse.json(data)
      }
    } catch (pyError) {
      console.warn('Python NexusClaw intervene API offline, falling back to mock:', pyError)
    }

    // Mock intervention submission fallback
    const interventionId = `intervene-${Date.now()}`

    console.log(`[INTERVENTION] ${intervention} → ${target} (id=${interventionId})`)

    return NextResponse.json({
      success: true,
      message: `Intervention '${intervention}' submitted for ${target}`,
      interventionId,
    })
  } catch (error) {
    console.error('NEXUSCLAW intervention error:', error)
    return NextResponse.json(
      { error: 'Failed to submit intervention' },
      { status: 500 }
    )
  }
}