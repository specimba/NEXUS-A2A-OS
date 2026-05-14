import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

// ─── Widget CRUD ───
// GET  /api/dashboards/[id]/widgets — List widgets for a dashboard
// POST /api/dashboards/[id]/widgets — Add a widget to a dashboard

interface RouteContext {
  params: Promise<{ id: string }>
}

export async function GET(
  _request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params

    const dashboard = await db.dashboard.findUnique({ where: { id } })
    if (!dashboard) {
      return NextResponse.json({ error: 'Dashboard not found' }, { status: 404 })
    }

    const widgets = await db.widget.findMany({
      where: { dashboardId: id },
      orderBy: { order: 'asc' },
    })

    const parsed = widgets.map((w) => ({
      ...w,
      config: JSON.parse(w.config),
      gridPos: JSON.parse(w.gridPos),
    }))

    return NextResponse.json({ widgets: parsed })
  } catch (error) {
    console.error('Widgets GET error:', error)
    return NextResponse.json({ error: 'Failed to fetch widgets' }, { status: 500 })
  }
}

export async function POST(
  request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params
    const body = await request.json()

    const dashboard = await db.dashboard.findUnique({ where: { id } })
    if (!dashboard) {
      return NextResponse.json({ error: 'Dashboard not found' }, { status: 404 })
    }

    const { type, title, subtitle, dataSource, config, gridPos, refreshMs } = body

    if (!type || typeof type !== 'string') {
      return NextResponse.json({ error: 'Widget type is required' }, { status: 400 })
    }
    if (!title || typeof title !== 'string') {
      return NextResponse.json({ error: 'Widget title is required' }, { status: 400 })
    }
    if (!dataSource || typeof dataSource !== 'string') {
      return NextResponse.json({ error: 'Widget dataSource is required' }, { status: 400 })
    }

    // Determine the next order value
    const maxOrderWidget = await db.widget.findFirst({
      where: { dashboardId: id },
      orderBy: { order: 'desc' },
      select: { order: true },
    })
    const nextOrder = (maxOrderWidget?.order ?? -1) + 1

    const widget = await db.widget.create({
      data: {
        dashboardId: id,
        type,
        title: title.trim(),
        subtitle: subtitle?.trim() || null,
        dataSource,
        config: config ? JSON.stringify(config) : '{}',
        gridPos: gridPos ? JSON.stringify(gridPos) : '{}',
        refreshMs: refreshMs || 30000,
        order: nextOrder,
      },
    })

    const parsed = {
      ...widget,
      config: JSON.parse(widget.config),
      gridPos: JSON.parse(widget.gridPos),
    }

    return NextResponse.json({ widget: parsed }, { status: 201 })
  } catch (error) {
    console.error('Widgets POST error:', error)
    return NextResponse.json({ error: 'Failed to create widget' }, { status: 500 })
  }
}
