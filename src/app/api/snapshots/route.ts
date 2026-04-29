import { db } from '@/lib/db'
import { NextResponse } from 'next/server'

// GET /api/snapshots?type=health|token&hours=24&pillar=Engine
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const type = searchParams.get('type') // 'health' | 'token' | null (returns both)
    const hours = parseInt(searchParams.get('hours') ?? '24', 10)
    const pillar = searchParams.get('pillar') // filter by pillar (health only)

    const since = new Date(Date.now() - hours * 60 * 60 * 1000)

    if (type === 'health') {
      const where: Record<string, unknown> = { recordedAt: { gte: since } }
      if (pillar) {
        (where as { pillar?: string }).pillar = pillar
      }
      const snapshots = await db.healthSnapshot.findMany({
        where,
        orderBy: { recordedAt: 'desc' },
      })
      return NextResponse.json({ type: 'health', snapshots })
    }

    if (type === 'token') {
      const snapshots = await db.tokenSnapshot.findMany({
        where: { recordedAt: { gte: since } },
        orderBy: { recordedAt: 'desc' },
      })
      return NextResponse.json({ type: 'token', snapshots })
    }

    // No type specified: return both
    const [healthSnapshots, tokenSnapshots] = await Promise.all([
      db.healthSnapshot.findMany({
        where: pillar ? { recordedAt: { gte: since }, pillar } : { recordedAt: { gte: since } },
        orderBy: { recordedAt: 'desc' },
      }),
      db.tokenSnapshot.findMany({
        where: { recordedAt: { gte: since } },
        orderBy: { recordedAt: 'desc' },
      }),
    ])

    return NextResponse.json({
      health: healthSnapshots,
      token: tokenSnapshots,
    })
  } catch (error) {
    console.error('Snapshots GET error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

// POST /api/snapshots
// Body: { type: 'health' | 'token', data: {...} }
export async function POST(request: Request) {
  try {
    const body = await request.json()
    const { type, data } = body

    if (!type || !data) {
      return NextResponse.json({ error: 'Missing type or data' }, { status: 400 })
    }

    if (type === 'health') {
      const { pillar, health, status, metadata } = data
      if (!pillar || health === undefined || !status) {
        return NextResponse.json(
          { error: 'Health snapshot requires pillar, health, and status' },
          { status: 400 }
        )
      }
      const snapshot = await db.healthSnapshot.create({
        data: {
          pillar,
          health: Number(health),
          status,
          metadata: metadata ?? null,
        },
      })
      return NextResponse.json({ type: 'health', snapshot }, { status: 201 })
    }

    if (type === 'token') {
      const { totalBudget, usedBudget, remainingBudget, tokensLastHour, burnRate, topModel, topAgent } = data
      if (totalBudget === undefined || usedBudget === undefined || remainingBudget === undefined || tokensLastHour === undefined || burnRate === undefined) {
        return NextResponse.json(
          { error: 'Token snapshot requires totalBudget, usedBudget, remainingBudget, tokensLastHour, and burnRate' },
          { status: 400 }
        )
      }
      const snapshot = await db.tokenSnapshot.create({
        data: {
          totalBudget: Number(totalBudget),
          usedBudget: Number(usedBudget),
          remainingBudget: Number(remainingBudget),
          tokensLastHour: Number(tokensLastHour),
          burnRate: Number(burnRate),
          topModel: topModel ?? null,
          topAgent: topAgent ?? null,
        },
      })
      return NextResponse.json({ type: 'token', snapshot }, { status: 201 })
    }

    return NextResponse.json({ error: 'Invalid type. Must be "health" or "token"' }, { status: 400 })
  } catch (error) {
    console.error('Snapshots POST error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
