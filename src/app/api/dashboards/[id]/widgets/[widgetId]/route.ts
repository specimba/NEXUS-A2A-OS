import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

// ─── Single Widget Operations ───
// PUT    /api/dashboards/[id]/widgets/[widgetId] — Update widget
// DELETE /api/dashboards/[id]/widgets/[widgetId] — Delete widget

interface RouteContext {
  params: Promise<{ id: string; widgetId: string }>
}

export async function PUT(
  request: NextRequest,
  context: RouteContext
) {
  try {
    const { id, widgetId } = await context.params
    const body = await request.json()

    // Verify dashboard exists
    const dashboard = await db.dashboard.findUnique({ where: { id } })
    if (!dashboard) {
      return NextResponse.json({ error: 'Dashboard not found' }, { status: 404 })
    }

    // Verify widget exists and belongs to this dashboard
    const existing = await db.widget.findFirst({
      where: { id: widgetId, dashboardId: id },
    })
    if (!existing) {
      return NextResponse.json({ error: 'Widget not found' }, { status: 404 })
    }

    const updateData: Record<string, unknown> = {}

    if (body.type !== undefined) updateData.type = body.type
    if (body.title !== undefined) updateData.title = body.title.trim()
    if (body.subtitle !== undefined) updateData.subtitle = body.subtitle?.trim() || null
    if (body.dataSource !== undefined) updateData.dataSource = body.dataSource
    if (body.config !== undefined) updateData.config = JSON.stringify(body.config)
    if (body.gridPos !== undefined) updateData.gridPos = JSON.stringify(body.gridPos)
    if (body.refreshMs !== undefined) updateData.refreshMs = body.refreshMs
    if (body.isCollapsed !== undefined) updateData.isCollapsed = body.isCollapsed
    if (body.order !== undefined) updateData.order = body.order

    const widget = await db.widget.update({
      where: { id: widgetId },
      data: updateData,
    })

    const parsed = {
      ...widget,
      config: JSON.parse(widget.config),
      gridPos: JSON.parse(widget.gridPos),
    }

    return NextResponse.json({ widget: parsed })
  } catch (error) {
    console.error('Widget PUT error:', error)
    return NextResponse.json({ error: 'Failed to update widget' }, { status: 500 })
  }
}

export async function DELETE(
  _request: NextRequest,
  context: RouteContext
) {
  try {
    const { id, widgetId } = await context.params

    // Verify widget exists and belongs to this dashboard
    const existing = await db.widget.findFirst({
      where: { id: widgetId, dashboardId: id },
    })
    if (!existing) {
      return NextResponse.json({ error: 'Widget not found' }, { status: 404 })
    }

    await db.widget.delete({ where: { id: widgetId } })

    return NextResponse.json({ success: true, message: 'Widget deleted' })
  } catch (error) {
    console.error('Widget DELETE error:', error)
    return NextResponse.json({ error: 'Failed to delete widget' }, { status: 500 })
  }
}
