import { db } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const budget = await db.sessionBudget.findFirst({ where: { isActive: true } })
    const usageLogs = await db.tokenUsageLog.findMany({
      take: 100,
      orderBy: { createdAt: 'desc' },
    })
    const agents = await db.agent.findMany({
      select: { name: true, totalTokens: true },
    })
    return NextResponse.json({ budget, usageLogs, agentUsage: agents })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
