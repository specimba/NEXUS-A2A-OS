import { db } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const agents = await db.agent.findMany({ orderBy: { lastActive: 'desc' } })
    return NextResponse.json(agents)
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
