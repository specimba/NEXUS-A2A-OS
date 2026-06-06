import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params
    const body = await req.json()
    const data: Record<string, unknown> = {}
    if ('title' in body) data.title = body.title
    if ('subtitle' in body) data.subtitle = body.subtitle
    if ('type' in body) data.type = body.type
    if ('dataSource' in body) data.dataSource = body.dataSource
    if ('config' in body) data.config = JSON.stringify(body.config)
    if ('posX' in body) data.posX = body.posX
    if ('posY' in body) data.posY = body.posY
    if ('width' in body) data.width = body.width
    if ('height' in body) data.height = body.height

    const widget = await db.customWidget.update({ where: { id }, data })
    return NextResponse.json(widget)
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
    await db.customWidget.delete({ where: { id } })
    return NextResponse.json({ success: true })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
