import { db } from '@/lib/db'
import { NextResponse } from 'next/server'

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
