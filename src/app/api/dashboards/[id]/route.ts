import { db } from '@/lib/db'
import { Prisma } from '@prisma/client'
import { NextRequest, NextResponse } from 'next/server'

// Minimum interval between lastViewed updates per dashboard (avoid write amplification
// since useApiData polls this endpoint every 15s).
const LAST_VIEWED_THROTTLE_MS = 60_000

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params
    const dashboard = await db.customDashboard.findUnique({
      where: { id },
      // Widgets are ordered by posY (the persisted layout index), with createdAt
      // as a stable tiebreaker for widgets that haven't been re-ordered yet.
      include: { widgets: { orderBy: [{ posY: 'asc' }, { createdAt: 'asc' }] } },
    })
    if (!dashboard) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }

    // Throttle lastViewed updates and return the fresh value when we do write.
    const now = Date.now()
    const sinceLastView = now - new Date(dashboard.lastViewed).getTime()
    if (sinceLastView >= LAST_VIEWED_THROTTLE_MS) {
      const updated = await db.customDashboard.update({
        where: { id },
        data: { lastViewed: new Date(now) },
        include: { widgets: { orderBy: [{ posY: 'asc' }, { createdAt: 'asc' }] } },
      })
      return NextResponse.json(updated)
    }
    return NextResponse.json(dashboard)
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params
    const body = await req.json()
    const data: Record<string, unknown> = {}
    if ('name' in body) data.name = body.name
    if ('description' in body) data.description = body.description
    if ('icon' in body) data.icon = body.icon
    if ('color' in body) data.color = body.color
    if ('isFavorite' in body) data.isFavorite = body.isFavorite
    if ('isPinned' in body) data.isPinned = body.isPinned
    if ('tags' in body) data.tags = JSON.stringify(body.tags ?? [])
    if ('sharedWith' in body) data.sharedWith = JSON.stringify(body.sharedWith ?? [])

    try {
      const updated = await db.customDashboard.update({
        where: { id },
        data,
        include: { widgets: { orderBy: [{ posY: 'asc' }, { createdAt: 'asc' }] } },
      })
      return NextResponse.json(updated)
    } catch (err) {
      if (
        err instanceof Prisma.PrismaClientKnownRequestError &&
        err.code === 'P2025'
      ) {
        return NextResponse.json({ error: 'Not found' }, { status: 404 })
      }
      throw err
    }
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params
    await db.customDashboard.delete({ where: { id } })
    return NextResponse.json({ success: true })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
