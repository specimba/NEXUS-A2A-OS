import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

export async function GET() {
  try {
    const dashboards = await db.customDashboard.findMany({
      include: { widgets: { orderBy: { createdAt: 'asc' } } },
      orderBy: [{ isPinned: 'desc' }, { lastViewed: 'desc' }],
    })
    return NextResponse.json(dashboards)
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const {
      name,
      description,
      icon = 'layout-dashboard',
      color = 'emerald',
      tags = [],
      cloneFromId,
    } = body

    if (!name || typeof name !== 'string') {
      return NextResponse.json({ error: 'name is required' }, { status: 400 })
    }

    const created = await db.customDashboard.create({
      data: {
        name,
        description: description ?? null,
        icon,
        color,
        tags: JSON.stringify(tags),
      },
    })

    // Optional clone: copy widgets from existing dashboard
    if (cloneFromId) {
      const source = await db.customDashboard.findUnique({
        where: { id: cloneFromId },
        include: { widgets: true },
      })
      if (source) {
        await db.customWidget.createMany({
          data: source.widgets.map((w) => ({
            dashboardId: created.id,
            type: w.type,
            title: w.title,
            subtitle: w.subtitle,
            dataSource: w.dataSource,
            config: w.config,
            posX: w.posX,
            posY: w.posY,
            width: w.width,
            height: w.height,
          })),
        })
      }
    }

    const full = await db.customDashboard.findUnique({
      where: { id: created.id },
      include: { widgets: true },
    })
    return NextResponse.json(full)
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
