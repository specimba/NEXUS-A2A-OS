import { db } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const decisions = await db.governorDecision.findMany({
      take: 50,
      orderBy: { createdAt: 'desc' },
      include: { agent: true },
    })
    const agents = await db.agent.findMany({
      select: { id: true, name: true, trustScore: true, tasksDone: true, tasksFailed: true },
    })
    return NextResponse.json({ decisions, agents })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
