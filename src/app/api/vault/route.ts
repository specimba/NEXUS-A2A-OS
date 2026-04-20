import { db } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const entries = await db.vaultEntry.findMany({
      take: 100,
      orderBy: { createdAt: 'desc' },
      include: { agent: { select: { name: true } } },
    })
    return NextResponse.json(entries)
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
