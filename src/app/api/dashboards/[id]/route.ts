import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

// ─── Single Dashboard Operations ───
// GET    /api/dashboards/[id] — Get dashboard with widgets
// PUT    /api/dashboards/[id] — Update dashboard
// DELETE /api/dashboards/[id] — Delete dashboard and all widgets (cascade)

interface RouteContext {
  params: Promise<{ id: string }>
}

export async function GET(
  _request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params

    const dashboard = await db.dashboard.findUnique({
      where: { id },
      include: { widgets: { orderBy: { order: 'asc' } } },
    })

    if (!dashboard) {
      return NextResponse.json({ error: 'Dashboard not found' }, { status: 404 })
    }

    const parsed = {
      ...dashboard,
      tags: dashboard.tags ? JSON.parse(dashboard.tags) : [],
      widgets: dashboard.widgets.map((w) => ({
        ...w,
        config: JSON.parse(w.config),
        gridPos: JSON.parse(w.gridPos),
      })),
    }

    return NextResponse.json({ dashboard: parsed })
  } catch (error) {
    console.error('Dashboard GET error:', error)
    return NextResponse.json({ error: 'Failed to fetch dashboard' }, { status: 500 })
  }
}

export async function PUT(
  request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params
    const body = await request.json()

    const existing = await db.dashboard.findUnique({ where: { id } })
    if (!existing) {
      return NextResponse.json({ error: 'Dashboard not found' }, { status: 404 })
    }

    const updateData: Record<string, unknown> = {}

    if (body.name !== undefined) updateData.name = body.name.trim()
    if (body.description !== undefined) updateData.description = body.description?.trim() || null
    if (body.layout !== undefined) updateData.layout = body.layout
    if (body.columns !== undefined) updateData.columns = body.columns
    if (body.isPublic !== undefined) updateData.isPublic = body.isPublic
    if (body.isDefault !== undefined) updateData.isDefault = body.isDefault
    if (body.tags !== undefined) updateData.tags = JSON.stringify(body.tags)

    const dashboard = await db.dashboard.update({
      where: { id },
      data: updateData,
      include: { widgets: { orderBy: { order: 'asc' } } },
    })

    const parsed = {
      ...dashboard,
      tags: dashboard.tags ? JSON.parse(dashboard.tags) : [],
      widgets: dashboard.widgets.map((w) => ({
        ...w,
        config: JSON.parse(w.config),
        gridPos: JSON.parse(w.gridPos),
      })),
    }

    return NextResponse.json({ dashboard: parsed })
  } catch (error) {
    console.error('Dashboard PUT error:', error)
    return NextResponse.json({ error: 'Failed to update dashboard' }, { status: 500 })
  }
}

export async function DELETE(
  _request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params

    const existing = await db.dashboard.findUnique({ where: { id } })
    if (!existing) {
      return NextResponse.json({ error: 'Dashboard not found' }, { status: 404 })
    }

    // Cascade delete will handle widgets automatically
    await db.dashboard.delete({ where: { id } })

    return NextResponse.json({ success: true, message: 'Dashboard and all widgets deleted' })
  } catch (error) {
    console.error('Dashboard DELETE error:', error)
    return NextResponse.json({ error: 'Failed to delete dashboard' }, { status: 500 })
  }
}
