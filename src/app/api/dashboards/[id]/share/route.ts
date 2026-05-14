import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'
import crypto from 'crypto'

// ─── Share Dashboard ───
// POST /api/dashboards/[id]/share — Generate a share token for the dashboard
// GET  /api/dashboards/[id]/share?token=xxx — Get shared dashboard by token

interface RouteContext {
  params: Promise<{ id: string }>
}

export async function POST(
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

    // Generate a unique share token if one doesn't exist
    let shareToken = dashboard.shareToken
    if (!shareToken) {
      shareToken = `dash_${crypto.randomBytes(16).toString('hex')}`
      await db.dashboard.update({
        where: { id },
        data: { shareToken, isPublic: true },
      })
    }

    const parsed = {
      ...dashboard,
      shareToken,
      tags: dashboard.tags ? JSON.parse(dashboard.tags) : [],
      widgets: dashboard.widgets.map((w) => ({
        ...w,
        config: JSON.parse(w.config),
        gridPos: JSON.parse(w.gridPos),
      })),
    }

    return NextResponse.json({
      shareToken,
      shareUrl: `/shared?token=${shareToken}`,
      dashboard: parsed,
    })
  } catch (error) {
    console.error('Share POST error:', error)
    return NextResponse.json({ error: 'Failed to generate share token' }, { status: 500 })
  }
}

export async function GET(
  request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params
    const { searchParams } = new URL(request.url)
    const token = searchParams.get('token')

    if (!token) {
      return NextResponse.json({ error: 'Share token is required (?token=xxx)' }, { status: 400 })
    }

    // Find dashboard by share token — verify the id matches too
    const dashboard = await db.dashboard.findFirst({
      where: { id, shareToken: token, isPublic: true },
      include: { widgets: { orderBy: { order: 'asc' } } },
    })

    if (!dashboard) {
      return NextResponse.json({ error: 'Invalid or expired share link' }, { status: 404 })
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
    console.error('Share GET error:', error)
    return NextResponse.json({ error: 'Failed to fetch shared dashboard' }, { status: 500 })
  }
}
