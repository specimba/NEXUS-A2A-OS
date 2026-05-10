import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

/**
 * Single Paper API (includes full LLM analysis)
 * GET /api/research/[id] — returns full paper data including llmAnalysis
 */

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const paper = await db.paper.findUnique({ where: { id } })
    if (!paper) {
      return NextResponse.json({ error: 'Paper not found' }, { status: 404 })
    }
    return NextResponse.json({ paper })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
