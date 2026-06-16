import { NextRequest, NextResponse } from 'next/server'

/**
 * GET /api/nexusclaw/status
 * Returns real-time NEXUSCLAW orchestrator metrics
 */
export async function GET(req: NextRequest) {
  try {
    // Mock data for now - will connect to Python backend
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

    // Mock intervention submission
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