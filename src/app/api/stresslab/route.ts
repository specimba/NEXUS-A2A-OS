import { db } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const templates = await db.testTemplate.findMany({ orderBy: { createdAt: 'desc' } })
    const runs = await db.testRun.findMany({
      take: 20,
      orderBy: { createdAt: 'desc' },
      include: { template: true, agent: true },
    })
    return NextResponse.json({ templates, runs })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
