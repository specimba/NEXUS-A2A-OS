import { db } from '@/lib/db'
import { audit, serializeConnection } from '@/lib/mcp'
import { Prisma } from '@prisma/client'
import { NextRequest, NextResponse } from 'next/server'

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const c = await db.mcpConnection.findUnique({ where: { id } })
    if (!c) return NextResponse.json({ error: 'Not found' }, { status: 404 })
    return NextResponse.json(serializeConnection(c))
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const body = await req.json()
    const data: Record<string, unknown> = {}
    if ('name' in body) data.name = body.name
    if ('endpoint' in body) data.endpoint = body.endpoint
    if ('transport' in body) data.transport = body.transport
    if ('autoReconnect' in body) data.autoReconnect = body.autoReconnect
    if ('enabled' in body) data.enabled = body.enabled
    if ('topicMap' in body) data.topicMap = JSON.stringify(body.topicMap ?? {})
    // apiKey is updated only when an explicit non-empty string is provided;
    // sending an empty string is treated as "clear the key".
    if ('apiKey' in body) data.apiKey = body.apiKey ? String(body.apiKey) : null

    try {
      const updated = await db.mcpConnection.update({ where: { id }, data })
      await audit('mcp.update', { target: id, metadata: { fields: Object.keys(data) } })
      return NextResponse.json(serializeConnection(updated))
    } catch (err) {
      if (err instanceof Prisma.PrismaClientKnownRequestError && err.code === 'P2025') {
        return NextResponse.json({ error: 'Not found' }, { status: 404 })
      }
      throw err
    }
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function DELETE(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    try {
      await db.mcpConnection.delete({ where: { id } })
    } catch (err) {
      if (err instanceof Prisma.PrismaClientKnownRequestError && err.code === 'P2025') {
        return NextResponse.json({ error: 'Not found' }, { status: 404 })
      }
      throw err
    }
    await audit('mcp.delete', { target: id })
    return NextResponse.json({ ok: true })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
