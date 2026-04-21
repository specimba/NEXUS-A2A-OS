import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

export async function GET() {
  try {
    const templates = await db.testTemplate.findMany({ orderBy: { createdAt: 'desc' } })
    const runs = await db.testRun.findMany({
      take: 20,
      orderBy: { createdAt: 'desc' },
      include: { template: true, agent: true },
    })
    return NextResponse.json({ templates, runs })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action, templateId, modelName, mode } = body

    if (action !== 'run_test') {
      return NextResponse.json(
        { error: `Unknown action: ${action}. Valid action: run_test` },
        { status: 400 }
      )
    }

    if (!templateId || !modelName || !mode) {
      return NextResponse.json(
        { error: 'Missing required fields: templateId, modelName, mode' },
        { status: 400 }
      )
    }

    const validModes = ['single', 'icl', 'agentic']
    if (!validModes.includes(mode)) {
      return NextResponse.json(
        { error: `Invalid mode: ${mode}. Valid modes: ${validModes.join(', ')}` },
        { status: 400 }
      )
    }

    const template = await db.testTemplate.findUnique({ where: { id: templateId } })
    if (!template) {
      return NextResponse.json({ error: 'Template not found' }, { status: 404 })
    }

    // Find an available agent for the test
    const agent = await db.agent.findFirst({
      where: { status: 'idle' },
      orderBy: { trustScore: 'desc' },
    })

    const testRun = await db.testRun.create({
      data: {
        templateId,
        agentId: agent?.id ?? null,
        modelName,
        mode,
        status: 'pending',
      },
      include: { template: true, agent: true },
    })

    return NextResponse.json({ testRun }, { status: 201 })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
