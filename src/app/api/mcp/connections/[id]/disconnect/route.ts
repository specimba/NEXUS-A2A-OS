import { db } from '@/lib/db'
import { audit, serializeConnection } from '@/lib/mcp'
import { NextRequest, NextResponse } from 'next/server'

export async function POST(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const conn = await db.mcpConnection.findUnique({ where: { id } })
    if (!conn) return NextResponse.json({ error: 'Not found' }, { status: 404 })

    const updated = await db.mcpConnection.update({
      where: { id },
      data: { status: 'disconnected' },
    })
    await db.mcpEvent.create({
      data: {
        connectionId: id,
        topic: 'connection.closed',
        level: 'info',
        payload: JSON.stringify({ reason: 'user_initiated' }),
      },
    })
    await audit('mcp.disconnect', { target: id })
    return NextResponse.json(serializeConnection(updated))
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
