import { db } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const models = await db.modelEntry.findMany({ orderBy: { tier: 'desc' } })
    return NextResponse.json(models)
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
