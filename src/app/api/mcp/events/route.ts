import { db } from '@/lib/db'
import { serializeEvent } from '@/lib/mcp'
import { NextRequest, NextResponse } from 'next/server'

const MAX_EVENT_SEARCH_LENGTH = 120

// GET /api/mcp/events?connectionId=&level=&since=&limit=
export async function GET(req: NextRequest) {
  try {
    const url = new URL(req.url)
    const connectionId = url.searchParams.get('connectionId') ?? undefined
    const level = url.searchParams.get('level') ?? undefined
    const since = url.searchParams.get('since')
    const limit = Math.min(parseInt(url.searchParams.get('limit') ?? '100', 10) || 100, 500)
    const searchInput = url.searchParams.get('q')?.trim() || undefined
    const search = searchInput?.slice(0, MAX_EVENT_SEARCH_LENGTH)

    const where: Record<string, unknown> = {}
    if (connectionId) where.connectionId = connectionId
    if (level && ['info', 'warn', 'error', 'debug'].includes(level)) where.level = level
    if (since) where.occurredAt = { gt: new Date(since) }
    if (search) {
      where.OR = [
        { topic: { contains: search } },
        { payload: { contains: search } },
      ]
    }

    const events = await db.mcpEvent.findMany({
      where,
      include: { connection: { select: { name: true } } },
      orderBy: { occurredAt: 'desc' },
      take: limit,
    })
    return NextResponse.json(events.map(serializeEvent))
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

// POST /api/mcp/events  → server-side event ingestion. Used by simulators,
// edge functions, and the client MCP library to push events into the log.
export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { connectionId, topic, level = 'info', payload = {} } = body as {
      connectionId?: string
      topic?: string
      level?: 'info' | 'warn' | 'error' | 'debug'
      payload?: unknown
    }
    if (!connectionId || !topic) {
      return NextResponse.json({ error: 'connectionId and topic are required' }, { status: 400 })
    }

    const conn = await db.mcpConnection.findUnique({ where: { id: connectionId } })
    if (!conn) return NextResponse.json({ error: 'Unknown connectionId' }, { status: 404 })

    const created = await db.mcpEvent.create({
      data: {
        connectionId,
        topic,
        level,
        payload: JSON.stringify(payload),
      },
      include: { connection: { select: { name: true } } },
    })
    // Update rolling stats on the parent connection.
    await db.mcpConnection.update({
      where: { id: connectionId },
      data: {
        lastEventAt: created.occurredAt,
        totalEvents: { increment: 1 },
        ...(level === 'error' ? { errorCount: { increment: 1 } } : {}),
      },
    })
    return NextResponse.json(serializeEvent(created), { status: 201 })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
