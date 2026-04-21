import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

export async function GET() {
  try {
    const models = await db.modelEntry.findMany({ orderBy: { tier: 'desc' } })
    return NextResponse.json({ models })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action, modelId } = body

    if (!action || !modelId) {
      return NextResponse.json(
        { error: 'Missing required fields: action, modelId' },
        { status: 400 }
      )
    }

    const model = await db.modelEntry.findUnique({ where: { id: modelId } })
    if (!model) {
      return NextResponse.json({ error: 'Model not found' }, { status: 404 })
    }

    if (action === 'toggle') {
      const updated = await db.modelEntry.update({
        where: { id: modelId },
        data: { isActive: !model.isActive },
      })
      return NextResponse.json({ model: updated })
    }

    if (action === 'health_check') {
      const updated = await db.modelEntry.update({
        where: { id: modelId },
        data: { lastChecked: new Date() },
      })
      return NextResponse.json({ model: updated })
    }

    return NextResponse.json(
      { error: `Unknown action: ${action}. Valid actions: toggle, health_check` },
      { status: 400 }
    )
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
