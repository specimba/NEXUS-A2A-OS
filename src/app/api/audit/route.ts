import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

// GET /api/audit?limit=50&action=mcp.
export async function GET(req: NextRequest) {
  try {
    const url = new URL(req.url)
    const limit = Math.min(parseInt(url.searchParams.get('limit') ?? '100', 10) || 100, 500)
    const actionPrefix = url.searchParams.get('action') ?? undefined

    const logs = await db.auditLog.findMany({
      where: actionPrefix ? { action: { startsWith: actionPrefix } } : {},
      orderBy: { createdAt: 'desc' },
      take: limit,
    })
    return NextResponse.json(
      logs.map((l) => ({
        id: l.id,
        actor: l.actor,
        action: l.action,
        target: l.target,
        metadata: safeJson(l.metadata),
        ip: l.ip,
        createdAt: l.createdAt.toISOString(),
      })),
    )
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

function safeJson(raw: string): unknown {
  try {
    return JSON.parse(raw)
  } catch {
    return raw
  }
}
