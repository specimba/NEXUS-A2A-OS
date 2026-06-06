import { NextRequest, NextResponse } from 'next/server'
import { PrismaClient } from '@prisma/client'

// Use a fresh PrismaClient to avoid stale cache issues during development
const globalForPrisma = globalThis as unknown as {
  feedbackPrisma: PrismaClient | undefined
}

const db = globalForPrisma.feedbackPrisma ?? new PrismaClient({ log: ['query'] })
if (process.env.NODE_ENV !== 'production') globalForPrisma.feedbackPrisma = db

// ─── Compute trend from recent ratings ────────────────────────────────────────
function computeTrend(ratings: number[]): 'improving' | 'declining' | 'stable' {
  if (ratings.length < 3) return 'stable'

  // Split into two halves: older and recent
  const mid = Math.floor(ratings.length / 2)
  const older = ratings.slice(0, mid)
  const recent = ratings.slice(mid)

  const avgOlder = older.reduce((a, b) => a + b, 0) / older.length
  const avgRecent = recent.reduce((a, b) => a + b, 0) / recent.length

  const diff = avgRecent - avgOlder
  if (diff > 0.3) return 'improving'
  if (diff < -0.3) return 'declining'
  return 'stable'
}

// ─── GET: Fetch all feedback with computed stats ──────────────────────────────
export async function GET() {
  try {
    const feedback = await db.agentFeedback.findMany({
      include: { agent: { select: { id: true, name: true, type: true, domain: true, status: true } } },
      orderBy: { createdAt: 'desc' },
    })

    // Compute per-agent stats
    const agentMap = new Map<string, {
      agentId: string
      agentName: string
      agentType: string
      agentDomain: string | null
      agentStatus: string
      ratings: number[]
      categories: Record<string, number[]>
      latestTrend: string
    }>()

    for (const fb of feedback) {
      const existing = agentMap.get(fb.agentId)
      if (existing) {
        existing.ratings.push(fb.rating)
        if (!existing.categories[fb.category]) existing.categories[fb.category] = []
        existing.categories[fb.category].push(fb.rating)
        existing.latestTrend = fb.trend
      } else {
        agentMap.set(fb.agentId, {
          agentId: fb.agentId,
          agentName: fb.agent.name,
          agentType: fb.agent.type,
          agentDomain: fb.agent.domain,
          agentStatus: fb.agent.status,
          ratings: [fb.rating],
          categories: { [fb.category]: [fb.rating] },
          latestTrend: fb.trend,
        })
      }
    }

    // Build agent stats
    const agentStats = Array.from(agentMap.values()).map((entry) => {
      const avgRating = entry.ratings.reduce((a, b) => a + b, 0) / entry.ratings.length
      const computedTrend = computeTrend(entry.ratings)

      // Category breakdown
      const categoryBreakdown: Record<string, { avg: number; count: number }> = {}
      for (const [cat, ratings] of Object.entries(entry.categories)) {
        categoryBreakdown[cat] = {
          avg: ratings.reduce((a, b) => a + b, 0) / ratings.length,
          count: ratings.length,
        }
      }

      // Alignment recommendation
      const recommendation = computedTrend === 'declining'
        ? 'Attention needed: Performance declining. Consider reassigning tasks or reviewing recent errors.'
        : computedTrend === 'improving'
          ? 'Positive trajectory: Agent is improving. Consider promoting to higher-trust lanes.'
          : 'Stable performance. Continue monitoring.'

      return {
        agentId: entry.agentId,
        agentName: entry.agentName,
        agentType: entry.agentType,
        agentDomain: entry.agentDomain,
        agentStatus: entry.agentStatus,
        avgRating: Math.round(avgRating * 100) / 100,
        totalFeedback: entry.ratings.length,
        trend: computedTrend,
        storedTrend: entry.latestTrend,
        categoryBreakdown,
        recommendation,
      }
    })

    // Overall stats
    const allRatings = feedback.map((f) => f.rating)
    const globalAvg = allRatings.length > 0
      ? Math.round((allRatings.reduce((a, b) => a + b, 0) / allRatings.length) * 100) / 100
      : 0

    // Category radar data (aggregate across all agents)
    const globalCategories: Record<string, number[]> = {}
    for (const fb of feedback) {
      if (!globalCategories[fb.category]) globalCategories[fb.category] = []
      globalCategories[fb.category].push(fb.rating)
    }
    const categoryRadar = Object.entries(globalCategories).map(([cat, ratings]) => ({
      category: cat,
      avgRating: Math.round((ratings.reduce((a, b) => a + b, 0) / ratings.length) * 100) / 100,
      count: ratings.length,
    }))

    // Alignment alerts: agents with declining trends
    const alignmentAlerts = agentStats
      .filter((a) => a.trend === 'declining')
      .map((a) => ({
        agentId: a.agentId,
        agentName: a.agentName,
        avgRating: a.avgRating,
        recommendation: a.recommendation,
      }))

    return NextResponse.json({
      feedback,
      agentStats,
      globalAvg,
      categoryRadar,
      alignmentAlerts,
      totalFeedback: feedback.length,
    })
  } catch (error) {
    console.error('[Feedback API] GET error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch feedback data' },
      { status: 500 }
    )
  }
}

// ─── POST: Submit new feedback ────────────────────────────────────────────────
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { agentId, rating, category, comment } = body

    // Validate
    if (!agentId || !rating || !category) {
      return NextResponse.json(
        { error: 'Missing required fields: agentId, rating, category' },
        { status: 400 }
      )
    }

    const ratingNum = Number(rating)
    if (ratingNum < 1 || ratingNum > 5 || !Number.isInteger(ratingNum)) {
      return NextResponse.json(
        { error: 'Rating must be an integer between 1 and 5' },
        { status: 400 }
      )
    }

    const validCategories = ['quality', 'speed', 'alignment', 'reliability']
    if (!validCategories.includes(category)) {
      return NextResponse.json(
        { error: `Category must be one of: ${validCategories.join(', ')}` },
        { status: 400 }
      )
    }

    // Verify agent exists
    const agent = await db.agent.findUnique({ where: { id: agentId } })
    if (!agent) {
      return NextResponse.json(
        { error: 'Agent not found' },
        { status: 404 }
      )
    }

    // Compute trend from recent feedback for this agent
    const recentFeedback = await db.agentFeedback.findMany({
      where: { agentId },
      orderBy: { createdAt: 'desc' },
      take: 10,
    })

    const recentRatings = recentFeedback.map((f) => f.rating).reverse()
    recentRatings.push(ratingNum)
    const trend = computeTrend(recentRatings)

    // Save
    const newFeedback = await db.agentFeedback.create({
      data: {
        agentId,
        rating: ratingNum,
        category,
        comment: comment || null,
        trend,
      },
      include: { agent: { select: { id: true, name: true, type: true, domain: true, status: true } } },
    })

    return NextResponse.json({
      success: true,
      feedback: newFeedback,
      computedTrend: trend,
    }, { status: 201 })
  } catch (error) {
    console.error('[Feedback API] POST error:', error)
    return NextResponse.json(
      { error: 'Failed to submit feedback' },
      { status: 500 }
    )
  }
}
