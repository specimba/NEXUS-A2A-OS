import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

export async function GET() {
  try {
    const papers = await db.paper.findMany({ orderBy: { relevanceScore: 'desc' } })
    const p0 = papers.filter(p => p.priorityTier === 'P0')
    const p1 = papers.filter(p => p.priorityTier === 'P1')
    const p2 = papers.filter(p => p.priorityTier === 'P2')
    return NextResponse.json({ papers, p0, p1, p2, total: papers.length })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()
    const { paperId, updates } = body

    if (!paperId) {
      return NextResponse.json(
        { error: 'Missing required field: paperId' },
        { status: 400 }
      )
    }

    if (!updates || typeof updates !== 'object') {
      return NextResponse.json(
        { error: 'Missing required field: updates (object)' },
        { status: 400 }
      )
    }

    const paper = await db.paper.findUnique({ where: { id: paperId } })
    if (!paper) {
      return NextResponse.json({ error: 'Paper not found' }, { status: 404 })
    }

    // Build update data with only allowed fields
    const data: Record<string, unknown> = {}
    if (updates.priorityTier !== undefined) {
      const validTiers = ['P0', 'P1', 'P2']
      if (!validTiers.includes(updates.priorityTier)) {
        return NextResponse.json(
          { error: `Invalid priorityTier: ${updates.priorityTier}. Valid: ${validTiers.join(', ')}` },
          { status: 400 }
        )
      }
      data.priorityTier = updates.priorityTier
    }
    if (updates.isVetted !== undefined) {
      data.isVetted = Boolean(updates.isVetted)
    }
    if (updates.implementationTask !== undefined) {
      data.implementationTask = updates.implementationTask
    }

    const updated = await db.paper.update({
      where: { id: paperId },
      data,
    })

    return NextResponse.json({ paper: updated })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
