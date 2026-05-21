import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params
    const body = await req.json()
    const {
      type,
      title,
      subtitle,
      dataSource,
      config = {},
      posX = 0,
      posY,
      width = 4,
      height = 2,
    } = body

    if (!type || !title || !dataSource) {
      return NextResponse.json(
        { error: 'type, title, and dataSource are required' },
        { status: 400 },
      )
    }
    if (![posX, width, height].every(isNonNegativeNumber)) {
      return NextResponse.json(
        { error: 'posX, width, and height must be non-negative numbers' },
        { status: 400 },
      )
    }
    if (posY !== undefined && !isNonNegativeNumber(posY)) {
      return NextResponse.json({ error: 'posY must be a non-negative number' }, { status: 400 })
    }

    // Auto-assign posY (used as the layout order index) so new widgets land at
    // the end of the canvas in a stable position. `posX` defaults to 0.
    const last = await db.customWidget.findFirst({
      where: { dashboardId: id },
      orderBy: { posY: 'desc' },
      select: { posY: true },
    })
    const nextPosY = posY === undefined ? (last ? last.posY + 1 : 0) : posY

    const widget = await db.customWidget.create({
      data: {
        dashboardId: id,
        type,
        title,
        subtitle: subtitle ?? null,
        dataSource,
        config: JSON.stringify(config),
        posX,
        posY: nextPosY,
        width,
        height,
      },
    })
    return NextResponse.json(widget)
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

// Batch update layout (PATCH /api/dashboards/[id]/widgets with { layout: [{id,posX,posY,width,height}] })
// All updates run in a single transaction and are scoped to the dashboard in the
// URL so widget IDs from other dashboards cannot be modified through this endpoint.
export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params
    const body = await req.json()
    const layout = body.layout as Array<{
      id: string
      posX?: number
      posY?: number
      width?: number
      height?: number
    }>
    if (!Array.isArray(layout)) {
      return NextResponse.json({ error: 'layout array required' }, { status: 400 })
    }
    if (!layout.every(isValidLayoutPatch)) {
      return NextResponse.json(
        { error: 'layout entries must include id and non-negative numeric positions/sizes' },
        { status: 400 },
      )
    }
    const results = await db.$transaction(
      layout.map((w) =>
        // updateMany lets us filter by both id and dashboardId; mismatches are
        // rejected below instead of corrupting widgets on other dashboards.
        db.customWidget.updateMany({
          where: { id: w.id, dashboardId: id },
          data: {
            ...(w.posX !== undefined && { posX: w.posX }),
            ...(w.posY !== undefined && { posY: w.posY }),
            ...(w.width !== undefined && { width: w.width }),
            ...(w.height !== undefined && { height: w.height }),
          },
        }),
      ),
    )
    if (results.some((result) => result.count !== 1)) {
      return NextResponse.json(
        { error: 'layout contains unknown or cross-dashboard widget ids' },
        { status: 409 },
      )
    }
    const dashboard = await db.customDashboard.findUnique({
      where: { id },
      include: { widgets: { orderBy: [{ posY: 'asc' }, { createdAt: 'asc' }] } },
    })
    return NextResponse.json(dashboard)
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

function isNonNegativeNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0
}

function isValidLayoutPatch(value: unknown): value is {
  id: string
  posX?: number
  posY?: number
  width?: number
  height?: number
} {
  if (!value || typeof value !== 'object') return false
  const entry = value as {
    id?: unknown
    posX?: unknown
    posY?: unknown
    width?: unknown
    height?: unknown
  }
  return (
    typeof entry.id === 'string' &&
    entry.id.length > 0 &&
    [entry.posX, entry.posY, entry.width, entry.height]
      .filter((item) => item !== undefined)
      .every(isNonNegativeNumber)
  )
}
