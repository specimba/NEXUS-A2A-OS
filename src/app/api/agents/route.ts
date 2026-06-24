import { db } from '@/lib/db'
import { NextResponse } from 'next/server'
import { BRAIN_API_BASE } from '@/lib/brain-api/contract'

export async function GET() {
  try {
    const apiKey = process.env.NEXUS_BRAIN_API_KEY || 'nexus-default-key'
    try {
      const res = await fetch(`${BRAIN_API_BASE}/api/agents`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey,
        },
        cache: 'no-store',
      })
      if (res.ok) {
        const data = await res.json()
        return NextResponse.json(data)
      }
    } catch (pyError) {
      console.warn('Python Brain agents API offline, falling back to direct Prisma:', pyError)
    }

    const agents = await db.agent.findMany({ orderBy: { lastActive: 'desc' } })
    return NextResponse.json(agents)
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
