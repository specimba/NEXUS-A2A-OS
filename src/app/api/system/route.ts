import { db } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const agents = await db.agent.findMany()
    const models = await db.modelEntry.findMany()
    const templates = await db.testTemplate.findMany()
    const papers = await db.paper.findMany()
    const budget = await db.sessionBudget.findFirst({ where: { isActive: true } })
    const config = await db.systemConfig.findUnique({ where: { key: 'constitution' } })
    const state = await db.systemConfig.findUnique({ where: { key: 'nexus_state' } })

    return NextResponse.json({
      agents,
      models,
      templates,
      papers,
      budget,
      constitution: config?.value ? JSON.parse(config.value) : null,
      state: state?.value ? JSON.parse(state.value) : null,
    })
  } catch (error) {
    console.error('System API error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
